from __future__ import annotations

"""Parallel document-level runner for CPU speedup.

Does not change SapBERT / NER model internals. Each worker loads its own
pipeline and processes a disjoint shard of notes. Use the same worker count
for same-env v7 and v8 comparisons.
"""

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    from modules.pipelines.factory import NER_MODEL_CHOICES, available_pipelines

    p = argparse.ArgumentParser(description="Parallel pipeline runner (document shards).")
    p.add_argument("--pipeline", choices=available_pipelines(), required=True)
    p.add_argument("--model", choices=NER_MODEL_CHOICES, default="vihealthbert")
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "v_dataset" / "var" / "test")
    p.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "output")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="If set, write submission/trace/base_v7_snapshot directly under this dir "
        "(same layout as run_pipeline.py --output-dir).",
    )
    p.add_argument("--run-name", type=str, default=None)
    p.add_argument("--version-name", type=str, default=None)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--threads-per-worker", type=int, default=4)
    p.add_argument("--skip-existing", action="store_true", default=True)
    p.add_argument("--no-skip-existing", action="store_false", dest="skip_existing")
    p.add_argument("--trace", action="store_true", default=True)
    p.add_argument("--no-trace", action="store_false", dest="trace")
    p.add_argument("--indent", type=int, default=4)
    p.add_argument("--samples", type=int, default=None)
    return p.parse_args()


def _worker(payload: dict) -> dict:
    """Process one shard of files in an isolated process."""
    # Limit BLAS / torch intra-op threads so workers do not oversubscribe.
    threads = str(payload["threads_per_worker"])
    os.environ["OMP_NUM_THREADS"] = threads
    os.environ["MKL_NUM_THREADS"] = threads
    os.environ["OPENBLAS_NUM_THREADS"] = threads
    os.environ["NUMEXPR_NUM_THREADS"] = threads
    os.environ["TORCH_NUM_THREADS"] = threads
    # Keep CPU-only unless caller exported CUDA_VISIBLE_DEVICES.
    try:
        import torch

        torch.set_num_threads(int(threads))
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    from modules.components.formatting.competition_json import CompetitionJSONFormatter
    from modules.core.schemas import Document
    from modules.pipelines.factory import build_pipeline

    pipeline = build_pipeline(payload["pipeline"], model_name=payload["model"])
    formatter = CompetitionJSONFormatter(
        include_empty_candidates_for_linkable_types=True
    )
    submission_dir = Path(payload["submission_dir"])
    trace_dir = Path(payload["trace_dir"]) if payload["trace_dir"] else None
    base_v7_dir = Path(payload["base_v7_dir"]) if payload.get("base_v7_dir") else None
    indent = None if payload["indent"] == 0 else payload["indent"]

    done = 0
    skipped = 0
    errors: list[str] = []
    for rel in payload["files"]:
        file_path = Path(rel)
        out_json = submission_dir / f"{file_path.stem}.json"
        if payload["skip_existing"] and out_json.exists() and out_json.stat().st_size > 0:
            skipped += 1
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
            document = Document(doc_id=file_path.stem, text=text)
            entities = pipeline.process_document(document)
            output = formatter.format(entities)
            out_json.write_text(
                json.dumps(output, ensure_ascii=False, indent=indent),
                encoding="utf-8",
            )
            if base_v7_dir is not None:
                base_entities = document.metadata.get("base_v7_entities")
                if base_entities is None:
                    raise RuntimeError(
                        f"{payload['pipeline']} missing base_v7_entities for {file_path.stem}"
                    )
                (base_v7_dir / f"{file_path.stem}.json").write_text(
                    json.dumps(base_entities, ensure_ascii=False, indent=indent),
                    encoding="utf-8",
                )
            if payload["trace"] and trace_dir is not None and "trace_txt" in document.metadata:
                (trace_dir / f"{file_path.stem}_trace.txt").write_text(
                    document.metadata["trace_txt"],
                    encoding="utf-8",
                )
            done += 1
        except Exception as exc:  # noqa: BLE001 - isolate worker failures
            errors.append(f"{file_path.stem}: {exc}")
    return {
        "worker": payload["worker_id"],
        "done": done,
        "skipped": skipped,
        "errors": errors,
    }


def main() -> None:
    args = parse_args()
    if args.output_dir is not None:
        run_dir = args.output_dir
    else:
        if not args.run_name:
            raise SystemExit("Provide --run-name or --output-dir")
        version_name = args.version_name or args.pipeline
        run_dir = args.output_root / version_name / args.run_name
    submission_dir = run_dir / "submission"
    trace_dir = run_dir / "trace" if args.trace else None
    base_v7_dir: Path | None = None
    if args.pipeline in {"v9_llm_recall", "v10_llm_conflict_resolution"}:
        base_v7_dir = run_dir / "base_v7_snapshot"
    submission_dir.mkdir(parents=True, exist_ok=True)
    if trace_dir is not None:
        trace_dir.mkdir(parents=True, exist_ok=True)
    if base_v7_dir is not None:
        base_v7_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input_dir.glob("*.txt"))
    if args.samples is not None:
        files = files[: args.samples]
    if args.skip_existing:
        pending = [
            f
            for f in files
            if not (submission_dir / f"{f.stem}.json").exists()
            or (submission_dir / f"{f.stem}.json").stat().st_size == 0
        ]
    else:
        pending = list(files)

    print(
        f"Parallel run: pipeline={args.pipeline} workers={args.workers} "
        f"threads/worker={args.threads_per_worker}"
    )
    print(f"Total files={len(files)} pending={len(pending)} skip_existing={args.skip_existing}")
    print(f"Submission -> {submission_dir}")
    if base_v7_dir is not None:
        print(f"Base v7    -> {base_v7_dir}")
    if not pending:
        print("Nothing to do.")
        return

    shards: list[list[Path]] = [[] for _ in range(args.workers)]
    for i, f in enumerate(pending):
        shards[i % args.workers].append(f)

    payloads = []
    for wid, shard in enumerate(shards):
        if not shard:
            continue
        payloads.append(
            {
                "worker_id": wid,
                "pipeline": args.pipeline,
                "model": args.model,
                "files": [str(p) for p in shard],
                "submission_dir": str(submission_dir),
                "trace_dir": str(trace_dir) if trace_dir else None,
                "base_v7_dir": str(base_v7_dir) if base_v7_dir else None,
                "trace": args.trace,
                "indent": args.indent,
                "skip_existing": args.skip_existing,
                "threads_per_worker": args.threads_per_worker,
            }
        )

    results = []
    with ProcessPoolExecutor(max_workers=len(payloads)) as ex:
        futs = {ex.submit(_worker, p): p["worker_id"] for p in payloads}
        with tqdm(total=len(pending), desc=f"{args.pipeline} parallel") as bar:
            # Progress is approximate (updated per finished worker).
            finished_files = 0
            for fut in as_completed(futs):
                res = fut.result()
                results.append(res)
                finished_files += res["done"] + res["skipped"]
                bar.update(res["done"] + res["skipped"])
                if res["errors"]:
                    print(f"Worker {res['worker']} errors: {res['errors'][:3]}")

    total_done = sum(r["done"] for r in results)
    total_skip = sum(r["skipped"] for r in results)
    total_err = sum(len(r["errors"]) for r in results)
    n_json = len(list(submission_dir.glob("*.json")))
    print(f"Done. newly_written={total_done} skipped={total_skip} errors={total_err}")
    print(f"Submission JSON count: {n_json}")
    if trace_dir is not None:
        print(f"Trace count: {len(list(trace_dir.glob('*_trace.txt')))}")
    if total_err:
        raise SystemExit(1)


if __name__ == "__main__":
    # Required for CUDA/fork safety on some platforms; we stay CPU-oriented.
    main()

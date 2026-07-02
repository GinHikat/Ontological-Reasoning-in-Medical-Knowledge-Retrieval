import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

# Setup paths
script_dir = Path(__file__).resolve().parent
var_dir = script_dir.parents[2] # VAR/
project_root = var_dir.parent   # Thesis/
sys.path.append(str(project_root))

from VAR.modules.utils import EntityExtractor

def load_dictionaries():
    """Load the pre-computed dictionaries and their embeddings."""
    diag_csv = var_dir / "data" / "viettel" / "base" / "short_diagnosis.csv"
    drug_csv = var_dir / "data" / "viettel" / "base" / "short_drug.csv"
    
    diag_npy = var_dir / "data" / "viettel" / "base" / "short_diagnosis.npy"
    drug_npy = var_dir / "data" / "viettel" / "base" / "short_drug.npy"
    
    df_diag = pd.read_csv(diag_csv) if diag_csv.exists() else pd.DataFrame()
    df_drug = pd.read_csv(drug_csv) if drug_csv.exists() else pd.DataFrame()
    
    diag_embs = np.load(diag_npy) if diag_npy.exists() else np.array([])
    drug_embs = np.load(drug_npy) if drug_npy.exists() else np.array([])
        
    return df_diag, diag_embs, df_drug, drug_embs

def run_pipeline(samples: int = None):
    print("Loading models and dictionaries...")
    df_diag, diag_embs, df_drug, drug_embs = load_dictionaries()
    
    extractor = EntityExtractor(mode='ner + retrieval')
    ner_model = extractor._get_ner_instance(lang="vi")
    
    # We use Vietnamese SapBERT for Diagnosis and English SapBERT for Drugs
    sapbert_vi = extractor._get_sapbert_instance(lang="vi")
    sapbert_en = extractor._get_sapbert_instance(lang="en")
    
    test_dir = var_dir / "data" / "var" / "test"
    output_dir = var_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping raw NER labels to final categories
    LABEL_MAP = {
        "Disease": "CHẨN_ĐOÁN",
        "Disease/Symptom": "CHẨN_ĐOÁN",
        "Condition": "CHẨN_ĐOÁN",
        "Drug": "THUỐC",
        "Medication": "THUỐC",
        "Chemical": "THUỐC",
        "Procedure": "TÊN_XÉT_NGHIỆM",
        "Test": "TÊN_XÉT_NGHIỆM"
    }

    test_files = list(test_dir.glob("*.txt"))
    if samples:
        test_files = test_files[:samples]
        
    print(f"Found {len(test_files)} test files to process.")
    
    for file_path in tqdm(test_files, desc="Processing Test Files"):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # 1. Perform NER
        # extract_entities returns list of dicts: {'term': ..., 'label': ..., 'offset': [start, end]}
        ner_results = ner_model.extract_entities(text)
        
        final_entities = []
        for ent in ner_results:
            raw_label = ent.get("label", "")
            mapped_type = LABEL_MAP.get(raw_label)
            
            # If the label is not one of the target ones, skip it
            if not mapped_type:
                continue
                
            term = ent.get("term", "")
            offset = ent.get("offset", [0, 0])
            candidates = []
            
            # 2. Compute Embeddings and Retrieval
            if mapped_type == "CHẨN_ĐOÁN" and not df_diag.empty and diag_embs.size > 0:
                # Embed with SapBERT Vietnamese
                emb = sapbert_vi.encode_text([term], show_progress=False)
                if emb.size > 0:
                    sims = cosine_similarity(emb, diag_embs)[0]
                    best_idx = np.argmax(sims)
                    best_id = str(df_diag.iloc[best_idx]['id'])
                    candidates = [best_id]
                    
            elif mapped_type == "THUỐC" and not df_drug.empty and drug_embs.size > 0:
                # Embed with SapBERT English
                emb = sapbert_en.encode_text([term], show_progress=False)
                if emb.size > 0:
                    sims = cosine_similarity(emb, drug_embs)[0]
                    best_idx = np.argmax(sims)
                    best_id = str(df_drug.iloc[best_idx]['rxcui'])
                    candidates = [best_id]
            
            # 3. Format Entity Output
            entity_output = {
                "text": term,
                "type": mapped_type,
                "assertions": [],
                "position": offset
            }
            
            # Candidates key is only present for Drug and Disease
            if mapped_type in ["CHẨN_ĐOÁN", "THUỐC"]:
                entity_output["candidates"] = candidates
                
            final_entities.append(entity_output)
            
        # Save JSON output
        out_json_path = output_dir / f"{file_path.stem}.json"
        with open(out_json_path, 'w', encoding='utf-8') as f:
            json.dump(final_entities, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run_pipeline()

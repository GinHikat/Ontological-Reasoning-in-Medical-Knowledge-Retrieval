import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import difflib

def get_lexical_similarity(str1, str2):
    if not str1 or not str2: return 0.0
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def get_best_row_lexical_sim(query, row):
    best_sim = 0.0
    for val in row.values:
        val_str = str(val)
        if not val_str or val_str == 'nan': continue
        if '|' in val_str:
            for syn in val_str.split('|'):
                sim = get_lexical_similarity(query, syn)
                if sim > best_sim: best_sim = sim
        else:
            sim = get_lexical_similarity(query, val_str)
            if sim > best_sim: best_sim = sim
    return best_sim

# Setup paths
script_dir = Path(__file__).resolve().parent
var_dir = script_dir.parents[1] # VAR/
project_root = var_dir.parent   # Thesis/
sys.path.append(str(var_dir))

from modules.utils import EntityExtractor

def load_dictionaries():
    """Load the pre-computed dictionaries and their embeddings."""
    diag_csv = var_dir / "v_dataset" / "viettel" / "base" / "short_diagnosis.csv"
    drug_csv = var_dir / "v_dataset" / "viettel" / "base" / "short_drug.csv"
    sym_csv = var_dir / "v_dataset" / "viettel" / "base" / "short_symptom.csv"
    
    diag_npy = var_dir / "v_dataset" / "viettel" / "base" / "short_diagnosis.npy"
    drug_npy = var_dir / "v_dataset" / "viettel" / "base" / "short_drug.npy"
    sym_npy = var_dir / "v_dataset" / "viettel" / "base" / "short_symptom.npy"
    
    df_diag = pd.read_csv(diag_csv) if diag_csv.exists() else pd.DataFrame()
    df_drug = pd.read_csv(drug_csv) if drug_csv.exists() else pd.DataFrame()
    df_sym = pd.read_csv(sym_csv) if sym_csv.exists() else pd.DataFrame()
    
    diag_embs = np.load(diag_npy) if diag_npy.exists() else np.array([])
    drug_embs = np.load(drug_npy) if drug_npy.exists() else np.array([])
    sym_embs = np.load(sym_npy) if sym_npy.exists() else np.array([])
        
    return df_diag, diag_embs, df_drug, drug_embs, df_sym, sym_embs

import re
def get_section_boundaries(text):
    """Returns the start character indices of the 3 main sections."""
    s1_match = re.search(r'1\.\s+(Tiền sử bệnh|Tiền sử)', text)
    s2_match = re.search(r'2\.\s+(Tiền sử bệnh hiện tại|Bệnh sử hiện tại)', text)
    s3_match = re.search(r'3\.\s+Đánh giá tại bệnh viện', text)
    
    return {
        "s1": s1_match.start() if s1_match else -1,
        "s2": s2_match.start() if s2_match else len(text),
        "s3": s3_match.start() if s3_match else len(text)
    }

def check_assertions(text, start, end, boundaries):
    assertions = []
    
    # isHistorical: Check if inside Section 1
    if boundaries["s1"] != -1 and boundaries["s1"] <= start < boundaries["s2"]:
        assertions.append("isHistorical")
        
    line_start = text.rfind('\n', 0, start)
    line_start = 0 if line_start == -1 else line_start + 1
    line_end = text.find('\n', end)
    line_end = len(text) if line_end == -1 else line_end
    
    line_text = text[line_start:line_end].strip().lower()
    
    # Rule 1: Line starts with negation
    if line_text.startswith("- không") or line_text.startswith("không "):
        assertions.append("isNegated")
        return assertions
        
    # Rule 2: Clause-based proximity with contrast word blocking
    clause_start = start
    # Split on periods or semicolons, but NOT commas (to keep lists together)
    while clause_start > line_start and text[clause_start - 1] not in ".;\n":
        clause_start -= 1
        
    preceding_text = text[clause_start:start].lower()
    
    last_neg_idx = -1
    for kw in ["không ", "chưa ", "phủ nhận "]:
        idx = preceding_text.rfind(kw)
        if idx > last_neg_idx:
            last_neg_idx = idx
            
    if last_neg_idx != -1:
        text_between = preceding_text[last_neg_idx:]
        
        # Remove the negation verbs themselves so their sub-words don't trigger contrast filters
        text_between = text_between.replace("không có", "").replace("không ghi nhận", "").replace("chưa ghi nhận", "")
        
        # If any contrast word appears AFTER the negation but BEFORE the entity, it cancels the negation
        contrast_words = [" nhưng ", " tuy nhiên ", ", có ", " lại có ", " kèm ", " và có "]
        if not any(cw in text_between for cw in contrast_words):
            assertions.append("isNegated")
            
    return assertions

def expand_drug_boundary(text, start, end):
    """Expand the end boundary to include dosage/frequency if immediately following."""
    pattern = r'^[\s\-]*(\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|viên|ống|lọ|gói|đơn vị|IU|UI|x\s*\d+|po|bid|tid|qid|prn|giọt|lần|/|ngày|giờ|phút)[a-zA-Z0-9\s/]*)'
    match = re.match(pattern, text[end:], flags=re.IGNORECASE)
    if match:
        new_end = end + match.end()
        while new_end > end and text[new_end-1].isspace():
            new_end -= 1
        return start, new_end
    return start, end

def run_pipeline(samples: int = None):
    print("Loading models and dictionaries...")
    df_diag, diag_embs, df_drug, drug_embs, df_sym, sym_embs = load_dictionaries()
    
    extractor = EntityExtractor(mode='ner + retrieval')
    ner_model = extractor._get_ner_instance(lang="vi")
    
    # We use Vietnamese SapBERT for Diagnosis and English SapBERT for Drugs
    sapbert_vi = extractor._get_sapbert_instance(lang="vi")
    sapbert_en = extractor._get_sapbert_instance(lang="en")
    
    test_dir = var_dir / "v_dataset" / "var" / "test"
    output_dir = var_dir / "output" / "legacy_v5" / "monolithic"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping raw NER labels to final categories
    LABEL_MAP = {
        "Drug": "THUỐC",
        "Medication": "THUỐC",
        "Chemical": "THUỐC",
        "Procedure": "TÊN_XÉT_NGHIỆM",
        "Test": "TÊN_XÉT_NGHIỆM",
        "Procedure/Treatment": "TÊN_XÉT_NGHIỆM"
    }

    test_files = list(test_dir.glob("*.txt"))
    if samples:
        test_files = test_files[:samples]
        
    print(f"Found {len(test_files)} test files to process.")
    
    for file_path in tqdm(test_files, desc="Processing Test Files"):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        boundaries = get_section_boundaries(text)
        
        # 1. Perform NER
        # extract_entities returns list of dicts: {'term': ..., 'label': ..., 'offset': [start, end]}
        ner_results = ner_model.extract_entities(text)
        
        final_entities = []
        for ent in ner_results:
            raw_label = ent.get("label", "")
            mapped_type = LABEL_MAP.get(raw_label)
            is_disease = raw_label in ["Disease", "Disease/Symptom", "Condition"]
            
            # If the label is not one of the target ones, skip it
            if not mapped_type and not is_disease:
                continue
                
            term = ent.get("term", "")
            offset = ent.get("offset", [0, 0])
            
            # 1.5 Fix Word Fragmentation
            start, end = offset
            if start is None or end is None:
                continue
                
            import string
            seps = set(string.whitespace + string.punctuation)
            
            # Expand backwards if not at a word boundary
            while start > 0 and text[start - 1] not in seps:
                start -= 1
                
            # Expand forwards if not at a word boundary
            while end < len(text) and text[end] not in seps:
                end += 1
                
            offset = [start, end]
            term = text[start:end]
            
            # --- 1.5.5 Precision Filter (Garbage Removal) ---
            term_normalized = " ".join(term.lower().strip(" \t\r\n.,;:-()[]{}").split())
            if not term_normalized:
                continue
                
            # Short abbreviation drop (unless whitelisted)
            if len(term_normalized) < 3 and term_normalized not in ["ho", "mủ", "u", "k"]:
                if mapped_type != "TÊN_XÉT_NGHIỆM": # Lab tests like CT, XQ can be short
                    continue

            # Generic artifacts
            if term_normalized in ["cảm thấy", "cảm giác", "khó chịu", "bất thường", "bình thường", "theo dõi"]:
                continue
            if term_normalized.startswith("cảm thấy ") and len(term_normalized.split()) <= 2:
                continue
                
            # Dosing-only artifacts
            if mapped_type == "THUỐC" and re.fullmatch(r"^\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui)$", term_normalized, re.IGNORECASE):
                continue
                
            # --- 1.5.6 Type Correction ---
            COMMON_SYMPTOMS = ["khó thở", "buồn nôn", "đau ngực", "đau đầu", "đau bụng", "đau lưng", "tiêu chảy", "mệt mỏi", "chóng mặt", "sốt", "ho", "nôn", "đờm"]
            # Check if any common symptom is in the normalized term
            if is_disease and any(sym in term_normalized for sym in COMMON_SYMPTOMS):
                mapped_type = "TRIỆU_CHỨNG"
                is_disease = False
                
            # Correct Procedure -> Drug if it has drug-like context
            if mapped_type == "TÊN_XÉT_NGHIỆM":
                before = text[max(0, start - 40):start].lower()
                after = text[end:min(len(text), end + 40)].lower()
                if re.search(r"^\s*(?:\d+(?:[.,]\d+)?\s*)?(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui|đơn vị)\b", after) or \
                   re.search(r"(?:thuốc|dùng|uống|sử dụng|điều trị)\s*$", before):
                    mapped_type = "THUỐC"
            
            # --- 1.5.7 Common Stopwords for Lab Tests / Procedures ---
            test_keywords = ["phân tích", "xét nghiệm"]
            
            if any(kw in term_normalized for kw in test_keywords) or term_normalized in ["ct", "mri", "x-quang", "xq"]:
                mapped_type = "TÊN_XÉT_NGHIỆM"
                is_disease = False  # Prevent it from going into the Symptom/Diagnosis lookup
                
            # 1.6 Expand Drug Boundaries & Check Assertions
            display_term = term
            if mapped_type == "THUỐC":
                exp_start, exp_end = expand_drug_boundary(text, start, end)
                offset = [exp_start, exp_end]
                display_term = text[exp_start:exp_end]
                
            assertions = check_assertions(text, start, end, boundaries)
            
            candidates = []
            
            # 2. Compute Embeddings and Retrieval
            if is_disease:
                # Embed with SapBERT Vietnamese
                emb = sapbert_vi.encode_text([term.lower()], show_progress=False)
                
                best_diag_sim = -1
                best_diag_id = None
                best_sym_sim = -1
                
                if emb.size > 0:
                    if not df_diag.empty and diag_embs.size > 0:
                        sims = cosine_similarity(emb, diag_embs)[0]
                        top_3_idx = np.argsort(sims)[-3:][::-1]
                        
                        best_hybrid_score = -1
                        for idx in top_3_idx:
                            sem_sim = sims[idx]
                            if sem_sim < 0.5: continue
                            lex_sim = get_best_row_lexical_sim(term, df_diag.iloc[idx])
                            hybrid_score = sem_sim + lex_sim * 0.5 # Give 50% weight to lexical match
                            
                            if hybrid_score > best_hybrid_score:
                                best_hybrid_score = hybrid_score
                                best_diag_sim = sem_sim
                                best_diag_id = str(df_diag.iloc[idx]['id'])
                        
                    if not df_sym.empty and sym_embs.size > 0:
                        sims = cosine_similarity(emb, sym_embs)[0]
                        best_idx = np.argmax(sims)
                        best_sym_sim = sims[best_idx]
                        
                if best_diag_sim >= best_sym_sim and best_diag_id is not None and best_diag_sim >= 0.5:
                    mapped_type = "CHẨN_ĐOÁN"
                    candidates = [best_diag_id]
                else:
                    mapped_type = "TRIỆU_CHỨNG"
                    candidates = []
                    
            elif mapped_type == "THUỐC" and not df_drug.empty and drug_embs.size > 0:
                # Embed with SapBERT English
                emb = sapbert_en.encode_text([display_term.lower()], show_progress=False)
                if emb.size > 0:
                    sims = cosine_similarity(emb, drug_embs)[0]
                    top_3_idx = np.argsort(sims)[-3:][::-1]
                    
                    best_hybrid_score = -1
                    best_id = None
                    best_sem_sim = -1
                    
                    for idx in top_3_idx:
                        sem_sim = sims[idx]
                        if sem_sim < 0.5: continue
                        lex_sim = get_best_row_lexical_sim(display_term, df_drug.iloc[idx])
                        hybrid_score = sem_sim + lex_sim * 0.5
                        
                        if hybrid_score > best_hybrid_score:
                            best_hybrid_score = hybrid_score
                            best_sem_sim = sem_sim
                            best_id = str(df_drug.iloc[idx]['rxcui'])
                            
                    if best_id and best_sem_sim >= 0.6:
                        candidates = [best_id]
            
            # 3. Format Entity Output
            entity_output = {
                "text": display_term,
                "type": mapped_type,
                "assertions": assertions,
                "position": offset
            }
            
            # Candidates key is only present for Drug and Diagnosis
            if mapped_type in ["CHẨN_ĐOÁN", "THUỐC"]:
                entity_output["candidates"] = candidates
                
            final_entities.append(entity_output)
            
            # --- Heuristic for KẾT_QUẢ_XÉT_NGHIỆM ---
            if mapped_type == "TÊN_XÉT_NGHIỆM" and boundaries.get("s3", -1) != -1 and offset[0] >= boundaries["s3"]:
                start_idx = offset[1]
                end_idx = text.find('\n', start_idx)
                if end_idx == -1:
                    end_idx = len(text)
                
                raw_substring = text[start_idx:end_idx]
                result_str = raw_substring.strip()
                result_str = re.sub(r'^[:\-]+\s*', '', result_str).strip()
                
                if result_str:
                    match_start = raw_substring.find(result_str)
                    actual_start = start_idx + match_start
                    final_entities.append({
                        "text": result_str,
                        "type": "KẾT_QUẢ_XÉT_NGHIỆM",
                        "candidates": [],
                        "assertions": [],
                        "position": [actual_start, actual_start + len(result_str)]
                    })
            
        # Save JSON output
        out_json_path = output_dir / f"{file_path.stem}.json"
        with open(out_json_path, 'w', encoding='utf-8') as f:
            json.dump(final_entities, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run_pipeline()

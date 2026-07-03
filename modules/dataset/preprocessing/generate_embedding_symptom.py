import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Setup paths
script_dir = Path(__file__).resolve().parent
var_dir = script_dir.parents[2]
sys.path.append(str(var_dir.parent)) # Thesis/

from VAR.modules.utils import EntityExtractor

kg_path = var_dir.parent / "data" / "viettel" / "mapping" / "external_kg.parquet"
out_csv = var_dir / "data" / "viettel" / "base" / "short_symptom.csv"
out_npy = var_dir / "data" / "viettel" / "base" / "short_symptom.npy"

if not out_csv.exists() or not out_npy.exists():
    print("Loading external KG...")
    df = pd.read_parquet(kg_path)
    df_sym = df[df['labels'].isin(['Disease', 'Phenotype'])].copy()
    
    # Fill missing values
    df_sym['medgemma_trans'] = df_sym['medgemma_trans'].fillna(df_sym['name'])
    
    df_sym['name_en'] = df_sym['name']
    df_sym['name_vi'] = df_sym['medgemma_trans']
    
    id_cols = ['uml_id', 'hpo_id', 'mesh_id', 'omim_id', 'icd', 'pubchem_id', 'drugbank_id']
    cols_to_keep = [col for col in id_cols if col in df_sym.columns] + ['name_en', 'name_vi']
    df_sym = df_sym[cols_to_keep]
    df_sym.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"Saved {len(df_sym)} symptoms to {out_csv}")
    
    print("Loading SapBERT VI...")
    extractor = EntityExtractor(mode='ner + retrieval')
    sapbert_vi = extractor._get_sapbert_instance(lang="vi")
    
    print("Computing embeddings...")
    names = [str(n).lower() for n in df_sym['name_vi'].fillna("").tolist()]
    print(f"Encoding {len(names)} symptom terms (Vietnamese)...")
    embeddings = sapbert_vi.encode_text(names, batch_size=64, show_progress=True)
    
    np.save(out_npy, embeddings)
    print(f"Saved embeddings to {out_npy}")
else:
    print("short_symptom.csv and short_symptom.npy already exist.")

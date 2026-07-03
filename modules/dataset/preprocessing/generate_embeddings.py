import sys
import os
from pathlib import Path
import pandas as pd
import json
import numpy as np
from tqdm import tqdm

tqdm.pandas()

# Setup paths to ensure we can import VAR.modules.utils
script_dir = Path(__file__).resolve().parent
var_dir = script_dir.parents[2] # VAR/
project_root = var_dir.parent   # Thesis/
sys.path.append(str(project_root))

from VAR.modules.utils import EntityExtractor

def generate_embeddings():
    print("Initializing EntityExtractor and SapBERTs...")
    extractor = EntityExtractor(mode='ner + retrieval')
    sapbert_en = extractor._get_sapbert_instance(lang="en")
    sapbert_vi = extractor._get_sapbert_instance(lang="vi")
    
    # Process Drugs (Temporarily skipped as requested)
    drug_csv = var_dir / "data" / "viettel" / "base" / "short_drug.csv"
    print(f"\nProcessing Drugs from {drug_csv}")
    if drug_csv.exists():
        df_drug = pd.read_csv(drug_csv)
        if 'term' in df_drug.columns:
            terms = [str(t).lower() for t in df_drug['term'].fillna("").tolist()]
            print(f"Encoding {len(terms)} drug terms...")
            embeddings = sapbert_en.encode_text(terms, batch_size=64, show_progress=True)
            
            # Save numpy array directly
            out_npy = drug_csv.with_suffix('.npy')
            np.save(out_npy, embeddings)
            print(f"Saved embeddings to {out_npy}")
        else:
            print(f"Column 'term' not found in {drug_csv}")
    else:
        print(f"File not found: {drug_csv}")
        
    # Process Diagnosis
    diag_csv = var_dir / "data" / "viettel" / "base" / "short_diagnosis.csv"
    print(f"\nProcessing Diagnosis from {diag_csv}")
    if diag_csv.exists():
        df_diag = pd.read_csv(diag_csv)
        if 'name_vi' in df_diag.columns:
            names = [str(n).lower() for n in df_diag['name_vi'].fillna("").tolist()]
            print(f"Encoding {len(names)} diagnosis terms (Vietnamese)...")
            embeddings = sapbert_vi.encode_text(names, batch_size=64, show_progress=True)
            
            # Save numpy array directly
            out_npy = diag_csv.with_suffix('.npy')
            np.save(out_npy, embeddings)
            print(f"Saved embeddings to {out_npy}")
        else:
            print(f"Column 'name_vi' not found in {diag_csv}")
    else:
        print(f"File not found: {diag_csv}")

if __name__ == "__main__":
    generate_embeddings()

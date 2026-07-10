import os
import csv
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

def process_rxnorm():
    # Path Configuration & Environment Setup
    current_script_path = Path(__file__).resolve()
    var_dir = current_script_path.parents[3]
    
    env_path = var_dir / ".env"
    load_dotenv(env_path)
    
    base_path_str = os.getenv("RXNORM_RRF_PATH")
    if not base_path_str:
        raise ValueError("RXNORM_RRF_PATH is not set in .env")
        
    base_path = Path(base_path_str)
    conso_file = base_path / "RXNCONSO.RRF"
    rel_file = base_path / "RXNREL.RRF"
    
    output_dir = var_dir / "v_dataset" / "viettel" / "mapping"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "drug_rxnorm.csv"
    
    # Data Structures
    term_dict = defaultdict(lambda: {
        "rxcui": set(),
        "tty": set(),
        "ingredients": set()
    })
    
    rxcui_to_terms = defaultdict(set)
    rxcui_to_snomed = defaultdict(set)
    rxcui_to_atc = defaultdict(set)
    rxcui_to_drugbank = defaultdict(set)
    
    # Parse RXNCONSO.RRF (Extract Terms & Cross-DB Mappings)
    print("Parsing RXNCONSO.RRF to extract terms and cross-database mappings...")
    try:
        with open(conso_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="RXNCONSO"):
                parts = line.strip().split('|')
                if len(parts) < 15: continue
                
                rxcui = parts[0]
                lat = parts[1]
                sab = parts[11]
                tty = parts[12]
                code = parts[13]
                term = parts[14].lower().strip()
                
                if lat != 'ENG': continue
                
                if sab == 'RXNORM':
                    term_dict[term]["rxcui"].add(rxcui)
                    term_dict[term]["tty"].add(tty)
                    rxcui_to_terms[rxcui].add(term)
                
                elif sab == 'SNOMEDCT_US':
                    rxcui_to_snomed[rxcui].add(code)
                elif sab == 'DRUGBANK':
                    rxcui_to_drugbank[rxcui].add(code)
                elif sab == 'ATC':
                    rxcui_to_atc[rxcui].add(code)
    except FileNotFoundError:
        print(f"Error: Could not find {conso_file}")
        return

    # Parse RXNREL.RRF (Extract Drug-to-Ingredient Relationships)
    print("Parsing RXNREL.RRF to extract drug-to-ingredient relationships...")
    ingredient_relations = {'has_ingredient', 'has_precise_ingredient', 'tradename_of', 'consists_of'}
    
    try:
        with open(rel_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="RXNREL"):
                parts = line.strip().split('|')
                if len(parts) < 11: continue
                
                rxcui1 = parts[0]
                rxcui2 = parts[4]
                rela = parts[7]
                
                if rela in ingredient_relations:
                    if rxcui1 in rxcui_to_terms and rxcui2 in rxcui_to_terms:
                        ingredient_terms = list(rxcui_to_terms[rxcui2])
                        for t in rxcui_to_terms[rxcui1]:
                            for ing_t in ingredient_terms:
                                term_dict[t]["ingredients"].add(ing_t)
    except FileNotFoundError:
        print(f"Warning: Could not find {rel_file}. Skipping relationships.")

    # Export to CSV
    print(f"Saving unified dictionary to {output_file}...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["term", "rxcui", "tty", "ingredients", "snomed", "atc", "drugbank"])
        
        saved_count = 0
        for term, data in tqdm(term_dict.items(), desc="Writing CSV"):
            if not data["rxcui"]:
                continue
                
            snomed_codes = set()
            atc_codes = set()
            drugbank_codes = set()
            
            for rxcui in data["rxcui"]:
                snomed_codes.update(rxcui_to_snomed[rxcui])
                atc_codes.update(rxcui_to_atc[rxcui])
                drugbank_codes.update(rxcui_to_drugbank[rxcui])
                
            str_rxcui = "|".join(data["rxcui"])
            str_tty = "|".join(data["tty"])
            str_ingredients = "|".join(data["ingredients"])
            str_snomed = "|".join(snomed_codes)
            str_atc = "|".join(atc_codes)
            str_drugbank = "|".join(drugbank_codes)
            
            writer.writerow([term, str_rxcui, str_tty, str_ingredients, str_snomed, str_atc, str_drugbank])
            saved_count += 1
            
    print(f"Done! Successfully saved {saved_count} unique drug terms.")

if __name__ == "__main__":
    process_rxnorm()

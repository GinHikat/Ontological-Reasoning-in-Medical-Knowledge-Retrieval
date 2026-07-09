import json
import re
import os

def apply_precision_filter_and_type_correction(entity, sentence):
    term = entity['entity']
    original_type = entity['type']
    
    # We don't have character boundaries in the Qwen JSONL out of the box, 
    # but we can do a simple substring find to check context
    start_char = sentence.find(term) 
    end_char = start_char + len(term) if start_char != -1 else -1

    mapped_type = original_type
    if original_type == "Disease/Symptom":
        mapped_type = "CHẨN_ĐOÁN" # Default to Diagnosis, then filter to Symptom
    elif original_type == "Procedure/Treatment":
        mapped_type = "TÊN_XÉT_NGHIỆM"
    elif original_type == "Drug":
        mapped_type = "THUỐC"
        
    term_normalized = " ".join(term.lower().strip(" \t\r\n.,;:-()[]{}").split())
    if not term_normalized:
        return None
        
    # Short abbreviation drop (unless whitelisted)
    if len(term_normalized) < 3 and term_normalized not in ["ho", "mủ", "u", "k"]:
        if mapped_type != "TÊN_XÉT_NGHIỆM":
            return None

    # Generic artifacts
    if term_normalized in ["cảm thấy", "cảm giác", "khó chịu", "bất thường", "bình thường", "theo dõi"]:
        return None
    if term_normalized.startswith("cảm thấy ") and len(term_normalized.split()) <= 2:
        return None
        
    # Dosing-only artifacts
    if mapped_type == "THUỐC" and re.fullmatch(r"^\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui)$", term_normalized, re.IGNORECASE):
        return None
        
    is_disease = (original_type == "Disease/Symptom")
    COMMON_SYMPTOMS = ["khó thở", "buồn nôn", "đau ngực", "đau đầu", "đau bụng", "đau lưng", "tiêu chảy", "mệt mỏi", "chóng mặt", "sốt", "ho", "nôn", "đờm"]
    if is_disease and any(sym in term_normalized for sym in COMMON_SYMPTOMS):
        mapped_type = "TRIỆU_CHỨNG"
        
    if mapped_type == "TÊN_XÉT_NGHIỆM" and start_char != -1:
        before = sentence[max(0, start_char - 40):start_char].lower()
        after = sentence[end_char:min(len(sentence), end_char + 40)].lower()
        if re.search(r"^\s*(?:\d+(?:[.,]\d+)?\s*)?(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui|đơn vị)\b", after) or \
           re.search(r"(?:thuốc|dùng|uống|sử dụng|điều trị)\s*$", before):
            mapped_type = "THUỐC"
            
    test_keywords = ["phân tích", "xét nghiệm"]
    if any(kw in term_normalized for kw in test_keywords) or term_normalized in ["ct", "mri", "x-quang", "xq"]:
        mapped_type = "TÊN_XÉT_NGHIỆM"
        
    entity['type'] = mapped_type
    
    # Assertions (Negation check based on V6 logic)
    assertions = []
    if start_char != -1:
        clause_start = start_char
        while clause_start > 0 and sentence[clause_start - 1] not in ".;\n":
            clause_start -= 1
        preceding_text = sentence[clause_start:start_char].lower()
        
        last_neg_idx = -1
        for kw in ["không ", "chưa ", "phủ nhận "]:
            idx = preceding_text.rfind(kw)
            if idx > last_neg_idx:
                last_neg_idx = idx
                
        if last_neg_idx != -1:
            text_between = preceding_text[last_neg_idx:]
            text_between = text_between.replace("không có", "").replace("không ghi nhận", "").replace("chưa ghi nhận", "")
            contrast_words = [" nhưng ", " tuy nhiên ", ", có ", " lại có ", " kèm ", " và có "]
            if not any(cw in text_between for cw in contrast_words):
                assertions.append("isNegated")
    
    entity['assertions'] = assertions
    return entity

def process_file(in_path, out_path):
    new_system_prompt = "Bạn là một chuyên gia y tế AI. Nhiệm vụ của bạn là trích xuất các thực thể y tế từ văn bản và trả về dưới dạng JSON list. Các loại thực thể hợp lệ bao gồm: CHẨN_ĐOÁN, TRIỆU_CHỨNG, THUỐC, TÊN_XÉT_NGHIỆM, KẾT_QUẢ_XÉT_NGHIỆM. Kết quả trả về phải chứa entity (tên thực thể), type (loại thực thể), assertions (mảng các chuỗi như 'isNegated', 'isHistorical'), start_token và end_token (chỉ số của từ bắt đầu và kết thúc trong câu, bắt đầu từ 0)."
    
    total = 0
    modified = 0
    dropped = 0
    
    with open(in_path, 'r', encoding='utf-8') as fin, open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            data = json.loads(line)
            messages = data.get("messages", [])
            
            sentence = ""
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = new_system_prompt
                elif msg["role"] == "user":
                    sentence = msg["content"]
            
            for msg in messages:
                if msg["role"] == "assistant":
                    try:
                        entities = json.loads(msg["content"])
                    except json.JSONDecodeError:
                        continue
                        
                    new_entities = []
                    for ent in entities:
                        total += 1
                        old_type = ent.get('type')
                        processed_ent = apply_precision_filter_and_type_correction(dict(ent), sentence)
                        
                        if processed_ent is not None:
                            new_entities.append(processed_ent)
                            if processed_ent['type'] != old_type or processed_ent.get('assertions'):
                                modified += 1
                        else:
                            dropped += 1
                            
                    msg["content"] = json.dumps(new_entities, ensure_ascii=False)
                    
            fout.write(json.dumps(data, ensure_ascii=False) + '\n')
            
    print(f"  Total Entities Processed: {total}")
    print(f"  Entities Modified/Relabeled: {modified}")
    print(f"  Entities Dropped (Garbage): {dropped}")

base_dir = r"d:\Study\Education\Projects\Thesis\v_dataset\viettel\vietnamese_ner\training\vietnamese\qwen_finetune"
files = ["qwen_train.jsonl", "qwen_dev.jsonl", "qwen_test.jsonl"]

for f in files:
    in_path = os.path.join(base_dir, f)
    out_path = os.path.join(base_dir, "relabel_" + f)
    print(f"Processing {f}...")
    process_file(in_path, out_path)

print("Relabeling Complete!")

TARGET_LABEL_DIAGNOSIS = "CHẨN_ĐOÁN"
TARGET_LABEL_DRUG = "THUỐC"
TARGET_LABEL_TEST_NAME = "TÊN_XÉT_NGHIỆM"
TARGET_LABEL_SYMPTOM = "TRIỆU_CHỨNG"
TARGET_LABEL_TEST_RESULT = "KẾT_QUẢ_XÉT_NGHIỆM"

TARGET_LABELS = {
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_TEST_NAME,
    TARGET_LABEL_SYMPTOM,
    TARGET_LABEL_TEST_RESULT,
}

RAW_LABEL_TO_TARGET = {
    "Drug": TARGET_LABEL_DRUG,
    "Medication": TARGET_LABEL_DRUG,
    "Chemical": TARGET_LABEL_DRUG,
    "Procedure": TARGET_LABEL_TEST_NAME,
    "Procedure/Treatment": TARGET_LABEL_TEST_NAME,
    "Test": TARGET_LABEL_TEST_NAME,
}

DISEASE_LIKE_RAW_LABELS = {"Disease", "Disease/Symptom", "Condition"}

ASSERTION_ELIGIBLE_LABELS = {
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
}

CANDIDATE_ELIGIBLE_LABELS = {
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
}

PROCEDURE_TEST_KEYWORDS = {
    "phân tích",
    "xét nghiệm",
    "chụp x-quang",
    "x-quang",
    "x quang",
    "điện tâm đồ",
    "monitor holter",
    "holter",
    "siêu âm",
    "sinh thiết",
    "nội soi",
    "mri",
    "ct",
    "ecg",
    "ekg",
}
PROCEDURE_TEST_EXACT_TERMS = {
    "ct",
    "mri",
    "ecg",
    "ekg",
    "cea",
    "wbc",
    "rbc",
    "hgb",
    "plt",
    "ast",
    "alt",
    "bun",
    "crp",
}

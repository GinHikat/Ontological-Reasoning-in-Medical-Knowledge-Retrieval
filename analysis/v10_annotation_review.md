# v10 annotation review

Human reviewers: fill **Human decision** only. Do not treat code gates as correctness.

Total replacements: **39**

## Category A

### Doc 1 — `atenololtrong` → `atenolol`

**Full line:** -  Ở nhà bệnh nhân đã sử dụng atenololtrong ngày

**Previous entity:**
- text: `atenololtrong`
- position: `[1849, 1862]`
- type: `THUỐC`
- candidates: `["1202"]`
- assertions: `[]`

**Proposed entity:**
- text: `atenolol`
- position: `[1849, 1857]`
- type: `THUỐC`
- candidates: `["1202"]`
- assertions: `[]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** atenolol | amiloride / atenolol / hydrochlorothiazide oral product | atenolol injectable solution | atenolol oral solution | atenolol / chlorthalidone / hydralazine oral tablet
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 5 — `propofol để` → `propofol`

**Full line:** - propofol để an thần

**Previous entity:**
- text: `propofol để`
- position: `[1375, 1386]`
- type: `THUỐC`
- candidates: `["8782"]`
- assertions: `[]`

**Proposed entity:**
- text: `propofol`
- position: `[1375, 1383]`
- type: `THUỐC`
- candidates: `["8782"]`
- assertions: `[]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** propofol | propovan | propofol injection | propothesia | propofol injectable product
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 50 — `amoxicillin.` → `amoxicillin`

**Full line:** Được chỉ định prednisone giảm liều và amoxicillin.

**Previous entity:**
- text: `amoxicillin.`
- position: `[1468, 1480]`
- type: `THUỐC`
- candidates: `["723"]`
- assertions: `[]`

**Proposed entity:**
- text: `amoxicillin`
- position: `[1468, 1479]`
- type: `THUỐC`
- candidates: `["723"]`
- assertions: `[]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** amoxicillin | amoxicillin 500 mg | amoxicillin / nystatin pill | amoxicillin disintegrating oral product | clavamox
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 50 — `azithromycin.` → `azithromycin`

**Full line:** Chuyển sang điều trị bằng azithromycin.

**Previous entity:**
- text: `azithromycin.`
- position: `[1539, 1552]`
- type: `THUỐC`
- candidates: `["18631"]`
- assertions: `[]`

**Proposed entity:**
- text: `azithromycin`
- position: `[1539, 1551]`
- type: `THUỐC`
- candidates: `["18631"]`
- assertions: `[]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** azithromycin | azithromycin oral powder product | azithromycin 250 mg | azithromycin 500 mg | zpak
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 75 — `nitroglycerin.` → `nitroglycerin`

**Full line:** Ngậm dưới lưỡi 4 liều nitroglycerin.

**Previous entity:**
- text: `nitroglycerin.`
- position: `[1256, 1270]`
- type: `THUỐC`
- candidates: `["4917"]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `nitroglycerin`
- position: `[1256, 1269]`
- type: `THUỐC`
- candidates: `["4917"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** nitroglycerin | nitroglycerin 6.4 mg | nitroglycerin 0.1 mg/ml | transderm nitro | nitroglycerin rectal ointment
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 94 — `alevenhưng` → `aleven`

**Full line:** - compazine và alevenhưng vẫn còn đau

**Previous entity:**
- text: `alevenhưng`
- position: `[777, 787]`
- type: `THUỐC`
- candidates: `["215098"]`
- assertions: `[]`

**Proposed entity:**
- text: `aleven`
- position: `[777, 783]`
- type: `THUỐC`
- candidates: `["215101"]`
- assertions: `[]`

**Why v10 changed it:** category A / drug_junk_boundary
**Candidate terms:** aleve | aleve 220 mg oral capsule | naproxen oral tablet [aleve] | aleve oral product | naproxen sodium 220 mg oral tablet [aleve]
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

## Category B

### Doc 3 — `Không đánh trống ngực` → `đánh trống ngực`

**Full line:** - Không đánh trống ngực

**Previous entity:**
- text: `Không đánh trống ngực`
- position: `[690, 711]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `đánh trống ngực`
- position: `[696, 711]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isNegated"]`

**Why v10 changed it:** category B / leading_negation_trim
**Candidate terms:** 
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 3 — `Không chóng mặt` → `chóng mặt`

**Full line:** - Không chóng mặt

**Previous entity:**
- text: `Không chóng mặt`
- position: `[733, 748]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `chóng mặt`
- position: `[739, 748]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isNegated"]`

**Why v10 changed it:** category B / leading_negation_trim
**Candidate terms:** 
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 3 — `Không buồn nôn` → `buồn nôn`

**Full line:** - Không buồn nôn

**Previous entity:**
- text: `Không buồn nôn`
- position: `[751, 765]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `buồn nôn`
- position: `[757, 765]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isNegated"]`

**Why v10 changed it:** category B / leading_negation_trim
**Candidate terms:** 
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

## Category C

### Doc 3 — `nhồi máu cơ tim vùng dưới` → `nhồi máu cơ tim vùng dưới cũ`

**Full line:** - điện tâm đồ (ecg) cho thấy bằng chứng có thể là nhồi máu cơ tim vùng dưới cũ và những thay đổi sóng T không đặc hiệu thay đổi sóng t.

**Previous entity:**
- text: `nhồi máu cơ tim vùng dưới`
- position: `[3336, 3361]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `nhồi máu cơ tim vùng dưới cũ`
- position: `[3336, 3364]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I252"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Nhồi máu cơ tim cũ
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 18 — `bóc tách động mạch chủ Stanford` → `bóc tách động mạch chủ Stanford loại B`

**Full line:** Kết quả chụp ảnh: chụp cắt lớp vi tính mạch máu (ctma) ngực được thực hiện để đánh giá tắc mạch phổi, kết quả Không thấy hình ảnh thuyên tắc mạch phổi. Phát hiện tổn thương bóc tách động mạch chủ Stanford loại B

**Previous entity:**
- text: `bóc tách động mạch chủ Stanford`
- position: `[641, 672]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `bóc tách động mạch chủ Stanford loại B`
- position: `[641, 679]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I710"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Tách thành động mạch chủ (bất kỳ đoạn nào)
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 19 — `Di căn não vùng trán` → `Di căn não vùng trán phải`

**Full line:** - Di căn não vùng trán phải dã phẫu thuật lấy u

**Previous entity:**
- text: `Di căn não vùng trán`
- position: `[115, 135]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Di căn não vùng trán phải`
- position: `[115, 140]`
- type: `CHẨN_ĐOÁN`
- candidates: `["Q011"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Thoát vị não qua vùng mũi trán
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 19 — `Tắc mạch huyết khối` → `Tắc mạch huyết khối tĩnh mạch chủ dưới`

**Full line:** - Tắc mạch huyết khối tĩnh mạch chủ dưới (IVC) và tĩnh mạch chủ trên (SVC) phải

**Previous entity:**
- text: `Tắc mạch huyết khối`
- position: `[167, 186]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Tắc mạch huyết khối tĩnh mạch chủ dưới`
- position: `[167, 205]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I743"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Thuyên tắc và huyết khối động mạch chi dưới
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 23 — `tụ máu ngoài màng cứng phải` → `tụ máu ngoài màng cứng phải cấp tính`

**Full line:** Chụp kiểm tra ghi nhận tụ máu ngoài màng cứng phải cấp tính trên nền tổn thương mạn tính.

**Previous entity:**
- text: `tụ máu ngoài màng cứng phải`
- position: `[752, 779]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `tụ máu ngoài màng cứng phải cấp tính`
- position: `[752, 788]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I621"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Xuất huyết ngoài màng cứng, không do chấn thương
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 24 — `ung thư vú trái` → `ung thư vú trái giai IIIB`

**Full line:** Bệnh lý mãn tính: mới được chẩn đoán ung thư vú trái giai IIIB ung thư vú trái

**Previous entity:**
- text: `ung thư vú trái`
- position: `[58, 73]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `ung thư vú trái giai IIIB`
- position: `[58, 83]`
- type: `CHẨN_ĐOÁN`
- candidates: `["C824"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** U lympho dạng nang độ IIIb
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 41 — `Viêm thực quản` → `Viêm thực quản độ C`

**Full line:** - nội soi (Viêm thực quản độ C, loét thực quản dưới 6 mm có điểm sắc tố, nhiều loét nông sạch đáy ở tá tràng và hồi tràng sớm)

**Previous entity:**
- text: `Viêm thực quản`
- position: `[478, 492]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K20"]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Viêm thực quản độ C`
- position: `[478, 497]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K230*"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Viêm thực quản do laoA18.8
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 51 — `hạ kali máu` → `hạ kali máu rõ rệt`

**Full line:** Các phát hiện chẩn đoán khác: hạ kali máu rõ rệt trong bối cảnh tiêu chảy và có khả năng nhiễm trùng đường hô hấp trên cấp, không xác định

**Previous entity:**
- text: `hạ kali máu`
- position: `[1203, 1214]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `hạ kali máu rõ rệt`
- position: `[1203, 1221]`
- type: `CHẨN_ĐOÁN`
- candidates: `["E876"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Hạ kali máu
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 57 — `bệnh rễ thần kinh tuỷ sống ở ngón tay` → `bệnh rễ thần kinh tuỷ sống ở ngón tay cái`

**Full line:** Triệu chứng hiện tại: bệnh rễ thần kinh tuỷ sống ở ngón tay cái

**Previous entity:**
- text: `bệnh rễ thần kinh tuỷ sống ở ngón tay`
- position: `[187, 224]`
- type: `CHẨN_ĐOÁN`
- candidates: `["M541"]`
- assertions: `[]`

**Proposed entity:**
- text: `bệnh rễ thần kinh tuỷ sống ở ngón tay cái`
- position: `[187, 228]`
- type: `CHẨN_ĐOÁN`
- candidates: `["M541"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Bệnh rễ thần kinh tủy sống
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 57 — `hẹp ống sống C4-5` → `hẹp ống sống C4-5, C5-6, C6-7`

**Full line:** Kết quả chụp ảnh: chụp cộng hưởng từ (mri) cột sống cổ cho thấy hẹp ống sống C4-5, C5-6, C6-7 và hẹp lỗ liên hợp

**Previous entity:**
- text: `hẹp ống sống C4-5`
- position: `[325, 342]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `hẹp ống sống C4-5, C5-6, C6-7`
- position: `[325, 354]`
- type: `CHẨN_ĐOÁN`
- candidates: `["M480"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Hẹp ống sống
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 63 — `viêm túi mật cấp tính` → `viêm túi mật cấp tính không biến chứng`

**Full line:** Kết quả chẩn đoán hình ảnh: chụp ct bụng, chậu, không thuốc cản quang cho thấy một lượng nhỏ dịch và mỡ bao quanh một quai ruột kết sigma, gợi ý viêm túi mật cấp tính không biến chứng

**Previous entity:**
- text: `viêm túi mật cấp tính`
- position: `[1567, 1588]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isNegated"]`

**Proposed entity:**
- text: `viêm túi mật cấp tính không biến chứng`
- position: `[1567, 1605]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K730"]`
- assertions: `["isNegated"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Viêm gan mãn trường diễn, không phân loại nơi khác
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 83 — `hở van hai lá` → `hở van hai lá nặng`

**Full line:** -  siêu âm tim cho thấy hở van hai lá nặng

**Previous entity:**
- text: `hở van hai lá`
- position: `[268, 281]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I340"]`
- assertions: `[]`

**Proposed entity:**
- text: `hở van hai lá nặng`
- position: `[268, 286]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I051"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Hở van hai lá do thấp
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 86 — `bệnh ba thân động mạch vành` → `bệnh ba thân động mạch vành nghiêm trọng`

**Full line:** - Chụp động mạch vành cho thấy bệnh ba thân động mạch vành nghiêm trọng

**Previous entity:**
- text: `bệnh ba thân động mạch vành`
- position: `[650, 677]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `bệnh ba thân động mạch vành nghiêm trọng`
- position: `[650, 690]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I082"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Bệnh cả van động mạch chủ và van ba lá
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 87 — `nhiễm trùng chi dưới` → `nhiễm trùng chi dưới bên phải`

**Full line:** Chẩn đoán: Phẫu thuật cắt cụt chân trái bên trên gối  và cắt cụt chân phải bên dưới gối / biến chứng thuyên tắc phổi hai bên  - nhiễm trùng chi dưới bên phải do Enterococcus kháng vancomycin

**Previous entity:**
- text: `nhiễm trùng chi dưới`
- position: `[795, 815]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `nhiễm trùng chi dưới bên phải`
- position: `[795, 824]`
- type: `CHẨN_ĐOÁN`
- candidates: `["J22"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Nhiễm trùng hô hấp dưới cấp không phân loại
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 88 — `Tăng áp động mạch phổi` → `Tăng áp động mạch phổi mức độ trung bình`

**Full line:** - Tăng áp động mạch phổi mức độ trung bình

**Previous entity:**
- text: `Tăng áp động mạch phổi`
- position: `[143, 165]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Tăng áp động mạch phổi mức độ trung bình`
- position: `[143, 183]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I270"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Tăng áp động mạch phổi nguyên phát
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 88 — `U lympho không hodgkin tế bàoB` → `U lympho không hodgkin tế bàoB lớn lan toả`

**Full line:** -U lympho không hodgkin tế bàoB lớn lan toả)

**Previous entity:**
- text: `U lympho không hodgkin tế bàoB`
- position: `[189, 219]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `U lympho không hodgkin tế bàoB lớn lan toả`
- position: `[189, 231]`
- type: `CHẨN_ĐOÁN`
- candidates: `["C833"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** U lympho không Hodgkin tế bào B lớn tỏa rộng
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 96 — `nhiễm trùng huyết` → `nhiễm trùng huyết đường vào tiết niệu`

**Full line:** Chẩn đoán: nhiễm trùng huyết đường vào tiết niệu- viêm tủy xương mãn tính,

**Previous entity:**
- text: `nhiễm trùng huyết`
- position: `[1472, 1489]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `nhiễm trùng huyết đường vào tiết niệu`
- position: `[1472, 1509]`
- type: `CHẨN_ĐOÁN`
- candidates: `["A40"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Nhiễm trùng huyết do liên cầu
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 97 — `nhiễm trùng` → `nhiễm trùng đường tiết niệu`

**Full line:** - tổng phân tích nước tiểu nhiễm trùng đường tiết niệu

**Previous entity:**
- text: `nhiễm trùng`
- position: `[862, 873]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `nhiễm trùng đường tiết niệu`
- position: `[862, 889]`
- type: `CHẨN_ĐOÁN`
- candidates: `["A39"]`
- assertions: `[]`

**Why v10 changed it:** category C / diagnosis_span_expand
**Candidate terms:** Nhiễm trùng do não mô cầu
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

## Category D

### Doc 4 — `viêm dạ dày.` → `viêm dạ dày`

**Full line:** Bệnh nhân được nội soi thực quản - dạ dày - tá tràng ngoại trú, kết quả ghi nhận viêm dạ dày.

**Previous entity:**
- text: `viêm dạ dày.`
- position: `[1533, 1545]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `viêm dạ dày`
- position: `[1533, 1544]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K297"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Viêm dạ dày, không đặc hiệu
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 4 — `men gan tăng.` → `men gan tăng`

**Full line:** Xét nghiệm chức năng gan cho thấy men gan tăng.

**Previous entity:**
- text: `men gan tăng.`
- position: `[1706, 1719]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `men gan tăng`
- position: `[1706, 1718]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K721"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Suy gan mãn
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 4 — `viêm dạ dày.` → `viêm dạ dày`

**Full line:** Chẩn đoán hình ảnh và thăm dò:Nội soi thực quản - dạ dày - tá tràng: viêm dạ dày.

**Previous entity:**
- text: `viêm dạ dày.`
- position: `[1940, 1952]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `viêm dạ dày`
- position: `[1940, 1951]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K297"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Viêm dạ dày, không đặc hiệu
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 16 — `tràn dịch màng phổi.` → `tràn dịch màng phổi`

**Full line:** Kết quả chẩn đoán hình ảnh: chụp x-quang ngực có xẹp phổi thùy dưới phải do chèn ép kèm tràn dịch màng phổi.

**Previous entity:**
- text: `tràn dịch màng phổi.`
- position: `[2106, 2126]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `tràn dịch màng phổi`
- position: `[2106, 2125]`
- type: `CHẨN_ĐOÁN`
- candidates: `["J93"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Tràn khí màng phổi
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 23 — `tụ dịch/tụ máu dưới màng cứng mạn tính.` → `tụ dịch/tụ máu dưới màng cứng mạn tính`

**Full line:** Khoảng 1 tháng trước nhập viện, bệnh nhân bị ngã và được chẩn đoán xuất huyết dưới nhện. Chụp cắt lớp vi tính sọ não cho hình ảnh  xuất huyết dưới nhện vùng trán phải, bầm dập nhu mô vùng trán phải và trán - thái dương phải, kèm một lớp dịch dưới màng cứng mỏng vùng thùy trán phải, nghĩ nhiều đến nang màng nhện hoặc tụ dịch/tụ máu dưới màng cứng mạn tính.

**Previous entity:**
- text: `tụ dịch/tụ máu dưới màng cứng mạn tính.`
- position: `[504, 543]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `tụ dịch/tụ máu dưới màng cứng mạn tính`
- position: `[504, 542]`
- type: `CHẨN_ĐOÁN`
- candidates: `["D593"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Hội chứng tan máu urê máu cao
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 28 — `vìviêm tụy` → `viêm tụy`

**Full line:** bệnh nhân có tiền sử nhập viện gần đây vìviêm tụy

**Previous entity:**
- text: `vìviêm tụy`
- position: `[60, 70]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `viêm tụy`
- position: `[62, 70]`
- type: `CHẨN_ĐOÁN`
- candidates: `["K040"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Viêm tủy
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 32 — `ho Bệnh bạch cầu dòng tủy mãn tính` → `Bệnh bạch cầu dòng tủy mãn tính`

**Full line:** - ho Bệnh bạch cầu dòng tủy mãn tính

**Previous entity:**
- text: `ho Bệnh bạch cầu dòng tủy mãn tính`
- position: `[43, 77]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Bệnh bạch cầu dòng tủy mãn tính`
- position: `[46, 77]`
- type: `CHẨN_ĐOÁN`
- candidates: `["D471"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Bệnh bạch cầu dòng trung tính mãn tính
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 36 — `bệnh lý BK.` → `bệnh lý BK`

**Full line:** *   creatinin tăng được cho là do bệnh lý BK.

**Previous entity:**
- text: `bệnh lý BK.`
- position: `[869, 880]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `bệnh lý BK`
- position: `[869, 879]`
- type: `CHẨN_ĐOÁN`
- candidates: `["M121"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Bệnh Kaschin-Beck
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 37 — `Bệnh thận mạn tính.` → `Bệnh thận mạn tính`

**Full line:** Bệnh thận mạn tính.

**Previous entity:**
- text: `Bệnh thận mạn tính.`
- position: `[176, 195]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `["isHistorical"]`

**Proposed entity:**
- text: `Bệnh thận mạn tính`
- position: `[176, 194]`
- type: `CHẨN_ĐOÁN`
- candidates: `["N18"]`
- assertions: `["isHistorical"]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Suy thận mãn tính
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 47 — `ung thư biểu mô tuyến.` → `ung thư biểu mô tuyến`

**Full line:** - Đã thực hiện sinh thiết và lấy mẫu bằng bàn chải vào ngày [Ngày] và kết quả lấy mẫu bằng bàn chải cho thấy tế bào bất thường, đáng ngại cho ung thư biểu mô tuyến.

**Previous entity:**
- text: `ung thư biểu mô tuyến.`
- position: `[1169, 1191]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `ung thư biểu mô tuyến`
- position: `[1169, 1190]`
- type: `CHẨN_ĐOÁN`
- candidates: `["C220"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Ung thư biểu mô tế bào gan
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 58 — `tai biến mạch máu não.` → `tai biến mạch máu não`

**Full line:** - Được gọi là Code tai biến mạch máu não.

**Previous entity:**
- text: `tai biến mạch máu não.`
- position: `[1022, 1044]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `tai biến mạch máu não`
- position: `[1022, 1043]`
- type: `CHẨN_ĐOÁN`
- candidates: `["I671"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Phình động mạch não, không vỡ
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

### Doc 88 — `dõiLoét bàn chân nhiễm trùng` → `Loét bàn chân nhiễm trùng`

**Full line:** Chẩn đoán: Theo dõiLoét bàn chân nhiễm trùng

**Previous entity:**
- text: `dõiLoét bàn chân nhiễm trùng`
- position: `[935, 963]`
- type: `TRIỆU_CHỨNG`
- candidates: `[]`
- assertions: `[]`

**Proposed entity:**
- text: `Loét bàn chân nhiễm trùng`
- position: `[938, 963]`
- type: `CHẨN_ĐOÁN`
- candidates: `["T874"]`
- assertions: `[]`

**Why v10 changed it:** category D / type_boundary_cleanup
**Candidate terms:** Nhiễm trùng của mỏm cắt cụt
**Auto flags:** (none)

Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE

Human decision:
Human corrected text:
Human corrected type:
Human corrected assertions:
Human corrected candidates:
Notes:

---

# Giải thích chi tiết đề bài Vòng 1 - Sơ loại

## 1. Tổng quan cuộc thi

Vòng 1 là vòng sơ loại, diễn ra trong khoảng thời gian:

- **Ngày mở vòng:** 02/07/2026
- **Ngày kết thúc:** 30/07/2026
- **Trạng thái:** Đang mở

Ở vòng này, thí sinh cần xây dựng hệ thống dự đoán nhãn cho các bản ghi y sinh/medical text. Kết quả dự đoán phải được nộp dưới dạng các file JSON theo đúng format mà Ban Tổ chức quy định.

Nói ngắn gọn, với mỗi đoạn văn bản đầu vào, hệ thống cần trích xuất ra các **khái niệm y tế** xuất hiện trong văn bản, ví dụ:

- Thuốc
- Triệu chứng
- Chẩn đoán/bệnh lý nếu có trong dữ liệu
- Các thông tin liên quan như mã ứng viên `candidates`, trạng thái `assertions`, vị trí xuất hiện trong văn bản

Đây là một bài toán kết hợp giữa nhiều nhiệm vụ NLP y sinh:

1. **Named Entity Recognition (NER):** nhận diện đoạn text nào là một thực thể y tế.
2. **Entity Typing:** xác định loại của thực thể, ví dụ `THUỐC`, `TRIỆU_CHỨNG`, `CHẨN_ĐOÁN`.
3. **Entity Linking / Candidate Prediction:** ánh xạ thực thể sang mã chuẩn trong ontology hoặc cơ sở tri thức, thông qua trường `candidates`.
4. **Assertion Detection:** xác định trạng thái hoặc quan hệ assertion của thực thể, ví dụ `isHistorical`.
5. **Offset Prediction:** xác định đúng vị trí bắt đầu và kết thúc của thực thể trong chuỗi đầu vào.

---

## 2. Yêu cầu nộp bài

### 2.1. File nộp chính

Thí sinh nộp một file nén tên là:

```text
output.zip
```

Sau khi giải nén, file zip phải có cấu trúc:

```text
output/
    ├── 1.json
    ├── 2.json
    ├── ...
    └── 100.json
```

Trong đó:

- `output/` là thư mục gốc sau khi giải nén.
- Mỗi file `N.json` chứa dự đoán cho bản ghi thứ `N`.
- Ví dụ `1.json` là nhãn/dự đoán của bản ghi 1.
- `2.json` là nhãn/dự đoán của bản ghi 2.
- Tương tự cho đến `100.json`, nếu tập test có 100 bản ghi.

Điều quan trọng là tên file phải khớp với ID hoặc thứ tự sample mà BTC yêu cầu. Nếu đặt sai tên file, thiếu file hoặc sai cấu trúc thư mục, hệ thống chấm có thể không đọc được kết quả.

### 2.2. Nội dung mỗi file JSON

Mỗi file JSON là một danh sách các object. Mỗi object biểu diễn một khái niệm y tế được hệ thống phát hiện trong văn bản đầu vào.

Dạng tổng quát:

```json
[
  {
    "text": "đoạn text được trích xuất",
    "type": "LOẠI_KHÁI_NIỆM",
    "candidates": ["mã_ứng_viên_1", "mã_ứng_viên_2"],
    "assertions": ["assertion_1", "assertion_2"],
    "position": [start, end]
  }
]
```

Một số entity có thể không có `candidates`, ví dụ trong đề mẫu các thực thể `TRIỆU_CHỨNG` không có trường `candidates`. Tuy nhiên, điều này cần tuân theo schema chính thức của BTC nếu có tài liệu chi tiết hơn.

---

## 3. Ý nghĩa từng trường trong output JSON

### 3.1. Trường `text`

`text` là chính xác đoạn văn bản được trích ra từ input.

Ví dụ input có đoạn:

```text
1. amlodipine 10 mg po daily
```

Output tương ứng:

```json
{
  "text": "amlodipine 10 mg po daily",
  "type": "THUỐC",
  "candidates": ["308135"],
  "assertions": ["isHistorical"],
  "position": [58, 83]
}
```

Ở đây `text` phải khớp với substring trong input từ vị trí `58` đến `83`.

Các lỗi thường gặp với trường `text`:

- Thiếu một phần liều lượng, ví dụ chỉ dự đoán `amlodipine` thay vì `amlodipine 10 mg po daily`.
- Dư khoảng trắng ở đầu/cuối.
- Bao gồm số thứ tự `1.` vào entity trong khi ground truth không bao gồm.
- Cắt sai cụm thuốc, bỏ sót đường dùng hoặc tần suất dùng thuốc.
- Gộp nhiều entity thành một entity quá dài.
- Tách một entity thành nhiều entity nhỏ không đúng ground truth.

Trường này được đánh giá bằng **Word Error Rate (WER)**, vì vậy độ giống theo từng từ rất quan trọng.

### 3.2. Trường `type`

`type` là loại khái niệm y tế.

Trong ví dụ có ít nhất hai loại:

```text
THUỐC
TRIỆU_CHỨNG
```

Có thể trong toàn bộ đề còn có các loại khác, ví dụ:

```text
CHẨN_ĐOÁN
BỆNH
THỦ_THUẬT
XÉT_NGHIỆM
```

Tuy nhiên, tài liệu đề bài được trích dẫn chỉ chắc chắn cho thấy `THUỐC` và `TRIỆU_CHỨNG`.

`type` rất quan trọng. Nếu dự đoán đúng `text` nhưng sai `type`, đề bài nói rõ rằng khái niệm sẽ bị tính như:

1. Một khái niệm ground truth bị bỏ sót.
2. Một khái niệm prediction sai được tạo thêm.

Và cả hai đều nhận 0 điểm trên cả 3 metric.

Ví dụ:

Ground truth:

```json
{
  "text": "ho",
  "type": "TRIỆU_CHỨNG"
}
```

Prediction sai:

```json
{
  "text": "ho",
  "type": "CHẨN_ĐOÁN"
}
```

Dù text là `ho` đúng hoàn toàn, hệ thống vẫn xem là sai nghiêm trọng vì loại entity không khớp.

### 3.3. Trường `candidates`

`candidates` là danh sách mã chuẩn ứng với khái niệm được phát hiện.

Ví dụ:

```json
{
  "text": "aspirin 81 mg po daily",
  "type": "THUỐC",
  "candidates": ["243670"],
  "assertions": ["isHistorical"],
  "position": [89, 111]
}
```

Ở đây `243670` có thể là một mã trong ontology hoặc terminology mà BTC sử dụng, ví dụ RxNorm, SNOMED CT, UMLS hoặc một mapping nội bộ. Với thuốc, các mã trong ví dụ giống mã RxNorm/RxCUI.

Vai trò của `candidates`:

- Chuẩn hóa tên entity về mã y tế.
- Giúp phân biệt các thực thể có tên gần giống nhau.
- Đánh giá khả năng liên kết khái niệm vào knowledge base/ontology.

Một entity có thể có:

- Một candidate duy nhất.
- Nhiều candidate nếu có nhiều mã hợp lệ.
- Không có `candidates` nếu loại entity không yêu cầu hoặc không có mapping.

Điểm `candidates_score` chiếm trọng số lớn nhất trong công thức cuối cùng: **40%**.

Điều này nghĩa là chỉ nhận diện đúng text chưa đủ. Hệ thống cần mapping đúng sang mã chuẩn.

### 3.4. Trường `assertions`

`assertions` là danh sách trạng thái hoặc thuộc tính assertion gắn với entity.

Trong ví dụ, tất cả thuốc đều có:

```json
"assertions": ["isHistorical"]
```

Điều này có thể hiểu là thuốc thuộc danh sách sử dụng trước nhập viện, tức là thông tin có tính lịch sử/bệnh sử, không nhất thiết là thuốc đang được kê tại thời điểm hiện tại.

Các triệu chứng trong ví dụ có:

```json
"assertions": []
```

Tức là không có assertion nào được gắn.

Tùy bộ dữ liệu, assertions có thể bao gồm những trạng thái như:

- `isHistorical`: thông tin trong quá khứ/lịch sử.
- `isNegated`: bị phủ định.
- `isHypothetical`: giả định/nghi ngờ.
- `isFamily`: thuộc tiền sử gia đình.
- `isConditional`: điều kiện.

Danh sách chính xác phải theo label schema của BTC.

Điểm `assertions_score` chiếm **30%** tổng điểm.

### 3.5. Trường `position`

`position` là cặp chỉ số:

```json
[start, end]
```

Trong đó:

- `start` là vị trí ký tự bắt đầu của entity trong input.
- `end` là vị trí ngay sau ký tự cuối cùng của entity.

Thông thường trong Python, đây là kiểu offset nửa mở `[start, end)`, nghĩa là:

```python
input_text[start:end] == entity_text
```

Ví dụ:

```json
{
  "text": "amlodipine 10 mg po daily",
  "position": [58, 83]
}
```

Có nghĩa là:

```python
input_text[58:83] == "amlodipine 10 mg po daily"
```

Mặc dù công thức metric trong đề chỉ nêu rõ `text`, `assertions`, `candidates`, trường `position` vẫn rất quan trọng vì có thể được hệ thống dùng để ghép prediction với ground truth. Nếu offset sai, hệ thống có thể không match entity đúng.

Các lỗi offset thường gặp:

- Đếm ký tự Unicode tiếng Việt sai.
- Nhầm giữa byte offset và character offset.
- Dùng end-inclusive thay vì end-exclusive.
- Bỏ qua newline hoặc nhiều khoảng trắng.
- Normalize text trước khi lấy offset nhưng lại nộp offset theo text gốc.

Khuyến nghị: luôn tính `position` trên **chuỗi input gốc**, không phải chuỗi đã lower-case, normalize dấu, xóa khoảng trắng hay tokenize.

---

## 4. Phân tích ví dụ input-output

### 4.1. Input mẫu

Input:

```text
Danh sách thuốc trước nhập viện chính xác và đầy đủ. 1. amlodipine 10 mg po daily 2. aspirin 81 mg po daily 3. metoprolol succinate xl 50 mg po daily 4. guaifenesin ml po q6h:prn điều trị ho 5. nystatin oral suspension 5 ml po qid:prn điều trị đau nhức 6. acetaminophen 325-650 mg po q6h:prn điều trị sốt đau 7. pravastatin 40 mg po daily 8. docusate sodium 100 mg po bid điều trị táo bón 9. senna 8.6 mg po bid:prn điều trị táo bón 10. clonazepam 0.5 mg po qam:prn điều trị lo âu 11. clonazepam 1.5 mg po qhs điều trị lo âu mất ngủ
```

Câu này mô tả danh sách thuốc trước nhập viện. Các thuốc thường đi kèm:

- Tên thuốc
- Hàm lượng/liều lượng
- Đường dùng, ví dụ `po` nghĩa là uống qua đường miệng
- Tần suất, ví dụ `daily`, `bid`, `q6h`, `qid`, `qhs`
- Trạng thái PRN, ví dụ `prn` nghĩa là dùng khi cần
- Triệu chứng hoặc mục đích điều trị sau cụm `điều trị`

### 4.2. Các entity thuốc

Ví dụ entity thuốc đầu tiên:

```json
{
  "text": "amlodipine 10 mg po daily",
  "type": "THUỐC",
  "candidates": ["308135"],
  "assertions": ["isHistorical"],
  "position": [58, 83]
}
```

Giải thích:

- `amlodipine` là tên thuốc.
- `10 mg` là hàm lượng.
- `po` là đường uống.
- `daily` là dùng hàng ngày.
- Vì input nói đây là thuốc trước nhập viện, assertion là `isHistorical`.
- Candidate `308135` là mã chuẩn của thuốc/dạng thuốc tương ứng.

Một entity khác:

```json
{
  "text": "clonazepam 1.5 mg po qhs",
  "type": "THUỐC",
  "candidates": ["197528"],
  "assertions": ["isHistorical"],
  "position": [507, 531]
}
```

Giải thích:

- `clonazepam` là thuốc.
- `1.5 mg` là liều lượng.
- `po` là uống.
- `qhs` thường nghĩa là dùng trước khi ngủ.
- Candidate khác với `clonazepam 0.5 mg po qam:prn` vì liều và cách dùng khác nhau có thể ánh xạ sang mã khác.

### 4.3. Các entity triệu chứng

Ví dụ:

```json
{
  "text": "ho",
  "type": "TRIỆU_CHỨNG",
  "assertions": [],
  "position": [196, 198]
}
```

Ở đây `ho` là triệu chứng được điều trị bởi `guaifenesin`.

Ví dụ khác:

```json
{
  "text": "táo bón",
  "type": "TRIỆU_CHỨNG",
  "assertions": [],
  "position": [397, 404]
}
```

`Táo bón` xuất hiện hai lần trong input, tương ứng với hai vị trí khác nhau:

1. Sau `docusate sodium 100 mg po bid điều trị táo bón`
2. Sau `senna 8.6 mg po bid:prn điều trị táo bón`

Do đó output cũng có hai object riêng cho cùng text `táo bón`, nhưng khác `position`.

Điều này cho thấy không nên tự động gộp các entity trùng text nếu chúng xuất hiện ở nhiều vị trí khác nhau.

---

## 5. Metric đánh giá

Điểm cuối cùng được tính từ ba nhóm metric:

```text
final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score
```

Trọng số:

| Thành phần | Trọng số | Ý nghĩa |
|---|---:|---|
| `text_score` | 0.3 | Độ đúng của đoạn text entity |
| `assertions_score` | 0.3 | Độ đúng của assertions |
| `candidates_score` | 0.4 | Độ đúng của mã candidate |

Như vậy, `candidates_score` quan trọng nhất.

### 5.1. `text_score`

Công thức:

```text
text_score = sum(1 - WER(i) for i in test) / len(test)
```

Trong đó:

- `i` là một sample trong tập test.
- `WER(i)` là Word Error Rate của trường `text` trong sample `i`.
- `1 - WER(i)` càng cao thì text prediction càng giống ground truth.

WER thường được tính dựa trên số thao tác cần để biến câu dự đoán thành câu đúng:

- Substitution: thay từ sai bằng từ đúng.
- Insertion: prediction có thêm từ thừa.
- Deletion: prediction thiếu từ.

Công thức phổ biến:

```text
WER = (S + I + D) / N
```

Trong đó:

- `S`: số từ bị thay thế.
- `I`: số từ bị chèn thừa.
- `D`: số từ bị thiếu.
- `N`: số từ trong ground truth.

Ví dụ đơn giản:

Ground truth:

```text
aspirin 81 mg po daily
```

Prediction:

```text
aspirin 81 mg daily
```

Prediction thiếu từ `po`, nên có 1 deletion trên 5 từ ground truth:

```text
WER = 1 / 5 = 0.2
text component = 1 - WER = 0.8
```

Nếu prediction:

```text
aspirin
```

thì thiếu nhiều từ hơn, WER cao hơn, điểm text thấp hơn.

### 5.2. `assertions_score`

Công thức:

```text
assertions_score = sum(J_assertions(i) for i in test) / len(test)
```

Trong đó `J_assertions(i)` là độ tương đồng Jaccard giữa tập assertions ground truth và tập assertions prediction của sample `i`.

Jaccard similarity được tính:

```text
J(A, B) = |A ∩ B| / |A ∪ B|
```

Ví dụ:

Ground truth assertions:

```text
{isHistorical, isNegated}
```

Prediction assertions:

```text
{isHistorical}
```

Khi đó:

```text
Intersection = {isHistorical}
Union = {isHistorical, isNegated}
J = 1 / 2 = 0.5
```

Nếu cả ground truth và prediction đều rỗng:

```text
J = 1
```

Nếu ground truth rỗng nhưng prediction không rỗng:

```text
J = 0
```

Điều này phạt các prediction thêm assertion không cần thiết.

### 5.3. `candidates_score`

Công thức trong đề:

```text
candidates_score =
    sum_i J_candidates(i) * weight(i)
    /
    sum_i weight(i)
```

Với:

```text
weight(i) = sum_k (len(ground_truth(k)) + 1)
```

Trong đó:

- `i` là một sample trong test.
- `k` là một candidate hoặc một khái niệm trong sample `i`, tùy cách BTC triển khai chấm.
- `ground_truth(k)` là tập candidates đúng của khái niệm `k`.
- `prediction(k)` là tập candidates dự đoán của khái niệm `k`.
- `J_candidates(i)` là Jaccard similarity trên trường `candidates`.

Điểm candidate không phải trung bình đơn giản trên tất cả sample mà là trung bình có trọng số. Sample hoặc entity có nhiều candidate ground truth hơn sẽ có trọng số lớn hơn thông qua `len(ground_truth(k)) + 1`.

Lý do cộng thêm `+1`:

- Tránh trọng số bằng 0 khi một khái niệm không có candidate.
- Vẫn tính ảnh hưởng của entity không có candidate.
- Giữ cho sample/entity rỗng candidate không bị bỏ qua hoàn toàn.

Ví dụ:

Ground truth candidates:

```text
{308135}
```

Prediction candidates:

```text
{308135}
```

Jaccard:

```text
J = 1 / 1 = 1
```

Nếu prediction sai:

```text
Ground truth = {308135}
Prediction = {999999}
Intersection = {}
Union = {308135, 999999}
J = 0 / 2 = 0
```

Nếu prediction có một mã đúng và một mã thừa:

```text
Ground truth = {308135}
Prediction = {308135, 999999}
Intersection = {308135}
Union = {308135, 999999}
J = 1 / 2 = 0.5
```

Vì vậy, không nên thêm quá nhiều candidate để “cầu may”, vì candidate thừa làm tăng union và giảm Jaccard.

---

## 6. Cách hiểu Jaccard trong đề

Đề bài định nghĩa `J_X(i)` cho trường `X`, với `X` có thể là `assertions` hoặc `candidates`.

Có ba trường hợp:

### 6.1. Cả ground truth và prediction đều rỗng

```text
len(ground_truth_X(i)) = 0
len(prediction_X(i)) = 0
```

Khi đó:

```text
J_X(i) = 1
```

Nghĩa là nếu thực tế không có assertion/candidate và model cũng không dự đoán gì, thì được tính đúng hoàn toàn.

### 6.2. Ground truth rỗng nhưng prediction không rỗng

```text
len(ground_truth_X(i)) = 0
len(prediction_X(i)) != 0
```

Khi đó:

```text
J_X(i) = 0
```

Nghĩa là model tự thêm assertion/candidate không có trong ground truth thì bị tính sai hoàn toàn cho trường đó.

### 6.3. Các trường hợp còn lại

```text
J_X(i) = |ground_truth_X(i) ∩ prediction_X(i)| / |ground_truth_X(i) ∪ prediction_X(i)|
```

Đây là Jaccard similarity chuẩn.

---

## 7. Lưu ý đặc biệt về sai `type`

Đề bài nhấn mạnh:

> Trong trường hợp đoán đúng phần text của khái niệm nhưng sai loại, ví dụ đoán `CHẨN_ĐOÁN` nhưng ground truth là `TRIỆU_CHỨNG`, khái niệm sẽ bị tính 2 lần và mỗi lần đều được tính 0 điểm với cả 3 loại metric.

Điều này có nghĩa là sai `type` cực kỳ nghiêm trọng.

Ví dụ ground truth:

```json
{
  "text": "mất ngủ",
  "type": "TRIỆU_CHỨNG",
  "assertions": [],
  "position": [547, 554]
}
```

Prediction:

```json
{
  "text": "mất ngủ",
  "type": "CHẨN_ĐOÁN",
  "assertions": [],
  "position": [547, 554]
}
```

Hệ thống có thể hiểu như sau:

1. Entity `mất ngủ` loại `TRIỆU_CHỨNG` trong ground truth không được dự đoán.
2. Entity `mất ngủ` loại `CHẨN_ĐOÁN` là một prediction thừa.

Kết quả là prediction này bị phạt nặng hơn so với chỉ sai candidate hoặc assertion.

Khuyến nghị:

- Cần ưu tiên classifier `type` thật chắc.
- Nếu không chắc một entity thuộc loại nào, nên xem phân phối label trong train/dev.
- Không nên tùy tiện đổi loại entity chỉ dựa vào từ khóa đơn giản.

---

## 8. Các yêu cầu về source code đối với top đội

Trước khi vòng 1 kết thúc, BTC sẽ yêu cầu khoảng top 15 đội gửi source code riêng để BTC dựng lại và đánh giá trên private test.

Mục đích:

- Tránh gian lận bằng cách hard-code output.
- Đảm bảo kết quả nộp có thể được tái lập từ code.
- Kiểm tra hệ thống có thực sự inference trên input mới hay không.

Source code cần bao gồm:

1. Toàn bộ code của nhóm:
   - Data processing
   - Training
   - Validation
   - Inference
   - Post-processing
   - Script tạo `output.zip`
2. Data nhóm sử dụng:
   - Dữ liệu train/dev được BTC cung cấp
   - Dữ liệu ngoài nếu được phép
   - File mapping ontology/candidate nếu có
3. Model weights:
   - Checkpoint model NER
   - Checkpoint model entity linking
   - Embedding/vector index nếu có
   - Adapter/LoRA weights nếu dùng
4. File README hướng dẫn cài đặt:
   - Môi trường Python
   - Phiên bản thư viện
   - Cách tải/copy dữ liệu
   - Cách chạy inference
   - Cách tạo file nộp

Nếu BTC không cài đặt được code, đội sẽ được liên hệ để hỗ trợ trong một khoảng thời gian nhất định. Nếu không hỗ trợ kịp hoặc không dựng lại được, đội có thể bị loại.

Điều này có nghĩa là ngay từ đầu nên thiết kế repo có khả năng reproducible.

---

## 9. Ràng buộc về tài nguyên và LLM/API

Đề bài nói:

- Thí sinh tự chuẩn bị tài nguyên tính toán.
- Với giải pháp LLM/agent, chỉ được self-host model.
- Không được sử dụng API ngoài.
- Model self-host tối đa **9B parameters**.

Ý nghĩa thực tế:

1. Không được gọi API như OpenAI, Claude, Gemini, v.v. trong pipeline dự thi nếu BTC cấm API ngoài.
2. Nếu dùng LLM, model phải chạy trên máy/infra của đội.
3. Model không được lớn hơn 9B params.
4. Cần chuẩn bị cách BTC có thể chạy lại model trong giới hạn phần cứng hợp lý.

Các model có thể cân nhắc nếu phù hợp luật:

- Qwen 2.5/3 dưới hoặc bằng 9B
- Llama-family dưới hoặc bằng 9B nếu license cho phép
- Mistral 7B
- Bio/clinical domain model nếu có phiên bản nhỏ
- PhoBERT/ViBERT/BERT-based model cho NER/classification

Tuy nhiên, cần kiểm tra luật chính thức để đảm bảo model, data và license được phép dùng.

---

## 10. Chiến lược giải bài toán

Một pipeline thực tế có thể chia thành các bước sau:

```text
Input text
   ↓
Tiền xử lý nhẹ
   ↓
Nhận diện span entity
   ↓
Phân loại type
   ↓
Dự đoán assertions
   ↓
Liên kết candidate/mã ontology
   ↓
Post-processing offset/schema
   ↓
Xuất JSON
   ↓
Đóng gói output.zip
```

### 10.1. Tiền xử lý

Mục tiêu tiền xử lý là giúp model xử lý input tốt hơn, nhưng không làm mất khả năng truy ngược offset về text gốc.

Nên làm:

- Chuẩn hóa Unicode nếu toàn bộ pipeline nhất quán.
- Tách câu hoặc segment theo số thứ tự nếu cần.
- Tokenize phục vụ model.
- Lưu mapping giữa token và character offset gốc.

Không nên làm tùy tiện:

- Xóa dấu tiếng Việt nếu cần output text gốc.
- Xóa hoặc gộp khoảng trắng mà không lưu mapping.
- Lowercase toàn bộ rồi dùng text lowercase để tạo output.
- Xóa dấu câu làm mất offset.

### 10.2. Nhận diện entity span

Có thể dùng nhiều hướng:

#### Hướng 1: Sequence labeling

Dùng model token classification với nhãn BIO/BILOU:

```text
B-THUỐC
I-THUỐC
B-TRIỆU_CHỨNG
I-TRIỆU_CHỨNG
O
```

Ưu điểm:

- Phù hợp bài toán NER.
- Dễ train/evaluate.
- Có thể lấy offset từ tokenizer.

Nhược điểm:

- Cần dữ liệu gán nhãn đủ tốt.
- Có thể khó với entity dài chứa liều lượng và viết tắt.

#### Hướng 2: Rule + dictionary

Dùng từ điển thuốc, triệu chứng, pattern liều lượng.

Ưu điểm:

- Chính xác với các pattern lặp lại.
- Dễ kiểm soát lỗi.
- Hữu ích cho thuốc vì tên thuốc thường có trong ontology.

Nhược điểm:

- Kém tổng quát nếu test có cách viết mới.
- Cần xử lý overlap và ambiguity.

#### Hướng 3: Hybrid

Kết hợp model NER và rule/dictionary.

Ví dụ:

- Model phát hiện span chính.
- Rule mở rộng span thuốc để bao gồm dosage/frequency.
- Dictionary hỗ trợ candidate linking.
- Post-processing sửa lỗi offset và type.

Đây thường là hướng mạnh cho bài toán y sinh có format bán cấu trúc.

### 10.3. Assertion detection

Có thể xem assertion là bài toán multi-label classification cho từng entity.

Input classifier có thể gồm:

- Câu chứa entity.
- Context trái/phải entity.
- Entity text.
- Entity type.

Output là danh sách assertion.

Trong ví dụ, các thuốc đều `isHistorical` vì câu đầu nói:

```text
Danh sách thuốc trước nhập viện
```

Do đó có thể dùng rule:

- Nếu đoạn văn là danh sách thuốc trước nhập viện, gán `isHistorical` cho thuốc.
- Không gán assertion cho triệu chứng nếu ground truth kiểu đó.

Nhưng cần kiểm tra dữ liệu train để tránh overfit vào ví dụ.

### 10.4. Candidate prediction / entity linking

Đây là phần có trọng số cao nhất. Một pipeline candidate tốt có thể gồm:

1. Chuẩn hóa entity text:
   - Lowercase
   - Chuẩn hóa khoảng trắng
   - Chuẩn hóa ký hiệu liều lượng
   - Tách tên hoạt chất, liều, route, frequency
2. Tra dictionary exact match.
3. Nếu không exact match, dùng fuzzy matching.
4. Nếu vẫn không có, dùng embedding retrieval.
5. Re-rank candidate bằng model hoặc rules.

Ví dụ thuốc:

```text
amlodipine 10 mg po daily
```

Có thể parse thành:

- Drug name: `amlodipine`
- Strength: `10 mg`
- Route: `po`
- Frequency: `daily`

Sau đó match với ontology để lấy mã `308135`.

Các lỗi phổ biến:

- Chỉ match tên hoạt chất mà bỏ liều, dẫn đến mã sai.
- Nhầm immediate release vs extended release, ví dụ `metoprolol succinate xl`.
- Nhầm liều `0.5 mg` và `1.5 mg`.
- Không xử lý viết tắt `po`, `bid`, `qid`, `qhs`, `qam`, `prn`.
- Không phân biệt thuốc và triệu chứng khi text ngắn.

---

## 11. Các viết tắt y khoa trong ví dụ

Một số viết tắt xuất hiện trong input:

| Viết tắt | Ý nghĩa thường gặp | Giải thích tiếng Việt |
|---|---|---|
| `po` | per os | dùng đường uống |
| `daily` | once daily | dùng hằng ngày |
| `bid` | bis in die | dùng 2 lần/ngày |
| `qid` | quater in die | dùng 4 lần/ngày |
| `q6h` | every 6 hours | mỗi 6 giờ |
| `qam` | every morning | mỗi buổi sáng |
| `qhs` | at bedtime | trước khi ngủ |
| `prn` | pro re nata | dùng khi cần |
| `xl` | extended release | phóng thích kéo dài |

Các viết tắt này có thể là tín hiệu quan trọng để nhận diện span thuốc.

Ví dụ:

```text
metoprolol succinate xl 50 mg po daily
```

Nếu bỏ `xl`, candidate có thể sai vì `metoprolol succinate xl` là dạng phóng thích kéo dài.

---

## 12. Kiểm tra output trước khi nộp

Nên có script validate trước khi zip:

### 12.1. Kiểm tra cấu trúc thư mục

Cấu trúc đúng:

```text
output/
    1.json
    2.json
    ...
```

Không nên zip sai kiểu:

```text
output.zip
    some_parent_folder/
        output/
            1.json
```

hoặc:

```text
output.zip
    1.json
    2.json
```

nếu BTC yêu cầu phải có thư mục `output/`.

### 12.2. Kiểm tra JSON hợp lệ

Mỗi file phải parse được:

```python
import json

with open("output/1.json", encoding="utf-8") as f:
    data = json.load(f)
```

Nên đảm bảo:

- Root là list.
- Mỗi phần tử là object/dict.
- Có đủ trường bắt buộc.
- `position` là list gồm 2 số nguyên.
- `assertions` là list.
- `candidates` nếu có thì là list string.
- Không có trailing comma.
- Encoding là UTF-8.

### 12.3. Kiểm tra offset

Nên validate:

```python
assert input_text[start:end] == entity["text"]
```

Nếu assertion này fail, cần sửa offset hoặc text.

### 12.4. Kiểm tra type hợp lệ

Nên có danh sách label hợp lệ từ train/schema:

```python
VALID_TYPES = {"THUỐC", "TRIỆU_CHỨNG", "CHẨN_ĐOÁN"}
```

Sau đó kiểm tra:

```python
assert entity["type"] in VALID_TYPES
```

### 12.5. Kiểm tra candidate không bị duplicate

Nếu candidate là set logic, nên loại duplicate:

```json
"candidates": ["308135", "308135"]
```

nên thành:

```json
"candidates": ["308135"]
```

Duplicate có thể làm hệ thống chấm không ổn định nếu BTC không xử lý set hóa.

---

## 13. Ví dụ tính điểm đơn giản

Giả sử có một entity thuốc.

Ground truth:

```json
{
  "text": "aspirin 81 mg po daily",
  "type": "THUỐC",
  "candidates": ["243670"],
  "assertions": ["isHistorical"]
}
```

Prediction A:

```json
{
  "text": "aspirin 81 mg po daily",
  "type": "THUỐC",
  "candidates": ["243670"],
  "assertions": ["isHistorical"]
}
```

Kết quả:

- Text đúng hoàn toàn: `text_score = 1`
- Assertion đúng: `assertions_score = 1`
- Candidate đúng: `candidates_score = 1`
- Final: `1.0`

Prediction B:

```json
{
  "text": "aspirin 81 mg daily",
  "type": "THUỐC",
  "candidates": ["243670"],
  "assertions": ["isHistorical"]
}
```

Kết quả:

- Thiếu `po`, text bị trừ điểm WER.
- Assertion đúng.
- Candidate đúng.
- Final vẫn khá cao nhưng thấp hơn prediction A.

Prediction C:

```json
{
  "text": "aspirin 81 mg po daily",
  "type": "THUỐC",
  "candidates": ["999999"],
  "assertions": ["isHistorical"]
}
```

Kết quả:

- Text đúng.
- Assertion đúng.
- Candidate sai hoàn toàn.
- Vì candidate chiếm 40%, final bị giảm mạnh.

Prediction D:

```json
{
  "text": "aspirin 81 mg po daily",
  "type": "TRIỆU_CHỨNG",
  "candidates": ["243670"],
  "assertions": ["isHistorical"]
}
```

Kết quả:

- Sai type.
- Bị tính như vừa miss entity đúng vừa thêm entity sai.
- Các metric cho khái niệm đó đều 0 theo lưu ý của đề.

---

## 14. Khuyến nghị tối ưu điểm

Do công thức final:

```text
0.3 text + 0.3 assertions + 0.4 candidates
```

nên ưu tiên theo thứ tự:

1. **Candidate linking chính xác** vì trọng số 40%.
2. **Type chính xác** vì sai type làm mất toàn bộ điểm entity.
3. **Span text chính xác** vì ảnh hưởng WER và khả năng match entity.
4. **Assertions chính xác** vì chiếm 30%.
5. **Offset đúng** để tránh lỗi ghép prediction-ground truth.

Một số chiến lược thực dụng:

- Tạo dictionary thuốc từ train và ontology.
- Tạo rule nhận diện liều lượng và tần suất dùng thuốc.
- Fine-tune model NER cho span và type.
- Dùng validation set để đo riêng từng metric.
- Làm post-processing để sửa các lỗi thường gặp.
- Không thêm candidate/assertion nếu không đủ tự tin, vì Jaccard phạt false positive.
- Giữ pipeline reproducible để BTC có thể chạy lại.

---

## 15. Checklist trước khi submit

Trước khi nộp `output.zip`, nên kiểm tra:

- [ ] File zip tên đúng là `output.zip`.
- [ ] Giải nén ra thư mục `output/`.
- [ ] Có đủ file `1.json`, `2.json`, ..., `100.json` hoặc đúng số lượng BTC yêu cầu.
- [ ] Mỗi file JSON parse được bằng Python.
- [ ] Root của mỗi JSON là list.
- [ ] Mỗi entity có `text`, `type`, `assertions`, `position`.
- [ ] Entity cần candidate có trường `candidates` đúng format.
- [ ] `position` là `[start, end]` và `input_text[start:end] == text`.
- [ ] Không dùng byte offset thay cho character offset.
- [ ] Không có candidate duplicate.
- [ ] Không có assertion không hợp lệ.
- [ ] Type nằm trong label schema hợp lệ.
- [ ] Không zip thừa parent directory.
- [ ] Chạy thử script chấm local nếu có.
- [ ] README/source/model/data đã sẵn sàng nếu đội vào top ~15.

---

## 16. Kết luận

Đề bài vòng 1 yêu cầu nộp dự đoán entity y tế ở dạng JSON. Mỗi entity cần có text, type, assertions, candidates nếu có, và vị trí trong input. Điểm cuối cùng được tính từ ba phần:

```text
final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score
```

Trong đó candidate linking có trọng số cao nhất, nhưng type sai sẽ bị phạt rất nặng. Vì vậy hệ thống tốt nên kết hợp nhận diện span chính xác, phân loại type chắc chắn, mapping candidate tốt, assertion hợp lý và post-processing cẩn thận để đảm bảo output đúng schema.

Ngoài điểm số, BTC còn yêu cầu top đội cung cấp source code, data, model weights và README để tái lập kết quả trên private test. Do đó, từ giai đoạn phát triển nên tổ chức code rõ ràng, có script inference tự động và có kiểm tra output trước khi nộp.

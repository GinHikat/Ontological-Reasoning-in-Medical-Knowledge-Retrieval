# Focus file sanity inspection

## File 87

### Original text

```
1.  Tiền sử bệnh
    Nhiều lần có ý định tự tử trước đây do chia tay bạn trai cũ
    Bệnh lý mãn tính
    - trầm cảm và  rối loạn lo âu
2.  Bệnh sử hiện tại
    Lý do nhập viện:  tổn thương chi dưới do tự tử không thành
    Theo lời người nhà kể lại bệnh nhân bị sốc khi chia tay bạn trai cũ, bị bạn bè trêu chọc, buồn chán, uống nhiều rượu,hút cần sa. Sau đó lái xe đến một cây cầu, nhảy từ trên cầu xuống  bệnh nhân nhảy cầu tự tử, sau đó tổn thương chi dưới , vào viện
Tình trạng khi đến khoa Cấp cứu:
Bệnh nhân tỉnh, tiếp xúc tốt
Không xác nhận đã bị trầm cảm trước đó, và không xác nhận có ý định tự tử
 Khám thấy bị tổn thương tổn thương chi dưới nghiêm trọng.
Chẩn đoán: Phẫu thuật cắt cụt chân trái bên trên gối  và cắt cụt chân phải bên dưới gối / biến chứng thuyên tắc phổi hai bên  - nhiễm trùng chi dưới bên phải do Enterococcus kháng vancomycin
    Điều trị :
 Đã phẫu thuật cắt cụt chân trái trên gối và chân phải dưới gối.
Dùng kháng sinh tĩnh mạch.

Có ý định điều trị và lắp chân giả
Bệnh nhân suy nghĩ tích cực nghĩ cho tương lai ( nói rằng uộc sống không dừng lại vì một chấn thương từ bên ngoài)
 Diễn biến ổn định và được chuyển vào khoa tâm thần nội trú.

```

### v6 predictions

- `Bệnh lý mãn tính` [[85, 101]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `trầm cảm` [[108, 116]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rối loạn lo âu` [[121, 135]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tổn thương chi dưới` [[179, 198]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `tự tử không thành` [[202, 219]] TRIỆU_CHỨNG cand=None asrt=[]
- `buồn chán` [[314, 323]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương chi dưới` [[441, 460]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `trầm cảm` [[555, 563]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `tổn thương tổn thương chi dưới nghiêm trọng` [[622, 665]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `Phẫu thuật cắt cụt chân trái` [[678, 706]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `cắt cụt chân` [[724, 736]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `thuyên tắc phổi hai bên` [[768, 791]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm trùng chi dưới` [[795, 815]] TRIỆU_CHỨNG cand=None asrt=[]
- `phẫu` [[877, 881]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `kháng sinh tĩnh mạch` [[943, 963]] THUỐC cand=['852617'] asrt=[]
- `lắp chân giả` [[988, 1000]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `suy nghĩ tích cực` [[1011, 1028]] TRIỆU_CHỨNG cand=None asrt=[]
- `chấn thương từ bên ngoài` [[1090, 1114]] TRIỆU_CHỨNG cand=None asrt=['isNegated']

### v7 predictions

- `Bệnh lý mãn tính` [[85, 101]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `trầm cảm` [[108, 116]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rối loạn lo âu` [[121, 135]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tổn thương chi dưới` [[179, 198]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `tự tử không thành` [[202, 219]] TRIỆU_CHỨNG cand=None asrt=[]
- `buồn chán` [[314, 323]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương chi dưới` [[441, 460]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `trầm cảm` [[555, 563]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `tổn thương tổn thương chi dưới nghiêm trọng` [[622, 665]] CHẨN_ĐOÁN cand=['T93'] asrt=[]
- `Phẫu thuật cắt cụt chân trái` [[678, 706]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `cắt cụt chân` [[724, 736]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `thuyên tắc phổi hai bên` [[768, 791]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm trùng chi dưới` [[795, 815]] TRIỆU_CHỨNG cand=None asrt=[]
- `vancomycin` [[847, 857]] THUỐC cand=['11124'] asrt=[]
- `phẫu` [[877, 881]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `kháng sinh tĩnh mạch` [[943, 963]] THUỐC cand=['852617'] asrt=[]
- `lắp chân giả` [[988, 1000]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `suy nghĩ tích cực` [[1011, 1028]] TRIỆU_CHỨNG cand=None asrt=[]
- `chấn thương từ bên ngoài` [[1090, 1114]] TRIỆU_CHỨNG cand=None asrt=['isNegated']

### New in v7

- `vancomycin` [[847, 857]] THUỐC cand=['11124'] asrt=[]

### Removed from v6


### Changed


## File 88

### Original text

```
1.  Tiền sử bệnh
    Các bệnh lý mãn tính
    - Đái tháo đường típ 1 có biến chứng viêm thần kinh ngoại biên
    - Viêm gan virus C và B
    - Tăng áp động mạch phổi mức độ trung bình
    -U lympho không hodgkin tế bàoB lớn lan toả)
    Tiền sử phẫu thuật / thủ thuật: 
Phẫu thuật thay toàn bộ khớp háng phải 
    Thuốc đang dùng trước khi nhập viện
    - Dùngmethadonekéo dài
    - lasixđã dừng cách vài tuần

2.  Bệnh sử hiện tại
    Lý do nhập viện: Phù chân trái và hoại tử ngày càng nặng
    Ttheo lời bệnh nhân kể, bệnh nhân có khó khăn trong việc tự chăm sóc bản thân tại nhà, bệnh nhân tự ý dừng Lasix vì không muốn đi tiểu nhiều lần. Sau khi dừng sử dụng lasix cách đây vài tuần, xuất hiện phù chân. Ngày nay phù chân và hoại tử nặng lên, chưa xử trí gì, vào viện.
Tình trạng lúc khám vào viện:
Bệnh nhân tỉnh, tiếp xúc được
Phù 2 chân nặng, Loét 2 bàn chân, chảy dịch vàng và có hoại tử đen kích thước 2*4 cm
Chẩn đoán: Theo dõiLoét bàn chân nhiễm trùng

```

### v6 predictions

- `bệnh lý mãn tính` [[25, 41]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Đái tháo đường típ 1` [[48, 68]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `viêm thần kinh ngoại biên` [[83, 108]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Viêm gan virus C và B` [[115, 136]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Tăng áp động mạch phổi` [[143, 165]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `U lympho không hodgkin tế bàoB lớn lan` [[189, 227]] CHẨN_ĐOÁN cand=['C833'] asrt=['isHistorical']
- `phẫu thuật` [[245, 255]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phẫu thuật thay toàn bộ khớp háng phải` [[270, 308]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Dùngmethadonekéo dài` [[356, 376]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `lasixđã` [[383, 390]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phù chân trái` [[453, 466]] TRIỆU_CHỨNG cand=None asrt=[]
- `hoại tử` [[470, 477]] TRIỆU_CHỨNG cand=None asrt=[]
- `đi tiểu nhiều lần` [[624, 641]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `phù chân` [[699, 707]] TRIỆU_CHỨNG cand=None asrt=[]
- `phù chân và hoại tử nặng` [[718, 742]] CHẨN_ĐOÁN cand=['Q845'] asrt=[]
- `Phù 2 chân` [[834, 844]] TRIỆU_CHỨNG cand=None asrt=[]
- `Loét 2 bàn chân` [[851, 866]] TRIỆU_CHỨNG cand=None asrt=[]
- `chảy dịch vàng` [[868, 882]] TRIỆU_CHỨNG cand=None asrt=[]
- `hoại tử đen` [[889, 900]] TRIỆU_CHỨNG cand=None asrt=[]
- `dõiLoét bàn chân nhiễm trùng` [[935, 963]] TRIỆU_CHỨNG cand=None asrt=[]

### v7 predictions

- `bệnh lý mãn tính` [[25, 41]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Đái tháo đường típ 1` [[48, 68]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `viêm thần kinh ngoại biên` [[83, 108]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Viêm gan virus C và B` [[115, 136]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Tăng áp động mạch phổi` [[143, 165]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `U lympho không hodgkin tế bàoB lớn lan` [[189, 227]] CHẨN_ĐOÁN cand=['C833'] asrt=['isHistorical']
- `phẫu thuật` [[245, 255]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phẫu thuật thay toàn bộ khớp háng phải` [[270, 308]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Dùngmethadonekéo dài` [[356, 376]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `methadone` [[360, 369]] THUỐC cand=['6813'] asrt=['isHistorical']
- `lasix` [[383, 388]] THUỐC cand=['202991'] asrt=['isHistorical']
- `lasixđã` [[383, 390]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phù chân trái` [[453, 466]] TRIỆU_CHỨNG cand=None asrt=[]
- `hoại tử` [[470, 477]] TRIỆU_CHỨNG cand=None asrt=[]
- `hoại tử ngày càng nặng` [[470, 492]] TRIỆU_CHỨNG cand=None asrt=[]
- `Lasix` [[604, 609]] THUỐC cand=['202991'] asrt=[]
- `đi tiểu nhiều lần` [[624, 641]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `lasix` [[664, 669]] THUỐC cand=['202991'] asrt=[]
- `phù chân` [[699, 707]] TRIỆU_CHỨNG cand=None asrt=[]
- `phù chân và hoại tử nặng` [[718, 742]] CHẨN_ĐOÁN cand=['Q845'] asrt=[]
- `Phù 2 chân` [[834, 844]] TRIỆU_CHỨNG cand=None asrt=[]
- `Loét 2 bàn chân` [[851, 866]] TRIỆU_CHỨNG cand=None asrt=[]
- `chảy dịch vàng` [[868, 882]] TRIỆU_CHỨNG cand=None asrt=[]
- `hoại tử đen` [[889, 900]] TRIỆU_CHỨNG cand=None asrt=[]
- `dõiLoét bàn chân nhiễm trùng` [[935, 963]] TRIỆU_CHỨNG cand=None asrt=[]

### New in v7

- `lasix` [[664, 669]] THUỐC cand=['202991'] asrt=[]
- `lasix` [[383, 388]] THUỐC cand=['202991'] asrt=['isHistorical']
- `hoại tử ngày càng nặng` [[470, 492]] TRIỆU_CHỨNG cand=None asrt=[]
- `methadone` [[360, 369]] THUỐC cand=['6813'] asrt=['isHistorical']
- `Lasix` [[604, 609]] THUỐC cand=['202991'] asrt=[]

### Removed from v6


### Changed


## File 89

### Original text

```
1.  Tiền sử bệnh
    Lịch sử phẫu thuật / thủ thuật: nội soi mật tuỵ ngược dòng (ERCP) ,đặt stent ống tuỵ gần,  phẫu thuật cắt bỏ khối u thần kinh nội tiết ở thân tụy
    Thuốc đang điều trị theo đơn
    - octreotide
    - flagyl, chăm sóc vết thương tại chỗ, nhịn ăn đường miệng, dinh dưỡng tĩnh mạch


2.  Bệnh sử hiện tại
    Lý do nhập viện: Tuột sonde dẫn lưu ổ bụng
    Theo lời bệnh nhân kể, bệnh nhân đã phẫu thuật bóc tách u nội tiết từ thân tuỵ gây biến chứng rò ống tuỵ mật. Sử dụng ống dẫn lưu tại chỗ dò (  do ERCP không thể qua được chỗ gián đoạn ống dẫn, đặt stent vào ống dẫn tụy gần, không làm giảm đáng kể lượng dịch rò) ,  hậu phẫu  bệnh nhân bị nhiễm Clostridioides difficile, và nhiễm trùng vết mổổ đã được điều trị bằng flagyl, chăm sóc vết thương tại chỗ, sau 23 ngày điều trị thì xuất viện.  Đêm trước ngày vào viện bệnh nhân bị tuột ống sonde dẫn lưu ổ bụng. Đến sáng hôm sau xuất hiện chân sonde dẫn lưu sưng nề, đỏ, chồng bệnh nhân thấy mũi chỉ khâu da cố định ống dẫn bị tuột ra, ống dẫn chỉ bị tuột ra khoảng 2,54 cm, xử trí cố định ống dẫn bằng băng dính và đến khám tại phòng cấp cứu.
Tình trạng lúc vào viện:
Tại chân sonde dẫn lưu ổ bụng sưng nề, đỏ
 ống dẫn lưu bị tuột ra 15,24 cm
Nhịn ăn uống đường miệng, nuôi dưỡng đường tĩnh mạch
 Catheter PICC được chuyển sang tay trái
Cận lâm sàng: 
- siêu âm:  không phát hiện huyết khối tĩnh mạch sâu 
    Thủ thuật đã thực hiện
    - PICC được chuyển sang LUE

```

### v6 predictions

- `phẫu thuật` [[29, 39]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nội soi mật tuỵ ngược dòng` [[53, 79]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ERCP` [[81, 85]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đặt stent ống tuỵ gần` [[88, 109]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `phẫu thuật cắt bỏ khối u thần kinh nội tiết` [[112, 155]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `octreotide` [[206, 216]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `flagyl` [[223, 229]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `dinh dưỡng` [[281, 291]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Tuột sonde dẫn lưu ổ bụng` [[346, 371]] TRIỆU_CHỨNG cand=None asrt=[]
- `rò ống tuỵ mật` [[470, 484]] TRIỆU_CHỨNG cand=None asrt=[]
- `Clostridioides difficile` [[671, 695]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `nhiễm trùng vết mổổ` [[700, 719]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `tuột ống sonde dẫn lưu ổ bụng` [[853, 882]] TRIỆU_CHỨNG cand=None asrt=[]
- `sưng nề` [[930, 937]] TRIỆU_CHỨNG cand=None asrt=[]
- `bụng sưng nề, đỏ` [[1166, 1182]] TRIỆU_CHỨNG cand=None asrt=[]
- `nuôi dưỡng` [[1242, 1252]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `tĩnh mạch` [[1259, 1268]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Catheter PICC` [[1270, 1283]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `siêu âm` [[1327, 1334]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `huyết khối tĩnh mạch sâu` [[1353, 1377]] CHẨN_ĐOÁN cand=['I81'] asrt=['isNegated']

### v7 predictions

- `phẫu thuật` [[29, 39]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nội soi mật tuỵ ngược dòng` [[53, 79]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ERCP` [[81, 85]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đặt stent ống tuỵ gần` [[88, 109]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `phẫu thuật cắt bỏ khối u thần kinh nội tiết` [[112, 155]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `octreotide` [[206, 216]] THUỐC cand=['7617'] asrt=['isHistorical']
- `flagyl` [[223, 229]] THUỐC cand=['202866'] asrt=['isHistorical']
- `dinh dưỡng` [[281, 291]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Tuột sonde dẫn lưu ổ bụng` [[346, 371]] TRIỆU_CHỨNG cand=None asrt=[]
- `rò ống tuỵ mật` [[470, 484]] TRIỆU_CHỨNG cand=None asrt=[]
- `Clostridioides difficile` [[671, 695]] THUỐC cand=['1534764'] asrt=['isNegated']
- `nhiễm trùng vết mổổ` [[700, 719]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `flagyl` [[742, 748]] THUỐC cand=['202866'] asrt=['isNegated']
- `sau` [[779, 782]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `tuột ống sonde dẫn lưu ổ bụng` [[853, 882]] TRIỆU_CHỨNG cand=None asrt=[]
- `sưng nề` [[930, 937]] TRIỆU_CHỨNG cand=None asrt=[]
- `bụng sưng nề, đỏ` [[1166, 1182]] TRIỆU_CHỨNG cand=None asrt=[]
- `15,24` [[1207, 1212]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `nuôi dưỡng` [[1242, 1252]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `tĩnh mạch` [[1259, 1268]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Catheter PICC` [[1270, 1283]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `siêu âm` [[1327, 1334]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `huyết khối tĩnh mạch sâu` [[1353, 1377]] CHẨN_ĐOÁN cand=['I81'] asrt=['isNegated']

### New in v7

- `15,24` [[1207, 1212]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `sau` [[779, 782]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `flagyl` [[742, 748]] THUỐC cand=['202866'] asrt=['isNegated']

### Removed from v6


### Changed

- `Clostridioides difficile` type TRIỆU_CHỨNG->THUỐC; cand None->['1534764']; asrt ['isNegated']->['isNegated']
- `octreotide` type TÊN_XÉT_NGHIỆM->THUỐC; cand None->['7617']; asrt []->['isHistorical']
- `flagyl` type TÊN_XÉT_NGHIỆM->THUỐC; cand None->['202866']; asrt []->['isHistorical']

## File 90

### Original text

```
2. Bệnh sử hiện tại
Lý do khám bệnh: giọng khàn do tổn thương dây thanh quản
Triệu chứng hiện tại
- giọng khàn
- tổn thương dây thanh quản thật sự

3. Đánh giá tại bệnh viện
Các thủ thuật đã thực hiện: nạo vét tổn thương dây thanh quản
```

### v6 predictions

- `giọng khàn` [[37, 47]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản` [[51, 76]] TRIỆU_CHỨNG cand=None asrt=[]
- `giọng khàn` [[100, 110]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản` [[113, 138]] TRIỆU_CHỨNG cand=None asrt=[]
- `nạo vét tổn thương dây thanh quản` [[202, 235]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### v7 predictions

- `giọng khàn` [[37, 47]] TRIỆU_CHỨNG cand=None asrt=[]
- `giọng khàn do tổn thương dây thanh quản` [[37, 76]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản` [[51, 76]] TRIỆU_CHỨNG cand=None asrt=[]
- `giọng khàn` [[100, 110]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản` [[113, 138]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản thật sự` [[113, 146]] TRIỆU_CHỨNG cand=None asrt=[]
- `nạo vét tổn thương dây thanh quản` [[202, 235]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### New in v7

- `giọng khàn do tổn thương dây thanh quản` [[37, 76]] TRIỆU_CHỨNG cand=None asrt=[]
- `tổn thương dây thanh quản thật sự` [[113, 146]] TRIỆU_CHỨNG cand=None asrt=[]

### Removed from v6


### Changed


## File 91

### Original text

```
1.  Tiền sử bệnh
    Các bệnh lý mãn tính
    - Viêm nội tâm mạc  , rối loạn chức năng tâm thất phải, rung nhĩ
sau Phẫu thuật thay van tim hai lá cơ học
    - Suy thận mạn giai V đang chạy thận nhân tạo chu kì các ngày thứ 2, thứ 6, chủ nhật, sau khi ghép thận thất bại
    Tiền sử phẫu thuật / thủ thuật
    - Phẫu thuật thay van hai lá cơ học
    - ghép thận thất bại
    Thuốc trước khi nhập viện: coumadin 3.0 mg /ngày

2.  Bệnh sử hiện tại
Lý do vào viện:, INR dưới ngưỡng điều trị
Theo lời bệnh nhân kể bệnh nhân xuất hiện chảy máu mũi xuất hiện khoảng 01 lần/ tuần. Khi làm xét nghiệm tại khoa chạy thận, phát hiện chỉ số đông máu dưới ngưỡng điều trị ( kết quả là INR 1.7) ,không có biểu hiện bất thường khác, vào viện
    Khám hiện tại:
Không chảy máu mũi
Không có đau ngực
Không có khó thở
Không có đau bụng
 Không có buồn nôn, không nôn
    Các cơ quan khác chưa phát hiện bất thường

3.  Khám tại bệnh viện
    Kết quả khám thực thể: dấu hiệu sinh tồn
 Nhiệt độ : 36.5 độ C
Mạch:  88 l/p
Huyết áp: 120/70 mmHg
Nhịp thở: 20 l/p
SPO2:  92 %
    Kết quả xét nghiệm: INR dưới ngưỡng điều trị 1.7
   Điều trị: Bắt đầu dùng heparin truyền tĩnh mạch liên tục
```

### v6 predictions

- `bệnh lý mãn tính` [[25, 41]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Viêm nội tâm mạc` [[48, 64]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rối loạn chức năng tâm thất phải` [[68, 100]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rung nhĩ` [[102, 110]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Phẫu thuật thay van tim hai lá cơ học` [[115, 152]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Suy thận mạn giai V` [[159, 178]] CHẨN_ĐOÁN cand=['N185'] asrt=['isHistorical']
- `ghép thận` [[251, 260]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `phẫu thuật` [[282, 292]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `thủ thuật` [[295, 304]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phẫu thuật thay van hai lá cơ học` [[311, 344]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ghép thận` [[351, 360]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `coumadin 3.0 mg /ng` [[401, 420]] THUỐC cand=['331762'] asrt=['isHistorical']
- `chảy máu mũi` [[529, 541]] CHẨN_ĐOÁN cand=['R041'] asrt=[]
- `đông máu` [[629, 637]] TRIỆU_CHỨNG cand=None asrt=[]
- `Không chảy máu mũi` [[746, 764]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau ngực` [[774, 782]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `khó thở` [[792, 799]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `đau bụng` [[809, 817]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `buồn nôn` [[828, 836]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `không nôn` [[838, 847]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `sinh tồn` [[955, 963]] TRIỆU_CHỨNG cand=None asrt=[]
- `INR dưới ngưỡng điều trị 1.7` [[1075, 1103]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `heparin truyền` [[1130, 1144]] THUỐC cand=['5224'] asrt=[]
- `tĩnh` [[1145, 1149]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### v7 predictions

- `bệnh lý mãn tính` [[25, 41]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Viêm nội tâm mạc` [[48, 64]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rối loạn chức năng tâm thất phải` [[68, 100]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rung nhĩ` [[102, 110]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Phẫu thuật thay van tim hai lá cơ học` [[115, 152]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Suy thận mạn giai V` [[159, 178]] CHẨN_ĐOÁN cand=['N185'] asrt=['isHistorical']
- `ghép thận` [[251, 260]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `phẫu thuật` [[282, 292]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `thủ thuật` [[295, 304]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Phẫu thuật thay van hai lá cơ học` [[311, 344]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ghép thận` [[351, 360]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `coumadin` [[401, 409]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `coumadin 3.0 mg /ng` [[401, 420]] THUỐC cand=['331762'] asrt=['isHistorical']
- `3.0` [[410, 413]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `INR dưới ngưỡng điều trị` [[462, 486]] TRIỆU_CHỨNG cand=None asrt=[]
- `chảy máu mũi` [[529, 541]] CHẨN_ĐOÁN cand=['R041'] asrt=[]
- `đông máu` [[629, 637]] TRIỆU_CHỨNG cand=None asrt=[]
- `INR` [[672, 675]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `1.7` [[676, 679]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `Không chảy máu mũi` [[746, 764]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau ngực` [[774, 782]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `khó thở` [[792, 799]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `đau bụng` [[809, 817]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `buồn nôn` [[828, 836]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `không nôn` [[838, 847]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `sinh tồn` [[955, 963]] TRIỆU_CHỨNG cand=None asrt=[]
- `INR dưới ngưỡng điều trị 1.7` [[1075, 1103]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `heparin truyền` [[1130, 1144]] THUỐC cand=['5224'] asrt=[]
- `tĩnh` [[1145, 1149]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### New in v7

- `3.0` [[410, 413]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `coumadin` [[401, 409]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `INR dưới ngưỡng điều trị` [[462, 486]] TRIỆU_CHỨNG cand=None asrt=[]
- `1.7` [[676, 679]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `INR` [[672, 675]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### Removed from v6


### Changed


## File 92

### Original text

```
1.  Tiền sử bệnh nội khoa
    Bệnh mạn tính: Nhiễm trùng đường tiết niệu kháng thuốc

2.  Bệnh sử  hiện tại
    Lý do nhập viện: theo dõi đại tràng giãn
    - Vào đợt kiểm tra sức khoẻ định kỳ sau ngã đang hồi phục phát hiện xét nghiệm máu có tăng bạch cầuNgày nay xuất hiện ý thúc chậm hơn, đã chụp CT ở tuyến trước chưa phát hiện bất thường trên phim chụp,  vào viện
    Tình trạng vào Khoa Cấp cứu. 
  Bệnh nhân lơ mơ
3.  Đánh giá tại bệnh viện
    Kết quả xét nghiệm: Bạch cầu tăng
    Kết quả chẩn đoán hình ảnh: chụp ctchưa phát hiện bất thường trên phim chụp
    Các kết quả  khác: Theo dõi đại tràng giãn
```

### v6 predictions

- `Nhiễm trùng đường tiết niệu kháng thuốc` [[45, 84]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đại tràng giãn` [[138, 152]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `CT ở tuyến` [[300, 310]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `trước chưa phát hiện bất thường trên phim chụp` [[311, 357]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `lơ mơ` [[415, 420]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Bạch cầu tăng` [[472, 485]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Bạch cầu tăng` [[472, 485]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `chụp ctchưa` [[518, 529]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `chụp ctchưa phát hiện bất thường trên phim chụp` [[518, 565]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `đại tràng giãn` [[598, 612]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### v7 predictions

- `Nhiễm trùng đường tiết niệu kháng thuốc` [[45, 84]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `theo dõi đại tràng giãn` [[129, 152]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đại tràng giãn` [[138, 152]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `CT ở tuyến` [[300, 310]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `trước chưa phát hiện bất thường trên phim chụp` [[311, 357]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `lơ mơ` [[415, 420]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Bạch cầu tăng` [[472, 485]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `chụp ctchưa` [[518, 529]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đại tràng giãn` [[598, 612]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### New in v7

- `theo dõi đại tràng giãn` [[129, 152]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### Removed from v6

- `chụp ctchưa phát hiện bất thường trên phim chụp` [[518, 565]] KẾT_QUẢ_XÉT_NGHIỆM

### Changed

- `Bạch cầu tăng` type KẾT_QUẢ_XÉT_NGHIỆM->TRIỆU_CHỨNG; cand None->None; asrt []->['isHistorical']

## File 93

### Original text

```
1. Tiền sử bệnh nội khoa
Ung thư vú di căn, tràn dịch màng phổi trái tái phát

2. Bệnh sử hiện tại
Lý do vào việni: khó thở
3. Khám tại bệnh viện
Lâm sàng: tràn dịch màng ngoài tim mức độ trung bình
Kết quả chẩn đoán hình ảnh: ung thư di căn theo đường bạch huyết ở hai phổi
Các thủ thuật đã thực hiện
- dẫn lưu dịch màng tim
- Không thực hiện gây dính màng phổi bằng talc

```

### v6 predictions

- `bệnh nội khoa
Ung thư vú di căn` [[11, 42]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tràn dịch màng phổi trái` [[44, 68]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `khó thở` [[116, 123]] TRIỆU_CHỨNG cand=None asrt=[]
- `tràn dịch màng ngoài tim` [[156, 180]] TRIỆU_CHỨNG cand=None asrt=[]
- `ung thư` [[227, 234]] TRIỆU_CHỨNG cand=None asrt=[]
- `căn` [[238, 241]] TRIỆU_CHỨNG cand=None asrt=[]
- `dẫn lưu dịch màng tim` [[304, 325]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `dính màng phổi` [[348, 362]] TRIỆU_CHỨNG cand=None asrt=['isNegated']

### v7 predictions

- `bệnh nội khoa
Ung thư vú di căn` [[11, 42]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tràn dịch màng phổi trái` [[44, 68]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `khó thở` [[116, 123]] TRIỆU_CHỨNG cand=None asrt=[]
- `tràn dịch màng ngoài tim` [[156, 180]] TRIỆU_CHỨNG cand=None asrt=[]
- `ung thư` [[227, 234]] TRIỆU_CHỨNG cand=None asrt=[]
- `căn` [[238, 241]] TRIỆU_CHỨNG cand=None asrt=[]
- `dẫn lưu dịch màng tim` [[304, 325]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `dính màng phổi` [[348, 362]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `talc` [[368, 372]] THUỐC cand=['10323'] asrt=['isNegated']

### New in v7

- `talc` [[368, 372]] THUỐC cand=['10323'] asrt=['isNegated']

### Removed from v6


### Changed


## File 94

### Original text

```
1.  Tiền sử bệnh nội khoa
    Các bệnh mãn tính: Ung thư vú di căn ER+/HER2−
    đang dùng thuốc  weekly taxol
và fulvestrant để điều trị

2.  Bệnh sử hiện tại
    Lý do nhập viện: đau bụng vùng hạ sườn phải ngày càng tăng
    Theo lời bệnh nhân kể, từ ngày hôm qua bệnh nhân đột ngột xuất hiện đau bụng hạ sườn phải, buồn nôn, nôn kèm theo đi ngoài phân lỏng, toàn nước,  không nhầy máu. Sáng cùng ngày vào viện đau bụng tăng lên , VAS 7/10 kèm theo buồn nôn, nôn nhiều, chưa xử trí thuốc gì, vào viện.
Tình trạng lúc vào:
Người bệnh tỉnh
Da niêm mạc hồngi
 Đau bụng hạ sườn phải
 Buồn nôn, nôn ra thức ăn và dịch dạ dày, không có máu 
Khám thấy
Huyết áp:130/76 mmHg
Mạch: 93 l/p
Nhiệt độ : 36.3 độ C
Nhịp thở: 14 l/p 
SPO2: 99 %
   Điều trị tại bệnh viện:
    - compazine và alevenhưng vẫn còn đau
    - Uống  morphineoral và  lorazepam đỡ đau  (có thể ngủ

3.  Đánh giá tại bệnh viện

```

### v6 predictions

- `Ung thư vú di căn ER+/HER2−` [[49, 76]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `fulvestrant` [[114, 125]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đau bụng vùng hạ sườn phải` [[181, 207]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng hạ sườn phải` [[295, 316]] TRIỆU_CHỨNG cand=None asrt=[]
- `buồn nôn` [[318, 326]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn` [[328, 331]] TRIỆU_CHỨNG cand=None asrt=[]
- `đi ngoài phân lỏng` [[341, 359]] TRIỆU_CHỨNG cand=None asrt=[]
- `toàn nước` [[361, 370]] TRIỆU_CHỨNG cand=None asrt=[]
- `không nhầy máu` [[373, 387]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng tăng` [[413, 426]] TRIỆU_CHỨNG cand=None asrt=[]
- `buồn nôn` [[451, 459]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn nhiều` [[461, 470]] TRIỆU_CHỨNG cand=None asrt=[]
- `Da niêm mạc hồngi` [[540, 557]] TRIỆU_CHỨNG cand=None asrt=[]
- `Đau bụng hạ sườn phải` [[559, 580]] TRIỆU_CHỨNG cand=None asrt=[]
- `Buồn nôn` [[582, 590]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn ra thức ăn` [[592, 606]] TRIỆU_CHỨNG cand=None asrt=[]
- `không có máu` [[623, 635]] TRIỆU_CHỨNG cand=None asrt=[]
- `compazine` [[764, 773]] THUỐC cand=['203546'] asrt=[]
- `alevenhưng` [[777, 787]] THUỐC cand=['215098'] asrt=[]
- `đau` [[796, 799]] TRIỆU_CHỨNG cand=None asrt=[]
- `morphineoral` [[812, 824]] THUỐC cand=['7052'] asrt=[]
- `lorazepam` [[829, 838]] THUỐC cand=['6470'] asrt=[]
- `đau` [[842, 845]] TRIỆU_CHỨNG cand=None asrt=[]

### v7 predictions

- `Ung thư vú di căn ER+/HER2−` [[49, 76]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `HER` [[71, 74]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `taxol` [[105, 110]] THUỐC cand=['196466'] asrt=['isHistorical']
- `fulvestrant` [[114, 125]] THUỐC cand=['282357'] asrt=['isHistorical']
- `đau bụng vùng hạ sườn phải` [[181, 207]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng hạ sườn phải` [[295, 316]] TRIỆU_CHỨNG cand=None asrt=[]
- `buồn nôn` [[318, 326]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn` [[328, 331]] TRIỆU_CHỨNG cand=None asrt=[]
- `đi ngoài phân lỏng` [[341, 359]] TRIỆU_CHỨNG cand=None asrt=[]
- `toàn nước` [[361, 370]] TRIỆU_CHỨNG cand=None asrt=[]
- `không nhầy máu` [[373, 387]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng tăng` [[413, 426]] TRIỆU_CHỨNG cand=None asrt=[]
- `VAS` [[433, 436]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `buồn nôn` [[451, 459]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn nhiều` [[461, 470]] TRIỆU_CHỨNG cand=None asrt=[]
- `Da niêm mạc hồngi` [[540, 557]] TRIỆU_CHỨNG cand=None asrt=[]
- `Đau bụng hạ sườn phải` [[559, 580]] TRIỆU_CHỨNG cand=None asrt=[]
- `Buồn nôn` [[582, 590]] TRIỆU_CHỨNG cand=None asrt=[]
- `nôn ra thức ăn` [[592, 606]] TRIỆU_CHỨNG cand=None asrt=[]
- `không có máu` [[623, 635]] TRIỆU_CHỨNG cand=None asrt=[]
- `compazine` [[764, 773]] THUỐC cand=['203546'] asrt=[]
- `alevenhưng` [[777, 787]] THUỐC cand=['215098'] asrt=[]
- `đau` [[796, 799]] TRIỆU_CHỨNG cand=None asrt=[]
- `morphineoral` [[812, 824]] THUỐC cand=['7052'] asrt=[]
- `lorazepam` [[829, 838]] THUỐC cand=['6470'] asrt=[]
- `đau` [[842, 845]] TRIỆU_CHỨNG cand=None asrt=[]

### New in v7

- `taxol` [[105, 110]] THUỐC cand=['196466'] asrt=['isHistorical']
- `HER` [[71, 74]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `VAS` [[433, 436]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### Removed from v6


### Changed

- `fulvestrant` type TÊN_XÉT_NGHIỆM->THUỐC; cand None->['282357']; asrt []->['isHistorical']

## File 96

### Original text

```
1. Tiền sử bệnh
- viêm tủy xương mãn tính và bàng quang thần kinh gây biến chứng liệt hai chi dưới và loét tì đè giai đoạn IV mãn tính
- đặt lưu sonde tiểu    gây nhiễm khuẩn đường tiết niệu tái phát
Thuốc đã dùng trước đây
- Đã sử dụngvancozosyn nhưng hiện tại đang dừng. Sau khi khám chuyên khoa Truyền nhiễm đang dùng bactrim để điều trị nhiễm khuẩn đường tiết niệu

2. Bệnh sử hiện tại
Lý do nhập viện: sốt cao
Cách ngày vào viện 2 tuần bệnh nhân đã vào viện vì hạ huyết áp và được chẩn đoán  nhiễm trùng huyết điều trị bằng kháng sinh  vancozosynbactrim  điều trị  bệnh viêm tuỷ xương.  Sau đó dùng zosyn 8 ngày và dừng tất cả kháng sinh để điều trị viêm tủy xương mãn tính tại khoa Hồi sức tích cực. Ra viện và tái khám không sử dụng thuốc kháng sinh vì khám lâm sàng ổn
 Sáng cùng ngày vào viện bệnh nhân xuất hiện sốt cao 39.7 độ C , vào viện điều trị.
Tình trạng lúc vào:
Bệnh nhân tỉnh
Cảm giác khát nước
Da khô, nếp véo da mất chậm
Không ngực,  không khó thở
Đau bụng, đau hông từng cơn-
Hạ huyết áp
Mạch nhanh 
Tim nhịp nhanh đều
Phổi thông khí đều
Còn sonde tiểu, nước tiểu có cặn
Cận lâm sàng::
- lactate 1.1-->0.8
- Cấy nước tiểu : nhiễm khuẩn đường tiết niệu có các vi khuẩn hỗn hợp
- cấy máu :âm tính
-chỉ số marker viêm của anh ấy đã có xu hướng tăng 
chẩn đoán hình ảnh: 
 - MRI:  không thấy tình trạng viêm xương tủy nặng hơn
- Xquang ngực thẳng: không thấy thâm nhiễm
Thủ thuật:
- svo2 là 82
Đặt ống thông tĩnh mạch trung tâm : đo cvp là 6
Chẩn đoán: nhiễm trùng huyết đường vào tiết niệu- viêm tủy xương mãn tính,

Điều trị: 
- Truyền dịch : 4000 ml NS 0.9 %
- Kháng sinh Cefepim và Vancomycin truyền tĩnh mạch

.

 

```

### v6 predictions

- `viêm tủy xương mãn tính` [[18, 41]] CHẨN_ĐOÁN cand=['M863'] asrt=['isHistorical']
- `liệt hai chi dưới` [[81, 98]] CHẨN_ĐOÁN cand=['G821'] asrt=['isHistorical']
- `loét tì đè giai đoạn IV` [[102, 125]] CHẨN_ĐOÁN cand=['L893'] asrt=['isHistorical']
- `tính` [[130, 134]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đặt lưu sonde tiểu` [[137, 155]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm khuẩn đường tiết niệu` [[163, 190]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `nhiễm khuẩn đường tiết niệu` [[341, 368]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `sốt cao` [[407, 414]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[466, 477]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm trùng huyết` [[497, 514]] TRIỆU_CHỨNG cand=None asrt=[]
- `viêm tuỷ xương` [[575, 589]] TRIỆU_CHỨNG cand=None asrt=[]
- `viêm tủy xương mãn tính` [[655, 678]] CHẨN_ĐOÁN cand=['M863'] asrt=[]
- `sốt cao 39.7 độ C` [[822, 839]] TRIỆU_CHỨNG cand=None asrt=[]
- `Cảm` [[896, 899]] TRIỆU_CHỨNG cand=None asrt=[]
- `khát nước
Da khô` [[905, 921]] TRIỆU_CHỨNG cand=None asrt=[]
- `nếp véo da mất chậm
Không ngực` [[923, 953]] TRIỆU_CHỨNG cand=None asrt=[]
- `không khó thở
Đau bụng` [[956, 978]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `đau hông từng cơn` [[980, 997]] TRIỆU_CHỨNG cand=None asrt=[]
- `Hạ huyết áp
Mạch nhanh` [[999, 1021]] TRIỆU_CHỨNG cand=None asrt=[]
- `Tim nhịp nhanh đều
Phổi thông khí đều` [[1023, 1060]] TRIỆU_CHỨNG cand=None asrt=[]
- `nước tiểu có cặn` [[1077, 1093]] TRIỆU_CHỨNG cand=None asrt=[]
- `nước tiểu` [[1135, 1144]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm khuẩn đường tiết niệu` [[1147, 1174]] TRIỆU_CHỨNG cand=None asrt=[]
- `khuẩn` [[1185, 1190]] TRIỆU_CHỨNG cand=None asrt=[]
- `cấy máu` [[1201, 1208]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `marker viêm` [[1226, 1237]] TRIỆU_CHỨNG cand=None asrt=[]
- `MRI` [[1294, 1297]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `viêm xương tủy` [[1322, 1336]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `Xquang ngực thẳng` [[1348, 1365]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Đặt ống thông tĩnh mạch trung tâm` [[1413, 1446]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm trùng huyết` [[1472, 1489]] TRIỆU_CHỨNG cand=None asrt=[]
- `viêm tủy xương mãn tính` [[1511, 1534]] CHẨN_ĐOÁN cand=['M863'] asrt=[]
- `Kháng sinh Cefepim` [[1583, 1601]] THUỐC cand=['2282002'] asrt=[]
- `Vancomycin` [[1605, 1615]] THUỐC cand=['11124'] asrt=[]
- `truyền tĩnh mạch` [[1616, 1632]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### v7 predictions

- `viêm tủy` [[18, 26]] CHẨN_ĐOÁN cand=['K040'] asrt=['isHistorical']
- `viêm tủy xương mãn tính` [[18, 41]] CHẨN_ĐOÁN cand=['M863'] asrt=['isHistorical']
- `liệt hai chi dưới` [[81, 98]] CHẨN_ĐOÁN cand=['G821'] asrt=['isHistorical']
- `loét tì đè giai đoạn IV` [[102, 125]] CHẨN_ĐOÁN cand=['L893'] asrt=['isHistorical']
- `tính` [[130, 134]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đặt lưu sonde tiểu` [[137, 155]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm khuẩn đường tiết niệu` [[163, 190]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `zosyn` [[241, 246]] THUỐC cand=['74170'] asrt=['isHistorical']
- `bactrim` [[321, 328]] THUỐC cand=['151399'] asrt=['isHistorical']
- `nhiễm khuẩn đường tiết niệu` [[341, 368]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `sốt cao` [[407, 414]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[466, 477]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm trùng huyết` [[497, 514]] TRIỆU_CHỨNG cand=None asrt=[]
- `zosyn` [[546, 551]] THUỐC cand=['74170'] asrt=[]
- `bactrim` [[551, 558]] THUỐC cand=['151399'] asrt=[]
- `viêm tuỷ xương` [[575, 589]] TRIỆU_CHỨNG cand=None asrt=[]
- `zosyn` [[604, 609]] THUỐC cand=['74170'] asrt=[]
- `viêm tủy` [[655, 663]] CHẨN_ĐOÁN cand=['K040'] asrt=[]
- `viêm tủy xương mãn tính` [[655, 678]] CHẨN_ĐOÁN cand=['M863'] asrt=[]
- `sốt cao 39.7 độ C` [[822, 839]] TRIỆU_CHỨNG cand=None asrt=[]
- `39.7` [[830, 834]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `Cảm` [[896, 899]] TRIỆU_CHỨNG cand=None asrt=[]
- `khát nước
Da khô` [[905, 921]] TRIỆU_CHỨNG cand=None asrt=[]
- `nếp véo da mất chậm
Không ngực` [[923, 953]] TRIỆU_CHỨNG cand=None asrt=[]
- `không khó thở
Đau bụng` [[956, 978]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `đau hông từng cơn` [[980, 997]] TRIỆU_CHỨNG cand=None asrt=[]
- `Hạ huyết áp
Mạch nhanh` [[999, 1021]] TRIỆU_CHỨNG cand=None asrt=[]
- `Tim nhịp nhanh đều
Phổi thông khí đều` [[1023, 1060]] TRIỆU_CHỨNG cand=None asrt=[]
- `nước tiểu có cặn` [[1077, 1093]] TRIỆU_CHỨNG cand=None asrt=[]
- `lactate` [[1111, 1118]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `1.1-->0.8` [[1119, 1128]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `nước tiểu` [[1135, 1144]] TRIỆU_CHỨNG cand=None asrt=[]
- `nhiễm khuẩn đường tiết niệu` [[1147, 1174]] TRIỆU_CHỨNG cand=None asrt=[]
- `khuẩn` [[1185, 1190]] TRIỆU_CHỨNG cand=None asrt=[]
- `cấy máu` [[1201, 1208]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `âm tính` [[1210, 1217]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `marker viêm` [[1226, 1237]] TRIỆU_CHỨNG cand=None asrt=[]
- `MRI` [[1294, 1297]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `viêm xương tủy` [[1322, 1336]] CHẨN_ĐOÁN cand=['M86'] asrt=['isNegated']
- `Xquang ngực thẳng` [[1348, 1365]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `svo2` [[1402, 1406]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Đặt ống thông tĩnh mạch trung tâm` [[1413, 1446]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đo cvp` [[1449, 1455]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm trùng huyết` [[1472, 1489]] TRIỆU_CHỨNG cand=None asrt=[]
- `viêm tủy` [[1511, 1519]] CHẨN_ĐOÁN cand=['K040'] asrt=[]
- `viêm tủy xương mãn tính` [[1511, 1534]] CHẨN_ĐOÁN cand=['M863'] asrt=[]
- `Truyền dịch` [[1550, 1561]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `4000` [[1564, 1568]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `0.9 %` [[1575, 1580]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `Kháng sinh Cefepim` [[1583, 1601]] THUỐC cand=['2282002'] asrt=[]
- `Vancomycin` [[1605, 1615]] THUỐC cand=['11124'] asrt=[]
- `truyền tĩnh mạch` [[1616, 1632]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### New in v7

- `svo2` [[1402, 1406]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `lactate` [[1111, 1118]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `viêm tủy` [[18, 26]] CHẨN_ĐOÁN cand=['K040'] asrt=['isHistorical']
- `viêm tủy` [[655, 663]] CHẨN_ĐOÁN cand=['K040'] asrt=[]
- `đo cvp` [[1449, 1455]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `bactrim` [[321, 328]] THUỐC cand=['151399'] asrt=['isHistorical']
- `1.1-->0.8` [[1119, 1128]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `âm tính` [[1210, 1217]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `0.9 %` [[1575, 1580]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `bactrim` [[551, 558]] THUỐC cand=['151399'] asrt=[]
- `viêm tủy` [[1511, 1519]] CHẨN_ĐOÁN cand=['K040'] asrt=[]
- `4000` [[1564, 1568]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `zosyn` [[241, 246]] THUỐC cand=['74170'] asrt=['isHistorical']
- `Truyền dịch` [[1550, 1561]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `zosyn` [[604, 609]] THUỐC cand=['74170'] asrt=[]
- `39.7` [[830, 834]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `zosyn` [[546, 551]] THUỐC cand=['74170'] asrt=[]

### Removed from v6


### Changed

- `viêm xương tủy` type TRIỆU_CHỨNG->CHẨN_ĐOÁN; cand None->['M86']; asrt ['isNegated']->['isNegated']

## File 97

### Original text

```
1.  Tiền sử bệnh nội khoa
    Các bệnh lý mãn tính: viêm tủy xương và bàng quang thần kinh có biến chứng liệt hai chi dưới

2.  Bệnh sử hiện tại
    Lý do nhập viện: biến đổi ý thức kèm theo hạ thân nhiệt và hạ huyết áp
    Thời điểm khởi phát triệu chứng: Được ghi nhận bởi đội cấp cứu trên đường đến Khoa Cấp cứu
Trước khi nhập viện, bệnh nhân được phát hiện trong tình trạng biến đổi ý thức, hạ thân nhiệt, hạ huyết áp với huyết áp tâm thu là 90
    Các triệu chứng hiện tại
    - biến đổi ý thức
    - hạ thân nhiệt
    - hạ huyết áp
    - đau toàn thân ít
    - đau ngực ít 
    - đau bụng
3.  Khám tại bệnh viện
    Dấu hiệu lâm sàng
    - hạ huyết áp
    - hạ thân nhiệt
    - lắc đầu có/không
    Kết quả xét nghiệm
    - kali là 6.6 mmol/l
    - creatinin là 1.9 mmol/l
    - tiểu cầu là 81 G/L
    - bạch cầu là 10.9 G/L
    - tổng phân tích nước tiểu nhiễm trùng đường tiết niệu
    Kết quả chẩn đoán hình ảnh
    - chẩn đoán hình ảnh: chụp x-quang ngực cho thấy không có hình ảnh tổn thương viêm cấp tính so với chụp x-quang ngực trước đó
    Các thủ thuật đã thực hiện
    - Đặt sonde bàng quang
    - Gửi xét nghiệm máu và cấy nước tiểu
    Các thủ thuậ khác
    - điện tâm đồ cho thấy nhịp chậm xoang 
- đường huyết lúc đóiđường huyết thấp)
```

### v6 predictions

- `viêm tủy xương và bàng quang thần kinh` [[52, 90]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `liệt hai chi dưới` [[105, 122]] CHẨN_ĐOÁN cand=['G821'] asrt=['isHistorical']
- `hạ thân nhiệt` [[191, 204]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[208, 219]] TRIỆU_CHỨNG cand=None asrt=[]
- `biến đổi ý thức` [[378, 393]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[395, 408]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[410, 421]] TRIỆU_CHỨNG cand=None asrt=[]
- `biến đổi ý thức` [[484, 499]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[506, 519]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[526, 537]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau toàn thân ít` [[544, 560]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau ngực ít` [[567, 578]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng` [[586, 594]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[646, 657]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[664, 677]] TRIỆU_CHỨNG cand=None asrt=[]
- `lắc đầu` [[684, 691]] TRIỆU_CHỨNG cand=None asrt=[]
- `phân tích nước tiểu` [[842, 861]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm trùng` [[862, 873]] TRIỆU_CHỨNG cand=None asrt=[]
- `x-quang` [[952, 959]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `thấy không có hình ảnh tổn thương viêm cấp tính so với chụp x-quang ngực trước đó` [[969, 1050]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `viêm` [[1003, 1007]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `x-quang ngực` [[1029, 1041]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Đặt sonde bàng quang` [[1088, 1108]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `xét nghiệm máu` [[1119, 1133]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `cấy nước tiểu` [[1137, 1150]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `điện tâm đồ` [[1179, 1190]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhịp chậm xoang` [[1200, 1215]] TRIỆU_CHỨNG cand=None asrt=[]

### v7 predictions

- `viêm tủy xương và bàng quang thần kinh` [[52, 90]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `liệt hai chi dưới` [[105, 122]] CHẨN_ĐOÁN cand=['G821'] asrt=['isHistorical']
- `hạ thân nhiệt` [[191, 204]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[208, 219]] TRIỆU_CHỨNG cand=None asrt=[]
- `biến đổi ý thức` [[378, 393]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[395, 408]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[410, 421]] TRIỆU_CHỨNG cand=None asrt=[]
- `biến đổi ý thức` [[484, 499]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[506, 519]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[526, 537]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau toàn thân ít` [[544, 560]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau ngực ít` [[567, 578]] TRIỆU_CHỨNG cand=None asrt=[]
- `đau bụng` [[586, 594]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ huyết áp` [[646, 657]] TRIỆU_CHỨNG cand=None asrt=[]
- `hạ thân nhiệt` [[664, 677]] TRIỆU_CHỨNG cand=None asrt=[]
- `lắc đầu` [[684, 691]] TRIỆU_CHỨNG cand=None asrt=[]
- `kali` [[730, 734]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `6.6 mmol/l` [[738, 748]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `creatinin` [[755, 764]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `1.9 mmol/l` [[768, 778]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `tiểu cầu` [[785, 793]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `81 G/L` [[797, 803]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `bạch cầu` [[810, 818]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `10.9 G/L` [[822, 830]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `phân tích nước tiểu` [[842, 861]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhiễm trùng` [[862, 873]] TRIỆU_CHỨNG cand=None asrt=[]
- `x-quang` [[952, 959]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `viêm` [[1003, 1007]] TRIỆU_CHỨNG cand=None asrt=['isNegated']
- `x-quang ngực` [[1029, 1041]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `Đặt sonde bàng quang` [[1088, 1108]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `xét nghiệm máu` [[1119, 1133]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `cấy nước tiểu` [[1137, 1150]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `điện tâm đồ` [[1179, 1190]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhịp chậm xoang` [[1200, 1215]] TRIỆU_CHỨNG cand=None asrt=[]

### New in v7

- `10.9 G/L` [[822, 830]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `kali` [[730, 734]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `1.9 mmol/l` [[768, 778]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `6.6 mmol/l` [[738, 748]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `creatinin` [[755, 764]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `81 G/L` [[797, 803]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `bạch cầu` [[810, 818]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `tiểu cầu` [[785, 793]] TÊN_XÉT_NGHIỆM cand=None asrt=[]

### Removed from v6

- `thấy không có hình ảnh tổn thương viêm cấp tính so với chụp x-quang ngực trước đó` [[969, 1050]] KẾT_QUẢ_XÉT_NGHIỆM

### Changed


## File 99

### Original text

```
1.  Tiền sử bệnh
    Bệnh lý mãn tính: rối loạn lo âu, không biệt định nghiêm trọng
    Tiền sử phẫu thuật / thủ thuật: phẫu thuật nội soi cắt bỏ tuyến tiền liệt  bên trái

2.  Bệnh sử
    Lý do nhập viện: buồn nôn, đau dai dẳng, và táo bón
    Triệu chứng hiện tại
    - buồn nôn
    - đau dai dẳng
    - táo bón

3.  Đánh giá tại bệnh viện
```

### v6 predictions

- `rối loạn lo âu` [[39, 53]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `biệt` [[61, 65]] CHẨN_ĐOÁN cand=['L80'] asrt=['isHistorical', 'isNegated']
- `phẫu thuật` [[96, 106]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nội soi` [[131, 138]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `buồn nôn` [[206, 214]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau dai dẳng` [[216, 228]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `táo bón` [[233, 240]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `buồn nôn` [[272, 280]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau dai dẳng` [[287, 299]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `táo bón` [[306, 313]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### v7 predictions

- `rối loạn lo âu` [[39, 53]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `rối loạn lo âu, không biệt định` [[39, 70]] CHẨN_ĐOÁN cand=['F419'] asrt=['isHistorical']
- `biệt` [[61, 65]] CHẨN_ĐOÁN cand=['L80'] asrt=['isHistorical', 'isNegated']
- `phẫu thuật` [[96, 106]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nội soi` [[131, 138]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `buồn nôn` [[206, 214]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau dai dẳng` [[216, 228]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `táo bón` [[233, 240]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `buồn nôn` [[272, 280]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau dai dẳng` [[287, 299]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `táo bón` [[306, 313]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### New in v7

- `rối loạn lo âu, không biệt định` [[39, 70]] CHẨN_ĐOÁN cand=['F419'] asrt=['isHistorical']

### Removed from v6


### Changed


## File 100

### Original text

```
1.  Tiền sử bệnh
    Các bệnh đã điều trị trước đây: tiền sử tăng calci máu trước đây; 11.6
    Các bệnh lý mãn tính
    - U ác của đại tràng
    - cường cận giáp nguyên phát
    - Xơ vữa động mạch
    - cơn đau thắt ngực ổn định

2. Bệnh sử
    Lý do nhập viện: đến khám vì tăng calci máu
    Triệu chứng hiện tại: tăng calci máu
    Các lần khám và xét nghiệm trước khi nhập viện
    - xét nghiệm xét nghiệm ngoại trú được thực hiện hôm nay và canxi là 12.0; canxi ion hóa 6.8 
    - xuất hiện hai lần ngất xỉu, một lần khi lái xe lần cuối và một lần khác khi nói chuyện với bạn trong xe một tháng trước
    - Cả hai lần đều kéo dài vài giây
    - Không có các biểu hiện đau ngực, khó thở, chóng mặt trước lần này
    - Không có biểu hiện động kinh
    - đã chỉ định MRI ngoại trú  có hình ảnh nhồi máu cũ nhỏ ở vỏ não đỉnh trái, không có tổn thương cấp tính
    - Bệnh nhân xuất hiện một lần đau ngực vào chiều ngày vào viện, cơn đau kéo dài khoảng 5 phút
 sau đó đã được sử dụng ngay 01 viên nitroglycerin đặt dưới lưỡi
    - Hiện tại bệnh nhân còn đau ở sau đầu và cổ từ khi bị ngã trong bồn tắm năm ngoái đến nay

3.  Đánh giá tại bệnh viện
    Kết quả xétí nghiệm
    - canxi toàn phần là 12.0; canxi ion hóa 6.8
    - canx toàn phầni là 12.3
    - cr (creatinine) 1.2
    Kết quả chẩn đoán hình ảnh: MRI ngoại trú cho thấy hình ảnh  nhồi máu cũ nhỏ ở vỏ não đỉnh trái nhưng không có quá trình cấp tính
    Xử trí thuốc
    - đã dùng Laxis 20mg tiêm tĩnh mạch
    - Truyền  dịch Natriclori 0.9 %  tĩnh mạch
```

### v6 predictions

- `tăng calci máu` [[61, 75]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `bệnh lý mãn tính` [[100, 116]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `U ác của đại tràng` [[123, 141]] CHẨN_ĐOÁN cand=['C170'] asrt=['isHistorical']
- `cường cận giáp nguyên phát` [[148, 174]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Xơ vữa động mạch` [[181, 197]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `cơn đau thắt ngực` [[204, 221]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tăng calci máu` [[275, 289]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tăng calci máu` [[316, 330]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `xét nghiệm ngoại trú` [[399, 419]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canxi ion hóa` [[461, 474]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ngất xỉu` [[504, 512]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau ngực` [[673, 681]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `khó thở` [[683, 690]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `chóng mặt` [[692, 701]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `động kinh` [[741, 750]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `MRI ngoại trú` [[769, 782]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhồi máu cũ` [[796, 807]] CHẨN_ĐOÁN cand=['I252'] asrt=['isHistorical']
- `đau ngực` [[895, 903]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `cơn đau` [[929, 936]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `nitroglycerin` [[996, 1009]] THUỐC cand=['4917'] asrt=['isHistorical']
- `đau ở sau đầu và cổ` [[1053, 1072]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `xétí nghiệm` [[1159, 1170]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canxi` [[1177, 1182]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canxi` [[1202, 1207]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canx` [[1226, 1230]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `creatinine` [[1260, 1270]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `) 1.2` [[1270, 1275]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `MRI ngoại trú` [[1308, 1321]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `hình ảnh  nhồi máu cũ nhỏ ở vỏ não đỉnh trái nhưng không có quá trình cấp tính` [[1331, 1409]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `nhồi máu cũ nhỏ ở vỏ não đỉnh trái` [[1341, 1375]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']

### v7 predictions

- `tăng calci máu` [[61, 75]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `bệnh lý mãn tính` [[100, 116]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `U ác của đại tràng` [[123, 141]] CHẨN_ĐOÁN cand=['C170'] asrt=['isHistorical']
- `cường cận giáp nguyên phát` [[148, 174]] CHẨN_ĐOÁN cand=['E210'] asrt=['isHistorical']
- `Xơ vữa động mạch` [[181, 197]] CHẨN_ĐOÁN cand=['I70'] asrt=['isHistorical']
- `cơn đau thắt ngực` [[204, 221]] CHẨN_ĐOÁN cand=['I20'] asrt=['isHistorical']
- `đến khám vì tăng calci máu` [[263, 289]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tăng calci máu` [[275, 289]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `tăng calci máu` [[316, 330]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `xét nghiệm ngoại trú` [[399, 419]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canxi ion hóa` [[461, 474]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `ngất xỉu` [[504, 512]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `đau ngực` [[673, 681]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `khó thở` [[683, 690]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `chóng mặt` [[692, 701]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `động kinh` [[741, 750]] TRIỆU_CHỨNG cand=None asrt=['isHistorical', 'isNegated']
- `MRI ngoại trú` [[769, 782]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhồi máu cũ` [[796, 807]] CHẨN_ĐOÁN cand=['I252'] asrt=['isHistorical']
- `đau ngực` [[895, 903]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `cơn đau` [[929, 936]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `ngay` [[983, 987]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nitroglycerin` [[996, 1009]] THUỐC cand=['4917'] asrt=['isHistorical']
- `đau ở sau đầu và cổ` [[1053, 1072]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `nay` [[1115, 1118]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `xétí nghiệm` [[1159, 1170]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canxi` [[1177, 1182]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `12.0` [[1196, 1200]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `canxi` [[1202, 1207]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `canx` [[1226, 1230]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `12.3` [[1245, 1249]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `creatinine` [[1260, 1270]] THUỐC cand=['2913'] asrt=['isHistorical']
- `) 1.2` [[1270, 1275]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `MRI ngoại trú` [[1308, 1321]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `nhồi máu cũ nhỏ ở vỏ não đỉnh trái` [[1341, 1375]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `Natriclori` [[1486, 1496]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `0.9 %` [[1497, 1502]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]

### New in v7

- `0.9 %` [[1497, 1502]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `nay` [[1115, 1118]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `đến khám vì tăng calci máu` [[263, 289]] TRIỆU_CHỨNG cand=None asrt=['isHistorical']
- `ngay` [[983, 987]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `12.3` [[1245, 1249]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]
- `Natriclori` [[1486, 1496]] TÊN_XÉT_NGHIỆM cand=None asrt=[]
- `12.0` [[1196, 1200]] KẾT_QUẢ_XÉT_NGHIỆM cand=None asrt=[]

### Removed from v6

- `hình ảnh  nhồi máu cũ nhỏ ở vỏ não đỉnh trái nhưng không có quá trình cấp tính` [[1331, 1409]] KẾT_QUẢ_XÉT_NGHIỆM

### Changed

- `creatinine` type TÊN_XÉT_NGHIỆM->THUỐC; cand None->['2913']; asrt []->['isHistorical']
- `cường cận giáp nguyên phát` type TRIỆU_CHỨNG->CHẨN_ĐOÁN; cand None->['E210']; asrt ['isHistorical']->['isHistorical']
- `cơn đau thắt ngực` type TRIỆU_CHỨNG->CHẨN_ĐOÁN; cand None->['I20']; asrt ['isHistorical']->['isHistorical']
- `Xơ vữa động mạch` type TRIỆU_CHỨNG->CHẨN_ĐOÁN; cand None->['I70']; asrt ['isHistorical']->['isHistorical']


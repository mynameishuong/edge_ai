# Task breakdown và bản đồ review AI-VIDS

Cập nhật 31/10/2026. Phạm vi tài liệu: phần đã làm + việc còn lại để đi tới Pi staging và production có kiểm chứng. Không thực thi thêm task triển khai khi tạo tài liệu này.

**Quy ước tỉ lệ:** % là ước lượng phân bổ công sức tương đối cho toàn bộ phạm vi trong bảng, tổng 100%; không phải % hoàn thành, % accuracy, diện tích sơ đồ hay cam kết thời gian. Chưa đủ dữ liệu để chốt man-day. Các task bằng % nhau vẫn có thể khác nhau về rủi ro/phụ thuộc.

**Trạng thái:** Đã kiểm local; Một phần; Đã chuẩn bị; chưa chạy đích; Chưa làm; Có kết quả chưa đạt. “Đã kiểm local” chỉ đúng với scope local ghi trong task; không tự chuyển thành đã đạt trên Pi/xe thật.

**Cách đánh số:** T01–T38 theo vị trí block kiến trúc, không phải thứ tự bắt buộc triển khai. Xem phụ thuộc và các mốc làm tiếp. A1/A2/A3 là các nguồn hoặc cấp kiểm thử thay thế: CSV, vcan, CAN vật lý.

[Mở bản review tương tác](TASK_REVIEW.html) · [Sơ đồ có mã tham chiếu](architecture.svg) · [Thiết kế A–Z](ARCHITECTURE.vi.md) · [Kết quả hiện tại](VALIDATION.vi.md)

## Đọc kiến trúc theo ba luồng

- Runtime: **A1/A2/A3 → B1 → B2 → B3 → (B4 + B5) → B6 → C2 → C1**.
- Training: **D1 → D2 → D3 → D4 → B4**; train trên PC, inference trên edge.
- Chuyển sang Pi/vận hành: **A4 → B4 parity → A2 → A3 → C3/C4 → D5**. Đây là lộ trình; xem dependency từng task để biết các nhánh cần đủ trước khi nghiệm thu.

## Tỉ lệ theo bốn vùng trên sơ đồ

| Vùng | Công sức ước lượng | Ý nghĩa |
|---|---:|---|
| A | 18% | Nguồn dữ liệu & phần cứng |
| B | 30% | Lõi xử lý trên Edge |
| C | 22% | Hiển thị, bằng chứng & vận hành |
| D | 30% | Dữ liệu train, model & phát hành |

## Bản đồ block → task

| Block trên arch | Tên block | Tỉ lệ | Task |
|---|---|---:|---|
| [A1](architecture.svg#arch-A1) | Dữ liệu đầu vào mô phỏng | 4% | [T01](#t01), [T02](#t02) |
| [A2](architecture.svg#arch-A2) | Phòng lab vcan | 5% | [T03](#t03), [T04](#t04) |
| [A3](architecture.svg#arch-A3) | CAN testbench phần cứng | 6% | [T05](#t05), [T06](#t06) |
| [A4](architecture.svg#arch-A4) | Môi trường chạy trên Pi | 3% | [T07](#t07) |
| [B1](architecture.svg#arch-B1) | Thu nhận frame | 6% | [T08](#t08), [T09](#t09) |
| [B2](architecture.svg#arch-B2) | Clock và chia cửa sổ | 4% | [T10](#t10), [T11](#t11) |
| [B3](architecture.svg#arch-B3) | Trích đặc trưng | 7% | [T12](#t12), [T13](#t13) |
| [B4](architecture.svg#arch-B4) | Inference C++ | 5% | [T14](#t14), [T15](#t15) |
| [B5](architecture.svg#arch-B5) | Rule và profile | 3% | [T16](#t16), [T17](#t17) |
| [B6](architecture.svg#arch-B6) | Quyết định và health | 5% | [T18](#t18), [T19](#t19) |
| [C1](architecture.svg#arch-C1) | Dashboard replay/live | 5% | [T20](#t20), [T21](#t21) |
| [C2](architecture.svg#arch-C2) | Event và evidence | 6% | [T22](#t22), [T23](#t23) |
| [C3](architecture.svg#arch-C3) | Đo chất lượng và hiệu năng | 6% | [T24](#t24), [T25](#t25) |
| [C4](architecture.svg#arch-C4) | Queue và xử lý lỗi | 5% | [T26](#t26), [T27](#t27) |
| [D1](architecture.svg#arch-D1) | Thu thập dữ liệu đại diện | 6% | [T28](#t28), [T29](#t29) |
| [D2](architecture.svg#arch-D2) | Chia tập và tạo feature dataset | 5% | [T30](#t30), [T31](#t31) |
| [D3](architecture.svg#arch-D3) | Train và đánh giá model | 9% | [T32](#t32), [T33](#t33), [T34](#t34) |
| [D4](architecture.svg#arch-D4) | Artifact và gói chuyển nền tảng | 5% | [T35](#t35), [T36](#t36) |
| [D5](architecture.svg#arch-D5) | Staging và phát hành | 5% | [T37](#t37), [T38](#t38) |

## Bằng chứng và phạm vi đã có

- 12 unit/integration tests đạt trên PC; 1.660 score windows đối chiếu C++/sklearn, max error 1.11e-16.
- UI replay chạy 460 windows, kiểm browser desktop/mobile; tất cả vẫn là dữ liệu tổng hợp.
- Gói Pi có inventory/checksum từng file; checker 32 golden windows đã chạy local, chưa chạy trên Pi.
- Chưa runtime-test SocketCAN trên Linux/Pi, chưa CAN phần cứng, chưa benchmark Pi, chưa live dashboard.
- **Chưa đạt:** payload shift chỉ 1/40 window vượt ML threshold, chưa có confirmed ALERT. Flooding/unknown ID hiện được rule bắt.

## Thứ tự làm tiếp đề xuất

1. **Review 0:** bạn đọc arch/task, chốt phạm vi lab, nguồn dữ liệu và tiêu chí recall/false alarm/delay; chưa tự đưa lên production.
2. **Mốc 1 — chứng minh runtime trên Pi:** T07 → T15; song song về mặt kế hoạch có thể chuẩn bị T28/T29, T05. Chỉ chạy trên Pi khi phạm vi bước này đã được chốt.
3. **Mốc 2 — live input trong lab:** T03/T09 → T04; T05/T06 khi có adapter. Review clock/window và health: T10/T19.
4. **Mốc 3 — làm model có ý nghĩa:** T28/T29 → T30/T31 → T13/T17 → T33 → T34. Chốt ngưỡng nghiệm thu trước tuning; chưa đạt thì quay lại feature/model, không promote.
5. **Mốc 4 — quan sát và độ bền:** T22/T21/T23/T26/T27; T24/T25 cung cấp bằng chứng chất lượng và hiệu năng.
6. **Mốc 5 — review staging/release:** T35/T37; T38 chỉ sau khi điều kiện vận hành đạt và có chấp thuận production.

## Chi tiết từng task

<a id="t01"></a>
### T01 — Chốt hợp đồng dữ liệu CAN

**Arch:** [A1](architecture.svg#arch-A1) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Mọi module phải hiểu thống nhất timestamp, ID, DLC và payload.
- **Outcome cần bàn giao:** CSV schema v1: timestamp_us, can_id_hex, dlc, data_hex, label; giới hạn Classic CAN standard 11-bit.
- **Outcome dùng để:** Làm đầu vào chung cho replay, capture adapter và xử lý dataset.
- **Review/điều kiện đạt:** Frame hợp lệ được đọc; timestamp âm/đảo, DLC sai và ID ngoài phạm vi bị từ chối.
- **Phụ thuộc:** Không có task tiền nhiệm bắt buộc trong bảng.
- **Bằng chứng hiện tại:** src/main.cpp: parse_frame; tests/test_pipeline.py; docs/ARCHITECTURE.vi.md mục F

<a id="t02"></a>
### T02 — Tạo dữ liệu và replay có thể lặp lại

**Arch:** [A1](architecture.svg#arch-A1) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Có thể kiểm tra toàn pipeline khi chưa nối Pi hoặc CAN thật.
- **Outcome cần bàn giao:** Các phiên train/validation/test/demo tổng hợp độc lập; replay nhanh và realtime.
- **Outcome dùng để:** Tái hiện lỗi và review logic bằng cùng một đầu vào.
- **Review/điều kiện đạt:** Demo phát 460 window; realtime chỉ phát kết quả sau cuối window; label không tham gia inference.
- **Phụ thuộc:** T01
- **Bằng chứng hiện tại:** tools/prepare.py: generate; src/main.cpp: read_csv/replay; tests/test_pipeline.py

<a id="t03"></a>
### T03 — Chuẩn bị vcan trên Linux/Pi

**Arch:** [A2](architecture.svg#arch-A2) · **Tỉ lệ:** 2% · **Trạng thái:** Đã chuẩn bị; chưa chạy đích

- **Ý nghĩa:** Tách lỗi socket/Linux khỏi lỗi dây, transceiver và bitrate.
- **Outcome cần bàn giao:** vcan0 hoạt động cùng checklist setup và teardown trên thiết bị đích.
- **Outcome dùng để:** Làm môi trường đầu tiên để chạy capture SocketCAN thật.
- **Review/điều kiện đạt:** Có log ip link, candump và frame nhận qua executable trên Linux/Pi.
- **Phụ thuộc:** T07
- **Bằng chứng hiện tại:** docs/DEPLOY_RASPBERRY_PI.vi.md mục 5; chưa có log chạy trên Pi

<a id="t04"></a>
### T04 — Viết virtual ECU và kịch bản vcan có ground truth

**Arch:** [A2](architecture.svg#arch-A2) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Frame gửi tay không đủ kiểm tra timing, recall hay detection delay.
- **Outcome cần bàn giao:** Traffic normal có chu kỳ, kịch bản bất thường trong lab, timestamp onset và expected behavior.
- **Outcome dùng để:** Cấp nguồn kiểm thử live có thể đo và tái lập.
- **Review/điều kiện đạt:** Kịch bản chạy lặp lại được; ground truth độc lập với output IDS; không gửi ra can0.
- **Phụ thuộc:** T03, T01
- **Bằng chứng hiện tại:** Chưa có test harness phát virtual ECU; generate hiện chỉ xuất CSV

<a id="t05"></a>
### T05 — Chọn adapter và chốt sơ đồ điện CAN lab

**Arch:** [A3](architecture.svg#arch-A3) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Pi không đọc CAN_H/CAN_L trực tiếp; phần cứng và driver phải khớp.
- **Outcome cần bàn giao:** BOM theo thiết bị thực, sơ đồ nối dây, termination, nguồn/reference và driver cần dùng.
- **Outcome dùng để:** Tránh nhầm lỗi phần cứng thành lỗi AI hoặc SocketCAN.
- **Review/điều kiện đạt:** Review đúng model adapter, listen-only, bitrate và topology; chưa chọn mua thay bạn.
- **Phụ thuộc:** Không có task tiền nhiệm bắt buộc trong bảng.
- **Bằng chứng hiện tại:** docs/ARCHITECTURE.vi.md mục C có thiết kế; chưa có BOM phần cứng được chốt

<a id="t06"></a>
### T06 — Bring-up can0 và xác nhận đường nhận vật lý

**Arch:** [A3](architecture.svg#arch-A3) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Cần chứng minh frame thực đi từ bus qua adapter vào Pi.
- **Outcome cần bàn giao:** Capture mẫu trên testbench, cấu hình interface và thống kê lỗi/drop.
- **Outcome dùng để:** Cho phép thay nguồn vcan bằng CAN vật lý sau khi đường nhận đạt.
- **Review/điều kiện đạt:** candump khớp nguồn lab; bitrate đúng; controller listen-only nếu yêu cầu thụ động; ghi nhận lỗi bus.
- **Phụ thuộc:** T05, T07, T09
- **Bằng chứng hiện tại:** docs/DEPLOY_RASPBERRY_PI.vi.md mục 6 là hướng dẫn, chưa có capture phần cứng

<a id="t07"></a>
### T07 — Kiểm tra OS và build native trên Pi

**Arch:** [A4](architecture.svg#arch-A4) · **Tỉ lệ:** 3% · **Trạng thái:** Đã chuẩn bị; chưa chạy đích

- **Ý nghĩa:** Executable Windows không chạy được trên Pi ARM64.
- **Outcome cần bàn giao:** Ghi cấu hình OS/CPU/RAM; binary C++17 build native trên Pi.
- **Outcome dùng để:** Tạo runtime đúng thiết bị để chạy replay và capture.
- **Review/điều kiện đạt:** Xác nhận aarch64/64-bit, build/link thành công và executable chạy được trên chính Pi.
- **Phụ thuộc:** Không có task tiền nhiệm bắt buộc trong bảng.
- **Bằng chứng hiện tại:** CMakeLists.txt; docs/DEPLOY_RASPBERRY_PI.vi.md mục 2–4; mới có object cross-compile ARM64

<a id="t08"></a>
### T08 — Parser và source adapter CSV

**Arch:** [B1](architecture.svg#arch-B1) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Frame phải được chuẩn hóa trước khi vào feature pipeline.
- **Outcome cần bàn giao:** C++ Frame và CSV source adapter có lỗi input rõ ràng.
- **Outcome dùng để:** Làm baseline kiểm tra xử lý dữ liệu độc lập phần cứng.
- **Review/điều kiện đạt:** Golden input, DLC 0, input sai và thứ tự timestamp đều được kiểm thử.
- **Phụ thuộc:** T01
- **Bằng chứng hiện tại:** src/main.cpp: Frame/parse_frame/read_csv; tests/test_pipeline.py

<a id="t09"></a>
### T09 — Receiver SocketCAN và quan sát frame bị bỏ

**Arch:** [B1](architecture.svg#arch-B1) · **Tỉ lệ:** 4% · **Trạng thái:** Đã chuẩn bị; chưa chạy đích

- **Ý nghĩa:** Đưa frame Linux live vào cùng pipeline đang chạy replay.
- **Outcome cần bàn giao:** socket/bind/poll/recvmsg; lọc frame v1; counter rx_drops và ignored_frames.
- **Outcome dùng để:** Nối kernel CAN với feature/inference trên edge.
- **Review/điều kiện đạt:** Chạy integration test trên vcan rồi can0; ngắt interface phải báo lỗi; drop/ignored counter kiểm chứng được.
- **Phụ thuộc:** T03, T08
- **Bằng chứng hiện tại:** src/main.cpp: capture; đã compile nhánh Linux thành object, chưa runtime-test

<a id="t10"></a>
### T10 — Chốt clock và timestamp live

**Arch:** [B2](architecture.svg#arch-B2) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Timing sai làm feature sai và báo detection delay không đáng tin.
- **Outcome cần bàn giao:** Clock contract; phương án kernel/hardware timestamp, monotonic mapping và xử lý clock discontinuity.
- **Outcome dùng để:** Tính IAT, ordering và delay có cùng miền clock.
- **Review/điều kiện đạt:** Không trừ timestamp khác clock domain; đo được sai số receipt timestamp dưới tải.
- **Phụ thuộc:** T09
- **Bằng chứng hiện tại:** Live hiện dùng steady_clock tại user space; chưa có kernel/hardware timestamp

<a id="t11"></a>
### T11 — Window engine 100 ms

**Arch:** [B2](architecture.svg#arch-B2) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** AI cần vector theo một khoảng thời gian xác định thay vì frame rời.
- **Outcome cần bàn giao:** Tumbling window 100 ms, quy tắc biên, window rỗng và EOF rõ ràng.
- **Outcome dùng để:** Làm đơn vị tính feature, inference và quyết định.
- **Review/điều kiện đạt:** Frame đúng biên vào window mới; gap sinh window rỗng; final partial window bị bỏ như contract.
- **Phụ thuộc:** T08
- **Bằng chứng hiện tại:** src/main.cpp: Extractor::advance/finish; tests/test_pipeline.py

<a id="t12"></a>
### T12 — Feature toàn cục v1 dùng chung train/runtime

**Arch:** [B3](architecture.svg#arch-B3) · **Tỉ lệ:** 3% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Ngăn lệch công thức giữa notebook train và executable triển khai.
- **Outcome cần bàn giao:** 8 feature float32: rate, ID diversity/entropy/share, byte stats, bit flip và same-ID IAT.
- **Outcome dùng để:** Cấp input có cùng schema cho Python training và C++ inference.
- **Review/điều kiện đạt:** Golden vector tính tay đạt; thứ tự/đơn vị/reset/giá trị thiếu được ghi rõ.
- **Phụ thuộc:** T11
- **Bằng chứng hiện tại:** src/main.cpp: Extractor; docs/ARCHITECTURE.vi.md mục G; tools/prepare.py: FEATURES

<a id="t13"></a>
### T13 — Feature theo từng ID/signal và ngữ cảnh

**Arch:** [B3](architecture.svg#arch-B3) · **Tỉ lệ:** 4% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Feature tổng hợp có thể làm loãng thay đổi của một ID; model hiện bắt yếu payload shift.
- **Outcome cần bàn giao:** Candidate schema v2: period error, counter continuity, per-ID payload; DBC/signal checks khi có dữ liệu.
- **Outcome dùng để:** Cải thiện phát hiện thay đổi tinh vi và giải thích được dấu hiệu.
- **Review/điều kiện đạt:** Feature train/runtime vẫn khớp; đánh giá trên validation riêng; không giải mã RPM/speed khi thiếu DBC đúng.
- **Phụ thuộc:** T28, T29, T12
- **Bằng chứng hiện tại:** Hạn chế được đo trong docs/VALIDATION.vi.md: payload shift 1/40 window vượt ngưỡng

<a id="t14"></a>
### T14 — Export cây và inference C++

**Arch:** [B4](architecture.svg#arch-B4) · **Tỉ lệ:** 3% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Inference trên edge cần độc lập với môi trường Python training.
- **Outcome cần bàn giao:** Forest loader, kiểm schema/topology, tính path length và anomaly score.
- **Outcome dùng để:** Chạy model trực tiếp trong executable C++ trên PC/Pi.
- **Review/điều kiện đạt:** Max abs error so với sklearn ≤1e-7; model không hợp lệ phải fail rõ ràng.
- **Phụ thuộc:** T12, T32
- **Bằng chứng hiện tại:** src/main.cpp: Forest; tools/prepare.py; 1660 window parity, max error 1.11e-16

<a id="t15"></a>
### T15 — Xác nhận score parity trên Pi

**Arch:** [B4](architecture.svg#arch-B4) · **Tỉ lệ:** 2% · **Trạng thái:** Đã chuẩn bị; chưa chạy đích

- **Ý nghĩa:** Compile được chưa chứng minh hành vi số học đúng trên thiết bị đích.
- **Outcome cần bàn giao:** Báo cáo checksum và 32 golden score trên native binary Pi.
- **Outcome dùng để:** Cho phép chuyển từ local inference sang kiểm thử edge thực.
- **Review/điều kiện đạt:** tools/verify_pi_bundle.py PASS trên Pi, score error ≤1e-7 và metadata đúng thiết bị.
- **Phụ thuộc:** T07, T14, T36
- **Bằng chứng hiện tại:** tools/verify_pi_bundle.py; đã PASS Windows, chưa chạy Pi

<a id="t16"></a>
### T16 — Rule baseline cho demo

**Arch:** [B5](architecture.svg#arch-B5) · **Tỉ lệ:** 1% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Một số dấu hiệu rõ ràng nên phát hiện và giải thích trực tiếp.
- **Outcome cần bàn giao:** Rule unknown_id và possible_flooding với profile tổng hợp.
- **Outcome dùng để:** Đối chứng rule-only và bảo đảm AI không phải nguồn quyết định duy nhất.
- **Review/điều kiện đạt:** Flooding/ID lạ có reason tương ứng; không gọi kết quả rule là kết quả model.
- **Phụ thuộc:** T11
- **Bằng chứng hiện tại:** src/main.cpp: Detector::emit; docs/VALIDATION.vi.md bảng kịch bản

<a id="t17"></a>
### T17 — Profile và rule đúng mạng lab

**Arch:** [B5](architecture.svg#arch-B5) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Whitelist/rate threshold toy không đại diện mọi xe hoặc mọi bus.
- **Outcome cần bàn giao:** Profile versioned cho ID, chu kỳ/rate và rule signal khi có DBC/ngữ cảnh.
- **Outcome dùng để:** Giảm false alert và làm cảnh báo có ý nghĩa với testbench thực.
- **Review/điều kiện đạt:** Profile xuất phát từ normal lab đã review; rule được test bằng positive/negative cases.
- **Phụ thuộc:** T28, T29, T06, T16
- **Bằng chứng hiện tại:** Đang hardcode ngưỡng demo >1800 frames/s; whitelist demo ở model header

<a id="t18"></a>
### T18 — Fusion rule/AI và debounce cảnh báo

**Arch:** [B6](architecture.svg#arch-B6) · **Tỉ lệ:** 3% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Một spike score không nên tự tạo chuỗi cảnh báo liên tục.
- **Outcome cần bàn giao:** State machine HEALTHY/SUSPECT/ALERT, ML cần 2 window; clear sau 5 normal; hard rule tức thời tại cuối window.
- **Outcome dùng để:** Biến score/rule thành trạng thái cảnh báo ổn định và kiểm chứng được.
- **Review/điều kiện đạt:** Có state transition tests; reason window hiện tại phân biệt với alarm còn latch.
- **Phụ thuộc:** T14, T16
- **Bằng chứng hiện tại:** src/main.cpp: Detector::emit; tests/test_pipeline.py; docs/ARCHITECTURE.vi.md mục J

<a id="t19"></a>
### T19 — Tách health khỏi alarm và theo dõi mất dữ liệu

**Arch:** [B6](architecture.svg#arch-B6) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** NO_DATA không phải attack và không nên làm mất alarm đang mở.
- **Outcome cần bàn giao:** sensor_health độc lập alarm_state; dữ liệu thiếu/drop được gắn degraded.
- **Outcome dùng để:** Tránh hiển thị healthy hoặc mất lịch sử khi sensor ngừng nhận.
- **Review/điều kiện đạt:** Silence/disconnect/drop không xóa alarm; health và alarm có test độc lập.
- **Phụ thuộc:** T09, T18
- **Bằng chứng hiện tại:** Có NO_DATA và counter; hiện vẫn dùng một state chung, chưa tách hai state

<a id="t20"></a>
### T20 — Dashboard review replay

**Arch:** [C1](architecture.svg#arch-C1) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Cần nhìn thấy traffic, score, state và giới hạn khi review local.
- **Outcome cần bàn giao:** UI replay 46 s, biểu đồ, model-only P95, kiến trúc và kết quả kiểm chứng.
- **Outcome dùng để:** Review logic đầu cuối trước khi nối phần cứng.
- **Review/điều kiện đạt:** 460 event, không lỗi JS; layout desktop/mobile đạt; ghi rõ dữ liệu mô phỏng.
- **Phụ thuộc:** T02, T18
- **Bằng chứng hiện tại:** ui/index.html; tools/serve.py; tests/browser_smoke.py; docs/local-demo.png

<a id="t21"></a>
### T21 — Dashboard nguồn CAN live

**Arch:** [C1](architecture.svg#arch-C1) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** UI hiện không tự thấy output từ capture can0.
- **Outcome cần bàn giao:** Source selector/capture lifecycle, NDJSON live vào API, UI phân biệt replay/live và nguồn metrics.
- **Outcome dùng để:** Quan sát vận hành Pi khi đang nhận CAN thật.
- **Review/điều kiện đạt:** UI khớp event capture; disconnect/stop xử lý được; không gán metadata replay hoặc số đo PC cho Pi.
- **Phụ thuộc:** T09, T19, T22, T20
- **Bằng chứng hiện tại:** tools/serve.py hiện chỉ gọi replay subprocess

<a id="t22"></a>
### T22 — Chuẩn hóa event/alert contract

**Arch:** [C2](architecture.svg#arch-C2) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Một window ALERT khác với một sự kiện tấn công duy nhất.
- **Outcome cần bàn giao:** Event có window/model/profile/clock/data quality; alert opened/updated/closed và ID liên kết.
- **Outcome dùng để:** Cho UI, logger và evaluator đếm/correlate cùng một sự kiện.
- **Review/điều kiện đạt:** Window và attack event không bị đếm lẫn; truy được model/profile gây quyết định.
- **Phụ thuộc:** T18, T19
- **Bằng chứng hiện tại:** Có NDJSON per-window và window_end_ms; chưa có alert lifecycle/model version trong từng event

<a id="t23"></a>
### T23 — Evidence và retention

**Arch:** [C2](architecture.svg#arch-C2) · **Tỉ lệ:** 4% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Score đơn lẻ không đủ điều tra; log không giới hạn có thể đầy ổ đĩa.
- **Outcome cần bàn giao:** Raw pre/post-event buffer, event index và rotation theo dung lượng/thời gian.
- **Outcome dùng để:** Từ một alert xem lại được frame liên quan, trong ngân sách lưu trữ đã chốt.
- **Review/điều kiện đạt:** Evidence khớp event ID và thời gian; không tăng RAM/disk vô hạn; có hành vi khi disk full.
- **Phụ thuộc:** T22, T26
- **Bằng chứng hiện tại:** Hiện chỉ NDJSON của lượt replay gần nhất; chưa raw ring buffer/rotation

<a id="t24"></a>
### T24 — Báo cáo chất lượng nhận diện

**Arch:** [C3](architecture.svg#arch-C3) · **Tỉ lệ:** 3% · **Trạng thái:** Một phần

- **Ý nghĩa:** Test pipeline PASS không đồng nghĩa model phát hiện tốt.
- **Outcome cần bàn giao:** Precision/recall/F1 theo window và event, false alerts/giờ, detection delay và các case miss.
- **Outcome dùng để:** Căn cứ quyết định model/profile có đủ dùng cho lab hay không.
- **Review/điều kiện đạt:** Tách AI-only/rule-only/fused; công bố thời lượng normal và số attack; đánh giá holdout độc lập.
- **Phụ thuộc:** T34, T22
- **Bằng chứng hiện tại:** docs/VALIDATION.vi.md có synthetic window results; chưa quality report dữ liệu thực

<a id="t25"></a>
### T25 — Benchmark tài nguyên và thời gian trên Pi

**Arch:** [C3](architecture.svg#arch-C3) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** PC P95 không cho biết throughput hay nhiệt/throttling của Pi.
- **Outcome cần bàn giao:** Pi report: model/full-pipeline latency, detection delay, frame/drop rate, CPU/RSS/nhiệt/disk.
- **Outcome dùng để:** Chốt tải đáp ứng được và ngân sách tài nguyên edge.
- **Review/điều kiện đạt:** Ghi đúng cấu hình Pi/OS/adapter; tách replay/vcan/CAN; đối chiếu mục tiêu đã được chốt.
- **Phụ thuộc:** T15, T04, T06
- **Bằng chứng hiện tại:** Hiện chỉ số đo model-only trên PC; chưa benchmark Pi

<a id="t26"></a>
### T26 — Bounded queues và logger bất đồng bộ

**Arch:** [C4](architecture.svg#arch-C4) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Ghi stdout/disk chậm hiện có thể chặn đường nhận frame.
- **Outcome cần bàn giao:** Capture queue và event queue có giới hạn, policy overflow và counter riêng.
- **Outcome dùng để:** Giữ đường nhận ổn định khi model/UI/logger có độ trễ.
- **Review/điều kiện đạt:** Stress test logger chậm; memory bounded; mọi frame/event drop quan sát được.
- **Phụ thuộc:** T09, T22
- **Bằng chứng hiện tại:** Runtime hiện là một luồng đồng bộ; chưa có SPSC queue/logger worker

<a id="t27"></a>
### T27 — Fault injection và phục hồi

**Arch:** [C4](architecture.svg#arch-C4) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Hệ thống cần báo sai/lỗi rõ ràng ngoài happy path.
- **Outcome cần bàn giao:** Test matrix: input/model hỏng, interface down, queue overflow, disk full, process restart.
- **Outcome dùng để:** Xác nhận lỗi không bị diễn giải thành normal và có quy trình recovery.
- **Review/điều kiện đạt:** Mỗi fault có expected state, log, exit/restart behavior và bằng chứng chạy trên đích.
- **Phụ thuộc:** T19, T23, T26
- **Bằng chứng hiện tại:** Đã test parser/model lỗi local; chưa interface/disk/queue/restart trên Pi

<a id="t28"></a>
### T28 — Chốt và lấy nguồn dữ liệu đại diện

**Arch:** [D1](architecture.svg#arch-D1) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Model toy không học hành vi thật của mạng CAN đích.
- **Outcome cần bàn giao:** Data registry cho HCRL/ROAD hoặc normal/attack lab captures; nguồn, điều kiện sử dụng và version.
- **Outcome dùng để:** Cung cấp đầu vào có provenance để train và đánh giá.
- **Review/điều kiện đạt:** File dữ liệu thực có sẵn và được nhận diện đúng; phạm vi xe/bus/label được mô tả.
- **Phụ thuộc:** Không có task tiền nhiệm bắt buộc trong bảng.
- **Bằng chứng hiện tại:** docs/ARCHITECTURE.vi.md có nguồn tham khảo; chưa tải/đưa dữ liệu thực vào pipeline

<a id="t29"></a>
### T29 — Adapter dataset và kiểm tra chất lượng dữ liệu

**Arch:** [D1](architecture.svg#arch-D1) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Mỗi bộ dữ liệu có format, clock và nhãn khác nhau.
- **Outcome cần bàn giao:** Converter về schema chung, kiểm monotonic/DLC/missing/duplicate và metadata onset/event.
- **Outcome dùng để:** Bảo đảm model học dữ liệu hợp lệ và evaluator có ground truth.
- **Review/điều kiện đạt:** Spot-check với raw source; label không đi vào feature; có báo cáo dữ liệu bị loại.
- **Phụ thuộc:** T28, T01
- **Bằng chứng hiện tại:** Chưa có HCRL/ROAD converter hoặc capture-normalizer lab

<a id="t30"></a>
### T30 — Split theo phiên và chống data leakage

**Arch:** [D2](architecture.svg#arch-D2) · **Tỉ lệ:** 3% · **Trạng thái:** Một phần

- **Ý nghĩa:** Random split frame gần nhau dễ làm kết quả đánh giá đẹp giả.
- **Outcome cần bàn giao:** Manifest train/validation/test theo capture/session/thời gian; purge nếu dùng overlapping window.
- **Outcome dùng để:** Giữ test thực sự chưa được dùng để fit/tune.
- **Review/điều kiện đạt:** Không trùng capture/event hoặc overlapping context giữa tập; threshold không chỉnh theo final test.
- **Phụ thuộc:** T29
- **Bằng chứng hiện tại:** Demo dùng seed/phiên riêng; chưa split/audit leakage trên dữ liệu thực

<a id="t31"></a>
### T31 — Tạo feature dataset có version

**Arch:** [D2](architecture.svg#arch-D2) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Cần truy được model được train từ feature/schema và dữ liệu nào.
- **Outcome cần bàn giao:** Feature CSV/metadata theo split, schema version và data fingerprint.
- **Outcome dùng để:** Tái lập training và phát hiện schema mismatch khi deploy.
- **Review/điều kiện đạt:** Dùng đúng extractor runtime; có row/window counts, units/order và provenance kiểm tra được.
- **Phụ thuộc:** T30, T12
- **Bằng chứng hiện tại:** Cùng C++ extractor đã dùng; chưa hoàn chỉnh fingerprint/lineage cho dataset thực

<a id="t32"></a>
### T32 — Train baseline Isolation Forest normal-only

**Arch:** [D3](architecture.svg#arch-D3) · **Tỉ lệ:** 2% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Có một model nhẹ và quy trình train làm baseline so sánh.
- **Outcome cần bàn giao:** Model fitted trên normal train, tham số cố định và seed/version được ghi.
- **Outcome dùng để:** Đưa anomaly detection vào pipeline C++ thay vì chỉ rule.
- **Review/điều kiện đạt:** Không dùng attack label làm feature; fit chỉ train split; tái lập được artifact demo.
- **Phụ thuộc:** T12, T02
- **Bằng chứng hiện tại:** tools/prepare.py; demo 64 trees/max_samples 128; mới trên dữ liệu tổng hợp

<a id="t33"></a>
### T33 — Calibration và chọn candidate trên validation

**Arch:** [D3](architecture.svg#arch-D3) · **Tỉ lệ:** 3% · **Trạng thái:** Một phần

- **Ý nghĩa:** Ngưỡng/model phải được chọn theo dữ liệu và false-alarm budget, không theo cảm giác.
- **Outcome cần bàn giao:** So sánh baseline/candidate, threshold và rule profile trên validation riêng.
- **Outcome dùng để:** Chọn operating point trước khi mở final test.
- **Review/điều kiện đạt:** Có normal/attack validation, lý do chọn threshold và trade-off; freeze trước final test.
- **Phụ thuộc:** T31, T32, T13, T17
- **Bằng chứng hiện tại:** Demo dùng percentile 99.5 normal validation; chưa chọn candidate bằng dữ liệu lab

<a id="t34"></a>
### T34 — Đánh giá holdout và xử lý các case miss

**Arch:** [D3](architecture.svg#arch-D3) · **Tỉ lệ:** 4% · **Trạng thái:** Có kết quả chưa đạt

- **Ý nghĩa:** Phải chứng minh model đạt mục tiêu phát hiện, không chỉ export đúng.
- **Outcome cần bàn giao:** Holdout report + failure analysis; candidate pass/fail rõ cho từng kịch bản.
- **Outcome dùng để:** Chặn việc đẩy model còn yếu lên môi trường sử dụng thực.
- **Review/điều kiện đạt:** Đạt tiêu chí recall/false alarm/delay đã chốt trên holdout; không che case miss hoặc hạ ngưỡng theo test.
- **Phụ thuộc:** T33, T04
- **Bằng chứng hiện tại:** Payload shift chỉ 1/40 window vượt ML threshold, không confirmed ALERT; dữ liệu thực chưa đánh giá

<a id="t35"></a>
### T35 — Model bundle và metadata phiên bản

**Arch:** [D4](architecture.svg#arch-D4) · **Tỉ lệ:** 2% · **Trạng thái:** Một phần

- **Ý nghĩa:** Model phải đi cùng schema/profile/threshold tương thích.
- **Outcome cần bàn giao:** Forest + manifest + checksum + golden vectors; bổ sung model/data/profile/build version.
- **Outcome dùng để:** Nhận diện chính xác bộ model/runtime được review hoặc rollback.
- **Review/điều kiện đạt:** Runtime/artifact mismatch bị phát hiện; metadata đủ tái lập; hash không bị gọi nhầm là chữ ký.
- **Phụ thuộc:** T14, T32
- **Bằng chứng hiện tại:** models/manifest.json, .forest, pi-golden-*; chưa đầy đủ version/provenance và runtime hash enforcement

<a id="t36"></a>
### T36 — Đóng gói chuyển sang Pi và kiểm integrity

**Arch:** [D4](architecture.svg#arch-D4) · **Tỉ lệ:** 3% · **Trạng thái:** Đã kiểm local

- **Ý nghĩa:** Chuyển đúng source/model, không mang virtualenv hoặc executable Windows sang Pi.
- **Outcome cần bàn giao:** ai-vids-pi-review.tar.gz có inventory và checksum từng file; checker standard-library Python.
- **Outcome dùng để:** Giảm lỗi copy thủ công và tạo một gói review có thể xác minh.
- **Review/điều kiện đạt:** Archive chứa đúng file; hash khớp; local golden checker đạt; không tự SSH hay cài đặt.
- **Phụ thuộc:** T14, T20
- **Bằng chứng hiện tại:** tools/package_pi.py; tools/verify_pi_bundle.py; build/ai-vids-pi-review.tar.gz đã kiểm local

<a id="t37"></a>
### T37 — Chạy Pi staging và lưu biên bản review

**Arch:** [D5](architecture.svg#arch-D5) · **Tỉ lệ:** 2% · **Trạng thái:** Đã chuẩn bị; chưa chạy đích

- **Ý nghĩa:** Đưa code lên Pi là một lần kiểm chứng thiết bị đích, chưa phải production.
- **Outcome cần bàn giao:** Checklist replay → vcan → lab CAN; log kết quả và quyết định review.
- **Outcome dùng để:** Xác định phần nào thực sự đạt trên Pi trước khi vận hành dài hạn.
- **Review/điều kiện đạt:** Có kết quả trực tiếp từ Pi, giới hạn và quyết định tiếp tục rõ; việc chạy Pi nằm trong phạm vi được bạn chốt.
- **Phụ thuộc:** T15, T04, T06, T21, T24, T25
- **Bằng chứng hiện tại:** docs/DEPLOY_RASPBERRY_PI.vi.md; chưa thực hiện staging trên Pi

<a id="t38"></a>
### T38 — Service, rollback và cổng chấp thuận production

**Arch:** [D5](architecture.svg#arch-D5) · **Tỉ lệ:** 3% · **Trạng thái:** Chưa làm

- **Ý nghĩa:** Cần khởi động/phục hồi có kiểm soát và quay lại bản đã biết tốt.
- **Outcome cần bàn giao:** Service account/systemd, interface startup, restart limits, version activation/rollback và runbook.
- **Outcome dùng để:** Vận hành dài hạn với bản đã kiểm chứng và có đường phục hồi.
- **Review/điều kiện đạt:** Staging/soak đạt; rollback được test; bạn chấp thuận production trước khi triển khai.
- **Phụ thuộc:** T37, T23, T26, T27, T35
- **Bằng chứng hiện tại:** Chưa có service/installer/rollback tự động; chưa có chấp thuận production

## Cách review từng task

Với mỗi task, đối chiếu block trên arch, đọc ý nghĩa, mở evidence hiện có rồi xem điều kiện đạt. Ghi feedback theo mẫu `T13: đồng ý scope; cần bổ sung counter continuity; nghiệm thu bằng ...`. Task có code nhưng chưa log chạy trên Pi giữ trạng thái chưa kiểm đích.

Thay đổi tỉ lệ hoặc thêm/bớt scope phải cân lại tổng 100%; không dùng bảng công sức để báo tiến độ hoàn thành. Bảng này chưa bao gồm mọi hạng mục chứng nhận/đảm bảo của hệ thống automotive production đầy đủ.

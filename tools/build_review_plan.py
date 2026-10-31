"""Generate a reviewable WBS mapped to the architecture; no deployment actions."""
from html import escape
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
GROUPS=[
    {'id':'A','name':'Nguồn dữ liệu & phần cứng','weight':18},
    {'id':'B','name':'Lõi xử lý trên Edge','weight':30},
    {'id':'C','name':'Hiển thị, bằng chứng & vận hành','weight':22},
    {'id':'D','name':'Dữ liệu train, model & phát hành','weight':30},
]
NODE_ROWS=[
 ('A1',4,'Recorded / synthetic traffic','Dữ liệu đầu vào mô phỏng'),
 ('A2',5,'Isolated Linux lab','Phòng lab vcan'),
 ('A3',6,'Physical CAN testbench','CAN testbench phần cứng'),
 ('A4',3,'CAN adapter → Pi 4','Môi trường chạy trên Pi'),
 ('B1',6,'Frame acquisition / source adapter','Thu nhận frame'),
 ('B2',4,'Validate → timestamp → window','Clock và chia cửa sổ'),
 ('B3',7,'Feature extraction / schema v1','Trích đặc trưng'),
 ('B4',5,'Isolation Forest','Inference C++'),
 ('B5',3,'Rule baseline','Rule và profile'),
 ('B6',5,'Decision + health state machine','Quyết định và health'),
 ('C1',5,'Review dashboard','Dashboard replay/live'),
 ('C2',6,'Event stream / evidence','Event và evidence'),
 ('C3',6,'Operational visibility','Đo chất lượng và hiệu năng'),
 ('C4',5,'Production hardening gate','Queue và xử lý lỗi'),
 ('D1',6,'Collect & curate','Thu thập dữ liệu đại diện'),
 ('D2',5,'Build normal feature sets','Chia tập và tạo feature dataset'),
 ('D3',9,'Train → export → verify','Train và đánh giá model'),
 ('D4',5,'Versioned artifact','Artifact và gói chuyển nền tảng'),
 ('D5',5,'Review → Pi → release','Staging và phát hành'),
]
NODES=[dict(id=i,weight=w,title=t,name=n) for i,w,t,n in NODE_ROWS]
STATUSES={
 'verified':'Đã kiểm local',
 'partial':'Một phần',
 'ready':'Đã chuẩn bị; chưa chạy đích',
 'todo':'Chưa làm',
 'gap':'Có kết quả chưa đạt',
}
TASKS=[]


def task(i,node,weight,name,why,outcome,use,accept,status,deps='',evidence=''):
    TASKS.append(dict(id=f'T{i:02}',node=node,weight=weight,name=name,why=why,outcome=outcome,
                      use=use,accept=accept,status=status,
                      deps=deps.split() if deps else [],evidence=evidence))


task(1,'A1',2,'Chốt hợp đồng dữ liệu CAN',
 'Mọi module phải hiểu thống nhất timestamp, ID, DLC và payload.',
 'CSV schema v1: timestamp_us, can_id_hex, dlc, data_hex, label; giới hạn Classic CAN standard 11-bit.',
 'Làm đầu vào chung cho replay, capture adapter và xử lý dataset.',
 'Frame hợp lệ được đọc; timestamp âm/đảo, DLC sai và ID ngoài phạm vi bị từ chối.',
 'verified',evidence='src/main.cpp: parse_frame; tests/test_pipeline.py; docs/ARCHITECTURE.vi.md mục F')
task(2,'A1',2,'Tạo dữ liệu và replay có thể lặp lại',
 'Có thể kiểm tra toàn pipeline khi chưa nối Pi hoặc CAN thật.',
 'Các phiên train/validation/test/demo tổng hợp độc lập; replay nhanh và realtime.',
 'Tái hiện lỗi và review logic bằng cùng một đầu vào.',
 'Demo phát 460 window; realtime chỉ phát kết quả sau cuối window; label không tham gia inference.',
 'verified','T01','tools/prepare.py: generate; src/main.cpp: read_csv/replay; tests/test_pipeline.py')
task(3,'A2',2,'Chuẩn bị vcan trên Linux/Pi',
 'Tách lỗi socket/Linux khỏi lỗi dây, transceiver và bitrate.',
 'vcan0 hoạt động cùng checklist setup và teardown trên thiết bị đích.',
 'Làm môi trường đầu tiên để chạy capture SocketCAN thật.',
 'Có log ip link, candump và frame nhận qua executable trên Linux/Pi.',
 'ready','T07','docs/DEPLOY_RASPBERRY_PI.vi.md mục 5; chưa có log chạy trên Pi')
task(4,'A2',3,'Viết virtual ECU và kịch bản vcan có ground truth',
 'Frame gửi tay không đủ kiểm tra timing, recall hay detection delay.',
 'Traffic normal có chu kỳ, kịch bản bất thường trong lab, timestamp onset và expected behavior.',
 'Cấp nguồn kiểm thử live có thể đo và tái lập.',
 'Kịch bản chạy lặp lại được; ground truth độc lập với output IDS; không gửi ra can0.',
 'todo','T03 T01','Chưa có test harness phát virtual ECU; generate hiện chỉ xuất CSV')
task(5,'A3',3,'Chọn adapter và chốt sơ đồ điện CAN lab',
 'Pi không đọc CAN_H/CAN_L trực tiếp; phần cứng và driver phải khớp.',
 'BOM theo thiết bị thực, sơ đồ nối dây, termination, nguồn/reference và driver cần dùng.',
 'Tránh nhầm lỗi phần cứng thành lỗi AI hoặc SocketCAN.',
 'Review đúng model adapter, listen-only, bitrate và topology; chưa chọn mua thay bạn.',
 'todo',evidence='docs/ARCHITECTURE.vi.md mục C có thiết kế; chưa có BOM phần cứng được chốt')
task(6,'A3',3,'Bring-up can0 và xác nhận đường nhận vật lý',
 'Cần chứng minh frame thực đi từ bus qua adapter vào Pi.',
 'Capture mẫu trên testbench, cấu hình interface và thống kê lỗi/drop.',
 'Cho phép thay nguồn vcan bằng CAN vật lý sau khi đường nhận đạt.',
 'candump khớp nguồn lab; bitrate đúng; controller listen-only nếu yêu cầu thụ động; ghi nhận lỗi bus.',
 'todo','T05 T07 T09','docs/DEPLOY_RASPBERRY_PI.vi.md mục 6 là hướng dẫn, chưa có capture phần cứng')
task(7,'A4',3,'Kiểm tra OS và build native trên Pi',
 'Executable Windows không chạy được trên Pi ARM64.',
 'Ghi cấu hình OS/CPU/RAM; binary C++17 build native trên Pi.',
 'Tạo runtime đúng thiết bị để chạy replay và capture.',
 'Xác nhận aarch64/64-bit, build/link thành công và executable chạy được trên chính Pi.',
 'ready',evidence='CMakeLists.txt; docs/DEPLOY_RASPBERRY_PI.vi.md mục 2–4; mới có object cross-compile ARM64')
task(8,'B1',2,'Parser và source adapter CSV',
 'Frame phải được chuẩn hóa trước khi vào feature pipeline.',
 'C++ Frame và CSV source adapter có lỗi input rõ ràng.',
 'Làm baseline kiểm tra xử lý dữ liệu độc lập phần cứng.',
 'Golden input, DLC 0, input sai và thứ tự timestamp đều được kiểm thử.',
 'verified','T01','src/main.cpp: Frame/parse_frame/read_csv; tests/test_pipeline.py')
task(9,'B1',4,'Receiver SocketCAN và quan sát frame bị bỏ',
 'Đưa frame Linux live vào cùng pipeline đang chạy replay.',
 'socket/bind/poll/recvmsg; lọc frame v1; counter rx_drops và ignored_frames.',
 'Nối kernel CAN với feature/inference trên edge.',
 'Chạy integration test trên vcan rồi can0; ngắt interface phải báo lỗi; drop/ignored counter kiểm chứng được.',
 'ready','T03 T08','src/main.cpp: capture; đã compile nhánh Linux thành object, chưa runtime-test')
task(10,'B2',2,'Chốt clock và timestamp live',
 'Timing sai làm feature sai và báo detection delay không đáng tin.',
 'Clock contract; phương án kernel/hardware timestamp, monotonic mapping và xử lý clock discontinuity.',
 'Tính IAT, ordering và delay có cùng miền clock.',
 'Không trừ timestamp khác clock domain; đo được sai số receipt timestamp dưới tải.',
 'partial','T09','Live hiện dùng steady_clock tại user space; chưa có kernel/hardware timestamp')
task(11,'B2',2,'Window engine 100 ms',
 'AI cần vector theo một khoảng thời gian xác định thay vì frame rời.',
 'Tumbling window 100 ms, quy tắc biên, window rỗng và EOF rõ ràng.',
 'Làm đơn vị tính feature, inference và quyết định.',
 'Frame đúng biên vào window mới; gap sinh window rỗng; final partial window bị bỏ như contract.',
 'verified','T08','src/main.cpp: Extractor::advance/finish; tests/test_pipeline.py')
task(12,'B3',3,'Feature toàn cục v1 dùng chung train/runtime',
 'Ngăn lệch công thức giữa notebook train và executable triển khai.',
 '8 feature float32: rate, ID diversity/entropy/share, byte stats, bit flip và same-ID IAT.',
 'Cấp input có cùng schema cho Python training và C++ inference.',
 'Golden vector tính tay đạt; thứ tự/đơn vị/reset/giá trị thiếu được ghi rõ.',
 'verified','T11','src/main.cpp: Extractor; docs/ARCHITECTURE.vi.md mục G; tools/prepare.py: FEATURES')
task(13,'B3',4,'Feature theo từng ID/signal và ngữ cảnh',
 'Feature tổng hợp có thể làm loãng thay đổi của một ID; model hiện bắt yếu payload shift.',
 'Candidate schema v2: period error, counter continuity, per-ID payload; DBC/signal checks khi có dữ liệu.',
 'Cải thiện phát hiện thay đổi tinh vi và giải thích được dấu hiệu.',
 'Feature train/runtime vẫn khớp; đánh giá trên validation riêng; không giải mã RPM/speed khi thiếu DBC đúng.',
 'todo','T28 T29 T12','Hạn chế được đo trong docs/VALIDATION.vi.md: payload shift 1/40 window vượt ngưỡng')
task(14,'B4',3,'Export cây và inference C++',
 'Inference trên edge cần độc lập với môi trường Python training.',
 'Forest loader, kiểm schema/topology, tính path length và anomaly score.',
 'Chạy model trực tiếp trong executable C++ trên PC/Pi.',
 'Max abs error so với sklearn ≤1e-7; model không hợp lệ phải fail rõ ràng.',
 'verified','T12 T32','src/main.cpp: Forest; tools/prepare.py; 1660 window parity, max error 1.11e-16')
task(15,'B4',2,'Xác nhận score parity trên Pi',
 'Compile được chưa chứng minh hành vi số học đúng trên thiết bị đích.',
 'Báo cáo checksum và 32 golden score trên native binary Pi.',
 'Cho phép chuyển từ local inference sang kiểm thử edge thực.',
 'tools/verify_pi_bundle.py PASS trên Pi, score error ≤1e-7 và metadata đúng thiết bị.',
 'ready','T07 T14 T36','tools/verify_pi_bundle.py; đã PASS Windows, chưa chạy Pi')
task(16,'B5',1,'Rule baseline cho demo',
 'Một số dấu hiệu rõ ràng nên phát hiện và giải thích trực tiếp.',
 'Rule unknown_id và possible_flooding với profile tổng hợp.',
 'Đối chứng rule-only và bảo đảm AI không phải nguồn quyết định duy nhất.',
 'Flooding/ID lạ có reason tương ứng; không gọi kết quả rule là kết quả model.',
 'verified','T11','src/main.cpp: Detector::emit; docs/VALIDATION.vi.md bảng kịch bản')
task(17,'B5',2,'Profile và rule đúng mạng lab',
 'Whitelist/rate threshold toy không đại diện mọi xe hoặc mọi bus.',
 'Profile versioned cho ID, chu kỳ/rate và rule signal khi có DBC/ngữ cảnh.',
 'Giảm false alert và làm cảnh báo có ý nghĩa với testbench thực.',
 'Profile xuất phát từ normal lab đã review; rule được test bằng positive/negative cases.',
 'partial','T28 T29 T06 T16','Đang hardcode ngưỡng demo >1800 frames/s; whitelist demo ở model header')
task(18,'B6',3,'Fusion rule/AI và debounce cảnh báo',
 'Một spike score không nên tự tạo chuỗi cảnh báo liên tục.',
 'State machine HEALTHY/SUSPECT/ALERT, ML cần 2 window; clear sau 5 normal; hard rule tức thời tại cuối window.',
 'Biến score/rule thành trạng thái cảnh báo ổn định và kiểm chứng được.',
 'Có state transition tests; reason window hiện tại phân biệt với alarm còn latch.',
 'verified','T14 T16','src/main.cpp: Detector::emit; tests/test_pipeline.py; docs/ARCHITECTURE.vi.md mục J')
task(19,'B6',2,'Tách health khỏi alarm và theo dõi mất dữ liệu',
 'NO_DATA không phải attack và không nên làm mất alarm đang mở.',
 'sensor_health độc lập alarm_state; dữ liệu thiếu/drop được gắn degraded.',
 'Tránh hiển thị healthy hoặc mất lịch sử khi sensor ngừng nhận.',
 'Silence/disconnect/drop không xóa alarm; health và alarm có test độc lập.',
 'partial','T09 T18','Có NO_DATA và counter; hiện vẫn dùng một state chung, chưa tách hai state')
task(20,'C1',2,'Dashboard review replay',
 'Cần nhìn thấy traffic, score, state và giới hạn khi review local.',
 'UI replay 46 s, biểu đồ, model-only P95, kiến trúc và kết quả kiểm chứng.',
 'Review logic đầu cuối trước khi nối phần cứng.',
 '460 event, không lỗi JS; layout desktop/mobile đạt; ghi rõ dữ liệu mô phỏng.',
 'verified','T02 T18','ui/index.html; tools/serve.py; tests/browser_smoke.py; docs/local-demo.png')
task(21,'C1',3,'Dashboard nguồn CAN live',
 'UI hiện không tự thấy output từ capture can0.',
 'Source selector/capture lifecycle, NDJSON live vào API, UI phân biệt replay/live và nguồn metrics.',
 'Quan sát vận hành Pi khi đang nhận CAN thật.',
 'UI khớp event capture; disconnect/stop xử lý được; không gán metadata replay hoặc số đo PC cho Pi.',
 'todo','T09 T19 T22 T20','tools/serve.py hiện chỉ gọi replay subprocess')
task(22,'C2',2,'Chuẩn hóa event/alert contract',
 'Một window ALERT khác với một sự kiện tấn công duy nhất.',
 'Event có window/model/profile/clock/data quality; alert opened/updated/closed và ID liên kết.',
 'Cho UI, logger và evaluator đếm/correlate cùng một sự kiện.',
 'Window và attack event không bị đếm lẫn; truy được model/profile gây quyết định.',
 'partial','T18 T19','Có NDJSON per-window và window_end_ms; chưa có alert lifecycle/model version trong từng event')
task(23,'C2',4,'Evidence và retention',
 'Score đơn lẻ không đủ điều tra; log không giới hạn có thể đầy ổ đĩa.',
 'Raw pre/post-event buffer, event index và rotation theo dung lượng/thời gian.',
 'Từ một alert xem lại được frame liên quan, trong ngân sách lưu trữ đã chốt.',
 'Evidence khớp event ID và thời gian; không tăng RAM/disk vô hạn; có hành vi khi disk full.',
 'todo','T22 T26','Hiện chỉ NDJSON của lượt replay gần nhất; chưa raw ring buffer/rotation')
task(24,'C3',3,'Báo cáo chất lượng nhận diện',
 'Test pipeline PASS không đồng nghĩa model phát hiện tốt.',
 'Precision/recall/F1 theo window và event, false alerts/giờ, detection delay và các case miss.',
 'Căn cứ quyết định model/profile có đủ dùng cho lab hay không.',
 'Tách AI-only/rule-only/fused; công bố thời lượng normal và số attack; đánh giá holdout độc lập.',
 'partial','T34 T22','docs/VALIDATION.vi.md có synthetic window results; chưa quality report dữ liệu thực')
task(25,'C3',3,'Benchmark tài nguyên và thời gian trên Pi',
 'PC P95 không cho biết throughput hay nhiệt/throttling của Pi.',
 'Pi report: model/full-pipeline latency, detection delay, frame/drop rate, CPU/RSS/nhiệt/disk.',
 'Chốt tải đáp ứng được và ngân sách tài nguyên edge.',
 'Ghi đúng cấu hình Pi/OS/adapter; tách replay/vcan/CAN; đối chiếu mục tiêu đã được chốt.',
 'todo','T15 T04 T06','Hiện chỉ số đo model-only trên PC; chưa benchmark Pi')
task(26,'C4',3,'Bounded queues và logger bất đồng bộ',
 'Ghi stdout/disk chậm hiện có thể chặn đường nhận frame.',
 'Capture queue và event queue có giới hạn, policy overflow và counter riêng.',
 'Giữ đường nhận ổn định khi model/UI/logger có độ trễ.',
 'Stress test logger chậm; memory bounded; mọi frame/event drop quan sát được.',
 'todo','T09 T22','Runtime hiện là một luồng đồng bộ; chưa có SPSC queue/logger worker')
task(27,'C4',2,'Fault injection và phục hồi',
 'Hệ thống cần báo sai/lỗi rõ ràng ngoài happy path.',
 'Test matrix: input/model hỏng, interface down, queue overflow, disk full, process restart.',
 'Xác nhận lỗi không bị diễn giải thành normal và có quy trình recovery.',
 'Mỗi fault có expected state, log, exit/restart behavior và bằng chứng chạy trên đích.',
 'partial','T19 T23 T26','Đã test parser/model lỗi local; chưa interface/disk/queue/restart trên Pi')
task(28,'D1',3,'Chốt và lấy nguồn dữ liệu đại diện',
 'Model toy không học hành vi thật của mạng CAN đích.',
 'Data registry cho HCRL/ROAD hoặc normal/attack lab captures; nguồn, điều kiện sử dụng và version.',
 'Cung cấp đầu vào có provenance để train và đánh giá.',
 'File dữ liệu thực có sẵn và được nhận diện đúng; phạm vi xe/bus/label được mô tả.',
 'todo',evidence='docs/ARCHITECTURE.vi.md có nguồn tham khảo; chưa tải/đưa dữ liệu thực vào pipeline')
task(29,'D1',3,'Adapter dataset và kiểm tra chất lượng dữ liệu',
 'Mỗi bộ dữ liệu có format, clock và nhãn khác nhau.',
 'Converter về schema chung, kiểm monotonic/DLC/missing/duplicate và metadata onset/event.',
 'Bảo đảm model học dữ liệu hợp lệ và evaluator có ground truth.',
 'Spot-check với raw source; label không đi vào feature; có báo cáo dữ liệu bị loại.',
 'todo','T28 T01','Chưa có HCRL/ROAD converter hoặc capture-normalizer lab')
task(30,'D2',3,'Split theo phiên và chống data leakage',
 'Random split frame gần nhau dễ làm kết quả đánh giá đẹp giả.',
 'Manifest train/validation/test theo capture/session/thời gian; purge nếu dùng overlapping window.',
 'Giữ test thực sự chưa được dùng để fit/tune.',
 'Không trùng capture/event hoặc overlapping context giữa tập; threshold không chỉnh theo final test.',
 'partial','T29','Demo dùng seed/phiên riêng; chưa split/audit leakage trên dữ liệu thực')
task(31,'D2',2,'Tạo feature dataset có version',
 'Cần truy được model được train từ feature/schema và dữ liệu nào.',
 'Feature CSV/metadata theo split, schema version và data fingerprint.',
 'Tái lập training và phát hiện schema mismatch khi deploy.',
 'Dùng đúng extractor runtime; có row/window counts, units/order và provenance kiểm tra được.',
 'partial','T30 T12','Cùng C++ extractor đã dùng; chưa hoàn chỉnh fingerprint/lineage cho dataset thực')
task(32,'D3',2,'Train baseline Isolation Forest normal-only',
 'Có một model nhẹ và quy trình train làm baseline so sánh.',
 'Model fitted trên normal train, tham số cố định và seed/version được ghi.',
 'Đưa anomaly detection vào pipeline C++ thay vì chỉ rule.',
 'Không dùng attack label làm feature; fit chỉ train split; tái lập được artifact demo.',
 'verified','T12 T02','tools/prepare.py; demo 64 trees/max_samples 128; mới trên dữ liệu tổng hợp')
task(33,'D3',3,'Calibration và chọn candidate trên validation',
 'Ngưỡng/model phải được chọn theo dữ liệu và false-alarm budget, không theo cảm giác.',
 'So sánh baseline/candidate, threshold và rule profile trên validation riêng.',
 'Chọn operating point trước khi mở final test.',
 'Có normal/attack validation, lý do chọn threshold và trade-off; freeze trước final test.',
 'partial','T31 T32 T13 T17','Demo dùng percentile 99.5 normal validation; chưa chọn candidate bằng dữ liệu lab')
task(34,'D3',4,'Đánh giá holdout và xử lý các case miss',
 'Phải chứng minh model đạt mục tiêu phát hiện, không chỉ export đúng.',
 'Holdout report + failure analysis; candidate pass/fail rõ cho từng kịch bản.',
 'Chặn việc đẩy model còn yếu lên môi trường sử dụng thực.',
 'Đạt tiêu chí recall/false alarm/delay đã chốt trên holdout; không che case miss hoặc hạ ngưỡng theo test.',
 'gap','T33 T04','Payload shift chỉ 1/40 window vượt ML threshold, không confirmed ALERT; dữ liệu thực chưa đánh giá')
task(35,'D4',2,'Model bundle và metadata phiên bản',
 'Model phải đi cùng schema/profile/threshold tương thích.',
 'Forest + manifest + checksum + golden vectors; bổ sung model/data/profile/build version.',
 'Nhận diện chính xác bộ model/runtime được review hoặc rollback.',
 'Runtime/artifact mismatch bị phát hiện; metadata đủ tái lập; hash không bị gọi nhầm là chữ ký.',
 'partial','T14 T32','models/manifest.json, .forest, pi-golden-*; chưa đầy đủ version/provenance và runtime hash enforcement')
task(36,'D4',3,'Đóng gói chuyển sang Pi và kiểm integrity',
 'Chuyển đúng source/model, không mang virtualenv hoặc executable Windows sang Pi.',
 'ai-vids-pi-review.tar.gz có inventory và checksum từng file; checker standard-library Python.',
 'Giảm lỗi copy thủ công và tạo một gói review có thể xác minh.',
 'Archive chứa đúng file; hash khớp; local golden checker đạt; không tự SSH hay cài đặt.',
 'verified','T14 T20','tools/package_pi.py; tools/verify_pi_bundle.py; build/ai-vids-pi-review.tar.gz đã kiểm local')
task(37,'D5',2,'Chạy Pi staging và lưu biên bản review',
 'Đưa code lên Pi là một lần kiểm chứng thiết bị đích, chưa phải production.',
 'Checklist replay → vcan → lab CAN; log kết quả và quyết định review.',
 'Xác định phần nào thực sự đạt trên Pi trước khi vận hành dài hạn.',
 'Có kết quả trực tiếp từ Pi, giới hạn và quyết định tiếp tục rõ; việc chạy Pi nằm trong phạm vi được bạn chốt.',
 'ready','T15 T04 T06 T21 T24 T25','docs/DEPLOY_RASPBERRY_PI.vi.md; chưa thực hiện staging trên Pi')
task(38,'D5',3,'Service, rollback và cổng chấp thuận production',
 'Cần khởi động/phục hồi có kiểm soát và quay lại bản đã biết tốt.',
 'Service account/systemd, interface startup, restart limits, version activation/rollback và runbook.',
 'Vận hành dài hạn với bản đã kiểm chứng và có đường phục hồi.',
 'Staging/soak đạt; rollback được test; bạn chấp thuận production trước khi triển khai.',
 'todo','T37 T23 T26 T27 T35','Chưa có service/installer/rollback tự động; chưa có chấp thuận production')


def validate():
    assert len(TASKS)==38 and len(NODES)==19
    assert sum(t['weight'] for t in TASKS)==100
    ids={t['id'] for t in TASKS}
    assert len(ids)==len(TASKS)
    for n in NODES:
        assert sum(t['weight'] for t in TASKS if t['node']==n['id'])==n['weight'],n
    for g in GROUPS:
        assert sum(n['weight'] for n in NODES if n['id'].startswith(g['id']))==g['weight']
    def visit(task_id,path):
        assert task_id not in path, f'Dependency cycle: {path} {task_id}'
        t=next(t for t in TASKS if t['id']==task_id)
        for dep in t['deps']:
            assert dep in ids,(task_id,dep)
            visit(dep,path+[task_id])
    for t in TASKS:
        assert t['status'] in STATUSES
        visit(t['id'],[])


def markdown(plan):
    lines=['# Task breakdown và bản đồ review AI-VIDS','',
      'Cập nhật 31/10/2026. Phạm vi tài liệu: phần đã làm + việc còn lại để đi tới Pi staging và production có kiểm chứng. Không thực thi thêm task triển khai khi tạo tài liệu này.','',
      '**Quy ước tỉ lệ:** % là ước lượng phân bổ công sức tương đối cho toàn bộ phạm vi trong bảng, tổng 100%; không phải % hoàn thành, % accuracy, diện tích sơ đồ hay cam kết thời gian. Chưa đủ dữ liệu để chốt man-day. Các task bằng % nhau vẫn có thể khác nhau về rủi ro/phụ thuộc.','',
      '**Trạng thái:** '+ '; '.join(STATUSES.values())+'. “Đã kiểm local” chỉ đúng với scope local ghi trong task; không tự chuyển thành đã đạt trên Pi/xe thật.','',
      '**Cách đánh số:** T01–T38 theo vị trí block kiến trúc, không phải thứ tự bắt buộc triển khai. Xem phụ thuộc và các mốc làm tiếp. A1/A2/A3 là các nguồn hoặc cấp kiểm thử thay thế: CSV, vcan, CAN vật lý.','',
      '[Mở bản review tương tác](TASK_REVIEW.html) · [Sơ đồ có mã tham chiếu](architecture.svg) · [Thiết kế A–Z](ARCHITECTURE.vi.md) · [Kết quả hiện tại](VALIDATION.vi.md)','',
      '## Đọc kiến trúc theo ba luồng','',
      '- Runtime: **A1/A2/A3 → B1 → B2 → B3 → (B4 + B5) → B6 → C2 → C1**.',
      '- Training: **D1 → D2 → D3 → D4 → B4**; train trên PC, inference trên edge.',
      '- Chuyển sang Pi/vận hành: **A4 → B4 parity → A2 → A3 → C3/C4 → D5**. Đây là lộ trình; xem dependency từng task để biết các nhánh cần đủ trước khi nghiệm thu.','',
      '## Tỉ lệ theo bốn vùng trên sơ đồ','',
      '| Vùng | Công sức ước lượng | Ý nghĩa |','|---|---:|---|']
    for g in GROUPS:lines.append(f"| {g['id']} | {g['weight']}% | {g['name']} |")
    lines+=['','## Bản đồ block → task','',
      '| Block trên arch | Tên block | Tỉ lệ | Task |','|---|---|---:|---|']
    for n in NODES:
        tasklinks=', '.join(f"[{t['id']}](#{t['id'].lower()})" for t in TASKS if t['node']==n['id'])
        lines.append(f"| [{n['id']}](architecture.svg#arch-{n['id']}) | {n['name']} | {n['weight']}% | {tasklinks} |")
    lines+=['','## Bằng chứng và phạm vi đã có','',
      '- 12 unit/integration tests đạt trên PC; 1.660 score windows đối chiếu C++/sklearn, max error 1.11e-16.',
      '- UI replay chạy 460 windows, kiểm browser desktop/mobile; tất cả vẫn là dữ liệu tổng hợp.',
      '- Gói Pi có inventory/checksum từng file; checker 32 golden windows đã chạy local, chưa chạy trên Pi.',
      '- Chưa runtime-test SocketCAN trên Linux/Pi, chưa CAN phần cứng, chưa benchmark Pi, chưa live dashboard.',
      '- **Chưa đạt:** payload shift chỉ 1/40 window vượt ML threshold, chưa có confirmed ALERT. Flooding/unknown ID hiện được rule bắt.','',
      '## Thứ tự làm tiếp đề xuất','',
      '1. **Review 0:** bạn đọc arch/task, chốt phạm vi lab, nguồn dữ liệu và tiêu chí recall/false alarm/delay; chưa tự đưa lên production.',
      '2. **Mốc 1 — chứng minh runtime trên Pi:** T07 → T15; song song về mặt kế hoạch có thể chuẩn bị T28/T29, T05. Chỉ chạy trên Pi khi phạm vi bước này đã được chốt.',
      '3. **Mốc 2 — live input trong lab:** T03/T09 → T04; T05/T06 khi có adapter. Review clock/window và health: T10/T19.',
      '4. **Mốc 3 — làm model có ý nghĩa:** T28/T29 → T30/T31 → T13/T17 → T33 → T34. Chốt ngưỡng nghiệm thu trước tuning; chưa đạt thì quay lại feature/model, không promote.',
      '5. **Mốc 4 — quan sát và độ bền:** T22/T21/T23/T26/T27; T24/T25 cung cấp bằng chứng chất lượng và hiệu năng.',
      '6. **Mốc 5 — review staging/release:** T35/T37; T38 chỉ sau khi điều kiện vận hành đạt và có chấp thuận production.','',
      '## Chi tiết từng task','']
    for t in TASKS:
        lines += [f"<a id=\"{t['id'].lower()}\"></a>",
          f"### {t['id']} — {t['name']}",'',
          f"**Arch:** [{t['node']}](architecture.svg#arch-{t['node']}) · **Tỉ lệ:** {t['weight']}% · **Trạng thái:** {STATUSES[t['status']]}",'',
          f"- **Ý nghĩa:** {t['why']}", f"- **Outcome cần bàn giao:** {t['outcome']}",
          f"- **Outcome dùng để:** {t['use']}", f"- **Review/điều kiện đạt:** {t['accept']}",
          f"- **Phụ thuộc:** {', '.join(t['deps']) or 'Không có task tiền nhiệm bắt buộc trong bảng.'}",
          f"- **Bằng chứng hiện tại:** {t['evidence']}",'']
    lines+=['## Cách review từng task','',
      'Với mỗi task, đối chiếu block trên arch, đọc ý nghĩa, mở evidence hiện có rồi xem điều kiện đạt. Ghi feedback theo mẫu `T13: đồng ý scope; cần bổ sung counter continuity; nghiệm thu bằng ...`. Task có code nhưng chưa log chạy trên Pi giữ trạng thái chưa kiểm đích.','',
      'Thay đổi tỉ lệ hoặc thêm/bớt scope phải cân lại tổng 100%; không dùng bảng công sức để báo tiến độ hoàn thành. Bảng này chưa bao gồm mọi hạng mục chứng nhận/đảm bảo của hệ thống automotive production đầy đủ.']
    return '\n'.join(lines)+'\n'


def html(plan,svg):
    data=json.dumps(plan,ensure_ascii=False).replace('</','<\\/')
    template='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI-VIDS · Task & architecture review</title>
<style>:root{color-scheme:dark;--bg:#0b1424;--panel:#132238;--line:#2e435e;--muted:#a8bbd3;--green:#54e3c2;--amber:#ffc46b}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#edf4ff;font:15px/1.6 'Segoe UI',sans-serif}main{max-width:1480px;padding:30px;margin:auto}h1{font-size:32px;line-height:1.2;margin:8px 0 16px}h2{font-size:20px}h3{font-size:18px;margin:10px 0}p{color:var(--muted)}.eyebrow{font-size:12px;letter-spacing:2px;color:var(--green)}.notice{background:#2d261d;border:1px solid #6a5330;border-radius:10px;padding:15px;color:var(--amber)}.groups{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}button,input,select{font:inherit}button{cursor:pointer}.group{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;color:#edf4ff;text-align:left}.group strong{font-size:27px;color:var(--green);display:block}.group span{font-size:13px;color:var(--muted)}details.arch{border:1px solid var(--line);border-radius:12px;padding:15px;margin:20px 0}summary{cursor:pointer}details.arch svg{display:block;width:100%;height:auto;margin-top:12px}g[data-arch-ref]{cursor:pointer}g[data-arch-ref]:hover>rect,g.selected>rect{stroke:#ffc46b;stroke-width:3}.path{background:var(--panel);border-radius:8px;padding:12px;margin:10px 0;font-size:14px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#0b1424f5;padding:14px 0;z-index:1}.toolbar input,.toolbar select{background:var(--panel);border:1px solid var(--line);color:#edf4ff;border-radius:7px;padding:10px;max-width:100%}.toolbar input{flex:1;min-width:180px}.toolbar button{background:var(--green);border:0;color:#082f2a;border-radius:7px;padding:10px 15px}.tasks{display:grid;grid-template-columns:1fr 1fr;gap:14px}.task{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0;scroll-margin-top:100px}.meta{display:flex;gap:8px;flex-wrap:wrap;font-size:12px}.chip{padding:3px 9px;background:#223650;border-radius:5px}.status.verified{color:var(--green)}.status.partial,.status.ready{color:var(--amber)}.status.gap{color:#ff8b9b}.status.todo{color:#a8bbd3}.task p{margin:7px 0}.label{color:var(--green);font-size:12px;display:block;margin-top:12px}.task details{border-top:1px solid var(--line);margin-top:15px;padding-top:10px}.evidence{font-family:Consolas,monospace;font-size:12px;overflow-wrap:anywhere}.deps button{background:#213b4d;border:1px solid #3b6579;border-radius:4px;color:var(--green);padding:3px 7px;margin:3px}a{color:var(--green)}.sub{font-size:13px;color:var(--muted)}.gate{border-left:3px solid var(--amber);padding:5px 15px;margin:18px 0}footer{margin:28px 0;color:var(--muted);font-size:12px}@media(max-width:800px){main{padding:18px}.groups{grid-template-columns:1fr 1fr}.tasks{grid-template-columns:1fr}h1{font-size:26px}.toolbar{position:static}}</style>
<main><div class="eyebrow">AI–VIDS / REVIEW PLAN · 31.10.2026</div><h1>38 task. 19 block kiến trúc. Một bản đồ để review.</h1><p>Mỗi task có ý nghĩa, đầu ra cần bàn giao, đầu ra dùng vào việc gì, điều kiện đạt, bằng chứng và phụ thuộc. Mã task đánh theo vị trí arch; thứ tự thực hiện xem mục phụ thuộc.</p><div class="notice"><b>100% = tổng công sức ước lượng theo phạm vi.</b> Không phải tiến độ hoàn thành hay accuracy. “Đã kiểm local” không có nghĩa đã chạy đạt trên Pi. Đây là kế hoạch để review, không thực hiện deployment.</div><div id="groups" class="groups"></div>
<div class="path"><b>Runtime:</b> A1/A2/A3 → B1 → B2 → B3 → (B4 + B5) → B6 → C2 → C1</div><div class="path"><b>Training:</b> D1 → D2 → D3 → D4 → B4 &nbsp; | &nbsp; <b>Triển khai:</b> A4 → kiểm đích → C3/C4 → D5</div>
<details class="arch" open><summary><b>Sơ đồ có mã tham chiếu — bấm vào block để lọc task tương ứng</b></summary>__SVG__</details>
<div class="gate"><b>Điểm chưa đạt cần thấy trước:</b> T34 — payload shift chỉ 1/40 window vượt ngưỡng model, chưa tạo confirmed ALERT. Flooding/ID lạ hiện do rule bắt. Chưa chạy trên Pi hoặc CAN vật lý.</div>
<h2 id="task-anchor">Danh sách task để review</h2><div class="toolbar"><input id="search" placeholder="Tìm T13, payload, timestamp, outcome…" aria-label="Tìm task"><select id="arch-filter" aria-label="Lọc block kiến trúc"></select><select id="status-filter" aria-label="Lọc trạng thái"></select><button id="reset">Xem tất cả</button></div><p id="count" class="sub"></p><div id="tasks" class="tasks"></div><footer>Ghi feedback theo mã, ví dụ: “T13: cần thêm counter continuity và test với capture lab”. Production cần quyết định riêng sau review. Bản này mở được offline; không cần cloud.</footer></main>
<script>const PLAN=__DATA__;const $=id=>document.getElementById(id);const byId=Object.fromEntries(PLAN.tasks.map(t=>[t.id,t]));function el(tag,txt,cls){let x=document.createElement(tag);if(txt!==undefined)x.textContent=txt;if(cls)x.className=cls;return x}function option(sel,v,txt){const o=el('option',txt);o.value=v;sel.append(o)}option($('arch-filter'),'all','Tất cả block kiến trúc');for(const g of PLAN.groups){option($('arch-filter'),g.id,g.id+' · '+g.name+' · '+g.weight+'%');const b=el('button',undefined,'group');b.append(el('strong',g.id+' · '+g.weight+'%'),el('span',g.name));b.onclick=()=>choose(g.id);$('groups').append(b)}for(const n of PLAN.nodes)option($('arch-filter'),n.id,n.id+' · '+n.name+' · '+n.weight+'%');option($('status-filter'),'all','Tất cả trạng thái');for(const [key,value]of Object.entries(PLAN.statuses))option($('status-filter'),key,value);
function choose(ref){$('arch-filter').value=ref;$('status-filter').value='all';$('search').value='';render();$('task-anchor').scrollIntoView({behavior:'smooth'});history.replaceState(null,'','#'+ref)}function focusTask(id){$('arch-filter').value='all';$('status-filter').value='all';$('search').value=id;render();document.getElementById(id)?.scrollIntoView({behavior:'smooth'});history.replaceState(null,'','#'+id)}
function render(){const q=$('search').value.toLowerCase().trim(),a=$('arch-filter').value,s=$('status-filter').value;let tasks=PLAN.tasks.filter(t=>(a==='all'||t.node===a||(a.length===1&&t.node.startsWith(a)))&&(s==='all'||t.status===s)&&(!q||[t.id,t.node,t.name,t.why,t.outcome,t.use,t.accept,t.evidence].join(' ').toLowerCase().includes(q)));$('count').textContent=tasks.length+' / '+PLAN.tasks.length+' task · '+tasks.reduce((n,t)=>n+t.weight,0)+'% công sức trong phạm vi đang lọc · không phải % hoàn thành';$('tasks').replaceChildren();for(const t of tasks){const card=el('article',undefined,'task');card.id=t.id;const meta=el('div',undefined,'meta');meta.append(el('span',t.id,'chip'),el('span',t.node+' · '+t.weight+'% công sức','chip'),el('span',PLAN.statuses[t.status],'status '+t.status));card.append(meta,el('h3',t.name));for(const [label,value]of [['Ý NGHĨA',t.why],['OUTCOME CẦN BÀN GIAO',t.outcome],['OUTCOME DÙNG ĐỂ',t.use]])card.append(el('span',label,'label'),el('p',value));const details=el('details');details.append(el('summary','Review / điều kiện đạt / bằng chứng'));details.append(el('span','ĐIỀU KIỆN ĐẠT','label'),el('p',t.accept),el('span','BẰNG CHỨNG HIỆN TẠI','label'),el('p',t.evidence,'evidence'),el('span','PHỤ THUỘC','label'));const deps=el('div',undefined,'deps');if(!t.deps.length)deps.textContent='Không có task tiền nhiệm bắt buộc trong bảng.';for(const d of t.deps){const b=el('button',d+' · '+byId[d].name);b.onclick=()=>focusTask(d);deps.append(b)}details.append(deps);card.append(details);$('tasks').append(card)}document.querySelectorAll('g[data-arch-ref]').forEach(g=>g.classList.toggle('selected',g.dataset.archRef===a||(a.length===1&&g.dataset.archRef.startsWith(a))))}
document.querySelectorAll('g[data-arch-ref]').forEach(g=>{g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label','Lọc task '+g.dataset.archRef);g.onclick=()=>choose(g.dataset.archRef);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(g.dataset.archRef)}}});$('search').oninput=render;$('arch-filter').onchange=render;$('status-filter').onchange=render;$('reset').onclick=()=>{$('search').value='';$('arch-filter').value='all';$('status-filter').value='all';history.replaceState(null,'',location.pathname);render()};const initial=decodeURIComponent(location.hash.slice(1));if(byId[initial])$('search').value=initial;else if(PLAN.nodes.some(n=>n.id===initial)||PLAN.groups.some(g=>g.id===initial))$('arch-filter').value=initial;render();</script></html>'''
    return template.replace('__SVG__',svg).replace('__DATA__',data)


def main():
    validate()
    plan={'date':'2026-10-31','weight_meaning':'relative effort estimate, NOT completion',
          'groups':GROUPS,'nodes':NODES,'statuses':STATUSES,'tasks':TASKS}
    (ROOT/'docs'/'REVIEW_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    subprocess.run([sys.executable,str(ROOT/'tools'/'draw_architecture.py')],check=True)
    svg=(ROOT/'docs'/'architecture.svg').read_text(encoding='utf-8')
    (ROOT/'docs'/'TASK_BREAKDOWN.vi.md').write_text(markdown(plan),encoding='utf-8')
    (ROOT/'docs'/'TASK_REVIEW.html').write_text(html(plan,svg),encoding='utf-8')
    print(f'Review plan: {len(TASKS)} tasks, {len(NODES)} nodes, 100% effort; dependencies acyclic')


if __name__=='__main__':
    main()

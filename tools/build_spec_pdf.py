"""Build a Vietnamese, paginated technical spec. No target deployment actions."""
from __future__ import annotations
import argparse
import base64
import hashlib
from html import escape as E
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'spec'
STEM='AI-VIDS_Spec_VMware_Ubuntu_RaspberryPi_Production_v1.0'
PLAN=json.loads((ROOT/'docs'/'REVIEW_PLAN.json').read_text(encoding='utf-8'))
LOG=json.loads((ROOT/'runtime'/'vm-log-walkthrough.json').read_text(encoding='utf-8'))
PAGES=[]


def p(s): return f'<p>{s}</p>'
def small(s): return f'<p class="small">{s}</p>'
def h(s): return f'<h2>{s}</h2>'
def code(s): return '<pre>'+E(textwrap.dedent(s).strip())+'</pre>'
def bullets(*items): return '<ul>'+''.join('<li>'+s+'</li>' for s in items)+'</ul>'
def note(s,kind='info'): return f'<div class="note {kind}">{s}</div>'
def ref(s): return f'<div class="source">Source / trace: {s}</div>'
def table(headers,rows,widths=None):
    cols='' if not widths else '<colgroup>'+''.join(f'<col style="width:{v}%">' for v in widths)+'</colgroup>'
    return '<table>'+cols+'<thead><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'
def two(left,right): return f'<div class="two"><div>{left}</div><div>{right}</div></div>'
def page(title,part,content,status='SPEC / REVIEW'):
    PAGES.append(dict(title=title,part=part,content=content,status=status))


def flow(items,caption='',cols=3):
    """Readable snake-flow SVG: each item is title, line1, line2, optional color."""
    nrows=(len(items)+cols-1)//cols
    width=720;height=nrows*100+8
    parts=[f'<svg class="flow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{E(caption)}">',
           '<defs><marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#587a92" stroke-width="1.4"/></marker></defs>']
    positions=[]
    for i,item in enumerate(items):
        row=i//cols;col=i%cols
        if row%2:col=cols-1-col
        x=8+col*240;y=8+row*100;positions.append((x,y))
        fill=item[3] if len(item)>3 else '#eaf5f3'
        parts.append(f'<rect x="{x}" y="{y}" width="224" height="76" rx="8" fill="{fill}" stroke="#89a7b4"/>')
        parts.append(f'<text x="{x+12}" y="{y+23}" style="font:700 14px Arial;fill:#113449">{E(item[0])}</text>')
        for j,line in enumerate(item[1:3]):
            parts.append(f'<text x="{x+12}" y="{y+44+j*17}" style="font:13px Arial;fill:#365369">{E(line)}</text>')
    for (x1,y1),(x2,y2) in zip(positions,positions[1:]):
        if y1==y2:
            if x2>x1: a,b=(x1+224,y1+38),(x2-2,y2+38)
            else:a,b=(x1,y1+38),(x2+226,y2+38)
        else:a,b=(x1+112,y1+76),(x2+112,y2-2)
        parts.append(f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="#587a92" stroke-width="1.8" fill="none" marker-end="url(#arr)"/>')
    parts.append('</svg>')
    if caption:parts.append(f'<div class="caption">{caption}</div>')
    return ''.join(parts)


def make_pages():
    page('AI-VIDS', 'ĐẶC TẢ LUỒNG CHẠY & TRIỂN KHAI',
      '<div class="cover-title">Từ CAN frame<br>đến cảnh báo tại edge.</div>'+
      p('Hai cấu hình trong một spec: <b>Ubuntu Linux trên VMware</b> để hiểu và kiểm chứng code hiện tại; <b>Raspberry Pi 4</b> cho kiến trúc production mục tiêu.')+
      flow([('V1 · Ubuntu VMware','Replay CSV + vcan0','Code hiện tại / kiểm Linux'),
            ('Core dùng chung','Feature → AI + rule','Decision → event'),
            ('V2 · Pi production','can0 + model lab hợp lệ','Vận hành / rollback')], 'Mỗi bước được map về task T01–T38 và block A/B/C/D trên kiến trúc.')+
      note('<b>Trạng thái phát hành: v1.0 — bản spec để review.</b> V2 là thiết kế cần triển khai và nghiệm thu. Việc tạo PDF không triển khai Pi/production.','warn')+
      table(['Thông tin','Giá trị'],[
        ('Ngôn ngữ / ngày','Tiếng Việt · 01/11/2026'),
        ('Repository','automotive-edge-ai-ids'),
        ('Đối tượng đọc','Người review hệ thống, embedded/Linux developer, người triển khai Pi'),
        ('Bằng chứng hiện có','12 tests local; parity 1.660 windows trên PC; 52 windows từ log VM khớp reference'),
        ('Điểm chặn production','Model demo payload shift 1/40 window vượt ngưỡng; chưa đủ confirmed ALERT; thiếu kiểm chứng Pi và các chức năng vận hành')
      ],[27,73]),'REVIEW · CHƯA PHÊ DUYỆT PRODUCTION')

    page('Cách đọc và so sánh hai cấu hình','ĐỊNH HƯỚNG',
      p('Đọc <b>trang 3 → 12</b> để hiểu bản đang chạy. Đọc <b>13 → 21</b> để thấy Pi phải khởi động, xử lý và phục hồi thế nào. Trang <b>22 → 24</b> map đầy đủ task; trang <b>25</b> là bảng lệnh tra nhanh.')+
      table(['Tiêu chí','V1 · Ubuntu trên VMware','V2 · Raspberry Pi production'],[
        ('Mục tiêu','Hiểu code, kiểm Linux và SocketCAN','Giám sát CAN dài hạn với giới hạn và health rõ ràng'),
        ('Nguồn frame','CSV replay hoặc vcan0','can0 qua adapter/driver đã chốt'),
        ('Kiến trúc CPU','Theo Ubuntu guest, thường x86_64','Linux ARM64/aarch64, kiểm trên Pi thật'),
        ('Model','demo.forest, dữ liệu tổng hợp','Model/profile theo lab/xe đích, đã đạt holdout'),
        ('C++ runtime','Một luồng đồng bộ','Capture/compute/logger tách bằng queue giới hạn — cần bổ sung'),
        ('Dashboard','Replay subprocess','Read-only live event API — cần bổ sung'),
        ('Vận hành','Terminal, log file thủ công','Service, retention, health, release/rollback'),
        ('Bằng chứng được dùng','Log VM không thay benchmark Pi','Testbench + Pi measurements + soak + release review')
      ],[20,40,40])+
      h('Quy ước trong tài liệu')+
      bullets('<b>HIỆN CÓ:</b> đọc được trong source hoặc có bằng chứng local đã lưu.',
              '<b>MỤC TIÊU V2:</b> yêu cầu thiết kế, chưa được coi là tính năng đã có.',
              '<b>TBD:</b> thông số cần chốt; không tự điền bằng kết quả đo trên PC/VM.',
              '<b>% công sức:</b> ước lượng phân bổ scope, không phải % hoàn thành hay accuracy.')+
      '<div id="toc-placeholder"></div>')

    page('Kiến trúc chung và ranh giới','CHUNG · A/B/C/D',
      flow([('A1 / A2 / A3 · Nguồn','CSV / vcan / CAN vật lý','Chọn theo cấp kiểm thử'),
            ('B1 · Thu nhận','CSV adapter / SocketCAN','Chuẩn hóa thành Frame'),
            ('B2 · Window / clock','Order + timestamp','100 ms theo schema v1'),
            ('B3 · Feature','8 float32 trong bản v1','Chung train và runtime'),
            ('B4 + B5 · Phân tích','Forest.score + rule','Score và lý do nghi ngờ'),
            ('B6 · Quyết định','Debounce / latch / health','State + event'),
            ('C2 · Log / evidence','V1: window NDJSON','V2: durable evidence'),
            ('C1 + C3 · Review','UI / quality / metrics','Quan sát và đánh giá'),
            ('D1 → D5 · Model','Train / export / release','Nạp bundle đã review')], 'Số block A/B/C/D thống nhất với sơ đồ và WBS đã bàn giao.')+
      note('Phạm vi v1 là Classic CAN standard 11-bit, payload 0–8 byte. Extended ID/RTR/error không vào feature ở capture; CAN FD chưa hỗ trợ. V2 phải chốt coverage theo bus thực, không tự xem lưu lượng ngoài scope là normal.','warn')+
      bullets('Đường IDS quan sát và phát cảnh báo; không tự gửi lệnh điều khiển/chặn frame.',
              'Ứng dụng chỉ đọc chưa bảo đảm controller thụ động ở tầng điện: listen-only phải được adapter/driver hỗ trợ và cấu hình.',
              'A1/A2/A3 là các nguồn/cấp kiểm thử; không cần chạy cả ba cùng lúc.',
              'CAN ID không xác thực danh tính ECU. Anomaly score không xác định attacker; spoofing/replay hợp ngữ cảnh có thể không phân biệt được nếu thiếu signal/counter/ngữ cảnh phù hợp.')+
      small('Cơ chế SocketCAN/interface/listen-only: <a href="https://docs.kernel.org/networking/can.html">Linux Kernel — SocketCAN</a>. Các lựa chọn module/queue trong spec là thiết kế dự án.'))

    page('Thành phần và bốn mode hiện có','V1 · CẤU TRÚC CODE',
      table(['Thành phần','Dùng ở đâu','Input → output'],[
        ('CMakeLists.txt','T07','Source C++17 → native executable'),
        ('src/main.cpp','B1–B6 + event stdout','Frame/vector/model → feature/score/state'),
        ('tools/verify_pi_bundle.py','T15/T36','Manifest + golden files → checksum/parity report'),
        ('tests/test_pipeline.py','Tests','Input tạm + subprocess → assertions'),
        ('tools/serve.py + ui/index.html','T20','C++ replay stdout → API → canvas/metrics'),
        ('tools/prepare.py, trên PC','T12/T32/T33/T35','Synthetic data → train/export/validation')
      ],[34,20,46])+
      table(['Mode ai-vids','Đầu vào bắt buộc','Chạy qua phần nào?'],[
        ('features INPUT OUTPUT','Raw CAN CSV','read_csv → parse_frame → Extractor; xuất feature CSV'),
        ('score MODEL FEATURES','Forest + vector CSV','Forest constructor → score; xuất scalar mỗi dòng'),
        ('replay INPUT MODEL [--realtime]','Raw CSV + forest','Extractor + model + rule + state; xuất NDJSON'),
        ('capture IFACE MODEL','Linux CAN interface + forest','SocketCAN → cùng core; xuất NDJSON')
      ],[31,27,42])+
      h('Những thứ cần cài, đúng theo vai trò')+
      bullets('Build: CMake, C++ compiler/build tools. Ubuntu dùng build-essential/cmake.',
              'Inference terminal: binary + CSV/model hoặc CAN interface. Không cần sklearn.',
              'Checker/tests/UI: Python 3 standard library. Browser chỉ vẽ kết quả.',
              'vcan: Linux module vcan, iproute2; cansend/candump thuộc can-utils.',
              'Training trên PC mới cần numpy/sklearn; không chạy lại khi replay.')+
      ref('CMakeLists.txt:3; src/main.cpp:260; tools/serve.py:19; tools/prepare.py:65'))

    page('VM: từ source tới binary và parity','V1 · T36 / T07 / T14 / T15',
      flow([('1 · Giải nén','Archive source + data/model','Không mang .exe/.venv Windows'),
            ('2 · CMake configure','Tìm compiler Linux','Sinh build configuration'),
            ('3 · Compile / link','src/main.cpp → executable','build/ai-vids'),
            ('4 · Check file hash','vm-bundle.json','File phải khớp inventory'),
            ('5 · C++ mode score','32 vector đã có sẵn','Không chạy raw extractor'),
            ('6 · So reference','Max abs error ≤ 1e-7','PASS cho chuyển nền tảng')])+
      code('''
        cd ~/ai-vids-vm
        cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
        cmake --build build -j2
        python3 tools/verify_pi_bundle.py --manifest vm-bundle.json
      ''')+
      p('<b>Hàm thực tế:</b> verifier đọc manifest → hashlib.sha256 từng file → subprocess gọi <code>ai-vids score</code> → đọc 32 score → so với golden-scores → in JSON PASS.')+
      note('PASS chỉ xác nhận integrity và score parity. Checker không đo recall/false alarm; Ubuntu x86_64 PASS chưa chứng minh ARM64/Pi PASS. Tên file có “pi” được giữ tương thích, không ép kiến trúc.','warn')+
      ref('tools/verify_pi_bundle.py:14; src/main.cpp:271; Forest::score:169; T07/T15 mới hoàn thành phần Linux khi có log đích.'))

    page('VM: 12 tests thực sự kiểm gì?','V1 · KIỂM CHỨC NĂNG',
      code('python3 -m unittest discover -s tests -v')+
      p('unittest tạo CSV/model lỗi trong thư mục tạm, gọi executable C++ bằng subprocess và assert output/exit code. Phần lớn tests gọi code thật.')+
      table(['Test / nhiệm vụ','Input / đường code','Điều kiện đạt'],[
        ('Golden features + boundary','00/FF cùng ID; frame ở 100 ms → features','Giá trị tính tay đúng; frame biên sang window mới'),
        ('Silent gap','Frame 0 rồi 300 ms → replay','Các window giữa là NO_DATA'),
        ('Label independence','Đổi normal thành attack trong cột label','Kết quả không đổi, bỏ timing đo'),
        ('DLC mismatch','DLC 8 nhưng payload 1 byte','Reject/exit nonzero'),
        ('Out-of-order timestamp','Timestamp giảm','Reject'),
        ('Negative timestamp','Timestamp âm','Reject'),
        ('Extended ID','ID ngoài standard 11-bit','Reject theo scope v1'),
        ('Empty payload','DLC 0','Được đọc hợp lệ'),
        ('Wrong model schema','Header model sai','Forest loader reject'),
        ('Synthetic scenarios','Replay 46 s','460 windows; xuất hiện reason theo kịch bản'),
        ('Export report metadata','Đọc validation.json có sẵn','Kiểm metadata; không chấm lại 1.660 vector trên VM'),
        ('Realtime boundary','Một window 100 ms','Không phát kết quả ngay tại t=0')
      ],[29,35,36])+
      note('Tests OK không thay quality evaluation. Scenario test chỉ yêu cầu thấy dấu hiệu; không chứng minh model bắt đủ 40/40 payload windows. State transition coverage cũng chưa đầy đủ.','warn')+
      ref('tests/test_pipeline.py:18; 32; 91; 105; 110'))

    page('VM replay: thứ tự gọi hàm','V1 · A1 → B1 → B2 → B3 → B4/B5 → B6',
      code('./build/ai-vids replay data/demo.csv models/demo.forest --realtime')+
      flow([('1 · main(replay)','Load Forest + whitelist','Tạo Extractor và Detector'),
            ('2 · read_csv / parse','Đọc từng dòng raw CSV','Frame{us, id, data}'),
            ('3 · Extractor.push','advance(timestamp) trước','Kiểm biên window cũ'),
            ('4 · finish window','8 feature float32','Reset sau khi emit'),
            ('5 · Detector.emit','Chờ window end nếu realtime','Gọi Forest.score'),
            ('6 · Rule + state','Unknown / rate / ML score','Debounce + latch'),
            ('7 · JSON stdout','Một dòng / window hoàn chỉnh','tee → terminal/file')], 'Callback/lambda nối các bước trong cùng một luồng, chưa phải queue hoặc RPC.')+
      table(['Arch / task','Hàm','Thứ tự cần nhớ'],[
        ('B1 · T08','parse_frame / read_csv','Label CSV không tham gia quyết định'),
        ('B2 · T11','advance','Đóng window cũ trước khi thêm frame ở biên'),
        ('B3 · T12','push + finish','Tích lũy từng frame; tạo vector lúc đóng window'),
        ('B4/B5/B6','score + emit','Một lần model/window, không phải model/frame')
      ],[23,27,50])+
      ref('src/main.cpp:279 → 122 → 98 → 76 → 66 → 46 → 190 → 169 → 206'))

    f=LOG['reconstructed_features'];event=LOG['example_event']
    page('Đi xuyên một window trong log của bạn','V1 · VÍ DỤ 40,8 → 40,9 GIÂY',
      note('<b>92 frame → 8 feature → 64 cây → score 0,461507 → không kích hoạt rule → HEALTHY.</b> Một dòng log là một window 100 ms.')+
      table(['Index / feature','Giá trị tái dựng','Ý nghĩa'],[
        ('0 · fps',f['fps'],'92 / 0,1 giây = 920 frames/s'),
        ('1 · unique_ids',f['unique_ids'],'Số ID khác nhau'),
        ('2 · id_entropy',f['id_entropy'],'Độ phân bố ID theo -Σ p log2 p'),
        ('3 · max_id_share',f['max_id_share'],'Tỷ trọng ID xuất hiện nhiều nhất'),
        ('4 · byte_mean',f['byte_mean'],'Trung bình giá trị byte payload'),
        ('5 · byte_std',f['byte_std'],'Population standard deviation'),
        ('6 · bit_flip_mean',f['bit_flip_mean'],'Tỷ lệ bit đổi giữa frame cùng ID/cùng DLC'),
        ('7 · same_id_iat_ms',f['same_id_iat_ms'],'Trung bình inter-arrival cùng ID trong window')
      ],[31,25,44])+
      p('Vector được tái dựng từ CSV/model gốc, không phải feature được in trong paste. 52/52 score ở đoạn log đầy đủ khớp reference trong 1e-9; khác biệt tối đa khoảng 4,67e-11 do số chữ số in.')+
      code('''
        unknown_frames = 0   → hard rule ID không kích hoạt
        fps = 920 <= 1800    → hard rule rate không kích hoạt
        score = 0.461507 < threshold = 0.608136
        abnormal = false    → reason = normal → state = HEALTHY
      ''')+
      p('Trong cây đầu: IAT 3,260888 &gt; 2,908064 nên đi phải; byte_std 19,05336 ≤ 19,17534 nên đi trái. Mỗi cây đi tới leaf; tổng hợp path length cho ra anomaly score, không phải xác suất tấn công.')+
      ref('runtime/vm-log-walkthrough.json; Extractor::finish:46; Forest::score:169; Detector::emit:190'))

    page('Event JSON, timestamp và ý nghĩa phép đo','CHUNG · CONTRACT V1',
      table(['Trường','Nguồn trong code','Cách đọc'],[
        ('t_ms','w.start / 1000','Bắt đầu window trong miền thời gian của source'),
        ('window_end_ms','(start + WINDOW_US) / 1000','Kết thúc window; không phải UTC'),
        ('frames / fps','w.count / w.x[0]','Số frame và rate quy đổi trên 100 ms'),
        ('score / threshold','Forest.score / model header','Score lớn hơn threshold là ML anomaly'),
        ('state / reason','Decision engine','State có lịch sử; reason của window hiện tại'),
        ('unknown_frames','Extractor + whitelist','Frame ngoài whitelist trong window'),
        ('inference_us','steady_clock quanh score()','Chỉ model; loại trừ window/feature/rule/UI'),
        ('rx_drops','SO_RXQ_OVFL ở capture','Socket-drop counter; replay giữ mặc định 0'),
        ('ignored_frames','Frame filter ở capture','Frame ngoài scope; replay giữ mặc định 0')
      ],[24,31,45])+
      h('Bốn đại lượng cần đo riêng')+
      bullets('<b>Model latency:</b> riêng thời gian score(x); ví dụ log là 20,126 µs = 0,020126 ms.',
              '<b>Processing latency:</b> từ frame/window đủ điều kiện tới quyết định, gồm queue/feature/model/rule.',
              '<b>Detection delay:</b> từ attack onset ground truth tới first confirmed alert; gồm pha window và debounce.',
              '<b>UI delay:</b> thời gian alert đã có tới lúc người dùng thấy; UI v1 poll mỗi 350 ms.')+
      note('Không suy ra detection delay từ model P95. Counter 0 trong replay không chứng minh CAN vật lý không mất frame. VM timing còn chịu ảnh hưởng host/hypervisor.','warn')+
      ref('src/main.cpp:182–212; ui/index.html:24–25. V2 cần timestamp source/receive/decision có clock_domain.'))

    page('VM vcan: luồng Linux socket thật','V1 · T03 / T09 · A2 → B1',
      code('''
        sudo modprobe vcan
        sudo ip link add dev vcan0 type vcan
        sudo ip link set dev vcan0 up
        ./build/ai-vids capture vcan0 models/demo.forest
      ''')+
      flow([('Terminal B · cansend','666#1122334455667788','Tiến trình phát frame'),
            ('Kernel Ubuntu · vcan0','CAN ảo trong guest','Không cần CAN controller'),
            ('B1 · capture()','if_nametoindex → socket','setsockopt → bind'),
            ('poll / recvmsg','Nhận frame và ancillary','Filter / timestamp → Frame'),
            ('Core dùng chung','Extractor → model + rule','Decision → JSON'),
            ('Nếu không có frame','poll timeout 20 ms','advance → có thể NO_DATA')])+
      code('cansend vcan0 666#1122334455667788')+
      p('0x666 ngoài whitelist nên hard rule tạo unknown_id/ALERT tại cuối window dù score AI thấp. Capture không đọc demo.csv; timestamp hiện là monotonic user-space receipt time từ lúc capture khởi động.')+
      note('vcan kiểm API/logic nhận Linux; không mô phỏng arbitration, lỗi điện hoặc tải CAN vật lý. Một frame ID whitelist gửi tay cũng không tạo đúng phân bố normal training.','warn')+
      ref('src/main.cpp:218–255. Linux Kernel: <a href="https://docs.kernel.org/networking/can.html">SocketCAN/vcan</a>.'))

    page('VM dashboard và điều kiện kết thúc mốc','V1 · T20 / C1',
      flow([('Browser · bấm Play','POST /api/replay','Chưa tính AI trong browser'),
            ('Python replay worker','subprocess.Popen','ai-vids replay --realtime'),
            ('Executable C++','Feature → AI/rule/state','JSON stdout từng window'),
            ('Python event reader','json.loads → deque 600','Ghi events.ndjson'),
            ('GET /api/state','Browser poll 350 ms','Lấy event và status'),
            ('Canvas + metrics','Vẽ score/state/P95','Chỉ thể hiện output nhận được')])+
      code('python3 tools/serve.py --port 8765')+
      p('Mở browser trong guest tại <code>http://127.0.0.1:8765</code>. Muốn xem từ host dùng SSH tunnel. Capture terminal không tự đi vào server v1; live UI thuộc T21.')+
      table(['Bằng chứng kết thúc VM','Điều kiện'],[
        ('Environment + build log','Ghi OS/kernel/arch/compiler; native build thành công'),
        ('verify-vm.json + tests-vm.log','32 golden score PASS; 12 tests OK nếu đã chạy'),
        ('replay-vm.ndjson','460 windows cho full demo; paste hiện chỉ có 52 window cuối đầy đủ'),
        ('capture-vcan.ndjson + stderr','Có frame từ cansend, unknown_id và NO_DATA phù hợp')
      ],[39,61])+
      small('Validation metadata/nhãn “local PC” trong UI v1 có phần cố định. Đọc host/log của lượt chạy, không xem label đó là tự nhận diện VM/Pi. Python <a href="https://docs.python.org/3/library/http.server.html">http.server</a> là công cụ review; không dùng nguyên server này làm production API.')+
      ref('tools/serve.py:19/63/79/90; ui/index.html:22–25'))

    page('Training và artifact dùng chung hai cấu hình','CHUNG · D1 → D2 → D3 → D4 → B4',
      flow([('D1 · Dữ liệu đại diện','Normal + ground truth','Nguồn / version / profile'),
            ('D2 · Split theo session','Train / val / holdout','Không random frame gần nhau'),
            ('Feature extractor C++','Cùng công thức runtime','Schema / units / float32'),
            ('D3 · Fit trên PC','Normal train only','Chọn candidate bằng validation'),
            ('Calibration / holdout','Freeze trước final test','Report miss / false alerts'),
            ('D4 · Bundle','Cây + manifest + profile','Golden vectors + provenance')])+
      table(['Hiện có trong demo','Yêu cầu cho production'],[
        ('64 cây; max_samples 128; 8 feature','Candidate phải đạt quality trên dữ liệu đại diện'),
        ('threshold = quantile(-score_samples(val), 0.995)','Ngưỡng chọn trên validation theo false-alarm budget đã chốt'),
        ('Whitelist 0x100/0x200/0x300; rate >1800','Profile đúng bus/xe và version; không mang nguyên ngưỡng toy'),
        ('Window 100 ms; không scaler','Manifest ràng buộc schema/window/preprocessing tương thích'),
        ('Header + SHA-256 + metadata demo','Runtime/profile/data/model versions; xác thực nguồn release theo kênh phân phối')
      ],[47,53])+
      note('Model demo chưa đạt payload-shift detection bền vững: 1/40 windows vượt ngưỡng, chưa confirmed ALERT. Không promote artifact này thành model production.','danger')+
      small('Quy ước score dự án là <code>-sklearn.score_samples(x)</code>; không nhầm decision_function/offset. Nguồn: <a href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html">IsolationForest API</a>.')+
      ref('tools/prepare.py:75/81/84/86/96/119; T28–T35.'))

    page('Pi production: kiến trúc mục tiêu','V2 · A3/A4 + B/C · CẦN TRIỂN KHAI',
      flow([('A3 · Bus + adapter','CAN_H/CAN_L → controller','Driver Linux → can0'),
            ('B1 · Capture thread','Nhận frame / timestamp','Không đợi disk hoặc UI'),
            ('Qframe · Bounded','Capacity + deadline','Drop policy/counter rõ'),
            ('B2/B3 · Compute worker','Window / features','Schema đúng model bundle'),
            ('B4/B5 · Inference/rule','Model lab đã nghiệm thu','Profile đúng mạng đích'),
            ('B6 · Decision / health','Alarm độc lập health','Event có lifecycle'),
            ('Qevent · Bounded','Ưu tiên alert/health','Không mất âm thầm'),
            ('C2 · Async logger','Evidence + event index','Retention / disk policy'),
            ('C1/C3 · Read-only API','Live UI / metrics','Nguồn dữ liệu là Pi')], 'Màu/khối mô tả V2 target; queues/logger/live API chưa có trong runtime hiện tại.')+
      bullets('Pi: Linux 64-bit; binary ARM64 build/kiểm trên đúng OS/libc; không copy executable Windows.',
              'Adapter có controller + transceiver + driver hỗ trợ chế độ được chốt. Termination ở hai đầu bus; phương án reference/cách ly theo adapter.',
              'Bitrate, ID format và coverage phải xuất phát từ bus thực. Không mặc định mọi bus đều 500 kbit/s.',
              'Nguồn/tản nhiệt/storage theo Pi thực; phải đo throttle và write load trước vận hành dài hạn.')+
      note('Production là đích của thiết kế này. Hiện chưa có bằng chứng chạy Pi, queue/logger/service/rollback hoặc chất lượng model đạt production.','warn'))

    page('Pi: luồng khởi động từ cấp nguồn tới READY','V2 · BOOT / READINESS',
      flow([('1 · OS / driver','Kernel boot, adapter xuất hiện','Ghi boot_id / runtime version'),
            ('2 · CAN configuration','Interface + bitrate/mode','Đơn vị quản trị riêng'),
            ('3 · Service account','Mount/path/permissions','Đủ quyền đọc CAN và log'),
            ('4 · Verify release','Manifest / schema / hash','Từ chối bundle sai'),
            ('5 · Load model/profile','Golden self-test','Không dùng model demo'),
            ('6 · Start workers','Queues / storage / capture','Init health = STARTING'),
            ('7 · Observe input','Interface + heartbeat + data','Warm-up theo profile'),
            ('8 · READY hoặc lỗi','READY theo điều kiện rõ','Không đồng nhất process active')])+
      table(['Readiness requirement','Điều kiện'],[
        ('PI-BOOT-01','Đúng model/runtime/schema/profile; checksum/self-test đạt; đường lưu trữ khả dụng'),
        ('PI-BOOT-02','Interface tồn tại và cấu hình đúng; mode/coverage khớp mạng đã chốt'),
        ('PI-BOOT-03','Capture/compute/logger heartbeat tiến triển; không backlog quá deadline'),
        ('PI-BOOT-04','Quan sát/không dữ liệu được phân biệt theo profile, không báo healthy vì model chưa load')
      ],[28,72])+
      p('Nếu model corrupt hoặc schema sai: không READY; phát lỗi rõ và dừng/chờ can thiệp theo policy. Nếu bus im lặng hợp lệ, dùng trạng thái NO_DATA/IDLE được khai báo, không tự xác nhận mạng an toàn.')+
      ref('T07/T09/T15/T19/T35/T38. Hiện main.cpp chỉ load + bind/capture; quy trình readiness V2 cần bổ sung.'))

    page('Pi: đường dữ liệu và giới hạn backlog','V2 · THỜI GIAN CHẠY',
      table(['Bước','Input → output','Ràng buộc thiết kế'],[
        ('1. Capture','can_frame + timestamp → normalized Frame','Không gọi disk/UI; quan sát kernel/driver/socket drops'),
        ('2. Qframe','Frame → compute worker','Bounded; counter; deadline; không tự tăng RAM'),
        ('3. Window/feature','Frames → vector + data_quality','Order/clock đúng; cửa sổ có mất dữ liệu phải degraded'),
        ('4. Model/rule','Vector/profile → score + reasons','Không nạp/train model mới trong hot path'),
        ('5. Decision','Evidence → alarm transition + health','Lưu model/profile versions và thời điểm decision'),
        ('6. Qevent/logger','Event → durable index/raw chunks','Giới hạn tải; alert/health không bị bỏ âm thầm'),
        ('7. API/UI','Store/snapshot → read-only view','UI không tạo backpressure vào capture')
      ],[22,38,40])+
      h('Định nghĩa ngân sách trước khi chọn capacity')+
      code('''
        capacity cơ sở ≈ measured_peak_frames_per_s × max_queue_wait_s
        cộng headroom được review; vẫn phải có max age/deadline
        detection_delay = decision_time - attack_onset_time
      ''')+
      bullets('Chốt peak load theo bus/capture thực; số frame/s không tự suy ra chính xác từ bitrate.',
              'Overflow policy phải rõ (ví dụ drop-new); tính đúng số rơi và đánh dấu window bị ảnh hưởng.',
              'Không chỉ đo average: cần P95/P99, max backlog age và resource dưới tải/ghi log chậm.',
              'Cả feature schema, window/hop và debounce phải được tính vào độ trễ phát hiện.')+
      note('SPSC queue, deadline/drop policy và worker tách luồng là yêu cầu mới của T26, chưa tồn tại trong C++ hiện tại.','warn')+
      ref('T10/T11/T12/T19/T25/T26; thay đổi concurrency phải kiểm parity/order/lifetime bộ nhớ.'))

    page('Pi: alarm và health là hai trục độc lập','V2 · T18 / T19 / T27',
      two(
        h('Alarm state')+code('''
          CLEAR → SUSPECT → OPEN
          OPEN → UPDATED → CLOSED
          Mỗi alarm có ID/lifecycle
          và evidence/model versions
        ''')+p('Debounce/hysteresis theo profile; rule nghiêm trọng có thể mở ngay sau window. Không đếm mỗi window OPEN thành một attack event.'),
        h('Sensor health')+code('''
          STARTING → OK
          OK → STALE / DEGRADED
          bất kỳ → FAILED
          phục hồi → OK + audit event
        ''')+p('Silence, drops, interface lỗi, disk/backlog và heartbeat quyết định health; không tự đóng alarm đang mở.'))+
      table(['Sự cố','Hành vi yêu cầu','Nghiệm thu'],[
        ('Mất traffic','STALE/NO_DATA theo profile; giữ alarm','Silence không xóa lịch sử alert'),
        ('Interface down','Health FAILED/STALE; lỗi có ngữ cảnh','Không in normal giả; recovery quan sát được'),
        ('Socket/app queue drop','DEGRADED; đếm đúng; mark window','Mất dữ liệu không bị che bởi score normal'),
        ('Model/schema lỗi','Không READY; không âm thầm bỏ ML','Fail rõ; rules-only chỉ khi cấu hình và hiển thị'),
        ('Disk full/slow','Health/storage error; policy evidence','Capture không treo theo disk'),
        ('Worker heartbeat đứng','Health FAILED; supervisor dừng với exit nonzero theo deadline đã chốt','Gây treo worker; restart không che downtime'),
        ('Process restart','Boot/session mới; phục hồi/open alarm policy','Không làm mất dấu downtime hoặc alarm')
      ],[24,43,33])+
      note('V1 hiện có một state chung; NO_DATA reset good/bad và thay state. Vì vậy phải sửa T19 trước khi coi là health/alarm production độc lập.','warn')+
      ref('Current: Detector::emit, main.cpp:198. Target: T19/T22/T27.'))

    page('Pi: event, evidence, API và retention','V2 · C1/C2/C3',
      table(['Đối tượng','Trường/đầu ra tối thiểu','Dùng để'],[
        ('Window event','window start/end, score, reasons, schema/model/profile, data_quality','Tái hiện một quyết định'),
        ('Alert event','alert_id, opened/updated/closed, IDs liên quan, severity/reasons','Đếm và theo dõi một incident'),
        ('Health event','interface/drop/backlog/storage/heartbeat, boot/session','Phân biệt detector lỗi với mạng bất thường'),
        ('Evidence chunk','Raw pre/post-window, clock metadata, event reference, checksum','Đi từ alert về frame nguồn'),
        ('Read-only API','Live event cursor, health/readiness, metrics','UI/operator quan sát nguồn Pi'),
        ('Audit event','Release activation/rollback, profile/threshold/config changes','Truy nguyên thay đổi vận hành')
      ],[22,47,31])+
      h('Storage contract')+
      bullets('Chốt quota byte/time và reserve cho health/error; retention không phải “giữ mãi”.',
              'Raw pre/post-event buffer và durable event index phải bounded; ghi độc lập capture.',
              'Định nghĩa flush/fsync theo mức mất dữ liệu chấp nhận; test sudden restart/disk-full.',
              'stdout/journal dùng cho chẩn đoán process; không thay thế evidence store có lifecycle.')+
      h('API contract đề xuất, chưa có trong server v1')+
      code('''
        GET /healthz       → tiến trình/worker còn sống?
        GET /readyz        → đủ điều kiện phân tích có ý nghĩa?
        GET /api/events?after=<cursor> → sự kiện live từ store
        GET /api/metrics   → thời gian, drop, resource, release
      ''')+
      p('Mặc định local-only hoặc truy cập qua SSH tunnel; nếu expose mạng phải có authentication/TLS và quyền đọc phù hợp. UI production không có nút phát scenario lên CAN.')+
      ref('T21/T22/T23/T25. Server http.server hiện tại chỉ là review tool; API trên là target mới.'))

    page('Pi: bundle, filesystem và CLI mục tiêu','V2 · D4 / T35 / T36',
      code('''
        /opt/ai-vids/releases/<release_id>/
          bin/ai-vids
          model/model.forest
          model/manifest.json
          profile/profile.json
          golden/features.csv + scores.txt
        /opt/ai-vids/current -> releases/<release_id>
        /etc/ai-vids/config.json
        /var/lib/ai-vids/         # events / evidence / state
        /run/ai-vids/             # runtime heartbeat / sockets
      ''')+
      table(['Manifest/config contract','Yêu cầu'],[
        ('Release identity','runtime build/arch/OS-ABI + model_id + schema_id + profile_id'),
        ('Compatibility','Feature order/units/window/scaler/threshold khớp binary; golden parity'),
        ('Data provenance','Training-data fingerprint, split/evaluation report và production eligibility'),
        ('Interface/profile','can0, bitrate/mode do setup kiểm; coverage ID/FD đúng scope'),
        ('Runtime budget','Queue capacity/deadline, silence policy, storage quota từ bench đã chốt'),
        ('Integrity/authenticity','Hash kiểm integrity; xác thực publisher theo kênh release, không gọi hash là chữ ký')
      ],[28,72])+
      note('<b>CLI V2 đề xuất:</b> <code>ai-vids run --config /etc/ai-vids/config.json</code>. Mode <code>run</code>, config parser, manifest enforcement và worker supervisor <b>chưa được implement</b>. Binary hiện tại chỉ có features/score/replay/capture.','danger')+
      p('Tách lệnh mới để không giả vờ cấu hình đã được áp dụng. V2 parser phải reject option/schema không hỗ trợ; loader phải chặn demo-only model ở chế độ production.')+
      ref('Current CLI: src/main.cpp:260. Target: T17/T19/T26/T35/T38.'))

    page('Pi: service và tiến trình khởi động','V2 · TEMPLATE CHƯA THỂ DÙNG VỚI BINARY V1',
      note('Unit dưới đây dành cho daemon V2 sau khi đã có mode run/config. ai-vids-can.service là unit setup adapter/interface phải viết và kiểm với OS/driver thật. Đây không phải installer đã chạy.','warn')+
      code('''
        [Unit]
        Description=AI-VIDS production candidate
        Requires=ai-vids-can.service
        After=local-fs.target ai-vids-can.service
        StartLimitIntervalSec=60
        StartLimitBurst=5

        [Service]
        Type=simple
        User=ai-vids
        Group=ai-vids
        WorkingDirectory=/opt/ai-vids/current
        ExecStart=/opt/ai-vids/current/bin/ai-vids run --config /etc/ai-vids/config.json
        Restart=on-failure
        RestartSec=3
        TimeoutStopSec=10
        RuntimeDirectory=ai-vids
        StateDirectory=ai-vids
        NoNewPrivileges=true
        ProtectSystem=strict
        ProtectHome=true
        PrivateTmp=true
        ReadWritePaths=/var/lib/ai-vids /run/ai-vids
        StandardOutput=journal
        StandardError=journal

        [Install]
        WantedBy=multi-user.target
      ''')+
      bullets('Interface được cấu hình bởi đơn vị quản trị riêng; IDS không tự đổi bitrate trong hot path.',
              'Type=simple chỉ giám sát process; READY phải do health/readiness contract kiểm. Không thêm Type=notify/WatchdogSec khi chưa có protocol heartbeat tương ứng.',
              'Không bật PrivateNetwork làm mất network namespace chứa can0. Kiểm quyền/sandbox trên OS đích; không mặc định chạy root để bỏ qua lỗi.')+
      small('Cơ chế service/restart/type: <a href="https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html">systemd.service</a>; môi trường/path isolation: <a href="https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html">systemd.exec</a>. Phải đối chiếu phiên bản systemd thực tế.'))

    page('Pi: deploy, promote và rollback','V2 · D5 / T37 / T38',
      flow([('1 · Build candidate','ARM64 + pinned environment','Bundle runtime/model/profile'),
            ('2 · Verify / self-test','Integrity + compatibility','Golden score + eligibility'),
            ('3 · Staging / shadow','Replay → vcan → testbench','Chưa thay bản đang dùng'),
            ('4 · Gate review','Quality / resources / soak','Chấp thuận release cụ thể'),
            ('5 · Activate','Chuyển current atomically','Restart có downtime được ghi'),
            ('6 · Post-start checks','Readiness + live smoke','Release IDs và health đúng'),
            ('7 · Fail → rollback','Chọn previous known-good','Runtime + model + profile'),
            ('8 · Audit / theo dõi','Ghi lý do và kết quả','Không auto-train trên traffic')])+
      table(['Tình huống','Hành vi yêu cầu'],[
        ('Candidate hash/schema sai','Không activate; giữ current; trả lỗi có release ID'),
        ('Service boot fail / không ready','Không đánh dấu deploy thành công; rollback theo policy'),
        ('New model tăng false alerts','Giữ evidence và operator review; rollback bản đã biết tốt'),
        ('Rollback','Đổi cả bộ tương thích; không chỉ thay forest khi feature schema khác'),
        ('Đang có alarm lúc restart','Giữ/rehydrate lifecycle hoặc mở incident downtime theo policy đã test')
      ],[34,66])+
      h('Pi staging: kiểm binary bằng CLI hiện có trước V2')+
      code('''
        cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
        cmake --build build -j2
        python3 tools/verify_pi_bundle.py
        ./build/ai-vids replay data/demo.csv models/demo.forest --realtime
      ''')+
      small('Sau khi có profile/model lab hợp lệ, capture dùng <code>ai-vids capture can0 MODEL</code>. Replay demo trên Pi chỉ kiểm chuyển nền tảng; không activate demo model cho production.')+
      note('Production chỉ được thực hiện sau khi bạn chấp thuận release và các gate đã đạt. PDF này không thực hiện SSH, đổi current, cài service hay cập nhật model trên thiết bị.','warn')+
      ref('T24/T25/T27/T34/T35/T37/T38. Source hiện tại chưa có updater, service installer hoặc rollback manager.'))

    page('Gate nghiệm thu và điểm chặn release','CHUNG / V2 · ACCEPTANCE',
      table(['Gate','Điều kiện đạt / đề xuất','Bằng chứng'],[
        ('G1 · Linux core','Native build; checksum; golden error ≤1e-7; 12 tests trong scope','VM logs; chưa thay Pi acceptance'),
        ('G2 · Pi parity','ARM64 binary trên Pi đúng cấu hình; golden score PASS','Pi environment + checker report'),
        ('G3 · Live input','vcan rồi CAN testbench; clock/order/filter/drop observability','Ground truth và capture logs'),
        ('G4 · Model quality','Chốt recall/event recall, false alerts/giờ và delay budget trước tuning; holdout độc lập','AI-only/rule-only/fused report; failure cases'),
        ('G5 · Performance','Mốc thử ban đầu ≥1000 frames/s, model P95 <20 ms; rated bus load và headroom phải chốt theo đo thực','Pi throughput/drop/CPU/RSS/nhiệt/backlog/P95/P99'),
        ('G6 · Reliability','Queue/disk/interface faults; restart; soak dài hạn. Đề xuất 24 h sau khi thống nhất tải và storage policy','Fault matrix; soak report; không unaccounted loss'),
        ('G7 · Release','Ready/stop/restart/rollback đúng; artifact compatibility; production approval','Release checklist + audit + quyết định review')
      ],[20,53,27])+
      h('Những ngưỡng phải chốt trước final test')+
      bullets('False-alarm budget và recall/detection-delay mục tiêu theo kịch bản; hiện chưa có giá trị được phê duyệt.',
              'Rated/peak traffic, allowable backlog/drop, CPU/RSS budget, nhiệt/throttle, quota và thời lượng lưu evidence.',
              'Tiêu chí startup readiness, silence hợp lệ, outage/recovery và rollback triggers.')+
      note('<b>Release blockers hiện tại:</b> model demo payload shift chưa đạt; thiếu dataset/profile thực; chưa đo Pi; chưa live UI, evidence retention, bounded queues, health/alarm separation hoặc rollback. Build chạy được không vượt qua các gate này.','danger')+
      ref('Mốc ≥1000 frames/s và <20 ms là mục tiêu thử nghiệm ban đầu trong ý tưởng, chưa phải kết quả đo/khả năng đã chứng minh.'))

    mapping={
      'T01':'parse_frame [98] · schema CSV', 'T02':'generate trên PC; main replay [279]',
      'T03':'modprobe / ip link · ngoài C++', 'T04':'Chưa có virtual ECU harness',
      'T05':'BOM/wiring/driver · chưa chốt hardware', 'T06':'capture(can0) [218] · chưa test vật lý',
      'T07':'CMake/native build · VM khác Pi ARM64', 'T08':'parse_frame/read_csv [98/122]',
      'T09':'capture/recvmsg [218/244]', 'T10':'timestamp lambda [235] · user space',
      'T11':'Extractor.advance/reset [66/62]', 'T12':'Extractor.push/finish [76/46]',
      'T13':'Chưa có per-ID/signal schema v2', 'T14':'Forest constructor/score [145/169]',
      'T15':'verify_pi_bundle.py [14] · golden parity', 'T16':'Detector.emit [195] · hard rules',
      'T17':'Whitelist [153] / rate [195] chỉ toy', 'T18':'Detector.emit state transitions [198]',
      'T19':'NO_DATA/counters có; chưa tách health', 'T20':'serve.replay [19] / UI poll [24]',
      'T21':'Chưa có live capture API/UI', 'T22':'emit JSON [206] · window event v1',
      'T23':'Chưa evidence buffer/retention', 'T24':'report.py / synthetic validation report',
      'T25':'emit inference_us [193]; chưa Pi bench', 'T26':'Chưa queues/async C++ logger',
      'T27':'test_pipeline negative cases [60]', 'T28':'Chưa dữ liệu thực trong pipeline',
      'T29':'Chưa converter HCRL/ROAD/lab', 'T30':'prepare [75] · synthetic sessions',
      'T31':'mode features [264] / prepare.extract [61]', 'T32':'prepare IsolationForest.fit [81]',
      'T33':'prepare threshold quantile [84]', 'T34':'Failure report: payload 1/40 ML windows',
      'T35':'Forest header/manifest [prepare 86/119]', 'T36':'package_pi.py + verifier [14]',
      'T37':'Guide/staging gates; chưa Pi staging', 'T38':'Chưa service/updater/rollback code',
    }
    short_status={'verified':'Kiểm local','partial':'Một phần','ready':'Chuẩn bị','todo':'Chưa làm','gap':'Chưa đạt'}
    for start,end in [(0,13),(13,26),(26,38)]:
        tasks=PLAN['tasks'][start:end]
        rows=[]
        for t in tasks:
            rows.append((f'<b>{t["id"]} · {t["node"]}</b><br>{t["weight"]}% · {short_status[t["status"]]}',
                         E(t['name'])+'<br><span class="small">'+E(mapping[t['id']])+'</span>',
                         E(t['use'])))
        page(f'Map task → code → outcome ({start+1:02}–{end:02})','TRA CỨU · WBS / ARCH',
          p('Task đánh theo vị trí kiến trúc, không phải thứ tự bắt buộc. Một hàm có thể hiện thực nhiều block. % là công sức tương đối; tổng 38 task bằng 100%.')+
          table(['Task / arch / effort','Công việc và implementation hiện tại','Outcome dùng để'],rows,[19,44,37])+
          small('“Kiểm local” là scope PC đã có bằng chứng, không tự đồng nghĩa VM/Pi đã đủ gate. Phụ thuộc và tiêu chí chi tiết có trong docs/TASK_BREAKDOWN.vi.md; bảng này map trực tiếp để đọc code.')+
          ref('Mặc định số [dòng] thuộc src/main.cpp, trừ khi ghi file khác. Source snapshot được ghi ở trang cuối.'))

    page('Tra nhanh: lệnh nào đi qua phần nào?','CHUNG · EXECUTION PLAYBOOK',
      table(['Lệnh','Đường xử lý','Kết quả'],[
        ('cmake --build build','Compiler/linker; không gọi main runtime','Binary mới; không tự train model'),
        ('ai-vids features INPUT OUTPUT','CSV → Extractor → vector','Feature CSV; không score/rule/state'),
        ('ai-vids score MODEL FEATURES','Vector có sẵn → Forest.score','Scalar mỗi dòng; không capture/window'),
        ('ai-vids replay INPUT MODEL','CSV → full core → emit','NDJSON; rx_drops/ignored mặc định 0'),
        ('ai-vids capture vcan0 MODEL','Linux socket → full core','NDJSON live; timestamp nhận user space'),
        ('python3 tools/serve.py','HTTP → subprocess replay khi bấm Play','API/UI replay; không tự thấy capture terminal'),
        ('ai-vids run --config ...','CLI V2 đề xuất','Chưa có trong binary hiện tại; chỉ dùng sau khi implement')
      ],[32,42,26])+
      h('Tự xem dữ liệu trung gian, không train lại')+
      code('''
        ./build/ai-vids features data/demo.csv runtime/inspect.csv
        ./build/ai-vids score models/demo.forest runtime/inspect.csv
        ./build/ai-vids replay data/demo.csv models/demo.forest
      ''')+
      h('Bốn câu hỏi để đọc một event')+
      bullets('Nguồn là replay hay capture, timestamp thuộc clock nào?',
              'Feature/model/profile version nào tạo score và threshold?',
              'Reason đến từ rule hay ML; state có đang latch theo lịch sử không?',
              'Health/data_quality có đủ tin cậy, hay đang có gap/drop/storage lỗi?')+
      ref('CLI dispatch main.cpp:260; fields emit:206; code walkthrough docs/VM_EXECUTION_MAP.vi.md.'))

    source_hash=hashlib.sha256((ROOT/'src'/'main.cpp').read_bytes()).hexdigest()
    page('Nguồn tham chiếu và checklist review','KẾT THÚC SPEC · v1.0',
      table(['Nguồn chính thức','Phần hỗ trợ trong spec'],[
        ('<a href="https://docs.kernel.org/networking/can.html">Linux Kernel — SocketCAN</a>','Interface/socket API, vcan, controller modes'),
        ('<a href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html">scikit-learn — IsolationForest</a>','Quy ước score/offset và mô hình forest'),
        ('<a href="https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html">systemd.service</a> / <a href="https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html">systemd.exec</a>','Type/restart và môi trường thực thi service'),
        ('<a href="https://docs.python.org/3/library/http.server.html">Python — http.server</a>','Phạm vi server review; không dùng nguyên bản cho production'),
        ('<a href="https://www.raspberrypi.com/documentation/computers/remote-access.html">Raspberry Pi — remote access</a>','SSH/SCP/tunnel cho quản trị local'),
        ('<a href="https://ubuntu.com/server/docs/how-to/security/openssh-server/">Ubuntu — OpenSSH</a>','Thiết lập SSH nếu dùng để copy/kết nối VM')
      ],[48,52])+
      p('Sơ đồ worker, requirement, release gates và config/CLI V2 là thiết kế đề xuất của dự án, không phải tính năng đã tồn tại chỉ vì có trong tài liệu. Tài liệu tham chiếu có thể theo bản mới; cần đối chiếu OS/kernel/systemd đích.')+
      h('Thông tin cần bạn chốt để triển khai V2')+
      bullets('Pi RAM/OS/kernel; adapter/model controller, driver, bitrate và ID/FD coverage.',
              'Dataset/profile/DBC và quyền truy cập dữ liệu đại diện cho mạng đích.',
              'Recall/false-alarm/detection-delay budget, peak load và resource/storage quota.',
              'Readiness/recovery, evidence retention, release/rollback triggers và người chấp thuận.')+
      note('Review theo mã: ví dụ “PI-BOOT-03 cần heartbeat compute; T19 phải giữ alarm khi mất traffic”. Chỉ thực hiện production sau quyết định riêng của bạn.','info')+
      small('<b>Source snapshot:</b> src/main.cpp SHA-256<br><span class="mono">'+source_hash+'</span>')+
      small('<b>Evidence dùng trong spec:</b> docs/VALIDATION.vi.md, docs/REVIEW_PLAN.json, runtime/vm-log-walkthrough.json; bản source và gói đã trao đổi. User paste có 52 window cuối đầy đủ, không phải toàn bộ bộ hồ sơ kiểm thử VM.')+
      small('<b>Revision:</b> 1.0 · 01/11/2026 · Nội dung tiếng Việt · Hai cấu hình V1/V2 trong một tài liệu.'))


CSS='''
@page{size:A4;margin:15mm 14mm 17mm}
*{box-sizing:border-box}html,body{margin:0;padding:0}body{font:10pt/1.34 Arial,'Segoe UI',sans-serif;color:#20364b;background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sheet{width:182mm;height:260mm;position:relative;break-after:page;page-break-after:always}.sheet:last-child{break-after:auto;page-break-after:auto}.topline{display:flex;justify-content:space-between;border-bottom:2px solid #087f78;padding:0 0 6px;color:#49677e;font-size:8pt;letter-spacing:.45px}.topline b{color:#087f78}.head h1{font-size:20pt;line-height:1.15;color:#102e48;margin:14px 0 12px}.head .section{font-size:8pt;letter-spacing:1px;text-transform:uppercase;color:#087f78;margin-top:11px}.body{padding-bottom:12px}p{margin:9px 0}h2{font-size:12pt;color:#113f5c;margin:14px 0 7px}ul{padding-left:19px;margin:8px 0}li{margin:5px 0}table{width:100%;border-collapse:collapse;table-layout:fixed;margin:11px 0;font-size:9pt;line-height:1.28}th{background:#173c53;color:#fff;text-align:left;font-weight:700}th,td{padding:7px 8px;vertical-align:top;border:1px solid #d4dfe7;overflow-wrap:anywhere}tbody tr:nth-child(even){background:#f1f6f8}pre{font:9pt/1.34 Consolas,'Courier New',monospace;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#eef3f7;border:1px solid #d2dce5;border-radius:6px;padding:11px 13px;margin:10px 0;color:#153b50}code,.mono{font-family:Consolas,'Courier New',monospace;font-size:.94em}code{background:#edf3f5;padding:1px 3px}.note{padding:10px 12px;border-left:4px solid #088579;background:#edf8f4;border-radius:3px;margin:11px 0}.note.warn{background:#fff6e3;border-color:#bc821b}.note.danger{background:#fff0f1;border-color:#b64252}.small{font-size:8.4pt;line-height:1.3;color:#4a657b}.source{font-size:8pt;line-height:1.3;color:#5b7184;margin-top:12px;border-top:1px solid #dfe7ec;padding-top:7px}.footer{position:absolute;bottom:0;left:0;right:0;border-top:1px solid #b9ccd8;padding-top:5px;display:flex;justify-content:space-between;font-size:8pt;color:#557086}.flow{display:block;width:100%;height:auto;margin:10px 0 3px}.caption{font-size:8pt;color:#577188;margin:3px 0 9px}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.cover-title{font-size:30pt;line-height:1.12;font-weight:700;letter-spacing:-.5px;color:#102f48;margin:22px 0 19px}a{color:#087b78;text-decoration:underline}.toc{font-size:8.6pt;columns:2;column-gap:24px}.toc div{break-inside:avoid;margin:4px 0}.page-tag{font-weight:700;color:#087f78}.sheet.cover .head h1{font-size:35pt;margin-bottom:3px}
@media screen{body{background:#dfe7ec}.sheet{background:#fff;margin:18px auto;padding:0;box-shadow:0 4px 18px #0002;outline:1px solid #bdcdd9}.topline{padding-top:4px}}
'''


def make_html():
    toc='<div class="toc">'+''.join(f'<div><a href="#page-{i+1}">{i+1:02} · {E(p["title"])}</a></div>' for i,p in enumerate(PAGES) if i>=2)+'</div>'
    PAGES[1]['content']=PAGES[1]['content'].replace('<div id="toc-placeholder"></div>',toc)
    sections=[]
    for i,item in enumerate(PAGES,1):
        sections.append(f'''<section class="sheet {'cover' if i==1 else ''}" id="page-{i}">
<div class="topline"><b>AI–VIDS / TECHNICAL SPEC v1.0</b><span>{E(item['status'])}</span></div>
<div class="head"><div class="section">{E(item['part'])}</div><h1>{E(item['title'])}</h1></div>
<div class="body">{item['content']}</div><div class="footer"><span>01/11/2026 · VM hiện tại / Pi production mục tiêu</span><span>{i:02} / {len(PAGES):02}</span></div></section>''')
    return '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI-VIDS — Spec Ubuntu VMware và Raspberry Pi Production v1.0</title><style>'+CSS+'</style><body>'+''.join(sections)+'</body></html>'


class CDP:
    def __init__(self,url):
        import websocket
        self.ws=websocket.create_connection(url,timeout=60,suppress_origin=True);self.id=0
    def call(self,method,params=None):
        self.id+=1;self.ws.send(json.dumps({'id':self.id,'method':method,'params':params or {}}))
        while True:
            r=json.loads(self.ws.recv())
            if r.get('id')==self.id:
                if 'error' in r:raise RuntimeError(r['error'])
                return r.get('result',{})
    def evaluate(self,expression):
        r=self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')


def render(chrome,html_path):
    profile=tempfile.mkdtemp(prefix='ai-vids-pdf-')
    args=[chrome,'--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',
          '--user-data-dir='+profile,'about:blank']
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    proc=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**kwargs)
    try:
        portfile=Path(profile)/'DevToolsActivePort';deadline=time.monotonic()+25
        while not portfile.exists():
            if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Chrome startup failed')
            time.sleep(.1)
        port=portfile.read_text().splitlines()[0]
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list') as r:targets=json.load(r)
        target=next(t for t in targets if t['type']=='page');cdp=CDP(target['webSocketDebuggerUrl'])
        cdp.call('Page.enable');cdp.call('Emulation.setEmulatedMedia',{'media':'print'})
        cdp.call('Page.navigate',{'url':html_path.as_uri()})
        deadline=time.monotonic()+20
        while not cdp.evaluate("document.readyState==='complete' && document.querySelectorAll('.sheet').length===26"):
            if time.monotonic()>deadline:raise RuntimeError('Spec load timeout')
            time.sleep(.1)
        cdp.evaluate('document.fonts.ready.then(()=>true)')
        bounds=cdp.evaluate("Array.from(document.querySelectorAll('.sheet')).map((p,i)=>({page:i+1,bottom:p.querySelector('.body').getBoundingClientRect().bottom,limit:p.querySelector('.footer').getBoundingClientRect().top-8}))")
        overflow=[b for b in bounds if b['bottom']>b['limit']]
        (OUT/'layout-validation.json').write_text(json.dumps({'pages':bounds,'overflow':overflow},indent=2),encoding='utf-8')
        if overflow:
            (OUT/'layout-overflow.json').write_text(json.dumps(overflow,indent=2),encoding='utf-8')
            raise RuntimeError('Page content overflow: '+json.dumps(overflow))
        data=cdp.call('Page.printToPDF',{'printBackground':True,'preferCSSPageSize':True,'displayHeaderFooter':False})
        raw_folder=ROOT/'build'/'spec';raw_folder.mkdir(parents=True,exist_ok=True)
        raw=raw_folder/(STEM+'.raw.pdf');raw.write_bytes(base64.b64decode(data['data']))
        cdp.ws.close()
        return raw
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill()


def finish_pdf(raw):
    from pypdf import PdfReader,PdfWriter
    reader=PdfReader(raw)
    if len(reader.pages)!=len(PAGES):raise RuntimeError(f'Unexpected PDF pages: {len(reader.pages)} vs {len(PAGES)}')
    for i,pdfpage in enumerate(reader.pages):
        text=' '.join(pdfpage.extract_text().split())
        if len(text)<120:raise RuntimeError(f'Empty/sparse PDF page {i+1}')
    writer=PdfWriter();writer.append(reader)
    for i,item in enumerate(PAGES):writer.add_outline_item(f'{i+1:02} · '+item['title'],i)
    writer.add_metadata({'/Title':'AI-VIDS — Spec Ubuntu VMware và Raspberry Pi Production v1.0',
                         '/Author':'AI-VIDS Project','/Subject':'Luồng chạy, task/code mapping và production target',
                         '/Keywords':'CAN, SocketCAN, Edge AI, Raspberry Pi, Ubuntu, VMware, technical spec'})
    target=OUT/(STEM+'.pdf')
    with target.open('wb') as f:writer.write(f)
    return target


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--html-only',action='store_true')
    parser.add_argument('--chrome',default=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    make_pages();assert len(PAGES)==26,len(PAGES)
    assert sum(t['weight'] for t in PLAN['tasks'])==100
    html_path=OUT/(STEM+'.html');html_path.write_text(make_html(),encoding='utf-8')
    (OUT/'spec-pages.json').write_text(json.dumps([{'page':i+1,'title':p['title'],'part':p['part']} for i,p in enumerate(PAGES)],ensure_ascii=False,indent=2),encoding='utf-8')
    if args.html_only:print(str(html_path));return
    raw=render(args.chrome,html_path);pdf=finish_pdf(raw)
    print(json.dumps({'pdf':pdf.name,'pages':len(PAGES),'bytes':pdf.stat().st_size,'html_source':html_path.name},ensure_ascii=True))


if __name__=='__main__':main()

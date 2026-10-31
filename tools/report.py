"""Persist evidence from the final local validation run, without overstating it."""
import json
import math
from pathlib import Path
import platform

ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'runtime'/'validation.json').read_text())
browser=json.loads((ROOT/'runtime'/'browser-validation.json').read_text())
events=[json.loads(line) for line in (ROOT/'runtime'/'events.ndjson').read_text().splitlines()]
times=sorted(e['inference_us'] for e in events if e['frames'])
p95=times[math.ceil(len(times)*.95)-1]
rows=[]
for label,start,end,expected in [('Flooding',8000,12000,'possible_flooding'),
                                ('Unknown ID',18000,22000,'unknown_id'),
                                ('Payload shift',28000,32000,'ml_anomaly'),
                                ('Silence',38000,40000,'no_frames')]:
    group=[e for e in events if start<=e['t_ms']<end]
    evidence=sum(e['reason']==expected for e in group)
    ml=sum(e['score']>e['threshold'] for e in group if e['frames'])
    rows.append(f'| {label} | {len(group)} | {evidence} | {ml} | `{expected}` |')
text=f'''# Kết quả kiểm chứng local

Cập nhật 29/10/2026. Môi trường: {platform.system()} {platform.machine()}, Python {platform.python_version()}; executable native C++17. Đây là kết quả trên PC hiện tại, **không phải Raspberry Pi**.

## Pipeline và model

- Build C++ native: đạt. Nhánh Linux/AArch64 được cross-compile thành object bằng Zig; chưa link/chạy trên Linux/Pi.
- Unit/integration: **12/12 đạt**, gồm feature tính tay, window boundary, realtime phát sau window end, silence, zero DLC, input lỗi, label leakage và model schema sai.
- Train: {report['train_windows']} window normal tổng hợp. Validation: {report['validation_windows']} window normal độc lập. Normal test: {report['normal_test_windows']} window riêng.
- Python/C++ score parity: **{report['parity_windows']} window**, max absolute error **{report['max_score_parity_error']:.3g}**, tiêu chí ≤1e-7.
- Threshold: **{report['threshold']:.6f}**, percentile 99.5% trên normal validation; không chỉnh bằng test set.
- ML window FPR trên normal test tổng hợp: **{report['normal_test_ml_window_fpr']*100:.2f}%**. Chỉ 60 giây normal tổng hợp; không suy ra false alerts/giờ trên xe.
- Model fingerprint SHA-256: `{report['artifact_sha256']}`.

## Replay qua dashboard

- Browser: {browser['browser']}; desktop {browser['desktop']}, viewport nhỏ {browser['mobile']}.
- Toàn bộ replay: **{len(events)} windows / 46 giây mô phỏng**; không lỗi JavaScript, không tràn chiều ngang ở ba tab.
- Model-only P95 ở lượt realtime replay trên local PC: **{p95:.1f} µs**. Không bao gồm window accumulation, feature extraction, queue, debounce hay UI; giá trị thay đổi theo máy/tải.

| Kịch bản tổng hợp | Windows | Windows có đúng dấu hiệu | Windows ML vượt ngưỡng | Lý do |
|---|---:|---:|---:|---|
{chr(10).join(rows)}

Cột ML và cột dấu hiệu đo hai thành phần khác nhau. Flooding/unknown ID có thể do rule bắt dù model không vượt ngưỡng. Không dùng kết quả ghép rule+AI để tuyên bố model AI tự nhận diện được tất cả kịch bản. Silence là health event.

**Vấn đề cần review:** ở kịch bản payload shift hiện tại, chỉ 1/40 window vượt threshold; không đủ hai window liên tiếp để tạo confirmed ALERT. Model global-feature này còn yếu với thay đổi payload và không đạt tiêu chí phát hiện bền vững cho kịch bản đó. Cần nghiên cứu feature theo từng ID/signal hoặc model bổ sung bằng dữ liệu đại diện; không hạ threshold dựa trên demo để che hạn chế này.

## Chưa được kiểm chứng

HCRL/ROAD, traffic thật, DBC, spoofing/replay theo ngữ nghĩa signal, SocketCAN runtime, Pi throughput/CPU/RAM/nhiệt, long-run stability, kernel/driver drops, evidence retention và production rollback. Không có deployment lên Pi hay production.

## Tái lập

```powershell
.\\.venv\\Scripts\\python.exe tools/prepare.py
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
.\\.venv\\Scripts\\python.exe tools/serve.py
# Terminal khác, cài requirements-review.txt nếu cần:
.\\.venv\\Scripts\\python.exe tests/browser_smoke.py
.\\.venv\\Scripts\\python.exe tools/report.py
```

![Review local](local-review.png)

![Demo flooding](local-demo.png)
'''
(ROOT/'docs'/'VALIDATION.vi.md').write_text(text,encoding='utf-8')
print('docs/VALIDATION.vi.md')

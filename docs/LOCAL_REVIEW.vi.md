# Review local

## Mở ứng dụng

Tại thư mục `automotive-edge-ai-ids`:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

Mở **http://127.0.0.1:8765**. Nếu port đã được dùng bởi bản server đang chạy thì mở URL đó; không cần chạy thêm server. Dừng bằng Ctrl+C trong terminal của server. Nếu muốn port khác:

```powershell
.\.venv\Scripts\python.exe tools/serve.py --port 8766
```

## Các bước review

1. Tab **Kiến trúc A–Z**: xem source, edge runtime, dashboard, train/export/release và những phần mới là thiết kế.
2. Tab **Chạy demo** → **Chạy kịch bản**: 46 giây traffic mô phỏng. C++ inference model đã train, xuất score thực.
3. Khoảng 8–12 s: frame rate cao, rule `possible_flooding`.
4. Khoảng 18–22 s: frame 0x666 ngoài whitelist, rule `unknown_id`.
5. Khoảng 28–32 s: payload đổi phân bố. Model hiện chỉ vượt ngưỡng 1/40 window ở kịch bản này nên chưa tạo confirmed ALERT; đây là hạn chế cần review và cải thiện feature/model. Một `ml_anomaly` cũng không phải bằng chứng xác nhận spoofing.
6. Khoảng 38–40 s: im lặng, trạng thái `NO_DATA`. Score UI hiển thị “—”.
7. Khi quay lại normal: ALERT chỉ clear sau 5 normal window liên tiếp.
8. Tab **Kiểm chứng**: xem số window đã đối chiếu C++/Python và ML window FPR trên normal tổng hợp holdout.

Biểu đồ dùng 12 giây gần nhất; window 100 ms. P95 trên UI là thời gian model C++ trên local PC, không bao gồm tích lũy window, đọc file, UI hay debounce. Giá trị này không đại diện Raspberry Pi.

## Kiểm thử bằng command line

```powershell
.\build\ai-vids.exe replay data/demo.csv models/demo.forest
.\build\ai-vids.exe features data/demo.csv data/manual_features.csv
.\build\ai-vids.exe score models/demo.forest data/manual_features.csv
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`replay` không có `--realtime` chạy nhanh nhất có thể; không dùng thời gian tổng của nó làm detection delay.

## Build bằng CMake trên Linux development

Các lệnh dưới đây là hướng dẫn cho bước Linux lab sau review, chưa được thực thi trên Pi:

```bash
cmake -S . -B build-linux -DCMAKE_BUILD_TYPE=Release
cmake --build build-linux -j2
./build-linux/ai-vids replay data/demo.csv models/demo.forest
```

Sau khi có Linux vcan0 đã cấu hình và source model phù hợp, mode capture có dạng:

```bash
./build-linux/ai-vids capture vcan0 models/demo.forest
```

Model demo chỉ hợp với traffic tổng hợp của demo; không dùng nó làm model bảo vệ CAN bus thật. Chưa có script phát traffic lên CAN trong bản này.

## Những gì cần chốt

Review kiến trúc, module, feature/schema, cách giải thích cảnh báo và giao diện. Sau đó mới chuyển sang tích hợp Linux/Pi, thu dữ liệu thực và benchmark. Không có tác vụ tự đẩy lên production.

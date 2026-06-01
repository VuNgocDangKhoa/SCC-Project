# Screen Content Coding (SCC) Evaluation

Hệ thống đánh giá và so sánh hiệu suất mã hóa video giữa **HEVC (H.265)** và **VVC (H.266)**.

Quy trình tự động: Video MP4 → YUV 4:4:4 → Mã hóa (4 codec × 4 QP) → Trích metrics → Vẽ RD curves.

## Mục lục

1. [Tính năng](#tính-năng)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Hướng dẫn cài đặt](#hướng-dẫn-cài-đặt)
4. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
5. [Chạy app & lệnh hữu ích](#chạy-app--lệnh-hữu-ích)

---

## Tính năng

* **Xử lý video tự động**
    * Chuyển đổi MP4 → YUV 4:4:4 tự động
    * Trích metadata (resolution, fps, total frames)
    * Hỗ trợ xử lý batch multiple videos cùng lúc

* **Mã hóa video song song**
    * Chạy multiprocessing với HM (HEVC) & VTM (VVC) encoders
    * So sánh 4 profile codec: HEVC-Anchor, HEVC-SCC, VVC-Anchor, VVC-SCC
    * Mỗi video test 4 mức chất lượng QP (22, 27, 32, 37)
    * Trích metrics từ encoder logs: bitrate, PSNR-Y, PSNR-U, PSNR-V, encoding time

* **Bảng dữ liệu thô (Raw Data)**
    * Xem chi tiết kết quả mã hóa của từng codec × QP
    * Tính toán thống kê: bitrate trung bình, PSNR trung bình
    * Số lượng codec đã test

* **Phân tích RD Curves (Rate-Distortion)**
    * Vẽ biểu đồ cho thấy mối quan hệ giữa bitrate và chất lượng
    * So sánh 4 codec trên cùng một đồ thị
    * Giúp nhận diện codec nào hiệu quả nhất

* **So sánh Encoding Time**
    * Biểu đồ histogram thời gian mã hóa của từng codec
    * Đánh giá độ phức tạp tính toán (VVC vs HEVC)

* **Phân tích BD-Rate (Bjøntegaard Delta Rate)**
    * Tính % tiết kiệm bitrate so với codec baseline
    * Cho phép chọn codec anchor và codec test
    * Đơn vị: % bitrate saving

* **So sánh hình ảnh (Visual Comparison)**
    * Xem side-by-side spectrogram video gốc và reconstructed
    * Nhận diện suy hao tín hiệu trực quan

* **Dashboard Streamlit tương tác**
    * 5 tab chính: Dữ liệu thô, RD Curves, Encoding Time, BD-Rate, Visual
    * Chọn video để xem báo cáo
    * Tải xuống kết quả CSV và biểu đồ PNG

---

## Yêu cầu hệ thống

- **Python 3.8+**
- **FFmpeg** (để convert MP4 → YUV)
- **Codec Encoders:**
  - HM: `codecs/scm/TAppEncoderStatic`
  - VTM: `codecs/vtm/EncoderAppStatic`

---

## Hướng dẫn cài đặt

⚡ **Quick Start (Ubuntu/Linux)**

```bash
# Kiểm tra FFmpeg đã cài chưa
ffmpeg -version

# Nếu chưa có, cài FFmpeg
sudo apt update
sudo apt install ffmpeg -y

# Kiểm tra lại
ffmpeg -version

# Mở thư mục project trong VS Code
# File → Open Folder → Chọn project → OK

# Mở Terminal: Ctrl + ~

# Tạo virtual environment (LẦN ĐẦU TIÊN)
python3 -m venv .venv

# Kích hoạt virtual environment (LẦN NÀO CŨNG CHẠY)
source .venv/bin/activate
# Nếu thành công, sẽ thấy: (.venv) ở đầu dòng

# Cài dependencies (LẦN ĐẦU TIÊN)
pip install -r requirements.txt

# Kiểm tra đã cài dependencies chưa
pip install -r requirements.txt
# Nếu thấy: Requirement already satisfied = OK ✓

# Cấp quyền cho encoder
chmod +x codecs/scm/TAppEncoderStatic
chmod +x codecs/vtm/EncoderAppStatic

# Đặt video vào thư mục ./input/ rồi chạy
python3 main.py

# Xem dashboard Streamlit
streamlit run app_demo.py
# Mở browser: http://localhost:8501
# Dừng: Ctrl + C
```

---

## Cấu trúc thư mục

```
scc_project/
├── .venv/                     # Virtual environment (tạo tự động)
├── input/                     # Video input (.mp4)
│   ├── Coding_1080p_30fps.mp4
│   └── Web_1080p_30fps.mp4
├── outputs/                   # Output folder
│   ├── yuv_raw/               # Converted YUV files
│   ├── encoded/               # Bitstreams & logs
│   ├── results.csv            # Metrics table
│   └── visualizations/        # RD curves, charts
├── codecs/
│   ├── scm/
│   │   ├── TAppEncoderStatic  # HM encoder
│   │   ├── encoder_hevc_anchor.cfg
│   │   └── encoder_hevc_scc.cfg
│   └── vtm/
│       ├── EncoderAppStatic   # VTM encoder
│       ├── encoder_vvc_anchor.cfg
│       └── encoder_vvc_scc.cfg
├── main.py                    # Entry point (5 giai đoạn)
├── codec_runner.py            # Chạy encoding tasks
├── input_process.py           # Convert MP4 → YUV
├── evaluate.py                # Trích metrics từ log
├── visualize_results.py       # Vẽ charts
├── app_demo.py                # Streamlit dashboard
├── requirements.txt           # Dependencies
└── README.md                  # File này
```

---

## Chạy app & lệnh hữu ích

```bash
# Chạy mã hóa (5 giai đoạn tự động)
python main.py

# Xem dashboard Streamlit
streamlit run app_demo.py

# Kiểm tra tiến độ encoding
echo "Bitstreams: $(ls ./outputs/encoded/*.bin 2>/dev/null | wc -l)/32" && \
echo "Logs: $(ls ./outputs/encoded/*.log 2>/dev/null | wc -l)/32"

# Kiểm tra lỗi
grep -r "Error" ./outputs/encoded/ 2>/dev/null || echo "ZERO ERRORS"

# Xem metrics CSV
head -20 ./outputs/results.csv

# Dọn dẹp (nếu cần chạy lại)
rm -rf ./outputs/encoded/ ./outputs/results.csv ./outputs/visualizations/

# Kiểm tra phiên bản Python
python3 --version

# Thoát virtual environment
deactivate
```

---


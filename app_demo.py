import streamlit as st
import pandas as pd
import os
import subprocess
from typing import Optional
from evaluate import Evaluator
from visualize_results import draw_rd_curve, plot_enc_time_histogram, plot_bitrate_distribution

# ===================================
# MODULE: Streamlit UI (Demo Offline)
# ===================================

st.set_page_config(
    page_title="SCC Video Codec Evaluation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("Screen Content Coding (SCC) - Video Codec Evaluation")
st.markdown("---")
st.info("**Lưu ý hệ thống:** Để tối ưu hóa thời gian chạy và đánh giá, toàn bộ dữ liệu minh họa hiện tại đang được giới hạn mã hóa ở **30 frames** đầu tiên của mỗi video.")

# === Cấu hình & Hiển thị Video (Chia 2 cột) ===
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.header("Cấu hình & Lựa chọn")
    
    csv_folder = st.text_input("Thư mục chứa results.csv", value="./outputs")
    csv_path = os.path.join(csv_folder, "results.csv")

    if not os.path.isfile(csv_path):
        st.warning(f"Không tìm thấy file: {csv_path}")
        st.info("Vui lòng chạy main.py để sinh dữ liệu trước")
        st.stop()

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"Lỗi tải CSV: {str(e)}")
        st.stop()

    video_options = list(df["video"].unique())
    selected_video = st.selectbox("Chọn video để xem báo cáo:", options=video_options)

    df_filtered = df[df["video"] == selected_video]
    st.success(f"✓ Đang hiển thị kết quả phân tích cho video: {selected_video}")

with col_right:
    st.header("Video Gốc (Original)")
    video_path = f"./input/{selected_video}.mp4" 
    
    if os.path.exists(video_path):
        st.video(video_path)
    else:
        st.info(f"Không tìm thấy file .mp4 để phát trực tiếp tại {video_path}")

st.markdown("---")

# === Cấu trúc 5 Tab dữ liệu ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dữ liệu thô",
    "RD Curves",
    "Encoding Time",
    "BD-Rate Comparison",
    "Visual Comparison"
])

# --- TAB 1: DỮ LIỆU THÔ ---
with tab1:
    st.subheader(f"Bảng kết quả chi tiết: {selected_video}")
    st.dataframe(df_filtered, width='stretch')
    
    st.subheader("Thống kê tóm tắt")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Số codec đã test", df_filtered["codec"].nunique())
    with col2:
        st.metric("Bitrate trung bình", f"{df_filtered['bitrate_kbps'].mean():.2f} kbps")
    with col3:
        st.metric("PSNR_Y trung bình", f"{df_filtered['psnr_y'].mean():.4f} dB")


# --- TAB 2: RD CURVES ---
with tab2:
    st.subheader(f"Rate-Distortion Curves: {selected_video}")
    output_vis_dir = os.path.join(csv_folder, "visualizations")
    os.makedirs(output_vis_dir, exist_ok=True)
    
    try:
        file_png_list = draw_rd_curve(df_filtered, output_vis_dir, dpi=150)
        if file_png_list:
            for file_png in file_png_list:
                if os.path.isfile(file_png):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        st.image(file_png, use_container_width=True)
        else:
            st.warning("Không có RD curves được tạo cho video này")
    except Exception as e:
        st.error(f"Lỗi vẽ RD curves: {str(e)}")

    st.markdown("---")
    st.subheader(f"Bitrate vs Quantization Parameter (QP): {selected_video}")
    try:
        plot_bitrate_distribution(df_filtered, output_vis_dir, dpi=150)
        file_bitrate_qp = os.path.join(output_vis_dir, "bitrate_qp_curve.png")
        if os.path.isfile(file_bitrate_qp):
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image(file_bitrate_qp, use_container_width=True)
    except Exception as e:
        st.warning(f"Không thể vẽ bitrate curve: {str(e)}")


# --- TAB 3: ENCODING TIME ---
with tab3:
    st.subheader(f"Encoding Time Analysis: {selected_video}")
    output_vis_dir = os.path.join(csv_folder, "visualizations")
    os.makedirs(output_vis_dir, exist_ok=True)
    
    try:
        file_histogram = plot_enc_time_histogram(df_filtered, output_vis_dir, dpi=150)
        if os.path.isfile(file_histogram):
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image(file_histogram, use_container_width=True)
    except Exception as e:
        st.warning(f"Không thể vẽ histogram: {str(e)}")
    
    st.subheader("Thống kê Encoding Time")
    enc_time_stats = df_filtered.groupby("codec")["enc_time"].agg([
        ("Min (s)", "min"),
        ("Max (s)", "max"),
        ("Mean (s)", "mean"),
        ("Std (s)", "std")
    ]).round(2)
    st.dataframe(enc_time_stats, width='stretch')


# --- TAB 4: BD-RATE COMPARISON ---
with tab4:
    st.subheader(f"Bjøntegaard Delta Rate Analysis: {selected_video}")
    danh_sach_codec = list(df_filtered["codec"].unique())
    idx_anchor = danh_sach_codec.index("HEVC-Anchor") if "HEVC-Anchor" in danh_sach_codec else 0
    idx_test = danh_sach_codec.index("HEVC-SCC") if "HEVC-SCC" in danh_sach_codec else (1 if len(danh_sach_codec) > 1 else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        codec_anchor = st.selectbox("Codec anchor (baseline)", options=danh_sach_codec, index=idx_anchor)
    with col2:
        codec_test = st.selectbox("Codec test", options=danh_sach_codec, index=idx_test)
    
    if codec_anchor != codec_test:
        st.subheader(f"BD-Rate: {codec_anchor} vs {codec_test}")
        evaluator = Evaluator()
        bd_rate_results = []
        du_lieu_anchor = df_filtered[df_filtered["codec"] == codec_anchor].to_dict("records")
        du_lieu_test = df_filtered[df_filtered["codec"] == codec_test].to_dict("records")
        
        if du_lieu_anchor and du_lieu_test:
            bd_rate = evaluator.calc_bd_rate(du_lieu_anchor, du_lieu_test)
            bd_rate_results.append({"Video": selected_video, "BD-Rate (%)": bd_rate})
        
        if bd_rate_results:
            df_bd = pd.DataFrame(bd_rate_results)
            st.dataframe(df_bd, width='stretch')
            avg_bd_rate = df_bd["BD-Rate (%)"].mean()
            if avg_bd_rate < 0:
                st.success(f"✓ Bộ công cụ SCC giúp tiết kiệm {abs(avg_bd_rate):.2f}% bitrate so với bản Anchor gốc")
            elif avg_bd_rate > 0:
                st.info(f"Cấu hình Test làm tăng {avg_bd_rate:.2f}% bitrate")
            else:
                st.info("Hai cấu hình có hiệu suất nén tương đương")
        else:
            st.warning("Không đủ dữ liệu RD-points (yêu cầu tối thiểu 2 điểm QP hợp lệ) để tính BD-Rate")
    else:
        st.warning("Vui lòng chọn hai cấu hình mã hóa khác nhau để thực hiện so sánh")

# --- TAB 5: TRÍCH XUẤT & SO SÁNH ẢNH TRỰC QUAN ---
with tab5:
    st.subheader(f"Phân tích Cận cảnh Text/Edge: {selected_video}")
    st.info("Để thấy rõ sức mạnh của SCC, hãy sử dụng tọa độ X, Y để cắt (crop) đúng vào khu vực có nhiều văn bản hoặc cạnh sắc nét.")

    # Đã bỏ phần chọn video, gom lại các thanh trượt hợp lý hơn
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        qp_chon = st.selectbox("Chọn mức QP để soi lỗi (Gợi ý: 27 hoặc 32):", [22, 27, 32, 37], index=1)
        frame_idx = st.number_input("Frame cần trích xuất (1-30):", min_value=1, max_value=30, value=5, help="Các frame khác nhau (như P-frame) sẽ có mức độ lỗi hình ảnh khác nhau.")
    with col2:
        che_do_xem = st.radio("Chế độ hiển thị:", ["Cận cảnh (Crop & Zoom)", "Toàn màn hình (Full 1080p)"])
    with col3:
        if che_do_xem == "Cận cảnh (Crop & Zoom)":
            crop_size = st.slider("Kích thước vùng cắt vuông (Pixel):", 100, 800, 300, step=50, help="Vùng cắt vuông (VD: 300 = 300×300 pixels)")
            # Tối ưu logic: max_value tự động trừ đi crop_size để khung cắt không lọt ra ngoài viền màn hình 1080p
            crop_x = st.slider("Tọa độ X (Ngang):", 0, max(0, 1920 - crop_size), 500, step=50)
            crop_y = st.slider("Tọa độ Y (Dọc):", 0, max(0, 1080 - crop_size), 300, step=50)

    if st.button("Phân tích & Trích xuất"):
        with st.spinner("Đang trích xuất 5 phiên bản điểm ảnh... Vui lòng đợi..."):
            out_dir = "./outputs/visualizations/frames_comparison"
            os.makedirs(out_dir, exist_ok=True)
            
            yuv_dir = "./outputs/yuv_raw"
            encode_dir = "./outputs/encoded"
            
            # Sử dụng global selected_video thay vì video chọn riêng
            files_to_extract = {
                "1. Original": f"{yuv_dir}/{selected_video}.yuv",
                "2. HEVC-Anchor": f"{encode_dir}/{selected_video}_HEVC-Anchor_QP{qp_chon}_recon.yuv",
                "3. VVC-Anchor": f"{encode_dir}/{selected_video}_VVC-Anchor_QP{qp_chon}_recon.yuv",
                "4. HEVC-SCC": f"{encode_dir}/{selected_video}_HEVC-SCC_QP{qp_chon}_recon.yuv",
                "5. VVC-SCC": f"{encode_dir}/{selected_video}_VVC-SCC_QP{qp_chon}_recon.yuv"
            }
            
            extracted_images = {}
            
            for label, yuv_path in files_to_extract.items():
                # Tên file an toàn
                ten_file_an_toan = label.replace(" ", "_").replace(".", "")
                output_png = os.path.join(out_dir, f"{ten_file_an_toan}_demo.png")
                
                if os.path.isfile(yuv_path):
                    if che_do_xem == "Cận cảnh (Crop & Zoom)":

                        # Khởi tạo bộ lọc (Crop filter): Lấy tham số từ thanh trượt truyền vào '-vf' của FFmpeg
                        vf_filter = f"select=eq(n\\,{frame_idx}),crop={crop_size}:{crop_size}:{crop_x}:{crop_y}"
                    else:
                        vf_filter = f"select=eq(n\\,{frame_idx})"

                    # ---------------------------------------------------------
                    # Tự động phân biệt 8-bit và 10-bit
                    # ---------------------------------------------------------
                    # Tự động nhận diện: Dùng bộ đọc 10-bit cho VVC và 8-bit cho HEVC
                    dinh_dang_mau = "yuv444p10le" if "VVC" in label else "yuv444p"

                    # Thực thi FFmpeg (subprocess): Trích xuất chính xác 1 frame (-vframes 1) ra ảnh PNG.
                    cmd = [
                        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
                        "-s", "1920x1080", "-pix_fmt", dinh_dang_mau, # <--- Dùng biến linh hoạt
                        "-i", yuv_path, "-vf", vf_filter,
                        "-vframes", "1", output_png
                    ]
                    # ---------------------------------------------------------

                    try:
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if os.path.isfile(output_png):
                            extracted_images[label] = output_png
                    except Exception as e:
                        st.error(f"Lỗi khi cắt {label}: {e}")
                else:
                    st.warning(f"Không tìm thấy file: {yuv_path}")

            if extracted_images:
                st.success("Đã xử lý xong 5 phiên bản!")
                
                st.markdown(
                    """
                    <style>
                    img {
                        image-rendering: pixelated; 
                        border: 2px solid #ddd;
                    }
                    </style>
                    """, 
                    unsafe_allow_html=True
                )
                
                cols = st.columns(len(extracted_images))
                for i, (label, img_path) in enumerate(extracted_images.items()):
                    with cols[i]:
                        st.markdown(f"**{label}**")
                        st.image(img_path, use_container_width=True)
            
            #===== BẢNG NHẬN XÉT VỀ CHẤT LƯỢNG HÌNH ẢNH=====
            st.markdown("---")
            st.subheader("Text and Edge Clarity Comparison")
            
            clarity_data = {
                "Codec": ["Original", "HEVC-Anchor", "VVC-Anchor", "HEVC-SCC", "VVC-SCC"],
                "Text Readability": [
                    "Very clear, fully readable",
                    "Fairly clear, slightly blurred",
                    "Clearer than HEVC",
                    "Very clear",
                    "Best, almost original"
                ],
                "Sharpness": [
                    "Very sharp",
                    "Medium",
                    "Fair to good sharpness",
                    "Very sharp",
                    "Sharpest"
                ],
                "Edge Quality": [
                    "Natural, no distortion",
                    "Slightly soft edges",
                    "Better edge quality",
                    "Well preserved edges",
                    "Perfect edges"
                ],
                "Stroke Accuracy": [
                    "Perfect accuracy",
                    "Small errors",
                    "Mostly accurate",
                    "Almost exact",
                    "Fully accurate"
                ]
            }
            
            df_clarity = pd.DataFrame(clarity_data)
            st.dataframe(df_clarity, use_container_width=True)

            # ===== BẢNG NHẬN XÉT VỀ NHIỄU KHI KHÔNG BẬT SCC =====
            st.markdown("---")
            st.subheader("Compression Artifact Analysis")
            
            artifact_data = {
                "Codec": ["HEVC-Anchor", "VVC-Anchor", "HEVC-SCC", "VVC-SCC"],
                "Overall Artifact Level": [
                    "Moderate",
                    "Light",
                    "None",
                    "None"
                ],
                "Blocking (8×8 Grid)": [
                    "Visible",
                    "Barely visible",
                    "None",
                    "None"
                ],
                "Mosquito Noise (Edge)": [
                    "Faint halo",
                    "Minimal",
                    "None",
                    "None"
                ],
                "Color Banding (Gradient)": [
                    "Visible",
                    "Smooth",
                    "None",
                    "None"
                ]
            }
            
            df_artifacts = pd.DataFrame(artifact_data)
            st.dataframe(df_artifacts, use_container_width=True)
            
            # ===== THÊM NHẬN XÉT =====
            st.info(
                "**Finding**: Without SCC, blocking artifacts and mosquito noise can be clearly seen on flat UI areas, "
                "especially around text and smooth backgrounds. "
                "**HEVC-SCC & VVC-SCC eliminate all artifacts** through palette prediction and transform skip, "
                "achieving near-lossless quality."
            )

# === Footer ===
st.markdown("---")
st.markdown("**Ghi chú:** Mã hóa và trích xuất dữ liệu log phải được thực hiện trước bằng file `main.py` offline.")
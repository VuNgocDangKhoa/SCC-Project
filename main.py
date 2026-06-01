import os
import sys
from typing import List, Dict
from input_process import convert_to_yuv, get_video_data
from codec_runner import create_encode_scenario, run_multi_process
from evaluate import Evaluator
from visualize_results import draw_rd_curve, plot_enc_time_histogram, plot_bitrate_distribution

# ===================================
# MODULE: Điều phối hệ thống chính (Main Orchestration)
# ===================================

# Cấu hình toàn cục
CONFIG = {
    "input_videos": [
        "input/Coding_1080p_30fps.mp4",
        "input/Web_1080p_30fps.mp4"
    ],  # Danh sách video MP4 input
    "output_dir": "./outputs",
    "yuv_dir": "./outputs/yuv_raw",
    "encode_dir": "./outputs/encoded",
    "results_csv": "./outputs/results.csv",
    "visualization_dir": "./outputs/visualizations",
    "max_workers": 2,  # Số tiến trình song song (giảm để tránh quá tải RAM)
    "cleanup_after_encode": False  # KHÔNG xóa file sau mã hóa
}

# ===================================
# Giai đoạn 1: Tiền xử lý video (Preprocessing)
# ===================================

def run_preprocessing() -> Dict[str, Dict]:
    # Chuyển MP4 sang YUV 4:4:4 và trích metadata
    
    print("\n" + "=" * 60)
    print("GIAI ĐOẠN 1: TIền xử lý video (Preprocessing)")
    print("=" * 60)
    
    os.makedirs(CONFIG["yuv_dir"], exist_ok=True)
    
    du_lieu_video = {}
    
    for video_file in CONFIG["input_videos"]:
        if not os.path.isfile(video_file):
            print(f"⚠️  File video không tồn tại: {video_file}")
            continue
        
        ten_video = os.path.splitext(os.path.basename(video_file))[0]
        file_yuv_output = os.path.join(CONFIG["yuv_dir"], f"{ten_video}.yuv")
        
        # Chuyển MP4 sang YUV
        if convert_to_yuv(video_file, file_yuv_output):
            # Trích metadata
            metadata = get_video_data(video_file)
            du_lieu_video[ten_video] = {
                "input_mp4": video_file,
                "output_yuv": file_yuv_output,
                "metadata": metadata
            }
            print(f"✓ Tiền xử lý xong: {ten_video}")
        else:
            print(f"✗ Tiền xử lý thất bại: {ten_video}")
    
    return du_lieu_video


# ===================================
# Giai đoạn 2: Tạo kịch bản mã hóa (Encoding Scenarios)
# ===================================

def run_create_scenarios(du_lieu_video: Dict[str, Dict]) -> List[Dict]:
    # Tạo 16 kịch bản cho mỗi video (4 codec x 4 QP)
    
    print("\n" + "=" * 60)
    print("GIAI ĐOẠN 2: Tạo kịch bản mã hóa")
    print("=" * 60)
    
    os.makedirs(CONFIG["encode_dir"], exist_ok=True)
    
    danh_sach_task = []
    
    for ten_video, info in du_lieu_video.items():
        file_yuv = info["output_yuv"]
        metadata = info["metadata"]
        
        scenarios = create_encode_scenario(
            video_name=ten_video,
            input_yuv=file_yuv,
            video_metadata=metadata,
            output_dir=CONFIG["encode_dir"]
        )
        
        danh_sach_task.extend(scenarios)
    
    print(f"✓ Tổng cộng: {len(danh_sach_task)} task mã hóa")
    return danh_sach_task


# ===================================
# Giai đoạn 3: Chạy mã hóa song song (Encoding)----------------------------------------------------
# ===================================

def run_encoding(danh_sach_task: List[Dict]) -> List[bool]:
    # Thực thi mã hóa với multiprocessing
    
    print("\n" + "=" * 60)
    print("GIAI ĐOẠN 3: Chạy mã hóa (Encoding)")
    print("=" * 60)
    
    if not danh_sach_task:
        print("⚠️  Không có task mã hóa")
        return []
    
    ket_qua_list = run_multi_process(
        tasks=danh_sach_task,
        max_workers=CONFIG["max_workers"]
    )
    
    return ket_qua_list


# ===================================
# Giai đoạn 4: Đánh giá kết quả (Evaluation)
# ===================================

def run_evaluation(
    danh_sach_task: List[Dict],
    du_lieu_video: Dict[str, Dict]
) -> None:
    # Trích metric từ log và tính BD-Rate
    
    print("\n" + "=" * 60)
    print("GIAI ĐOẠN 4: Đánh giá kết quả (Evaluation)")
    print("=" * 60)
    
    os.makedirs(os.path.dirname(CONFIG["results_csv"]), exist_ok=True)
    
    evaluator = Evaluator(output_csv_path=CONFIG["results_csv"])
    
    for task in danh_sach_task:
        ten_video = task["video_name"]
        
        # Lấy metadata
        if ten_video not in du_lieu_video:
            print(f"⚠️  Không tìm metadata cho: {ten_video}")
            continue
        
        metadata = du_lieu_video[ten_video]["metadata"]
        total_frames = metadata["total_frames"]
        fps = metadata["fps"]
        
        # Trích metric từ log
        du_lieu_metric = evaluator.read_data_log(task, total_frames, fps)
        
        # Ghi vào CSV
        evaluator.save_result(du_lieu_metric)
    
    print(f"✓ Đã ghi kết quả vào: {CONFIG['results_csv']}")


# ===================================
# Giai đoạn 5: Trực quan hóa dữ liệu (Visualization)
# ===================================

def run_visualization() -> None:
    # Vẽ RD curves, histogram, v.v.
    
    print("\n" + "=" * 60)
    print("GIAI ĐOẠN 5: Trực quan hóa dữ liệu (Visualization)")
    print("=" * 60)
    
    if not os.path.isfile(CONFIG["results_csv"]):
        print(f"⚠️  Không tìm thấy: {CONFIG['results_csv']}")
        return
    
    try:
        import pandas as pd
        df = pd.read_csv(CONFIG["results_csv"])
        
        os.makedirs(CONFIG["visualization_dir"], exist_ok=True)
        
        # Vẽ RD curves
        print("Vẽ RD curves...")
        draw_rd_curve(df, CONFIG["visualization_dir"], dpi=300)
        
        # Vẽ histogram encoding time
        print("Vẽ histogram encoding time...")
        plot_enc_time_histogram(df, CONFIG["visualization_dir"], dpi=300)
        
        # Vẽ bitrate curve
        print("Vẽ bitrate curve...")
        plot_bitrate_distribution(df, CONFIG["visualization_dir"], dpi=300)
        
        print(f"✓ Đã lưu visualizations vào: {CONFIG['visualization_dir']}")
        
    except Exception as e:
        print(f"⚠️  Lỗi visualization: {str(e)}")


# ===================================
# Hàm chính (Main)
# ===================================

def main():
    # Chạy quy trình đầy đủ
    
    print("\n" + "=" * 60)
    print("🎬 SCREEN CONTENT CODING (SCC) EVALUATION")
    print("=" * 60)
    print(f"Config: {CONFIG}")
    
    # Giai đoạn 1: Tiền xử lý
    du_lieu_video = run_preprocessing()
    
    if not du_lieu_video:
        print("⚠️  Không có video nào được xử lý thành công")
        return
    
    # Giai đoạn 2: Tạo kịch bản
    danh_sach_task = run_create_scenarios(du_lieu_video)
    
    # Giai đoạn 3: Chạy mã hóa------------------------------------------------------------------
    ket_qua_encoding = run_encoding(danh_sach_task)
    
    # Giai đoạn 4: Đánh giá
    run_evaluation(danh_sach_task, du_lieu_video)
    
    # Giai đoạn 5: Trực quan hóa
    run_visualization()
    
    print("\n" + "=" * 60)
    print("✓ HOÀN TẤT TOÀN BỘ QUY TRÌNH")
    print("=" * 60)
    print(f"Kết quả CSV: {CONFIG['results_csv']}")
    print(f"Visualizations: {CONFIG['visualization_dir']}")
    print("\nCó thể chạy Streamlit UI bằng:")
    print("  streamlit run app_demo.py")


if __name__ == "__main__":
    main()
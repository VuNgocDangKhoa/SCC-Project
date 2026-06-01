import os
import subprocess
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
import pandas as pd

# ===================================
# MODULE: Trực quan hóa dữ liệu (Visualization)
# ===================================

def draw_rd_curve(
    dataframe: pd.DataFrame,
    output_dir: str,
    dpi: int = 300
) -> List[str]:
    # Vẽ đồ thị Rate-Distortion cho mỗi video
    # Trả về danh sách đường dẫn file PNG
    
    os.makedirs(output_dir, exist_ok=True)
    danh_sach_file_png = []
    
    if dataframe.empty:
        print("Cảnh báo: DataFrame rỗng, không vẽ RD curve")
        return danh_sach_file_png
    
    try:
        # Nhóm theo video
        nhom_theo_video = dataframe.groupby("video")
        
        for ten_video, nhom_data in nhom_theo_video:
            # Nhóm theo codec
            nhom_theo_codec = nhom_data.groupby("codec")
            
            fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
            
            mau_sac = plt.cm.Set1(range(len(nhom_theo_codec)))
            
            for (ten_codec, codec_data), mau in zip(nhom_theo_codec, mau_sac):
                # Sắp xếp theo bitrate
                codec_data = codec_data.sort_values("bitrate_kbps")
                
                bitrate = codec_data["bitrate_kbps"].values
                psnr = codec_data["psnr_y"].values
                
                ax.plot(
                    bitrate,
                    psnr,
                    marker="o",
                    label=ten_codec,
                    color=mau,
                    linewidth=2,
                    markersize=6
                )
            
            ax.set_xlabel("Bitrate (kbps)", fontsize=12)
            ax.set_ylabel("PSNR_Y (dB)", fontsize=12)
            ax.set_title(f"RD Curve: {ten_video}", fontsize=14, fontweight="bold")
            ax.legend(loc="best")
            ax.grid(True, alpha=0.3)
            
            # Lưu file
            ten_file = os.path.join(output_dir, f"rd_curve_{ten_video}.png")
            plt.savefig(ten_file, dpi=dpi, bbox_inches="tight")
            plt.close(fig)
            
            danh_sach_file_png.append(ten_file)
            print(f"✓ Vẽ RD curve: {ten_file}")
        
        return danh_sach_file_png
        
    except Exception as e:
        print(f"Lỗi vẽ RD curve: {str(e)}")
        return danh_sach_file_png


def yuv_to_png(
    input_yuv: str,
    output_png: str,
    width: int,
    height: int,
    frame_index: int = 0,
    pixel_format: str = "yuv444p",
    dpi: int = 300
) -> bool:
    # Trích 1 frame YUV sang PNG
    
    try:
        # Sử dụng FFmpeg để convert YUV -> PNG
        # Skip frame_index * width * height * 1.5 bytes (YUV 4:4:4)
        
        # Tính offset byte
        bytes_per_frame = width * height * 3  # YUV 4:4:4 = 3 bytes/pixel
        seek_offset = frame_index * bytes_per_frame
        
        danh_sach_lenh = [
            "ffmpeg",
            "-f", "rawvideo",
            "-video_size", f"{width}x{height}",
            "-pixel_format", pixel_format,
            "-i", input_yuv,
            "-vf", f"select=eq(n\\,{frame_index})",
            "-vsync", "0",
            output_png
        ]
        
        ket_qua = subprocess.run(
            danh_sach_lenh,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if ket_qua.returncode == 0 and os.path.isfile(output_png):
            print(f"✓ Trích frame YUV -> PNG: {output_png}")
            return True
        else:
            print(f"Lỗi convert YUV->PNG: {ket_qua.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Lỗi: Timeout convert YUV->PNG")
        return False
    except Exception as e:
        print(f"Lỗi yuv_to_png: {str(e)}")
        return False


def compare_crops(
    image_list: List[str],
    crop_region: Tuple[int, int, int, int],
    output_dir: str
) -> List[str]:
    # Crop ảnh từ danh sách và so sánh
    # crop_region: (x, y, width, height)
    
    os.makedirs(output_dir, exist_ok=True)
    danh_sach_crop_png = []
    
    x, y, w, h = crop_region
    
    try:
        for i, image_path in enumerate(image_list):
            if not os.path.isfile(image_path):
                print(f"Cảnh báo: Image không tồn tại: {image_path}")
                continue
            
            # Dùng FFmpeg crop
            ten_file_crop = os.path.join(
                output_dir,
                f"crop_{i}_{os.path.basename(image_path)}"
            )
            
            danh_sach_lenh = [
                "ffmpeg",
                "-i", image_path,
                "-vf", f"crop={w}:{h}:{x}:{y}",
                "-y",
                ten_file_crop
            ]
            
            ket_qua = subprocess.run(
                danh_sach_lenh,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if ket_qua.returncode == 0:
                danh_sach_crop_png.append(ten_file_crop)
                print(f"✓ Crop image: {ten_file_crop}")
            else:
                print(f"Lỗi crop: {ket_qua.stderr}")
        
        return danh_sach_crop_png
        
    except Exception as e:
        print(f"Lỗi compare_crops: {str(e)}")
        return danh_sach_crop_png


def plot_enc_time_histogram(
    dataframe: pd.DataFrame,
    output_dir: str,
    dpi: int = 300
) -> str:
    # Vẽ biểu đồ encoding time theo codec
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
        
        # Nhóm theo codec
        nhom_codec = dataframe.groupby("codec")["enc_time"].mean()
        
        nhom_codec.plot(kind="bar", ax=ax, color="skyblue", edgecolor="navy")
        
        ax.set_xlabel("Codec", fontsize=12)
        ax.set_ylabel("Avg Encoding Time (s)", fontsize=12)
        ax.set_title("Encoding Time Comparison", fontsize=14, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        
        plt.xticks(rotation=45, ha="right")
        
        ten_file = os.path.join(output_dir, "enc_time_histogram.png")
        plt.savefig(ten_file, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        
        print(f"✓ Vẽ histogram: {ten_file}")
        return ten_file
        
    except Exception as e:
        print(f"Lỗi vẽ histogram: {str(e)}")
        return ""


def plot_bitrate_distribution(
    dataframe: pd.DataFrame,
    output_dir: str,
    dpi: int = 300
) -> str:
    # Vẽ phân phối bitrate theo QP
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
        
        # Nhóm theo QP
        nhom_qp = dataframe.groupby("qp")["bitrate_kbps"].mean()
        
        nhom_qp.plot(kind="line", ax=ax, marker="o", color="green", linewidth=2, markersize=8)
        
        ax.set_xlabel("QP", fontsize=12)
        ax.set_ylabel("Avg Bitrate (kbps)", fontsize=12)
        ax.set_title("Bitrate vs QP", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        
        ten_file = os.path.join(output_dir, "bitrate_qp_curve.png")
        plt.savefig(ten_file, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        
        print(f"✓ Vẽ bitrate curve: {ten_file}")
        return ten_file
        
    except Exception as e:
        print(f"Lỗi vẽ bitrate curve: {str(e)}")
        return ""
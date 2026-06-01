import os
import subprocess
import json
import re
from typing import Dict, Optional

# ===================================
# MODULE: Tiền xử lý video (Input Processing)
# ===================================

# ----------------------------------
# Hàm chính: Chuyển MP4 sang YUV 4:4:4
# ----------------------------------

def convert_to_yuv(input_mp4: str, output_yuv: str) -> bool:
    # Kiểm tra file input tồn tại
    if not os.path.isfile(input_mp4):
        print(f"Lỗi: File input không tồn tại: {input_mp4}")
        return False
    
    # Tạo thư mục output nếu chưa có
    thu_muc_output = os.path.dirname(output_yuv)
    if thu_muc_output:
        os.makedirs(thu_muc_output, exist_ok=True)
    
    # Chuẩn bị lệnh FFmpeg
    tieu_chi = "yuv444p"
    danh_sach_lenh = [
        "ffmpeg",
        "-y",
        "-i", input_mp4,
        "-pix_fmt", tieu_chi,
        "-f", "rawvideo",
        output_yuv
    ]
    
    try:
        print(f"Đang chuyển: {input_mp4} -> {output_yuv}")
        ket_qua = subprocess.run(
            danh_sach_lenh,
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if ket_qua.returncode != 0:
            print(f"Lỗi FFmpeg: {ket_qua.stderr}")
            return False
        
        if os.path.isfile(output_yuv):
            kich_thuoc = os.path.getsize(output_yuv)
            print(f"✓ Thành công. Kích thước: {kich_thuoc} bytes")
            return True
        else:
            print("Lỗi: File YUV không được tạo")
            return False
            
    except subprocess.TimeoutExpired:
        print("Lỗi: Timeout (>3600s)")
        return False
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return False


def get_video_data(video_path: str) -> Dict:
    # Trích xuất metadata từ video bằng ffprobe
    
    # Tham số mặc định (fallback)
    du_lieu_mac_dinh = {
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "bit_depth": 8,
        "total_frames": 300
    }
    
    if not os.path.isfile(video_path):
        print(f"Cảnh báo: File không tồn tại, dùng mặc định: {video_path}")
        return du_lieu_mac_dinh
    
    try:
        # Lấy thông tin video từ ffprobe
        danh_sach_lenh = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,bits_per_raw_sample",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        
        ket_qua = subprocess.run(
            danh_sach_lenh,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if ket_qua.returncode != 0:
            print(f"Cảnh báo ffprobe: {ket_qua.stderr}")
            return du_lieu_mac_dinh
        
        du_lieu_json = json.loads(ket_qua.stdout)
        
        # Trích xuất từ JSON
        chieu_rong = du_lieu_json["streams"][0].get("width", 1920)
        chieu_cao = du_lieu_json["streams"][0].get("height", 1080)
        
        # Xử lý FPS (có thể là '30000/1001' hoặc '30/1')
        fps_str = du_lieu_json["streams"][0].get("r_frame_rate", "30/1")
        fps = _tinh_fps_tu_chuoi(fps_str)
        
        # Bit depth (mặc định 8)
        chieu_sau_bit = du_lieu_json["streams"][0].get("bits_per_raw_sample", 8)
        if chieu_sau_bit is None:
            chieu_sau_bit = 8
        
        # Tính tổng frame
        duration = float(du_lieu_json.get("format", {}).get("duration", 10))
        tong_frame = int(duration * fps)
        if tong_frame <= 0:
            tong_frame = 300
        
        du_lieu_trich_xuat = {
            "width": chieu_rong,
            "height": chieu_cao,
            "fps": fps,
            "bit_depth": chieu_sau_bit,
            "total_frames": tong_frame
        }
        
        print(f"✓ Metadata: {chieu_rong}x{chieu_cao} @ {fps}fps, {tong_frame} frames")
        return du_lieu_trich_xuat
        
    except json.JSONDecodeError:
        print("Cảnh báo: Không parse JSON từ ffprobe")
        return du_lieu_mac_dinh
    except subprocess.TimeoutExpired:
        print("Cảnh báo: Timeout ffprobe")
        return du_lieu_mac_dinh
    except Exception as e:
        print(f"Cảnh báo: {str(e)}")
        return du_lieu_mac_dinh


# ===================================
# Hàm bổ trợ nội bộ
# ===================================

def _tinh_fps_tu_chuoi(fps_str: str) -> float:
    # Parse FPS từ chuỗi dạng '30000/1001' hoặc '30/1'
    try:
        if "/" in fps_str:
            tach = fps_str.split("/")
            tu = float(tach[0])
            mau = float(tach[1])
            if mau != 0:
                return tu / mau
        else:
            return float(fps_str)
    except (ValueError, ZeroDivisionError, IndexError):
        pass
    
    return 30.0  # Mặc định 30fps nếu parse thất bại
import os
import re
import csv
from typing import Dict, List, Optional
import pandas as pd
from scipy.interpolate import PchipInterpolator

# ===================================
# MODULE: Đánh giá toán học (Evaluation)
# ===================================

class Evaluator:
    # Lớp xử lý trích xuất metric và tính BD-Rate
    
    def __init__(self, output_csv_path: str = "results.csv"):
        self.output_csv = output_csv_path
        self._khoi_tao_csv()
    
    def _khoi_tao_csv(self) -> None:
        # Tự động xóa file kết quả cũ (nếu có) để tránh lỗi nhân bản dữ liệu
        if os.path.isfile(self.output_csv):
            try:
                os.remove(self.output_csv)
                print(f"🧹 Đã dọn dẹp file cũ: {self.output_csv}")
            except Exception as e:
                print(f"Không thể xóa file cũ: {str(e)}")

        # Tạo file CSV mới toanh và ghi dòng tiêu đề (header)
        with open(self.output_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "video",
                "codec",
                "qp",
                "bitrate_kbps",
                "psnr_y",
                "enc_time"
            ])
    
    def read_data_log(
        self,
        task_dict: Dict,
        total_frames: int,
        fps: float
    ) -> Dict:
        # Trích xuất PSNR_Y, SSIM, EncTime từ log
        
        file_log = task_dict["output_log"]
        file_bitstream = task_dict["output_bin"]
        
        du_lieu = {
            "video": task_dict["video_name"],
            "codec": task_dict["codec_name"],
            "qp": task_dict["qp"],
            "bitrate_kbps": 0.0,
            "psnr_y": 0.0,
            "enc_time": 0.0
        }
        
        # === Tính bitrate từ .bin ===
        if os.path.isfile(file_bitstream):
            kich_thuoc_bytes = os.path.getsize(file_bitstream)
            if kich_thuoc_bytes > 0 and total_frames > 0:
                # Bitrate_kbps = (size_bytes * 8 * fps) / (total_frames * 1000)
                du_lieu["bitrate_kbps"] = (kich_thuoc_bytes * 8 * fps) / (total_frames * 1000)
        
        # === Trích xuất từ log file ===
        if os.path.isfile(file_log):
            try:
                with open(file_log, "r") as f:
                    noi_dung_log = f.read()
            except:
                return du_lieu
            
            # Trích PSNR_Y (dB)
            psnr_y = _truy_xuat_psnr_y(noi_dung_log)
            if psnr_y is not None:
                du_lieu["psnr_y"] = psnr_y         
           
            # Trích EncTime (giây)
            enc_time = _truy_xuat_enc_time(noi_dung_log)
            if enc_time is not None:
                du_lieu["enc_time"] = enc_time
        
        return du_lieu
    
    def save_result(self, du_lieu: Dict) -> None:
        # Ghi kết quả vào CSV (append mode)
        
        try:
            with open(self.output_csv, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    du_lieu["video"],
                    du_lieu["codec"],
                    du_lieu["qp"],
                    round(du_lieu["bitrate_kbps"], 2),
                    round(du_lieu["psnr_y"], 4),
                    round(du_lieu["enc_time"], 2)
                ])
            print(f"✓ Ghi CSV: {du_lieu['video']} {du_lieu['codec']} QP{du_lieu['qp']}")
        except Exception as e:
            print(f"Lỗi ghi CSV: {str(e)}")
    
    @staticmethod
    def calc_bd_rate(
        du_lieu_anchor: List[Dict],
        du_lieu_test: List[Dict],
        metric: str = "psnr_y"
    ) -> float:
        # Tính Bjøntegaard Delta Rate (BD-Rate)
        # Input: danh sách dict với 'bitrate_kbps' và metric (psnr_y/ssim)
        
        if not du_lieu_anchor or not du_lieu_test:
            return 0.0
        
        # Sắp xếp tăng dần theo metric
        rd_anchor = sorted(
            [(d[metric], d["bitrate_kbps"]) for d in du_lieu_anchor if d[metric] > 0],
            key=lambda x: x[0]
        )
        rd_test = sorted(
            [(d[metric], d["bitrate_kbps"]) for d in du_lieu_test if d[metric] > 0],
            key=lambda x: x[0]
        )
        
        if len(rd_anchor) < 2 or len(rd_test) < 2:
            print("Cảnh báo: Không đủ điểm RD để tính BD-Rate")
            return 0.0
        
        try:
            # Tách metric và bitrate
            metric_anchor = [x[0] for x in rd_anchor]
            bitrate_anchor = [x[1] for x in rd_anchor]
            
            metric_test = [x[0] for x in rd_test]
            bitrate_test = [x[1] for x in rd_test]
            
            # Tạo PCHIP interpolator (log scale)
            interp_anchor = PchipInterpolator(
                metric_anchor,
                bitrate_anchor,
                extrapolate=True
            )
            interp_test = PchipInterpolator(
                metric_test,
                bitrate_test,
                extrapolate=True
            )
            
            # Tính BD-Rate (đơn vị: %)
            metric_min = max(min(metric_anchor), min(metric_test))
            metric_max = min(max(metric_anchor), max(metric_test))
            
            if metric_min >= metric_max:
                return 0.0
            
            n_samples = 100
            metric_range = [metric_min + (metric_max - metric_min) * i / (n_samples - 1) for i in range(n_samples)]
            
            bitrate_anchor_interp = [interp_anchor(m) for m in metric_range]
            bitrate_test_interp = [interp_test(m) for m in metric_range]
            
            # BD-Rate = (1/N) * sum((BR_test / BR_anchor - 1) * 100)
            bd_rate = 0.0
            for i in range(len(metric_range)):
                if bitrate_anchor_interp[i] > 0:
                    bd_rate += (bitrate_test_interp[i] / bitrate_anchor_interp[i] - 1) * 100
            
            bd_rate /= len(metric_range)
            
            return round(bd_rate, 2)
            
        except Exception as e:
            print(f"Cảnh báo calc_bd_rate: {str(e)}")
            return 0.0
    
    def load_csv_to_dataframe(self) -> pd.DataFrame:
        # Tải CSV vào pandas DataFrame
        
        if os.path.isfile(self.output_csv):
            try:
                return pd.read_csv(self.output_csv)
            except:
                return pd.DataFrame()
        return pd.DataFrame()


# ===================================
# Hàm bổ trợ nội bộ (Regex parsing)
# ===================================

def _truy_xuat_psnr_y(noi_dung_log: str) -> Optional[float]:
    # Trích PSNR_Y từ log VTM 24.0
    # Định dạng: "a  1036.8846    54.3546  57.6439..."
    
    pattern_list = [
        r'a\s+[0-9\.]+\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+[0-9\.]+',
        r"PSNR_Y\s*=\s*([\d.]+)",
        r"PSNR\s+Y[:\s]+(\d+\.\d+)",
        r"PSNR\s*:\s*(\d+\.\d+)"
    ]
    
    for pattern in pattern_list:
        match = re.search(pattern, noi_dung_log, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None

 
def _truy_xuat_enc_time(noi_dung_log: str) -> Optional[float]:
    # Trích EncTime từ log của cả HM (HEVC) và VTM (VVC)
    
    pattern_list = [
        # Bắt log VTM: "Total Time:     1821.912 sec. [user]     1822.043 sec. [elapsed]"
        r'Total\s+Time:\s+[0-9\.]+\s+sec\.\s+\[user\]\s+([0-9\.]+)\s+sec\.\s+\[elapsed\]',
        # Bắt log HM: " Total Time:      12.345 sec."
        r'Total\s+Time\s*:\s+([0-9\.]+)\s+sec\.',
        # Các trường hợp dự phòng khác
        r"EncTime\s*=\s*([\d.]+)\s*s",
        r"Total\s+Encoding\s+Time[:\s]+(\d+\.\d+)",
        r"Encoding\s+Time[:\s]+(\d+\.\d+)"
    ]
    
    for pattern in pattern_list:
        match = re.search(pattern, noi_dung_log, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None
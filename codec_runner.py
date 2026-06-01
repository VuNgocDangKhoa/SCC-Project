import os
import subprocess
import json
from typing import List, Dict, Optional
from multiprocessing import Pool
from input_process import get_video_data

CODEC_HM_PATH = "codecs/scm/TAppEncoderStatic" 
CODEC_VTM_PATH = "codecs/vtm/EncoderAppStatic"

if os.name == "nt":
    CODEC_HM_PATH += ".exe"
    CODEC_VTM_PATH += ".exe"

def create_encode_scenario(
    video_name: str,
    input_yuv: str,
    video_metadata: Dict,
    output_dir: str
) -> List[Dict]:
    
    os.makedirs(output_dir, exist_ok=True)
    
    chieu_rong = video_metadata["width"]
    chieu_cao = video_metadata["height"]
    fps = video_metadata["fps"]
    # tong_frame = video_metadata["total_frames"]
    tong_frame = 30
    print(f"\n⚠️ THÔNG BÁO: Đang bật chế độ giới hạn! Các video sẽ bị ép nén ở mức {tong_frame} frames.\n")
    
    danh_sach_qp = [22, 27, 32, 37]

    # Chay
    danh_sach_codec = [
        {"name": "HEVC-Anchor", "type": "hm"},
        {"name": "HEVC-SCC", "type": "hm"},
        {"name": "VVC-Anchor", "type": "vtm"},
        {"name": "VVC-SCC", "type": "vtm"}
    ]
    
    danh_sach_scenario = []
    
    for codec_info in danh_sach_codec:
        ten_codec = codec_info["name"]
        loai_codec = codec_info["type"]
        
        for qp in danh_sach_qp:
            id_scenario = f"{video_name}_{ten_codec}_QP{qp}"
            
            output_bin = os.path.join(output_dir, f"{id_scenario}.bin")
            output_recon = os.path.join(output_dir, f"{id_scenario}_recon.yuv")
            output_log = os.path.join(output_dir, f"{id_scenario}.log")
            
            scenario = {
                "id": id_scenario,
                "video_name": video_name,
                "codec_name": ten_codec,
                "codec_type": loai_codec,
                "qp": qp,
                "input_yuv": input_yuv,
                "width": chieu_rong,
                "height": chieu_cao,
                "fps": fps,
                "num_frames": tong_frame,
                "output_bin": output_bin,
                "output_recon": output_recon,
                "output_log": output_log,
                "profile": ten_codec
            }
            danh_sach_scenario.append(scenario)
    
    print(f"✓ Tạo {len(danh_sach_scenario)} kịch bản mã hóa")
    
    return danh_sach_scenario

def run_encode(task: Dict) -> bool:
    id_scenario = task["id"]
    
    print(f"[{id_scenario}] Đang mã hóa...")
    
    if task["codec_type"] == "hm":
        danh_sach_lenh = _tao_lenh_hm(
            input_yuv=task["input_yuv"],
            qp=task["qp"],
            width=task["width"],
            height=task["height"],
            num_frames=task["num_frames"],
            output_bin=task["output_bin"],
            output_recon=task["output_recon"],
            output_log=task["output_log"],
            profile=task["profile"] 
        )
    else:
        danh_sach_lenh = _tao_lenh_vtm(
            input_yuv=task["input_yuv"],
            qp=task["qp"],
            width=task["width"],
            height=task["height"],
            fps=task["fps"],
            num_frames=task["num_frames"],
            output_bin=task["output_bin"],
            output_recon=task["output_recon"],
            output_log=task["output_log"],
            profile=task["profile"]
        )
    
    try:
        # ĐÃ SỬA: Mở file log trước và ghi trực tiếp từ luồng chạy để không rớt 1 byte dữ liệu nào
        with open(task["output_log"], "w", encoding="utf-8") as f_log:
            ket_qua_chay = subprocess.run(
                danh_sach_lenh,
                stdout=f_log,             # Đẩy toàn bộ dữ liệu chính vào file log
                stderr=subprocess.STDOUT, # Gộp toàn bộ cảnh báo/lỗi vào luồng chính (nằm chung trong file)
                text=True,
                timeout=86400,
                shell=False
            )
        
        if ket_qua_chay.returncode != 0:
            print(f"[{id_scenario}] Lỗi mã hóa (returncode={ket_qua_chay.returncode})")
            return False
        
        print(f"[{id_scenario}] Thành công ✓")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"[{id_scenario}] Lỗi: Timeout (>86400s)")
        return False
    except Exception as e:
        print(f"[{id_scenario}] Lỗi: {str(e)}")
        return False

def run_multi_process(tasks: List[Dict], max_workers: int = 4) -> List[bool]:
    print(f"\n=== Bắt đầu multiprocessing ({max_workers} workers) ===")
    
    try:
        with Pool(processes=max_workers) as pool:
            ket_qua_list = pool.map(run_encode, tasks)
        
        so_thanh_cong = sum(1 for r in ket_qua_list if r)
        print(f"✓ Hoàn tất: {so_thanh_cong}/{len(tasks)} thành công")
        
        return ket_qua_list
        
    except Exception as e:
        print(f"Lỗi multiprocessing: {str(e)}")
        return [False] * len(tasks)

def _tao_lenh_hm(
    input_yuv: str,
    qp: int,
    width: int,
    height: int,
    num_frames: int,
    output_bin: str,
    output_recon: str,
    output_log: str,
    profile: str
) -> List[str]:

    preset_map = {
        "HEVC-Anchor": "hevc_anchor",
        "HEVC-SCC": "hevc_scc"
    }
    preset = preset_map.get(profile, "hevc_anchor")

    config_file = f"codecs/scm/encoder_{preset}.cfg"

    danh_sach_lenh = [
        CODEC_HM_PATH,
        "-c", config_file,
        "-i", input_yuv,
        "-wdt", str(width),
        "-hgt", str(height),
        "-fr", "30",
        "-f", str(num_frames),
        "-q", str(qp),
        "-b", output_bin,
        "-o", output_recon
    ]

    return danh_sach_lenh

def _tao_lenh_vtm(
    input_yuv: str,
    qp: int,
    width: int,
    height: int,
    fps: int,
    num_frames: int,
    output_bin: str,
    output_recon: str,
    output_log: str,
    profile: str
) -> List[str]:
    
    preset_map = {
        "VVC-Anchor": "vvc_anchor",
        "VVC-SCC": "vvc_scc"
    }
    preset = preset_map.get(profile, "vvc_scc")

    config_file = f"codecs/vtm/encoder_{preset}.cfg"
    
    danh_sach_lenh = [
        CODEC_VTM_PATH,
        "-c", config_file,
        "-i", input_yuv,
        "--InputBitDepth=8",
        "--InputChromaFormat=444",
        "--Profile=main_10_444",
        f"--SourceWidth={width}",
        f"--SourceHeight={height}",
        f"--FrameRate={fps}",
        f"--FramesToBeEncoded={num_frames}",
        f"--QP={qp}",
        f"--BitstreamFile={output_bin}",
        f"--ReconFile={output_recon}"
    ]
    
    return danh_sach_lenh
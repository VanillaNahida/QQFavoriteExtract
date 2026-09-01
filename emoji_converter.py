# coding=utf-8

import os
import hashlib
import tempfile
from PIL import Image, ImageSequence


def is_apng_file(file_path):
    """
    通过解析 PNG Chunk 极速判断是否为 APNG（带有 acTL 块）
    """
    if not file_path or not os.path.exists(file_path):
        return False
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if header != b'\x89PNG\r\n\x1a\n':
                return False
            while True:
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                length = int.from_bytes(length_bytes, 'big')
                chunk_type = f.read(4)
                if chunk_type == b'acTL':
                    return True
                if chunk_type in (b'IDAT', b'IEND'):
                    break
                # 跳过数据块以及 4 字节 CRC
                f.seek(length + 4, 1)
    except Exception:
        pass
    return False


def get_temp_gif_cache_dir():
    """获取 APNG 预览转码临时缓存目录"""
    temp_dir = os.path.join(tempfile.gettempdir(), "QQFavoriteExtract_GIF_Cache")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def convert_apng_to_gif(apng_path, output_gif_path=None):
    """
    将 APNG 转换为带透明度的标准 GIF 动图。
    如果未指定 output_gif_path，则在系统临时目录生成一个以文件哈希命名的缓存文件。
    返回生成的 gif 路径，若转换失败则返回 None。
    """
    if not os.path.exists(apng_path):
        return None

    if output_gif_path is None:
        try:
            with open(apng_path, 'rb') as f:
                content = f.read()
            file_hash = hashlib.md5(content).hexdigest()
        except Exception:
            file_hash = hashlib.md5(apng_path.encode('utf-8')).hexdigest()
        output_gif_path = os.path.join(get_temp_gif_cache_dir(), f"{file_hash}.gif")

    # 如果临时缓存已存在且非空，直接返回
    if os.path.exists(output_gif_path) and os.path.getsize(output_gif_path) > 0:
        return output_gif_path

    try:
        im = Image.open(apng_path)
        frames = []
        durations = []
        
        # 逐帧提取
        for frame in ImageSequence.Iterator(im):
            # 保持 RGBA 色彩与透明通道
            rgba_frame = frame.convert('RGBA')
            frames.append(rgba_frame)
            # 获取帧间隔时间，默认为 40ms (25fps)
            dur = frame.info.get('duration', 40)
            if dur <= 0:
                dur = 40
            durations.append(dur)

        if not frames:
            return None

        # 确保目标目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_gif_path)), exist_ok=True)

        # 保存为 GIF (disposal=2 防止帧残留叠影)
        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2
        )
        return output_gif_path
    except Exception as e:
        print(f"APNG 转 GIF 失败 ({apng_path}): {e}")
        return None

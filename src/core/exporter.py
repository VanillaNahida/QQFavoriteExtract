# coding=utf-8
"""表情导出逻辑：marketface 内存解密 / APNG 转 GIF / 常规复制。纯函数模块，不依赖 Qt。"""

import os
import shutil
from typing import Callable, List, Optional

from src.core.emoji_scanner import get_actual_extension
from src.core.emoji_converter import is_apng_file, convert_apng_to_gif
from src.core.marketface_handler import recover_marketface_data


def _unique_dest_path(dst_dir, stem, ext):
    """生成不重复的目标文件名（如同名则追加 _1、_2...）"""
    dest_file = os.path.join(dst_dir, f"{stem}.{ext}")
    suffix_number = 1
    while os.path.exists(dest_file):
        dest_file = os.path.join(dst_dir, f"{stem}_{suffix_number}.{ext}")
        suffix_number += 1
    return dest_file


def export_emoji_files(
    file_paths: List[str],
    dst_dir: str,
    folder_key: str,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> int:
    """
    批量导出表情文件。

    :param file_paths: 待导出的源文件完整路径列表
    :param dst_dir: 目标目录（不存在则自动创建）
    :param folder_key: 当前表情分类（用于判断是否走 marketface 解密分支）
    :param log_callback: 每导出一个文件时的日志回调
    :param progress_callback: 进度回调 (已完成数, 总数)
    :param cancel_check: 取消检查，返回 True 时提前终止
    :return: 成功导出的文件数量
    """
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    total_files = len(file_paths)
    copied_count = 0

    for idx, src_file in enumerate(file_paths):
        if cancel_check and cancel_check():
            break
        if not src_file or not os.path.exists(src_file):
            continue

        actual_ext = get_actual_extension(src_file)
        filename_no_ext = os.path.splitext(os.path.basename(src_file))[0]

        # marketface 原文件无扩展名且经过加密，导出前必须在内存中恢复。
        if folder_key == "marketface":
            recovered = recover_marketface_data(src_file)
            if recovered is None:
                if log_callback:
                    log_callback(f"跳过（无法解密或 GIF 校验失败）: {os.path.basename(src_file)}")
                continue
            file_data, _ = recovered
            dest_file = _unique_dest_path(dst_dir, filename_no_ext, "gif")
            with open(dest_file, "wb") as output_file:
                output_file.write(file_data)
            copied_count += 1
            if log_callback:
                log_callback(
                    f"导出(marketface解密) [{copied_count}/{total_files}]: "
                    f"{os.path.basename(src_file)} -> {os.path.basename(dest_file)}"
                )
        # 如果检测到是 APNG 格式的表情，将其转码为通用动图 GIF 导出
        elif actual_ext and actual_ext.lower() == 'png' and is_apng_file(src_file):
            dest_file = os.path.join(dst_dir, f"{filename_no_ext}.gif")
            converted_path = convert_apng_to_gif(src_file, dest_file)
            if converted_path:
                copied_count += 1
                if log_callback:
                    log_callback(
                        f"导出(APNG转GIF) [{copied_count}/{total_files}]: "
                        f"{os.path.basename(src_file)} -> {os.path.basename(dest_file)}"
                    )
            else:
                # 转换失败回退为直接复制 PNG
                dest_file = _unique_dest_path(dst_dir, filename_no_ext, "png")
                shutil.copy2(src_file, dest_file)
                copied_count += 1
                if log_callback:
                    log_callback(
                        f"导出(回退PNG) [{copied_count}/{total_files}]: "
                        f"{os.path.basename(src_file)} -> {os.path.basename(dest_file)}"
                    )
        else:
            filename = os.path.basename(src_file)
            if actual_ext:
                # 如果原文件名没有正确的后缀，就补上
                if not filename.lower().endswith(f".{actual_ext}"):
                    dest_file = os.path.join(dst_dir, f"{filename}.{actual_ext}")
                else:
                    dest_file = os.path.join(dst_dir, filename)
            else:
                dest_file = os.path.join(dst_dir, filename)

            shutil.copy2(src_file, dest_file)
            copied_count += 1
            if log_callback:
                log_callback(
                    f"导出 [{copied_count}/{total_files}]: "
                    f"{os.path.basename(src_file)} -> {os.path.basename(dest_file)}"
                )

        if progress_callback:
            progress_callback(copied_count, total_files)

    return copied_count

# coding=utf-8
# @Author：香草味的纳西妲
# Email：nahida1027@126.com
# Date：2024/12/19

import os
import sys
import shutil
import struct
import mimetypes
import subprocess
import configparser
from tqdm import tqdm
from time import sleep
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def get_userdata_save_path():
    '''获取用户数据目录存储所在位置'''
    # 指定 INI 文件的路径
    ini_file_path = r'C:\Users\Public\Documents\Tencent\QQ\UserDataInfo.ini'
    
    # 创建 ConfigParser 对象
    config = configparser.ConfigParser()
    
    # 读取 INI 文件
    try:
        print("开始使用UTF-8读取QQ配置文件")
        config.read(ini_file_path, encoding='utf-8')
    except UnicodeDecodeError:
        print("UTF-8解码QQ配置文件出错！正在尝试以GBK编码打开文件……")
        config.read(ini_file_path, encoding='gbk')
    except FileNotFoundError:
        print(f"错误: 未找到QQ配置文件“{ini_file_path}”\n可能原因是你未安装QQ或未登录QQ")
        return None
    except configparser.Error as e:
        print(f"无法解析 INI 配置文件 - {e}")
        return None

    # 检查是否存在 [UserDataSet] 节
    if 'UserDataSet' not in config:
        print("错误: INI 文件中不存在 [UserDataSet] 节")
        return None
    
    # 获取 UserDataSavePath 的值
    userdata_save_path = config.get('UserDataSet', 'UserDataSavePath', fallback=None)
    
    if userdata_save_path:
        print(f"查找到用户数据存储目录为: {userdata_save_path}")
    else:
        print("错误: 未找到 UserDataSavePath 的值")
    return userdata_save_path

def get_numeric_subdirectories(parent_dir):
    try:
        # 列出目录下的所有子目录
        subdirs = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]
        # 过滤出以数字命名的子目录
        numeric_subdirs = [name for name in subdirs if name.isdigit()]
        return numeric_subdirs
    except FileNotFoundError:
        print(f"错误: 目录未找到 - {parent_dir}")
        return []
    except Exception as e:
        print(f"错误: {e}")
        return []

def choose_directory(numeric_subdirs):
    if not numeric_subdirs:
        print("没有找到QQ账号数据相关文件夹，可能是你未登录QQ帐号，请尝试登录QQ后重试！")
        return None
    
    print("请选择你的QQ账号数据文件夹：")
    for idx, dir_name in enumerate(numeric_subdirs, start=1):
        print(f"{idx}. {dir_name}")
    
    while True:
        try:
            choice = input("请输入数字选择文件夹: ")
            choice_num = int(choice)
            if 1 <= choice_num <= len(numeric_subdirs):
                selected_dir = numeric_subdirs[choice_num - 1]
                print(f"你选择的文件夹是: {selected_dir}")
                return selected_dir
            else:
                print(f"请输入一个介于 1 和 {len(numeric_subdirs)} 之间的数字。")
        except ValueError:
            print("无效输入，请输入一个数字！")

def select_userdata_dir_main(qq_userdata_dir):
    '''完整文件夹路径'''
    parent_dir = qq_userdata_dir  # 目标目录路径
    numeric_subdirs = get_numeric_subdirectories(parent_dir)
    
    if numeric_subdirs:
        selected_dir = choose_directory(numeric_subdirs)
        if selected_dir:
            selected_dir_path = os.path.join(parent_dir, selected_dir)
            # print(f"完整的文件夹路径: {selected_dir_path}")
            # 返回绝对路径
            return selected_dir_path
    else:
        print("没有找到QQ帐号用户数据文件夹！")

def set_emoction_save_path():
    '''让用户选择要保存表情包的位置'''
    print("请在弹出的窗口中选择要保存表情包的位置")
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askdirectory(
        title="请选择要保存表情包的位置"
    )
    if file_path:
        return file_path
    else:
        print("你取消了选择，程序退出")
        sys.exit()
    

def copy_directory_with_progress(src, dst):
    """复制文件并显示进度条。"""
    try:
        # 检查源目录是否存在
        if not os.path.exists(src):
            print(f"错误: 源目录不存在 - {src}")
            return

        # 如果目标目录不存在，则创建
        if not os.path.exists(dst):
            os.makedirs(dst)
            print(f"创建目标目录: {dst}")

        # 遍历源目录中的所有文件
        total_files = sum(len(files) for _, _, files in os.walk(src))
        print(f"总文件数: {total_files}")

        with tqdm(total=total_files, unit='文件', desc="正在复制文件，进度") as pbar:
            for root, dirs, files in os.walk(src):
                # 计算相对路径
                rel_path = os.path.relpath(root, src)
                # 构建目标路径
                dest_path = os.path.join(dst, rel_path)
                # 如果目标路径不存在，则创建
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)
                    # 复制文件
                    shutil.copy2(src_file, dest_file)
                    # 更新进度条
                    pbar.update(1)

        # print("复制文件完成！正在打开输出文件夹……")
        # try:
        #     subprocess.Popen(['explorer', os.path.abspath(dst)])
        # except Exception as e:
        #     print(f"无法打开资源管理器: {e}")

    except Exception as e:
        print(f"错误: {e}")

# 定义常见的图片格式及其文件头（魔数）
FILE_SIGNATURES = {
    'jpg': (b'\xff\xd8\xff', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1'),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'gif': (b'GIF87a', b'GIF89a'),
    'bmp': (b'BM',),
    'tiff': (b'II*\x00', b'MM\x00*'),
    'webp': (b'RIFF', b'WEBP'),
    'ico': (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'),
    'psd': (b'8BPS',),
    'svg': (b'<?xml', b'<svg'),
    'heic': (b'ftypheic', b'ftypheix', b'ftyphevc', b'ftyphevx'),
    'avif': (b'ftypavif', b'ftypavis'),
}

# 映射文件扩展名到 MIME 类型
MIME_MAPPING = {
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'psd': 'image/vnd.adobe.photoshop',
    'svg': 'image/svg+xml',
    'heic': 'image/heic',
    'avif': 'image/avif',
}

def get_actual_extension(file_path):
    """
    读取文件头并返回实际的文件扩展名
    """
    with open(file_path, 'rb') as f:
        header = f.read(16)  # 读取前16个字节

    for ext, signatures in FILE_SIGNATURES.items():
        for sig in signatures:
            if header.startswith(sig):
                return ext
    return None  # 如果未匹配到任何已知类型

def get_recommended_extension(file_path):
    """
    使用 mimetypes 获取推荐的文件扩展名
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        for ext, mt in MIME_MAPPING.items():
            if mt == mime_type:
                return ext
    return None

def correct_file_extension(file_path):
    """
    纠正文件的扩展名
    """
    actual_ext = get_actual_extension(file_path)
    if not actual_ext:
        print(f"未识别的文件类型: {file_path}")
        return

    recommended_ext = get_recommended_extension(file_path)
    if recommended_ext:
        if actual_ext.lower() != recommended_ext.lower():
            # 去除现有扩展名
            base_name, _ = os.path.splitext(file_path)
            # 添加正确的扩展名
            new_file_path = f"{base_name}.{actual_ext}"
            if os.path.exists(new_file_path):
                print(f"目标文件已存在，跳过: {new_file_path}")
                return
            try:
                os.rename(file_path, new_file_path)
                print(f"已重命名: {file_path} -> {new_file_path}")
            except Exception as e:
                print(f"重命名失败: {file_path}. 错误: {e}")
    else:
        print(f"无法确定推荐扩展名: {file_path}")

def batch_correct_extensions(directory):
    """
    批量纠正指定目录下的文件扩展名
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            # 仅处理图片文件
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                correct_file_extension(file_path)

# 主函数
def main():
    print("QQNT表情包批量导出工具 V1.0")
    # 获取用户QQ指定账号的数据目录
    file_path = Path(select_userdata_dir_main(get_userdata_save_path()))
    # 拼接表情的绝对路径
    emoji_path = file_path / "nt_qq" / "nt_data" / "Emoji" / "personal_emoji" / "Ori"
    print(f"该账号的表情目录绝对路径为：{emoji_path}")
    # 设置并指定保存的目录
    save_path = set_emoction_save_path() + "/提取的表情"
    print(f"选择了：{save_path}")
    sleep(0.5)
    print("开始复制文件……")
    copy_directory_with_progress(emoji_path, save_path)
    print("复制完成！开始重命名文件……")
    sleep(0.5)
    batch_correct_extensions(save_path)
    print("复制文件完成！正在打开输出文件夹……")
    try:
        subprocess.Popen(['explorer', os.path.abspath(save_path)])
    except Exception as e:
        print(f"无法打开资源管理器: {e}")

if __name__ == "__main__":
    main()

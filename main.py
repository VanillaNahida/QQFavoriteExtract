# coding=utf-8
# @Author：香草味的纳西妲
# Email：nahida1027@126.com
# Date：2024/11/27

import os
import sys
import shutil
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
        config.read(ini_file_path, encoding='utf-8')
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
        print("没有找到QQ账号数据相关文件夹")
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
        print("没有找到以数字命名的文件夹。")

def set_emoction_save_path():
    '''让用户选择要保存表情包的位置'''
    print("请在弹出的窗口中选择要保存表情包的位置")
    root = tk.Tk()
    root.withdraw()
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

        print("复制文件完成！正在打开输出文件夹……")
        try:
            subprocess.Popen(['explorer', os.path.abspath(dst)])
        except Exception as e:
            print(f"无法打开资源管理器: {e}")

    except Exception as e:
        print(f"错误: {e}")

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

if __name__ == "__main__":
    main()
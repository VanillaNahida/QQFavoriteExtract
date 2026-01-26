# coding=utf-8
# @Author：香草味的纳西妲
# Email：nahida1027@126.com

import os
import sys
import json
import time
import shutil
import chardet
import requests
import mimetypes
import subprocess
import configparser
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QIcon

# 版本号
VERSION = "1.4.3"

icon = os.path.dirname(os.path.abspath(__file__))


class QQNTEmojiExporter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.savePath = None
        self.default_ini_path = r'C:\Users\Public\Documents\Tencent\QQ\UserDataInfo.ini'
        self.userdata_save_path_cache = None
        self.initUI()

    def initUI(self):
        self.setFixedSize(800, 600)  # 固定窗口大小为 800x600
        self.setWindowTitle(f'QQNT表情包批量提取工具 GUI版 {VERSION} Build：2025/12/10')

        layout = QtWidgets.QVBoxLayout()
        form_layout = QtWidgets.QFormLayout()

        save_path_layout = QtWidgets.QHBoxLayout()
        self.savePathEdit = QtWidgets.QLineEdit()
        self.set_font(self.savePathEdit)
        self.selectDirButton = QtWidgets.QPushButton('浏览文件夹')
        self.set_font(self.selectDirButton)
        self.selectDirButton.clicked.connect(self.selectSavePath)
        save_path_layout.addWidget(self.savePathEdit)
        save_path_layout.addWidget(self.selectDirButton)
        save_path_label = QtWidgets.QLabel('保存路径:')
        save_path_label.setFont(QtGui.QFont("SimHei", 11, QtGui.QFont.Bold))  # 设置字体为黑体，字号11，加粗
        form_layout.addRow(save_path_label, save_path_layout)
        self.userComboBox = QtWidgets.QComboBox()
        self.set_font(self.userComboBox)
        
        # 添加问号帮助按钮
        self.helpButton = QtWidgets.QPushButton("?")
        self.helpButton.setFixedSize(25, 25)
        self.helpButton.setStyleSheet("""
            QPushButton {
                border-radius: 12px;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.helpButton.clicked.connect(self.showHelp)
        
        # 创建水平布局放置下拉框和帮助按钮
        user_layout = QtWidgets.QHBoxLayout()
        user_layout.addWidget(self.userComboBox)
        user_layout.addWidget(self.helpButton)
        
        user_label = QtWidgets.QLabel('选择用户:')
        user_label.setFont(QtGui.QFont("SimHei", 11, QtGui.QFont.Bold))  # 设置字体为黑体，字号11，加粗
        form_layout.addRow(user_label, user_layout)
        layout.addLayout(form_layout)

        self.startButton = QtWidgets.QPushButton('开始导出')
        self.set_font(self.startButton)
        self.startButton.clicked.connect(self.startExport)
        layout.addWidget(self.startButton)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 20px;
            }
        """)
        layout.addWidget(self.progressBar)

        # 添加只读的文本编辑框用于日志输出
        self.logTextEdit = QtWidgets.QTextEdit()
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setStyleSheet("""
            QTextEdit {
                font-family: SimHei;
                font-size: 20px;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.logTextEdit)

        # 添加状态标签
        self.statusLabel = QtWidgets.QLabel('')
        self.set_font(self.statusLabel)
        self.statusLabel.setStyleSheet("QLabel {font-size: 20px;}")
        layout.addWidget(self.statusLabel)

        # 添加反馈按钮
        self.feedbackButton = QtWidgets.QPushButton('👉使用中遇到问题？点我加群反馈！👈')
        self.feedbackButton.setFont(QtGui.QFont("黑体", 14, QtGui.QFont.Bold))
        self.feedbackButton.clicked.connect(lambda: subprocess.Popen(['start', 'https://sharechain.qq.com/50d8e1a4ad264dc2faad9c1ec52b2c14'], shell=True))
        layout.addWidget(self.feedbackButton)

        self.setLayout(layout)
        
        # 程序启动提示
        self.log(f"💬 QQNT表情包批量提取工具 GUI版 {VERSION} Build：2025/12/10")
        self.log("💡Tips: 使用中遇到问题或者反馈bug，可点击程序下方按钮反馈！")
        self.log("💡建议在使用前提前打开要提取表情包的账户，随便选择一个聊天窗口，将表情全部加载出来，这样提取的表情包更齐全。")

        self.populateUserComboBox()

    def set_font(self, widget):
        font = QtGui.QFont("SimHei", 11)  # 使用系统自带的黑体字体
        widget.setFont(font)

    def selectSavePath(self):
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "💬 请选择表情包保存路径", options=options)
        if directory:
            self.savePathEdit.setText(directory)
            self.savePath = directory
            self.log(f"✅ 已将保存路径设置为: {directory}")

    def get_nickname_cache_path(self):
        appdata_path = os.getenv('LOCALAPPDATA')
        if not appdata_path:
            appdata_path = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'LocalLow')
        cache_dir = os.path.join(appdata_path, 'QQ表情包批量提取工具数据目录')
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, '用户昵称缓存.json')

    def load_nickname_cache(self):
        cache_path = self.get_nickname_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_nickname_cache(self, cache_data):
        cache_path = self.get_nickname_cache_path()
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except:
            self.log("❌ 保存昵称缓存失败")

    def get_user_nickname(self, qq_number):
        cache = self.load_nickname_cache()
        now = int(time.time())
        
        # 检查缓存中是否有有效数据
        if qq_number in cache and \
           'username_expire_time' in cache[qq_number] and \
           cache[qq_number]['username_expire_time'] > now:
            return cache[qq_number].get('name', '')
        
        # 从API获取新数据
        try:
            response = requests.get(f"https://uapis.cn/api/v1/social/qq/userinfo?qq={qq_number}")
            data = response.json()
            if response.status_code == 200 and data["nickname"]:
                # 更新缓存
                cache[qq_number] = {
                    'name': data['nickname'],
                    'username_expire_time': now + 3600  # 1小时后过期
                }
                self.save_nickname_cache(cache)
                return data['nickname']
        except:
            pass
        
        return ''

    def populateUserComboBox(self):
        configPath = self.default_ini_path
        if os.path.exists(configPath):
            userdata_save_path = self.get_userdata_save_path(configPath)
            if userdata_save_path:
                numeric_subdirs = self.get_numeric_subdirectories(userdata_save_path)
                if numeric_subdirs:
                    for subdir in numeric_subdirs:
                        nickname = self.get_user_nickname(subdir)
                        if nickname:
                            display_name = f"{nickname}（{subdir}）"
                            self.userComboBox.addItem(display_name, subdir)
                        else:
                            self.userComboBox.addItem(subdir, subdir)
                else:
                    self.log("❌ 未找到任何用户目录")
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "手动选择目录",
                        "未找到任何用户目录，是否要手动选择聊天记录所在目录？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        QtWidgets.QMessageBox.No
                    )
                    
                    if reply == QtWidgets.QMessageBox.Yes:
                        self.log("💬 请手动选择QQ聊天记录所在目录...")
                        options = QtWidgets.QFileDialog.Options()
                        directory = QtWidgets.QFileDialog.getExistingDirectory(
                            self, 
                            "选择QQ聊天记录所在目录（必须是有QQ号文件夹的目录）",
                            options=options
                        )
                        
                        if directory:
                            self.log(f"✅ 已手动选择目录: {directory}")
                            numeric_subdirs = self.get_numeric_subdirectories(directory)
                            if numeric_subdirs:
                                for subdir in numeric_subdirs:
                                    nickname = self.get_user_nickname(subdir)
                                    if nickname:
                                        display_name = f"{nickname}（{subdir}）"
                                        self.userComboBox.addItem(display_name, subdir)
                                    else:
                                        self.userComboBox.addItem(subdir, subdir)
                            else:
                                self.log("❌ 手动选择的目录中也未找到任何用户目录")
                        else:
                            self.log("💬 用户取消了手动选择目录")
                            sys.exit()
            else:
                self.log("❌ 读取配置文件失败")
        else:
            self.log("❌ 未找到配置文件")
            reply = QtWidgets.QMessageBox.question(
                self,
                "手动选择配置文件",
                "未找到配置文件，是否要手动选择配置文件？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                self.log("💬 请手动选择配置文件...")
                configPath, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, 
                    "💬 选择配置文件", 
                    "", 
                    "INI Files (*.ini);;All Files (*)"
                )
                
                if configPath:
                    self.log(f"✅ 已手动选择配置文件: {configPath}")
                    userdata_save_path = self.get_userdata_save_path(configPath)
                    if userdata_save_path:
                        numeric_subdirs = self.get_numeric_subdirectories(userdata_save_path)
                        if numeric_subdirs:
                            for subdir in numeric_subdirs:
                                nickname = self.get_user_nickname(subdir)
                                if nickname:
                                    display_name = f"{nickname}（{subdir}）"
                                    self.userComboBox.addItem(display_name, subdir)
                                else:
                                    self.userComboBox.addItem(subdir, subdir)
                        else:
                            self.log("❌ 未找到任何用户目录")
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "手动选择目录",
                                "未找到任何用户目录，是否要手动选择聊天记录所在目录？",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                QtWidgets.QMessageBox.No
                            )
                            
                            if reply == QtWidgets.QMessageBox.Yes:
                                self.log("💬 请手动选择QQ聊天记录所在目录...")
                                options = QtWidgets.QFileDialog.Options()
                                directory = QtWidgets.QFileDialog.getExistingDirectory(
                                    self, 
                                    "选择QQ聊天记录所在目录（必须是有QQ号文件夹的目录）",
                                    options=options
                                )
                                
                                if directory:
                                    self.log(f"✅ 已手动选择目录: {directory}")
                                    numeric_subdirs = self.get_numeric_subdirectories(directory)
                                    if numeric_subdirs:
                                        for subdir in numeric_subdirs:
                                            nickname = self.get_user_nickname(subdir)
                                            if nickname:
                                                display_name = f"{nickname}（{subdir}）"
                                                self.userComboBox.addItem(display_name, subdir)
                                            else:
                                                self.userComboBox.addItem(subdir, subdir)
                                    else:
                                        self.log("❌ 手动选择的目录中也未找到任何用户目录")
                                else:
                                    self.log("💬 用户取消了手动选择目录")
                                    sys.exit()
                            else:
                                sys.exit()
                    else:
                        self.log("❌ 读取配置文件失败")
                else:
                    self.log("💬 用户取消了手动选择配置文件")
                    sys.exit()

    def sanitize_filename(self, name):
        # Windows文件名非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip()

    def get_display_name(self, qq_number):
        cache = self.load_nickname_cache()
        if qq_number in cache and 'name' in cache[qq_number]:
            return f"{cache[qq_number]['name']}（{qq_number}）"
        return qq_number

    def startExport(self):
        selected_data = self.userComboBox.currentData()  # 获取存储的原始QQ号
        if not selected_data:
            self.log("❌ 你还没有选择用户呢，请先选择一个用户！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择用户呢，请先选择一个用户！', QtWidgets.QMessageBox.Ok)
            return

        if not self.savePath:
            self.log("❌ 你还没有选择保存路径呢，请先选择保存路径！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择保存路径呢，请先选择保存路径！', QtWidgets.QMessageBox.Ok)
            return

        configPath = self.default_ini_path
        if not os.path.exists(configPath):
            self.log("❌ 未找到配置文件，请手动选择！")
            configPath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "💬 选择配置文件", "", "INI Files (*.ini);;All Files (*)")
            if not configPath:
                self.log("💬 请先选择配置文件！")
                return

        self.log("💬 正在读取配置文件……")
        userdata_save_path = self.get_userdata_save_path(configPath)
        if userdata_save_path:
            file_path = Path(os.path.join(userdata_save_path, selected_data))
            emoji_path = file_path / "nt_qq" / "nt_data" / "Emoji" / "personal_emoji" / "Ori"
            display_name = self.get_display_name(selected_data)
            safe_name = self.sanitize_filename(display_name)
            output_dir = f"{self.savePath}/{safe_name}_提取的表情"
            
            self.log(f"✅ 复制表情包文件到: {output_dir}")
            self.copy_directory_with_progress(str(emoji_path), output_dir)
            self.log("✅ 复制完成！开始重命名文件")
            self.batch_correct_extensions(output_dir)
            self.log("✅ 完成！正在打开输出文件夹……")
            try:
                subprocess.Popen(['explorer', os.path.abspath(output_dir)])
                QtWidgets.QMessageBox.information(self, '完成', '提取成功！', QtWidgets.QMessageBox.Ok)


            except Exception as e:
                self.log(f"❌ 无法打开资源管理器: {e}")
        else:
            self.log("❌ 读取配置文件失败")

    def get_userdata_save_path(self, ini_file_path):
        # 优先使用缓存的目录
        if self.userdata_save_path_cache:
            return self.userdata_save_path_cache
            
        config = configparser.ConfigParser()
        target_string = '[UserDataSet]'
        userdata_save_path = None
        
        try:
            self.log(f"💬 开始检测QQ配置文件编码类型……")
            encode = self.read_file_with_correct_encoding(ini_file_path, target_string)
            if encode:
                config.read(ini_file_path, encoding=encode)
                if 'UserDataSet' in config:
                    userdata_save_path = config.get('UserDataSet', 'UserDataSavePath', fallback=None)
        except UnicodeDecodeError:
            self.log(f"❌ 解码QQ配置文件出错！")
        except FileNotFoundError:
            self.log(f"❌ 配置文件不存在！")
        except configparser.Error as e:
            self.log(f"❌ 配置文件解析错误: {e}")
        
        # 如果没有获取到用户数据保存路径，询问用户是否手动选择
        if not userdata_save_path:
            self.log("❌ 无法从配置文件中获取聊天记录路径！")
            reply = QtWidgets.QMessageBox.question(
                self,
                "手动选择目录",
                "无法从配置文件中获取聊天记录路径，是否要手动选择聊天记录所在目录？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                self.log("💬 请手动选择QQ聊天记录所在目录...")
                options = QtWidgets.QFileDialog.Options()
                directory = QtWidgets.QFileDialog.getExistingDirectory(
                    self, 
                    "选择QQ聊天记录所在目录（必须是有QQ号文件夹的目录）",
                    options=options
                )
                
                if directory:
                    self.log(f"✅ 已手动选择目录: {directory}")
                    # 保存到缓存
                    self.userdata_save_path_cache = directory
                    return directory
                else:
                    self.log("💬 用户取消了手动选择目录")
                    sys.exit()
        
        # 保存到缓存
        self.userdata_save_path_cache = userdata_save_path
        return userdata_save_path

    def get_numeric_subdirectories(self, parent_dir):
        try:
            subdirs = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]
            numeric_subdirs = [name for name in subdirs if name.isdigit()]
            return numeric_subdirs
        except FileNotFoundError:
            return []
        except Exception as e:
            self.log(f"❌ 获取子目录时出错: {e}")
            return []

    def copy_directory_with_progress(self, src, dst):
        try:
            if not os.path.exists(src):
                self.log(f"❌ 源目录不存在: {src}")
                return

            if not os.path.exists(dst):
                os.makedirs(dst)

            total_files = sum(len(files) for _, _, files in os.walk(src))
            self.progressBar.setMaximum(total_files)

            file_count = 0
            for root, dirs, files in os.walk(src):
                rel_path = os.path.relpath(root, src)
                dest_path = os.path.join(dst, rel_path)
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)
                    shutil.copy2(src_file, dest_file)
                    file_count += 1
                    self.progressBar.setValue(file_count)
                    self.log(f"复制文件: {src_file} 到 {dest_file}")
                    QtCore.QCoreApplication.processEvents()  # 更新进度条显示
            self.log("✅ 复制目录完成")
        except Exception as e:
            self.log(f"❌ 复制目录时出错: {e}")

    def log(self, message):
        self.logTextEdit.append(message)
        # 同时更新状态标签
        self.statusLabel.setText(message)
        # 自动滚动到底部
        scrollbar = self.logTextEdit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.logTextEdit.ensureCursorVisible()

    def is_content_valid(self, content, min_chinese=1):
        # 验证内容是否包含至少一个中文字符（避免误判为拉丁编码）
        chinese_chars = sum('\u4e000' <= char <= '\u9fff' for char in content)
        return chinese_chars >= min_chinese

    def read_file_with_correct_encoding(self, file_path, target_string):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            self.log(f"❌ 文件读取失败: {e}")
            return False

        # ------------------------- 编码检测优化 -------------------------
        # 1. 优先尝试中文相关编码（GB18030覆盖GBK，兼容性更好）
        priority_encodings = ['gb18030', 'utf-8', 'utf-16', 'ascii']
        
        # 2. 使用cchardet检测（比chardet更快更准）
        try:
            detected = chardet.detect(data)
            if detected['encoding']:
                # 如果检测到的是非中文编码且置信度低，将其后置
                if detected['confidence'] < 0.7 or detected['encoding'].lower() not in ['gb18030', 'gbk', 'utf-8']:
                    priority_encodings.append(detected['encoding'])
                else:
                    priority_encodings.insert(0, detected['encoding'])  # 高置信度中文编码前置
        except:
            pass
        
        # 3. 补充其他可能编码并去重
        encodings = priority_encodings + [
            'gbk', 'big5', 'utf-16-le', 'utf-16-be', 'shift_jis',
            'iso-8859-1', 'latin-1', 'cp936', 'cp950', 'utf-7'
        ]
        seen = set()
        ordered_encodings = []
        for enc in encodings:
            enc_lower = enc.lower()
            if enc_lower not in seen:
                seen.add(enc_lower)
                ordered_encodings.append(enc)
        
        # ------------------------- 解码验证优化 -------------------------
        for enc in ordered_encodings:
            try:
                content = data.decode(enc, errors='strict')  # 严格模式避免静默错误
            except (UnicodeDecodeError, LookupError):
                continue
            # 改进验证：检查目标字符串且无异常字符（如乱码）
            if target_string in content and self.is_content_valid(content):
                self.log(f"✅ 成功解码！ | 检测到的编码类型为: {enc.ljust(12)}")
                return enc.ljust(12)
        self.log("❌ 解码失败，未找到匹配编码。请联系开发者或者查看常见问题指南")
        return None

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

    def get_actual_extension(self, file_path):
        with open(file_path, 'rb') as f:
            header = f.read(16)

        for ext, signatures in self.FILE_SIGNATURES.items():
            for sig in signatures:
                if header.startswith(sig):
                    return ext
        return None

    def get_recommended_extension(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            for ext, mt in self.MIME_MAPPING.items():
                if mt == mime_type:
                    return ext
        return None

    def correct_file_extension(self, file_path):
        actual_ext = self.get_actual_extension(file_path)
        if not actual_ext:
            return

        recommended_ext = self.get_recommended_extension(file_path)
        if recommended_ext:
            if actual_ext.lower() != recommended_ext.lower():
                base_name, _ = os.path.splitext(file_path)
                new_file_path = f"{base_name}.{actual_ext}"
                if os.path.exists(new_file_path):
                    return
                try:
                    os.rename(file_path, new_file_path)
                    self.log(f"💬 重命名文件: {file_path} 为 {new_file_path}")
                except Exception as e:
                    self.log(f"❌ 重命名文件时出错: {e}")
                    return

    def showHelp(self):
        """显示帮助信息"""
        help_text = "使用帮助：\n\n" \
                    "1. 使用时请确保已登录过QQ并加载过全部表情包\n" \
                    "2. 提取的时候会自动创建以账号昵称和QQ号开头的文件夹\n" \
                    "3. 程序会自动获取对应QQ号的昵称，如果没有获取到昵称，保存文件夹将只显示QQ号\n" \
                    "4. 选择一个账号后，点击'开始导出'按钮即可提取该账号的表情包\n" \
                    "5. 导出的表情包比账号内实际的表情包要多属正常现象，因为QQ会缓存一些表情包\n\n" \
                    "  注意：如果没有找到任何用户，请确保QQ已经在本地登录过。并确保路径正确\n" \
                    "  可以尝试在设置内修改QQ的聊天记录路径或者手动指定聊天数据文件夹的所在位置"
        
        QtWidgets.QMessageBox.information(
            self,
            "使用帮助",
            help_text,
            QtWidgets.QMessageBox.Ok
        )
    
    def batch_correct_extensions(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type and mime_type.startswith('image/'):
                    self.correct_file_extension(file_path)

def main():
    app = QtWidgets.QApplication(sys.argv)
    ex = QQNTEmojiExporter()
    app.setWindowIcon(QIcon(os.path.join(icon, "icon.ico")))
    ex.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

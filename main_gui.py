# coding=utf-8

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

from emoji_converter import is_apng_file, convert_apng_to_gif
from emoji_scanner import get_actual_extension, scan_emoji_folder
from marketface_handler import recover_marketface_data

icon = os.path.dirname(os.path.abspath(__file__))


class QQNTEmojiExporter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.savePath = None
        self.default_ini_path = r'C:\Users\Public\Documents\Tencent\QQ\UserDataInfo.ini'
        self.userdata_save_path_cache = None
        
        # 懒加载相关的状态变量
        self.emoji_file_paths = []     # 存放当前分类下所有待加载表情包文件的完整路径
        self.loaded_emoji_count = 0    # 已渲染到列表中的表情包数量
        self.batch_size = 100          # 每次懒加载的表情包数量
        self.is_loading = False        # 是否正在加载，防止重复触发
        self.active_movies = {}        # 存放当前正在播放动图的项目 {item: (label, movie)}
        
        self.initUI()

    def initUI(self):
        self.resize(1400, 650)  # 初始化窗口大小
        self.setMinimumSize(1000, 500)  # 限制最小大小，防止缩太小
        self.setWindowTitle('QQNT表情包批量提取工具')

        # 主水平布局：左侧控制区，右侧预览区
        main_layout = QtWidgets.QHBoxLayout()

        # 左侧控制面板布局
        left_layout = QtWidgets.QVBoxLayout()
        form_layout = QtWidgets.QFormLayout()

        # 数据读取路径选择
        read_path_layout = QtWidgets.QHBoxLayout()
        self.readPathEdit = QtWidgets.QLineEdit()
        self.readPathEdit.setReadOnly(True)
        self.set_font(self.readPathEdit)
        self.selectReadDirButton = QtWidgets.QPushButton('选择数据目录')
        self.set_font(self.selectReadDirButton)
        self.selectReadDirButton.clicked.connect(self.selectReadPath)
        read_path_layout.addWidget(self.readPathEdit)
        read_path_layout.addWidget(self.selectReadDirButton)
        read_path_label = QtWidgets.QLabel('数据路径:')
        read_path_label.setFont(QtGui.QFont("SimHei", 11, QtGui.QFont.Bold))
        form_layout.addRow(read_path_label, read_path_layout)

        # 保存路径选择
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

        # 选择分类下拉框
        self.emojiFolderComboBox = QtWidgets.QComboBox()
        self.set_font(self.emojiFolderComboBox)
        emoji_folder_label = QtWidgets.QLabel('选择分类:')
        emoji_folder_label.setFont(QtGui.QFont("SimHei", 11, QtGui.QFont.Bold))
        form_layout.addRow(emoji_folder_label, self.emojiFolderComboBox)

        left_layout.addLayout(form_layout)

        # 扫描表情按钮
        self.scanButton = QtWidgets.QPushButton('扫描表情包预览')
        self.set_font(self.scanButton)
        self.scanButton.clicked.connect(self.scanEmojis)
        left_layout.addWidget(self.scanButton)

        self.exportSelectedButton = QtWidgets.QPushButton('导出选中表情')
        self.set_font(self.exportSelectedButton)
        self.exportSelectedButton.clicked.connect(self.exportSelected)
        left_layout.addWidget(self.exportSelectedButton)

        self.exportAllButton = QtWidgets.QPushButton('导出全部表情')
        self.set_font(self.exportAllButton)
        self.exportAllButton.clicked.connect(self.exportAll)
        left_layout.addWidget(self.exportAllButton)

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
        left_layout.addWidget(self.progressBar)

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
        left_layout.addWidget(self.logTextEdit)

        # 添加状态标签
        self.statusLabel = QtWidgets.QLabel('')
        self.set_font(self.statusLabel)
        self.statusLabel.setStyleSheet("QLabel {font-size: 20px;}")
        left_layout.addWidget(self.statusLabel)

        # 底部致谢声明
        self.thanksLabel = QtWidgets.QLabel()
        self.thanksLabel.setFont(QtGui.QFont("SimHei", 9))
        self.thanksLabel.setText('致谢：本工具基于原作者 <a href="https://github.com/VanillaNahida" style="color: #05B8CC; text-decoration: underline;">VanillaNahida</a> 的项目二次开发')
        self.thanksLabel.setOpenExternalLinks(True)  # 允许用户点击超链接直接在浏览器中打开 GitHub 地址
        self.thanksLabel.setStyleSheet("color: #666666; padding-top: 5px;")
        left_layout.addWidget(self.thanksLabel)

        # 右侧表情包预览区域
        right_layout = QtWidgets.QVBoxLayout()

        # 顶部标题和选择控制栏
        preview_header_layout = QtWidgets.QHBoxLayout()
        preview_label = QtWidgets.QLabel('表情包预览区')
        preview_label.setFont(QtGui.QFont("SimHei", 12, QtGui.QFont.Bold))
        preview_header_layout.addWidget(preview_label)
        
        preview_header_layout.addStretch()
        
        self.selectAllButton = QtWidgets.QPushButton('全选已加载')
        self.set_font(self.selectAllButton)
        self.selectAllButton.setFixedSize(110, 28)
        self.selectAllButton.clicked.connect(self.selectAllLoaded)
        preview_header_layout.addWidget(self.selectAllButton)
        
        self.clearSelectionButton = QtWidgets.QPushButton('清空选择')
        self.set_font(self.clearSelectionButton)
        self.clearSelectionButton.setFixedSize(100, 28)
        self.clearSelectionButton.clicked.connect(self.clearSelection)
        preview_header_layout.addWidget(self.clearSelectionButton)
        
        right_layout.addLayout(preview_header_layout)

        self.previewListWidget = QtWidgets.QListWidget()
        self.previewListWidget.setViewMode(QtWidgets.QListView.IconMode)
        self.previewListWidget.setResizeMode(QtWidgets.QListView.Adjust)
        self.previewListWidget.setIconSize(QtCore.QSize(100, 100))
        self.previewListWidget.setGridSize(QtCore.QSize(120, 120))
        self.previewListWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)  # 允许多选
        self.previewListWidget.setDragEnabled(False)
        self.previewListWidget.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 2px solid grey;
                border-radius: 5px;
            }
            QListWidget::item {
                border: 1px solid transparent;
                margin: 5px;
            }
            QListWidget::item:selected {
                background-color: #a6e2e6;
                border: 1px solid #05B8CC;
                border-radius: 5px;
            }
        """)
        right_layout.addWidget(self.previewListWidget)

        # 最右侧单个表情大图预览区域
        detail_layout = QtWidgets.QVBoxLayout()
        detail_title = QtWidgets.QLabel('表情详细预览')
        detail_title.setFont(QtGui.QFont("SimHei", 12, QtGui.QFont.Bold))
        detail_layout.addWidget(detail_title)

        # 大图显示 Label
        self.detailPreviewLabel = QtWidgets.QLabel()
        self.detailPreviewLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.detailPreviewLabel.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)
        self.detailPreviewLabel.setFixedSize(250, 250)
        self.detailPreviewLabel.setStyleSheet("background-color: #f9f9f9; border: 1px solid #cccccc; border-radius: 5px;")
        detail_layout.addWidget(self.detailPreviewLabel, alignment=QtCore.Qt.AlignCenter)

        # 详细属性展示 Label
        self.detailInfoLabel = QtWidgets.QLabel("未选中表情")
        self.detailInfoLabel.setFont(QtGui.QFont("SimHei", 10))
        self.detailInfoLabel.setWordWrap(True)
        self.detailInfoLabel.setFixedWidth(250)  # 固定宽度，防止超长路径把布局撑开
        self.detailInfoLabel.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.detailInfoLabel.setStyleSheet("color: #333333; padding-top: 10px;")
        detail_layout.addWidget(self.detailInfoLabel)
        
        detail_layout.addStretch()

        # 把左侧和中间布局分别包装到 QWidget 中，配合 QSplitter 实现拖拽控制宽度
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(260)
        left_widget.setMaximumWidth(600)

        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)

        detail_widget = QtWidgets.QWidget()
        detail_widget.setLayout(detail_layout)
        detail_widget.setFixedWidth(280)

        # 创建分割器，将左侧控制区和中间预览区放进去
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([380, 740])
        
        # 设置拉伸因子：拉伸窗口时，左侧不改变大小，只有中间预览区改变大小
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # 把分割器和右侧详细预览添加到主水平布局
        main_layout.addWidget(splitter, stretch=1)
        main_layout.addWidget(detail_widget)

        self.setLayout(main_layout)
        self.detail_movie = None
        self.detail_movie_buffer = None
        
        # 连接用户变化槽函数以动态更新表情分类下拉框
        self.userComboBox.currentIndexChanged.connect(self.onUserChanged)
        
        # 监听预览列表滚动条实现滚动懒加载
        self.previewListWidget.verticalScrollBar().valueChanged.connect(self.onScrollBarMoved)
        
        # 监听选中项变化实现选中播放动图
        self.previewListWidget.itemSelectionChanged.connect(self.onItemSelectionChanged)

        # 程序启动提示
        self.log("💬 QQNT表情包批量提取工具启动成功")
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

    def selectReadPath(self):
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "选择QQ聊天记录所在目录（即包含QQ号数字文件夹的 Tencent Files 目录）",
            options=options
        )
        if directory:
            self.log(f"✅ 已选择数据目录: {directory}")
            self.userdata_save_path_cache = directory
            self.populateUserComboBox()
        else:
            self.log("💬 取消选择数据目录")

    def populateUserComboBox(self):
        # 优先使用界面/缓存里设定的路径，若没有，则通过配置文件/智能扫描定位聊天数据文件夹
        userdata_save_path = self.userdata_save_path_cache
        if not userdata_save_path:
            userdata_save_path = self.get_userdata_save_path(self.default_ini_path)

        if userdata_save_path and os.path.exists(userdata_save_path):
            self.readPathEdit.setText(userdata_save_path)
            self.userdata_save_path_cache = userdata_save_path
            
            numeric_subdirs = self.get_numeric_subdirectories(userdata_save_path)
            # 清空以免重复添加
            self.userComboBox.clear()
            if numeric_subdirs:
                for subdir in numeric_subdirs:
                    nickname = self.get_user_nickname(subdir)
                    if nickname:
                        display_name = f"{nickname}（{subdir}）"
                        self.userComboBox.addItem(display_name, subdir)
                    else:
                        self.userComboBox.addItem(subdir, subdir)
                self.log(f"✅ 成功加载了 {len(numeric_subdirs)} 个QQ用户文件夹")
            else:
                self.log(f"⚠️ 在目录 [{userdata_save_path}] 下未找到任何QQ号数据文件夹（纯数字命名且含有nt_qq）")
        else:
            # 找不到任何路径
            self.readPathEdit.setText("")
            self.userComboBox.clear()
            self.log("⚠️ 未能自动定位到QQ聊天数据文件夹，请手动点击按钮 [选择数据目录] 指定！")
        
        # 填充完毕后，手动触发一次分类下拉框填充
        self.onUserChanged()

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

    def onUserChanged(self):
        selected_data = self.userComboBox.currentData()
        self.emojiFolderComboBox.clear()
        if not selected_data:
            return

        # 优先使用已缓存的用户聊天数据目录
        userdata_save_path = self.userdata_save_path_cache
        if not userdata_save_path:
            configPath = self.default_ini_path
            userdata_save_path = self.get_userdata_save_path(configPath)

        if not userdata_save_path:
            return

        file_path = Path(os.path.join(userdata_save_path, selected_data))
        emoji_root = file_path / "nt_qq" / "nt_data" / "Emoji"

        if emoji_root.exists() and emoji_root.is_dir():
            try:
                subdirs = [d for d in os.listdir(emoji_root) if os.path.isdir(emoji_root / d)]
                # 一些常见的分类翻译映射，更加直观友好
                name_mapping = {
                    'personal_emoji': '个人表情 (personal_emoji)',
                    'emoji-recv': '接收到表情[谨慎加载,内含巨量表情] (emoji-recv)',
                    'marketface': '商店表情 (marketface)',
                    'BaseEmojiSyastems': '系统表情[已支持APNG动图转GIF导出] (BaseEmojiSyastems)',
                    'emoji-related': '候选表情[打字时系统推荐] (emoji-related)'
                }
                for subdir in subdirs:
                    display_name = name_mapping.get(subdir, f"{subdir} (其他分类)")
                    self.emojiFolderComboBox.addItem(display_name, subdir)
            except Exception as e:
                self.log(f"⚠️ 读取表情分类出错: {e}")
        else:
            self.log(f"⚠️ 未找到该账户的 Emoji 目录: {emoji_root}")

    def onScrollBarMoved(self, value):
        # 如果滚动条滑动到了底部 90% 的位置，且还有图片没加载，并且当前没在加载中，就继续加载下一批
        scroll_bar = self.previewListWidget.verticalScrollBar()
        max_val = scroll_bar.maximum()
        if max_val > 0 and value > max_val * 0.9:
            if self.loaded_emoji_count < len(self.emoji_file_paths) and not self.is_loading:
                self.loadMoreEmojis()

    def is_marketface_selected(self):
        return self.emojiFolderComboBox.currentData() == "marketface"

    def get_preview_data(self, file_path_str):
        """返回 (图片字节, 实际格式, 帧数)，marketface 全程在内存中解密。"""
        if self.is_marketface_selected():
            recovered = recover_marketface_data(file_path_str)
            if recovered is None:
                return None, None, 0
            file_data, frame_count = recovered
            return file_data, "gif", frame_count

        actual_ext = get_actual_extension(file_path_str)
        if not actual_ext:
            return None, None, 0

        try:
            with open(file_path_str, "rb") as file:
                file_data = file.read()
            frame_count = 1
            reader = QtGui.QImageReader()
            buffer = QtCore.QBuffer()
            buffer.setData(QtCore.QByteArray(file_data))
            buffer.open(QtCore.QIODevice.ReadOnly)
            reader.setDevice(buffer)
            if reader.supportsAnimation():
                frame_count = max(reader.imageCount(), 1)
            buffer.close()
            return file_data, actual_ext, frame_count
        except Exception:
            return None, None, 0

    def loadMoreEmojis(self):
        if self.is_loading:
            return
        self.is_loading = True
        
        start_idx = self.loaded_emoji_count
        end_idx = min(start_idx + self.batch_size, len(self.emoji_file_paths))
        
        if start_idx >= end_idx:
            self.is_loading = False
            return

        self.log(f"💬 正在加载预览图 {start_idx + 1} - {end_idx} ...")
        self.progressBar.setMaximum(len(self.emoji_file_paths))
        
        batch_paths = self.emoji_file_paths[start_idx:end_idx]
        
        for idx, file_path_str in enumerate(batch_paths):
            current_count = start_idx + idx + 1
            self.progressBar.setValue(current_count)
            file_data, actual_ext, frame_count = self.get_preview_data(file_path_str)
            if file_data and actual_ext:
                try:
                    pixmap = QtGui.QPixmap()
                    if pixmap.loadFromData(file_data):
                        is_animated = frame_count > 1
                        badge_text = "GIF" if actual_ext.lower() == "gif" else actual_ext.upper()

                        # 核心内存优化：立即缩放，释放原始大图在内存中的占用
                        scaled_pixmap = pixmap.scaled(
                            100, 100,
                            QtCore.Qt.KeepAspectRatio,
                            QtCore.Qt.SmoothTransformation
                        )

                        # 如果是动图，在缩略图上画角标
                        if is_animated:
                            painter = QtGui.QPainter(scaled_pixmap)
                            rect = QtCore.QRect(55, 84, 45, 16)
                            painter.fillRect(rect, QtGui.QColor(0, 0, 0, 160))
                            painter.setPen(QtGui.QColor(255, 255, 255))
                            font = QtGui.QFont("Arial", 8, QtGui.QFont.Bold)
                            painter.setFont(font)
                            painter.drawText(rect, QtCore.Qt.AlignCenter, badge_text)
                            painter.end()

                        icon = QtGui.QIcon(scaled_pixmap)
                        item = QtWidgets.QListWidgetItem(icon, "")
                        item.setData(QtCore.Qt.UserRole, file_path_str)
                        item.setData(QtCore.Qt.UserRole + 1, is_animated)
                        item.setData(QtCore.Qt.UserRole + 2, icon)
                        item.setToolTip(
                            f"格式: {actual_ext.upper()}\n"
                            f"路径: {os.path.basename(file_path_str)}"
                        )
                        self.previewListWidget.addItem(item)
                except Exception:
                    # 避免控制台大量打印，只记录在日志中
                    pass
            
            # 每隔 10 张图，或者到尾部时刷新一次界面以防止界面冻结
            if idx % 10 == 0 or idx == len(batch_paths) - 1:
                QtCore.QCoreApplication.processEvents()
                
        self.loaded_emoji_count = end_idx
        self.log(f"✅ 已加载表情预览：{self.loaded_emoji_count}/{len(self.emoji_file_paths)}")
        self.is_loading = False

    def onItemSelectionChanged(self):
        """当选中项发生变化时，在最右侧的详细预览面板中播放动图或展示大图，并展示属性信息"""
        current_item = self.previewListWidget.currentItem()
        
        # 1. 停止之前的 movie
        if hasattr(self, 'detail_movie') and self.detail_movie:
            try:
                self.detail_movie.stop()
            except Exception:
                pass
            self.detail_movie = None
        if hasattr(self, 'detail_movie_buffer') and self.detail_movie_buffer:
            try:
                self.detail_movie_buffer.close()
            except Exception:
                pass
            self.detail_movie_buffer = None

        self.detailPreviewLabel.clear()
        
        # 2. 检查是否有焦点项被选中
        if not current_item or not current_item.isSelected():
            self.detailInfoLabel.setText("未选中表情")
            return
            
        file_path_str = current_item.data(QtCore.Qt.UserRole)
        is_animated = current_item.data(QtCore.Qt.UserRole + 1)
        
        if not file_path_str or not os.path.exists(file_path_str):
            self.detailInfoLabel.setText("文件不存在")
            return
            
        # 3. 读取并展示文件属性信息
        try:
            file_size_kb = os.path.getsize(file_path_str) / 1024
            actual_ext = get_actual_extension(file_path_str)
            file_name = os.path.basename(file_path_str)
            
            if self.is_marketface_selected():
                format_display = "GIF（已解密）"
            else:
                format_display = actual_ext.upper() if actual_ext else '未知'
                if actual_ext and actual_ext.lower() == 'png' and is_apng_file(file_path_str):
                    format_display = "APNG (动态图片)"
                
            info_text = f"<b>文件名:</b><br/>{file_name}<br/><br/>"
            info_text += f"<b>格式:</b> {format_display}<br/>"
            info_text += f"<b>大小:</b> {file_size_kb:.2f} KB<br/><br/>"
            info_text += f"<b>保存路径:</b><br/>{file_path_str}"
            self.detailInfoLabel.setText(info_text)
        except Exception as e:
            self.detailInfoLabel.setText(f"获取信息失败: {e}")
            
        # 4. 展示预览图（marketface 使用内存解密数据，不创建临时文件）
        try:
            if self.is_marketface_selected():
                file_data, actual_ext, frame_count = self.get_preview_data(file_path_str)
                if not file_data:
                    self.detailPreviewLabel.setText("marketface 解密失败")
                    return

                buffer = QtCore.QBuffer(self)
                buffer.setData(QtCore.QByteArray(file_data))
                buffer.open(QtCore.QIODevice.ReadOnly)
                self.detail_movie_buffer = buffer
                self.detail_movie = QtGui.QMovie(self)
                self.detail_movie.setDevice(buffer)
                self.detail_movie.setCacheMode(QtGui.QMovie.CacheAll)
                size_buffer = QtCore.QBuffer(self)
                size_buffer.setData(QtCore.QByteArray(file_data))
                size_buffer.open(QtCore.QIODevice.ReadOnly)
                reader = QtGui.QImageReader(size_buffer)
                orig_size = reader.size()
                size_buffer.close()
                if orig_size.isValid():
                    scaled_size = orig_size.scaled(240, 240, QtCore.Qt.KeepAspectRatio)
                    self.detail_movie.setScaledSize(scaled_size)
                else:
                    self.detail_movie.setScaledSize(QtCore.QSize(240, 240))
                self.detailPreviewLabel.setMovie(self.detail_movie)
                self.detail_movie.start()
            elif is_animated:
                play_path = file_path_str
                # 如果是 APNG 格式，转换为临时 GIF 进行流畅播放
                if is_apng_file(file_path_str):
                    converted_gif = convert_apng_to_gif(file_path_str)
                    if converted_gif:
                        play_path = converted_gif

                self.detail_movie = QtGui.QMovie(play_path)
                reader = QtGui.QImageReader(play_path)
                orig_size = reader.size()
                if orig_size.isValid():
                    scaled_size = orig_size.scaled(240, 240, QtCore.Qt.KeepAspectRatio)
                    self.detail_movie.setScaledSize(scaled_size)
                else:
                    self.detail_movie.setScaledSize(QtCore.QSize(240, 240))

                self.detailPreviewLabel.setMovie(self.detail_movie)
                self.detail_movie.start()
            else:
                pixmap = QtGui.QPixmap()
                if pixmap.load(file_path_str):
                    scaled_pixmap = pixmap.scaled(
                        240, 240, QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.SmoothTransformation
                    )
                    self.detailPreviewLabel.setPixmap(scaled_pixmap)
                else:
                    self.detailPreviewLabel.setText("图片加载失败")
        except Exception as e:
            self.detailPreviewLabel.setText(f"预览失败: {e}")

    def scanEmojis(self):
        selected_data = self.userComboBox.currentData()
        if not selected_data:
            self.log("❌ 你还没有选择用户呢，请先选择一个用户！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择用户呢，请先选择一个用户！', QtWidgets.QMessageBox.Ok)
            return

        selected_folder = self.emojiFolderComboBox.currentData()
        if not selected_folder:
            self.log("❌ 你还没有选择表情分类呢，请先选择一个分类！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择表情分类呢，请先选择一个分类！', QtWidgets.QMessageBox.Ok)
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
        if not userdata_save_path:
            self.log("❌ 读取配置文件失败")
            return

        file_path = Path(os.path.join(userdata_save_path, selected_data))
        emoji_path = file_path / "nt_qq" / "nt_data" / "Emoji" / selected_folder
        
        if not emoji_path.exists():
            self.log(f"❌ 未找到该用户的表情分类目录: {emoji_path}")
            QtWidgets.QMessageBox.warning(self, '警告', '未找到该分类的本地目录，可能是该账号在本地未生成对应分类，或者路径不正确。', QtWidgets.QMessageBox.Ok)
            return

        # 停止所有正在播放的动图并清空活动字典
        for item_id, (item, label, movie) in list(self.active_movies.items()):
            try:
                movie.stop()
            except Exception:
                pass
        self.active_movies.clear()

        # 停止右侧预览大图的播放并清空
        if hasattr(self, 'detail_movie') and self.detail_movie:
            try:
                self.detail_movie.stop()
            except Exception:
                pass
            self.detail_movie = None
        if hasattr(self, 'detail_movie_buffer') and self.detail_movie_buffer:
            try:
                self.detail_movie_buffer.close()
            except Exception:
                pass
            self.detail_movie_buffer = None
        self.detailPreviewLabel.clear()
        self.detailInfoLabel.setText("未选中表情")

        self.previewListWidget.clear()
        self.emoji_file_paths = []
        self.loaded_emoji_count = 0
        self.log(f"💬 开始智能扫描分类 [{selected_folder}] 表情文件...")

        self.progressBar.setMaximum(100)
        self.progressBar.setValue(30)
        QtCore.QCoreApplication.processEvents()

        # 调用模块化扫描器
        self.emoji_file_paths = scan_emoji_folder(emoji_path, selected_folder)
        total_valid = len(self.emoji_file_paths)

        if total_valid == 0:
            self.log("❌ 未筛选出任何有效的表情包图片")
            self.progressBar.setValue(100)
            return

        self.log(f"✅ 扫描并筛选完毕，共发现 {total_valid} 个有效表情图片。")
        self.progressBar.setValue(100)
        
        # 触发第一批的懒加载
        self.loadMoreEmojis()

    def copy_files_with_progress(self, file_paths, dst_dir):
        try:
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)

            total_files = len(file_paths)
            self.progressBar.setMaximum(total_files)
            self.progressBar.setValue(0)

            copied_count = 0
            for idx, src_file in enumerate(file_paths):
                if not src_file or not os.path.exists(src_file):
                    continue
                
                # marketface 原文件无扩展名且经过加密，导出前必须在内存中恢复。
                selected_folder = self.emojiFolderComboBox.currentData()
                actual_ext = get_actual_extension(src_file)
                filename_no_ext = os.path.splitext(os.path.basename(src_file))[0]

                if selected_folder == "marketface":
                    recovered = recover_marketface_data(src_file)
                    if recovered is None:
                        self.log(f"跳过（无法解密或 GIF 校验失败）: {os.path.basename(src_file)}")
                        continue
                    file_data, _ = recovered
                    dest_file = os.path.join(dst_dir, f"{filename_no_ext}.gif")
                    if os.path.exists(dest_file):
                        stem = filename_no_ext
                        suffix_number = 1
                        while os.path.exists(dest_file):
                            dest_file = os.path.join(
                                dst_dir, f"{stem}_{suffix_number}.gif"
                            )
                            suffix_number += 1
                    with open(dest_file, "wb") as output_file:
                        output_file.write(file_data)
                    copied_count += 1
                    self.progressBar.setValue(copied_count)
                    self.log(
                        f"导出(marketface解密) [{copied_count}/{total_files}]: "
                        f"{os.path.basename(src_file)} -> {os.path.basename(dest_file)}"
                    )
                # 如果检测到是 APNG 格式的表情，将其转码为通用动图 GIF 导出
                elif actual_ext and actual_ext.lower() == 'png' and is_apng_file(src_file):
                    dest_file = os.path.join(dst_dir, f"{filename_no_ext}.gif")
                    converted_path = convert_apng_to_gif(src_file, dest_file)
                    if converted_path:
                        copied_count += 1
                        self.progressBar.setValue(copied_count)
                        self.log(f"导出(APNG转GIF) [{copied_count}/{total_files}]: {os.path.basename(src_file)} -> {os.path.basename(dest_file)}")
                    else:
                        # 转换失败回退为直接复制 PNG
                        dest_file = os.path.join(dst_dir, f"{filename_no_ext}.png")
                        shutil.copy2(src_file, dest_file)
                        copied_count += 1
                        self.progressBar.setValue(copied_count)
                        self.log(f"导出(回退PNG) [{copied_count}/{total_files}]: {os.path.basename(src_file)} -> {os.path.basename(dest_file)}")
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
                    self.progressBar.setValue(copied_count)
                    self.log(f"导出 [{copied_count}/{total_files}]: {os.path.basename(src_file)} -> {os.path.basename(dest_file)}")
                
                if idx % 5 == 0 or idx == total_files - 1:
                    QtCore.QCoreApplication.processEvents()
            self.log(f"✅ 成功导出 {copied_count} 个表情文件！")
        except Exception as e:
            self.log(f"❌ 导出文件时出错: {e}")

    def selectAllLoaded(self):
        for i in range(self.previewListWidget.count()):
            item = self.previewListWidget.item(i)
            item.setSelected(True)
        self.log(f"✅ 已全选当前加载的 {self.previewListWidget.count()} 个表情")

    def clearSelection(self):
        self.previewListWidget.clearSelection()
        self.log("✅ 已清空当前的选择")

    def quickScanPaths(self, config_path, selected_data, selected_folder):
        self.log("💬 正在快速获取文件路径...")
        userdata_save_path = self.get_userdata_save_path(config_path)
        if not userdata_save_path:
            return
        file_path = Path(os.path.join(userdata_save_path, selected_data))
        emoji_path = file_path / "nt_qq" / "nt_data" / "Emoji" / selected_folder
        if emoji_path.exists():
            self.emoji_file_paths = scan_emoji_folder(emoji_path, selected_folder)

    def exportSelected(self):
        selected_data = self.userComboBox.currentData()
        if not selected_data:
            self.log("❌ 你还没有选择用户呢，请先选择一个用户！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择用户呢，请先选择一个用户！', QtWidgets.QMessageBox.Ok)
            return

        if not self.savePath:
            self.log("❌ 你还没有选择保存路径呢，请先选择保存路径！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择保存路径呢，请先选择保存路径！', QtWidgets.QMessageBox.Ok)
            return

        selected_folder = self.emojiFolderComboBox.currentData()
        if not selected_folder:
            self.log("❌ 你还没有选择表情分类呢，请先选择一个分类！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择表情分类呢，请先选择一个分类！', QtWidgets.QMessageBox.Ok)
            return

        selected_items = self.previewListWidget.selectedItems()
        if len(selected_items) == 0:
            self.log("❌ 您尚未选择任何表情！请先在右侧预览区选中表情后再导出。")
            QtWidgets.QMessageBox.warning(self, '提示', '请先在右侧预览区选中表情后再导出！', QtWidgets.QMessageBox.Ok)
            return

        configPath = self.default_ini_path
        if not os.path.exists(configPath):
            self.log("❌ 未找到配置文件，请手动选择！")
            configPath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "💬 选择配置文件", "", "INI Files (*.ini);;All Files (*)")
            if not configPath:
                self.log("💬 请先选择配置文件！")
                return

        reply = QtWidgets.QMessageBox.question(
            self,
            "确认导出选中",
            f"确定导出当前选中的 {len(selected_items)} 个表情？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        if reply == QtWidgets.QMessageBox.No:
            self.log("💬 用户取消了导出操作")
            return

        userdata_save_path = self.get_userdata_save_path(configPath)
        if userdata_save_path:
            display_name = self.get_display_name(selected_data)
            safe_name = self.sanitize_filename(display_name)
            output_dir = f"{self.savePath}/{safe_name}_{selected_folder}_提取的选中表情"
            self.log(f"✅ 正在复制选中的表情文件到: {output_dir}")
            selected_paths = [item.data(QtCore.Qt.UserRole) for item in selected_items if item.data(QtCore.Qt.UserRole)]
            self.copy_files_with_progress(selected_paths, output_dir)
            self.log("✅ 完成！正在打开输出文件夹……")
            try:
                subprocess.Popen(['explorer', os.path.abspath(output_dir)])
                QtWidgets.QMessageBox.information(self, '完成', '选中表情提取成功！', QtWidgets.QMessageBox.Ok)
            except Exception as e:
                self.log(f"❌ 无法打开资源管理器: {e}")
        else:
            self.log("❌ 读取配置文件失败")

    def exportAll(self):
        selected_data = self.userComboBox.currentData()
        if not selected_data:
            self.log("❌ 你还没有选择用户呢，请先选择一个用户！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择用户呢，请先选择一个用户！', QtWidgets.QMessageBox.Ok)
            return

        if not self.savePath:
            self.log("❌ 你还没有选择保存路径呢，请先选择保存路径！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择保存路径呢，请先选择保存路径！', QtWidgets.QMessageBox.Ok)
            return

        selected_folder = self.emojiFolderComboBox.currentData()
        if not selected_folder:
            self.log("❌ 你还没有选择表情分类呢，请先选择一个分类！")
            QtWidgets.QMessageBox.information(self, '提示', '你还没有选择表情分类呢，请先选择一个分类！', QtWidgets.QMessageBox.Ok)
            return

        configPath = self.default_ini_path
        if not os.path.exists(configPath):
            self.log("❌ 未找到配置文件，请手动选择！")
            configPath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "💬 选择配置文件", "", "INI Files (*.ini);;All Files (*)")
            if not configPath:
                self.log("💬 请先选择配置文件！")
                return

        # 如果尚未进行扫描路径获取，在此执行一次静默/快速获取
        if len(self.emoji_file_paths) == 0:
            self.quickScanPaths(configPath, selected_data, selected_folder)

        if len(self.emoji_file_paths) == 0:
            self.log("❌ 该表情分类下未发现任何有效的图片文件，无法导出！")
            QtWidgets.QMessageBox.warning(self, '提示', '该分类下未发现任何有效的表情图片文件！', QtWidgets.QMessageBox.Ok)
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "确认导出全部",
            f"当前不管界面是否完全加载，将直接导出扫描到的该分类下所有 {len(self.emoji_file_paths)} 个表情？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        if reply == QtWidgets.QMessageBox.No:
            self.log("💬 用户取消了导出操作")
            return

        userdata_save_path = self.get_userdata_save_path(configPath)
        if userdata_save_path:
            display_name = self.get_display_name(selected_data)
            safe_name = self.sanitize_filename(display_name)
            output_dir = f"{self.savePath}/{safe_name}_{selected_folder}_提取的全部表情"
            self.log(f"✅ 正在复制所有表情文件到: {output_dir}")
            self.copy_files_with_progress(self.emoji_file_paths, output_dir)
            self.log("✅ 完成！正在打开输出文件夹……")
            try:
                subprocess.Popen(['explorer', os.path.abspath(output_dir)])
                QtWidgets.QMessageBox.information(self, '完成', '全部提取成功！', QtWidgets.QMessageBox.Ok)
            except Exception as e:
                self.log(f"❌ 无法打开资源管理器: {e}")
        else:
            self.log("❌ 读取配置文件失败")

    def detect_tencent_files_path(self):
        """自动检测系统文档中是否存在 Tencent Files 目录，且在该目录下含有符合QQ结构的数字子文件夹"""
        def get_windows_documents_path():
            try:
                import winreg
                sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    personal_path, _ = winreg.QueryValueEx(key, "Personal")
                    return personal_path
            except Exception:
                return None

        candidate_roots = []
        
        # 1. 注册表读取的“我的文档”绝对路径
        doc_path = get_windows_documents_path()
        if doc_path:
            candidate_roots.append(Path(doc_path))
            
        # 2. 常见的系统文件夹与用户主目录
        user_home = Path(os.path.expanduser('~'))
        candidate_roots.append(user_home / "Documents")
        candidate_roots.append(user_home)
        candidate_roots.append(Path(r"C:\Users\Public\Documents"))

        # 去重并确保目录真实存在
        seen = set()
        unique_roots = []
        for root in candidate_roots:
            try:
                resolved = root.resolve()
                if resolved not in seen and resolved.exists():
                    seen.add(resolved)
                    unique_roots.append(resolved)
            except Exception:
                continue

        # 遍历根目录寻找含有 {QQ号}/nt_qq 的 Tencent Files 文件夹
        for root in unique_roots:
            tencent_dir = root / "Tencent Files"
            if tencent_dir.exists() and tencent_dir.is_dir():
                try:
                    for sub in os.listdir(tencent_dir):
                        sub_path = tencent_dir / sub
                        if sub.isdigit() and sub_path.is_dir():
                            # 若纯数字QQ号子目录下包含 nt_qq 目录，认定这就是我们要找的聊天记录根目录
                            if (sub_path / "nt_qq").exists():
                                return str(tencent_dir)
                except Exception:
                    continue
        return None

    def get_userdata_save_path(self, ini_file_path):
        # 优先使用缓存的目录
        if self.userdata_save_path_cache:
            return self.userdata_save_path_cache
            
        config = configparser.ConfigParser()
        target_string = '[UserDataSet]'
        userdata_save_path = None
        
        # 1. 尝试从配置文件中读取路径
        if os.path.exists(ini_file_path):
            try:
                self.log(f"💬 开始检测QQ配置文件编码类型……")
                encode = self.read_file_with_correct_encoding(ini_file_path, target_string)
                if encode:
                    config.read(ini_file_path, encoding=encode)
                    if 'UserDataSet' in config:
                        userdata_save_path = config.get('UserDataSet', 'UserDataSavePath', fallback=None)
            except Exception as e:
                self.log(f"⚠️ 解析配置文件出错: {e}")

        # 2. 如果配置文件读取失败或路径不存在，启动系统目录智能扫描
        if not userdata_save_path or not os.path.exists(userdata_save_path):
            self.log("💬 正在尝试在系统常见目录中智能检索 Tencent Files 文件夹...")
            detected_path = self.detect_tencent_files_path()
            if detected_path:
                self.log(f"✅ 智能定位到 Tencent Files 目录: {detected_path}")
                userdata_save_path = detected_path
        
        if userdata_save_path and os.path.exists(userdata_save_path):
            self.userdata_save_path_cache = userdata_save_path
            return userdata_save_path
            
        return None

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
        self.log("❌ 解码失败，未找到匹配编码。")
        return None

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

    def get_recommended_extension(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            for ext, mt in self.MIME_MAPPING.items():
                if mt == mime_type:
                    return ext
        return None

    def correct_file_extension(self, file_path):
        actual_ext = get_actual_extension(file_path)
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

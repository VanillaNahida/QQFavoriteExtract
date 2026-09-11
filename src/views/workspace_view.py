# coding=utf-8
"""表情提取工作台：配置 → 扫描 → 预览 → 提取 一条清晰路径。"""

import os
import subprocess
from functools import partial
from html import escape as _html_escape

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QStackedWidget, QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget, ComboBox,
                            FluentIcon as FIF, InfoBar, LineEdit, MessageBox,
                            PopupTeachingTip, PrimaryPushButton, PushButton,
                            StrongBodyLabel, SubtitleLabel, TeachingTipTailPosition,
                            TransparentPushButton)

from src.app.signal_bus import signalBus
from src.core.app_settings import cfg
from src.core.config import (get_category_display_name, get_category_path,
                             get_emoji_root, get_numeric_subdirectories,
                             get_pic_root, get_userdata_save_path)
from src.core.emoji_converter import is_apng_file
from src.core.emoji_scanner import get_actual_extension
from src.core.user_service import UserService
from src.core.workers import (DetailLoaderWorker, ExportWorker, PreviewLoaderWorker,
                              ScanWorker, SortWorker, start_worker)
from src.utils.helpers import format_exc, get_asset_path, sanitize_filename, to_display_path
from src.widgets.emoji_detail_widget import DetailPanelCard, EmojiDetailWidget
from src.widgets.emoji_preview_widget import EmojiEntry, EmojiPreviewWidget
from src.widgets.image_viewer import LargeImageViewer
from src.widgets.rotating_chevron_button import RotatingChevronButton
from src.widgets.state_tool_tip import StateToolTipManager


_ZERO_WIDTH_SPACE = '\u200b'


def _escape_wbr(text, chunk=16):
    """HTML 转义，并给过长的连续无空白文本插入零宽空格（U+200B）作为断行点。

    Qt QLabel 的 RichText 不把 <wbr> 当作断行点，需改用零宽空格让
    QTextDocument 在任意位置断行。先按原始文本分块再逐块转义，
    避免转义实体（如 &amp;）被切断。
    """
    if len(text) <= chunk:
        return _html_escape(text)
    parts = [text[i:i + chunk] for i in range(0, len(text), chunk)]
    return _ZERO_WIDTH_SPACE.join(_html_escape(p) for p in parts)


class WorkspaceView(QWidget):
    """表情提取工作台页面。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('workspaceView')

        # 状态
        self.save_path = ''
        self.userdata_save_path_cache = ''
        self.generation = 0
        self.is_loading = False
        self.current_folder_key = ''
        self._workers = {}          # kind -> WorkerBase
        self._live_threads = {}     # worker -> QThread（start_worker 自动维护）
        self._exporting = False
        self._config_anim = None    # 配置面板展开/收起动画
        self._detail_anim = None    # 详情面板展开/收起动画
        self._drawer_width_cache = 0
        self._image_viewer = None   # 大图预览窗口（单例复用，关闭仅隐藏）
        self._help_tip = None       # 当前显示的问号教学气泡（复用单例，点击重开）

        # 服务
        self.user_service = UserService(self)
        self.tooltip = StateToolTipManager(self)

        self._init_ui()
        self._connect_signals()
        self._init_state()
        self.populate_users()

    # ---------- UI ----------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ---- 顶部标题行 ----
        header = QHBoxLayout()
        title = SubtitleLabel('表情提取工作台')
        header.addWidget(title)
        header.addStretch()
        self.config_collapse_button = RotatingChevronButton(self)
        self.config_collapse_button.setToolTip('收起配置面板')
        self.config_collapse_button.clicked.connect(self._toggle_config)
        header.addWidget(self.config_collapse_button)
        root.addLayout(header)

        # ---- 配置卡（可折叠）----
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)
        config_layout.setContentsMargins(20, 16, 20, 16)
        config_layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        # 表单标签：必须用带主题的 BodyLabel，原生 QLabel 不随深浅色切换变色
        read_path_label = BodyLabel('数据路径', self)
        save_path_label = BodyLabel('保存路径', self)
        user_label = BodyLabel('选择用户', self)
        category_label = BodyLabel('选择分类', self)

        self.read_path_edit = LineEdit(self)
        self.read_path_edit.setReadOnly(True)
        self.read_path_edit.setPlaceholderText('QQ 聊天数据目录（Tencent Files）')
        self.select_read_button = PushButton('选择数据目录', self)
        read_row = QHBoxLayout()
        read_row.setSpacing(8)
        read_row.addWidget(self.read_path_edit, 1)
        read_row.addWidget(self.select_read_button)
        form.addRow(read_path_label, read_row)

        self.save_path_edit = LineEdit(self)
        self.save_path_edit.setPlaceholderText('表情导出保存位置')
        self.select_save_button = PushButton('浏览…', self)
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        save_row.addWidget(self.save_path_edit, 1)
        save_row.addWidget(self.select_save_button)
        form.addRow(save_path_label, save_row)

        self.user_combo = ComboBox(self)
        user_row = QHBoxLayout()
        user_row.setSpacing(4)
        user_row.addWidget(self.user_combo, 1)
        user_row.addWidget(self._create_help_button(
            '没显示用户？',
            '没有显示用户？',
            '1. 请确认「数据路径」已指向 QQ 聊天数据目录（Tencent Files文件夹）。\n'
            '2. 请确保你使用的是新版的QQNT而不是怀旧版QQ。\n'))
        form.addRow(user_label, user_row)

        self.category_combo = ComboBox(self)
        category_row = QHBoxLayout()
        category_row.setSpacing(4)
        category_row.addWidget(self.category_combo, 1)
        category_row.addWidget(self._create_help_button(
            '没有表情分类？',
            '下拉框没有表情分类？',
            '1. 请确保你使用的是新版的QQNT而不是怀旧版QQ。\n'
            '2. 需要在QQ内加载过对应的表情包才可扫描到。\n'
            '3. 若仍为空，请执行操作2后重启软件。'))
        form.addRow(category_label, category_row)

        self.scan_button = PrimaryPushButton('扫描表情包并预览', self)
        self.scan_button.setFixedHeight(36)
        form.addRow('', self.scan_button)

        config_layout.addLayout(form)
        root.addWidget(self.config_card)

        # ---- 扫描完成后的摘要行 ----
        self.summary_row = QWidget(self)
        summary_layout = QHBoxLayout(self.summary_row)
        summary_layout.setContentsMargins(4, 0, 4, 0)
        self.summary_label = BodyLabel('')
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch()
        self.summary_row.setVisible(False)
        root.addWidget(self.summary_row)

        # ---- 导出操作条（常驻）----
        export_bar = QHBoxLayout()
        self.export_selected_button = PrimaryPushButton('导出选中表情', self)
        self.export_all_button = PushButton('导出全部表情', self)
        export_bar.addWidget(self.export_selected_button)
        export_bar.addWidget(self.export_all_button)
        export_bar.addStretch()
        self.detail_toggle_button = RotatingChevronButton(self)
        self.detail_toggle_button.setToolTip('收起详情面板')
        self.detail_toggle_button.clicked.connect(self._toggle_detail)
        export_bar.addWidget(self.detail_toggle_button)
        root.addLayout(export_bar)

        # ---- 预览区 + 悬浮详情抽屉 ----
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(16)

        # 预览承载容器：预览卡填满容器，详情抽屉作为悬浮覆盖层叠在其上
        self.preview_host = QWidget(self)
        host_layout = QVBoxLayout(self.preview_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        self.preview_card = CardWidget(self.preview_host)
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(16, 12, 16, 12)
        preview_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_title = StrongBodyLabel('表情包预览区')
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        self.select_all_button = PushButton('全选已加载', self)
        self.clear_sel_button = PushButton('清空选择', self)
        preview_header.addWidget(self.select_all_button)
        preview_header.addWidget(self.clear_sel_button)
        preview_layout.addLayout(preview_header)

        # 空状态引导页 + 预览网格
        self.stack = QStackedWidget(self)
        self.empty_page = self._build_empty_page()
        self.preview_widget = EmojiPreviewWidget(self)
        self.stack.addWidget(self.empty_page)      # index 0
        self.stack.addWidget(self.preview_widget)  # index 1
        preview_layout.addWidget(self.stack, 1)
        host_layout.addWidget(self.preview_card)

        self.content_layout.addWidget(self.preview_host, 1)

        # 详情抽屉（悬浮覆盖层）：不占布局空间，展开时从右侧滑入覆盖预览区
        # 使用高不透明度卡片，深色模式下悬浮文字更易读
        self.detail_card = DetailPanelCard(self.preview_host)
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(16, 12, 16, 12)
        self.detail_widget = EmojiDetailWidget(self.detail_card)
        detail_layout.addWidget(self.detail_widget)
        self.detail_card.setVisible(False)

        root.addLayout(self.content_layout, 1)

        # ---- 底部状态行 ----
        self.status_label = CaptionLabel('请先选择用户与分类，然后点击「扫描表情包并预览」')
        root.addWidget(self.status_label)

    # ---------- 问号帮助按钮 ----------

    def _create_help_button(self, tooltip, title, content):
        """创建带图标的透明帮助按钮：悬浮提示 + 点击弹出自主排查教学气泡。"""
        btn = TransparentPushButton(FIF.QUESTION, '帮助', self.config_card)
        btn.setToolTip(tooltip)
        btn.clicked.connect(lambda: self._show_help_tip(btn, title, content))
        return btn

    def _show_help_tip(self, target, title, content):
        """在按钮旁弹出教学气泡；重复点击时先关闭旧气泡再重开。

        使用 PopupTeachingTip.create：Popup 窗口点击外部空白自动关闭；
        其内部同时连接 view.closed 信号，右上角叉号亦可正常关闭
        （TeachingTip.make 不会连接该信号）。
        """
        if self._help_tip is not None:
            try:
                self._help_tip.close()
            except RuntimeError:
                pass
            self._help_tip = None
        tip = PopupTeachingTip.create(
            target, title, content, FIF.QUESTION,
            isClosable=True, duration=-1,
            tailPosition=TeachingTipTailPosition.TOP,
            parent=self.window())
        # 气泡自毁（点击外部/关闭按钮）后清空引用，避免悬垂
        tip.destroyed.connect(self._on_help_tip_destroyed)
        self._help_tip = tip

    def _on_help_tip_destroyed(self):
        self._help_tip = None

    def _build_empty_page(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        icon_label = QLabel(page)
        # 空状态占位图：使用本地素材图片（等比缩放，避免非正方形图片拉伸）
        icon_pixmap = QPixmap(get_asset_path('ClanChat_Emoji_Dummy01.png'))
        if icon_pixmap.isNull():
            icon_pixmap = FIF.EMOJI_TAB_SYMBOLS.icon().pixmap(160, 160)
        else:
            icon_pixmap = icon_pixmap.scaled(
                160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label = BodyLabel('这里空空如也~\n请先选择用户与分类后，点击上方「扫描表情包并预览」开始')
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch(3)
        return page

    # ---------- 信号连接 ----------

    def _connect_signals(self):
        self.select_read_button.clicked.connect(self.select_read_path)
        self.select_save_button.clicked.connect(self.select_save_path)
        self.scan_button.clicked.connect(self.on_scan_clicked)
        self.export_selected_button.clicked.connect(self._on_export_selected)
        self.export_all_button.clicked.connect(self._on_export_all)
        self.select_all_button.clicked.connect(self.preview_widget.select_all_loaded)
        self.clear_sel_button.clicked.connect(self.preview_widget.clear_selection)

        self.user_combo.currentIndexChanged.connect(self.on_user_changed)
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)

        self.preview_widget.loadMoreRequested.connect(self._start_preview_batch)
        self.preview_widget.sortRequested.connect(self._on_sort_requested)
        self.preview_widget.extractCurrentRequested.connect(self._on_export_current)
        self.preview_widget.extractSelectedRequested.connect(self._on_export_selected)
        self.preview_widget.openFolderRequested.connect(self._on_open_folder)
        self.preview_widget.openLargeImageRequested.connect(self._on_open_large_image)
        self.preview_widget.statusChanged.connect(self._on_preview_status)
        self.preview_widget.itemSelectionChanged.connect(self._on_selection_changed)

        self.detail_widget.collapsedChanged.connect(self._on_detail_collapsed)

        # 设置页修改保存路径后，同步工作台输入框与导出目标
        signalBus.savePathChanged.connect(self._on_save_path_synced)

        self.user_service.nicknameReady.connect(self._on_nickname_ready)

    def _init_state(self):
        saved = cfg.get(cfg.savePath)
        if saved:
            self.save_path_edit.setText(to_display_path(saved))
            self.save_path = saved
        # 详情面板折叠状态
        self.detail_widget.set_collapsed(not cfg.get(cfg.detailPanelExpanded))
        # 配置面板启动时默认展开：箭头初始化为朝上（180°），
        # 保证首次点击收起时也有 180°→0° 的旋转动画
        self.config_collapse_button.set_direction(180, animated=False)

    # ---------- 用户/分类 ----------

    def populate_users(self):
        userdata_path = self.userdata_save_path_cache
        auto_detected = False
        if not userdata_path:
            # 优先自动检测：QQ 会把当前聊天数据位置写入 UserDataInfo.ini
            userdata_path = get_userdata_save_path()
            if userdata_path:
                auto_detected = True
        if not userdata_path or not os.path.exists(userdata_path):
            # 回退：上次手动选择并保存的目录
            userdata_path = cfg.get(cfg.lastDataPath)

        if userdata_path and os.path.exists(userdata_path):
            self.read_path_edit.setText(to_display_path(userdata_path))
            self.userdata_save_path_cache = userdata_path
            cfg.set(cfg.lastDataPath, userdata_path)
            if auto_detected:
                self._notify_auto_detected(userdata_path)

            qq_list = get_numeric_subdirectories(userdata_path)
            self.user_combo.clear()
            if qq_list:
                for qq in qq_list:
                    display = self.user_service.get_display_name(qq)
                    self.user_combo.addItem(display, None, qq)
                    if display == qq:
                        self.user_service.fetch_nickname(qq)  # 异步回填昵称
                signalBus.logMessage.emit('info', f'成功加载 {len(qq_list)} 个QQ用户文件夹')
            else:
                signalBus.logMessage.emit('warn', f'在目录 [{to_display_path(userdata_path)}] 下未找到任何QQ号数据文件夹')
        else:
            self.read_path_edit.setText('')
            self.user_combo.clear()
            signalBus.logMessage.emit('warn', '未能自动定位到QQ聊天数据文件夹，请手动选择数据目录')
            self._warn_manual_path()
        self.on_user_changed()

    def _warn_manual_path(self):
        """自动检测失败时，右上角通知用户手动选择聊天记录位置。"""
        if self.isVisible():
            InfoBar.warning('未找到QQ数据目录', '自动检测失败，请手动选择聊天记录位置', duration=5000, parent=self)
        else:
            # 启动阶段窗口尚未显示：推迟到事件循环开始（窗口已展示）后再弹出
            QTimer.singleShot(0, self._warn_manual_path)

    def _notify_auto_detected(self, path):
        """自动检测到QQ数据目录时，右上角通知已自动定位并填充路径。"""
        if self.isVisible():
            InfoBar.success('成功！', f'已为您自动定位QQ数据目录，路径已自动填充：\n{to_display_path(path)}', duration=5000, parent=self)
        else:
            # 启动阶段窗口尚未显示：推迟到事件循环开始（窗口已展示）后再弹出
            QTimer.singleShot(0, lambda: self._notify_auto_detected(path))

    def on_user_changed(self):
        self._reset_workspace()
        qq = self.user_combo.currentData()
        self.category_combo.clear()
        if not qq:
            return
        userdata = self.userdata_save_path_cache or get_userdata_save_path()
        if not userdata:
            return
        emoji_root = get_emoji_root(userdata, qq)
        if emoji_root.exists() and emoji_root.is_dir():
            for d in sorted(os.listdir(emoji_root)):
                if os.path.isdir(emoji_root / d):
                    self.category_combo.addItem(get_category_display_name(d), None, d)
        else:
            signalBus.logMessage.emit('warn', f'未找到该账户的 Emoji 目录: {to_display_path(emoji_root)}')
        # 收藏图片分类：Pic 目录存在时提供「收藏图片」扫描入口（扫描 Pic/日期/Ori 下原图）
        if get_pic_root(userdata, qq).exists():
            self.category_combo.addItem(get_category_display_name('pic'), None, 'pic')

    def on_category_changed(self):
        self._reset_workspace()

    def _on_nickname_ready(self, qq, nickname):
        if not nickname:
            return
        for i in range(self.user_combo.count()):
            if self.user_combo.itemData(i) == qq:
                self.user_combo.setItemText(i, f"{nickname}（{qq}）")
                break

    # ---------- 目录选择 ----------

    def select_read_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, '选择QQ聊天记录所在目录（即包含QQ号数字文件夹的 Tencent Files 目录）')
        if directory:
            self.userdata_save_path_cache = directory
            cfg.set(cfg.lastDataPath, directory)
            signalBus.logMessage.emit('info', f'已选择数据目录: {directory}')
            self.populate_users()
        else:
            signalBus.logMessage.emit('info', '取消选择数据目录')

    def select_save_path(self):
        directory = QFileDialog.getExistingDirectory(self, '请选择表情包保存路径')
        if directory:
            self.save_path_edit.setText(to_display_path(directory))
            self.save_path = directory
            cfg.set(cfg.savePath, directory)
            signalBus.logMessage.emit('info', f'已将保存路径设置为: {to_display_path(directory)}')
            # 通知设置页同步显示
            signalBus.savePathChanged.emit(directory)

    def _on_save_path_synced(self, path):
        """设置页修改保存路径后同步工作台输入框与导出目标。"""
        if not path:
            return
        self.save_path_edit.setText(to_display_path(path))
        self.save_path = path

    # ---------- 扫描 ----------

    def on_scan_clicked(self):
        qq = self.user_combo.currentData()
        if not qq:
            InfoBar.warning('提示', '请先选择一个用户', duration=5000, parent=self)
            return
        folder = self.category_combo.currentData()
        if not folder:
            InfoBar.warning('提示', '请先选择一个表情分类', duration=5000, parent=self)
            return
        userdata = self.userdata_save_path_cache or get_userdata_save_path()
        if not userdata:
            InfoBar.error('错误', '未找到聊天数据目录，请手动选择数据目录', duration=5000, parent=self)
            return
        emoji_path = get_category_path(userdata, qq, folder)
        if not emoji_path.exists():
            InfoBar.error('错误', f'未找到该分类的本地目录:\n{emoji_path}', duration=5000, parent=self)
            return

        # 取消旧任务，进入新一轮（代际令牌 +1）
        self._cancel_all_workers()
        self.generation += 1
        self.is_loading = False
        self.current_folder_key = folder
        self.preview_widget.set_entries([])
        self.detail_widget.show_placeholder('未选中表情')

        self.scan_button.setEnabled(False)
        self.tooltip.show('正在扫描表情包…', '正在遍历分类目录…')
        signalBus.logMessage.emit('info', f'开始智能扫描分类 [{folder}] 表情文件...')

        worker = ScanWorker(self.generation, str(emoji_path), folder)
        worker.progress.connect(self._on_scan_progress)
        worker.finished.connect(self._on_scan_finished)
        self._workers['scan'] = worker
        start_worker(worker, self)

    def _on_scan_progress(self, current, total):
        self.tooltip.update(f'已处理 {current}/{total} 个文件…')

    def _on_scan_finished(self, gen, paths):
        self.scan_button.setEnabled(True)
        if gen != self.generation:
            return
        if not paths:
            self.tooltip.finish('扫描完成', '未发现有效表情')
            InfoBar.warning('扫描完成', '未筛选出任何有效的表情包图片', duration=5000, parent=self)
            return
        entries = [EmojiEntry(path=p) for p in paths]
        self.preview_widget.set_entries(entries)
        self._show_preview_or_empty()
        self._collapse_config()
        self.tooltip.finish('扫描完成', f'共发现 {len(paths)} 个有效表情')
        InfoBar.success('扫描完成', f'发现 {len(paths)} 个有效表情', duration=5000, parent=self)
        signalBus.logMessage.emit('info', f'扫描并筛选完毕，共发现 {len(paths)} 个有效表情图片')
        self._start_preview_batch()

    # ---------- 预览懒加载 ----------

    def _start_preview_batch(self):
        if self.is_loading:
            return
        if self.preview_widget.loaded_count >= len(self.preview_widget.entries):
            return
        self.is_loading = True

        start_idx = self.preview_widget.loaded_count
        entries = self.preview_widget.entries[start_idx:start_idx + self.preview_widget.batch_size]
        paths = [e.path for e in entries]

        worker = PreviewLoaderWorker(
            self.generation, paths, self.current_folder_key == 'marketface', start_idx, len(paths))
        worker.batchReady.connect(self._on_batch_ready)
        worker.finished.connect(self._on_preview_finished)
        self._workers['preview'] = worker
        start_worker(worker, self)

    def _on_batch_ready(self, gen, start_idx, items):
        if gen != self.generation:
            return
        self.preview_widget.append_batch(items)

    def _on_preview_finished(self, gen):
        if gen != self.generation:
            return
        self.is_loading = False
        # 若滚动条仍在底部附近，继续加载以填满视口
        if self.preview_widget.loaded_count < len(self.preview_widget.entries):
            scroll_bar = self.preview_widget.verticalScrollBar()
            if scroll_bar.maximum() <= 0 or scroll_bar.value() > scroll_bar.maximum() * 0.9:
                self._start_preview_batch()

    # ---------- 排序 ----------

    def _on_sort_requested(self, key, order):
        if not self.preview_widget.entries:
            return
        self.preview_widget.sort_key = key
        self.preview_widget.sort_order = order
        self._cancel_worker('sort')
        gen = self.generation
        self.tooltip.show('正在排序…', '正在读取文件信息…')
        worker = SortWorker(
            gen, list(self.preview_widget.entries), key, order,
            self.current_folder_key == 'marketface')
        worker.finished.connect(self._on_sort_finished)
        self._workers['sort'] = worker
        start_worker(worker, self)

    def _on_sort_finished(self, gen, entries):
        if gen != self.generation:
            return
        self.tooltip.finish('排序完成', f'按所选方式排序，共 {len(entries)} 个表情')
        self.preview_widget.set_entries(entries)
        self.is_loading = False
        self._start_preview_batch()

    # ---------- 详情预览 ----------

    def _on_selection_changed(self):
        item = self.preview_widget.currentItem()
        if item is None or not item.isSelected():
            self.detail_widget.show_placeholder('未选中表情')
            # 取消选中时自动收起详情面板（带动画）
            if not self.detail_widget.is_collapsed():
                self.detail_widget.set_collapsed(True, persist=False)
                self._animate_detail_collapse()
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            self.detail_widget.show_placeholder('文件不存在')
            return
        # 选中项目时自动展开详情面板（带动画）
        if self.detail_widget.is_collapsed():
            self.detail_widget.set_collapsed(False, persist=False)
            self._animate_detail_expand()
        self.detail_widget.set_info(self._build_detail_info(path))
        self._load_detail(path)

    def _build_detail_info(self, path):
        entry = self.preview_widget.get_entry(path)
        file_name = os.path.basename(path)
        try:
            size_kb = os.path.getsize(path) / 1024
        except Exception:
            size_kb = 0

        if self.current_folder_key == 'marketface':
            format_display = 'GIF（已解密）'
        elif entry and entry.ext:
            format_display = entry.ext.upper()
            if entry.ext.lower() == 'apng' or entry.is_apng:
                format_display = 'APNG (动态图片)'
        else:
            ext = get_actual_extension(path)
            format_display = ext.upper() if ext else '未知'
            if ext == 'png' and is_apng_file(path):
                format_display = 'APNG (动态图片)'

        info_text = f"<b>文件名:</b><br/>{_escape_wbr(file_name)}<br/><br/>"
        info_text += f"<b>格式:</b> {_html_escape(format_display)}<br/>"
        info_text += f"<b>大小:</b> {size_kb:.2f} KB<br/><br/>"
        # 路径较长：插入零宽空格断行点，配合自动换行完整显示
        info_text += f"<b>保存路径:</b><br/>{_escape_wbr(to_display_path(path))}"
        return info_text

    def _load_detail(self, path):
        self._cancel_worker('detail')
        worker = DetailLoaderWorker(self.generation, path, self.current_folder_key == 'marketface')
        worker.finished.connect(self._on_detail_loaded)
        self._workers['detail'] = worker
        start_worker(worker, self)

    def _on_detail_loaded(self, gen, payload):
        if gen != self.generation:
            return
        if not payload:
            self.detail_widget.previewLabel.setText('预览失败')
            return
        if payload['kind'] == 'data':
            self.detail_widget.play_bytes(payload['data'])
        else:
            ext = (payload.get('ext') or '').lower()
            if ext == 'gif':
                self.detail_widget.play_file(payload['path'])
            else:
                self.detail_widget.show_image(payload['path'])

    # ---------- 导出 ----------

    def _on_export_current(self):
        path = self.preview_widget.get_current_path()
        if not path:
            InfoBar.warning('提示', '请先点选一个表情', duration=5000, parent=self)
            return
        self._confirm_and_export([path], '提取当前表情')

    def _on_export_selected(self):
        paths = self.preview_widget.get_selected_paths()
        if not paths:
            InfoBar.warning('提示', '请先在预览区选中表情后再导出', duration=5000, parent=self)
            return
        self._confirm_and_export(paths, '提取的选中表情')

    def _on_export_all(self):
        if not self.preview_widget.entries:
            InfoBar.warning('提示', '请先扫描表情包', duration=5000, parent=self)
            return
        paths = [e.path for e in self.preview_widget.entries]
        self._confirm_and_export(paths, '提取的全部表情')

    def _confirm_and_export(self, paths, suffix):
        if not self.save_path:
            InfoBar.warning('提示', '请先选择保存路径', duration=5000, parent=self)
            return
        display_name = self.user_service.get_display_name(self.user_combo.currentData() or '')
        safe_name = sanitize_filename(display_name) or 'unknown'
        output_dir = os.path.join(self.save_path, f"{safe_name}_{self.current_folder_key}_{suffix}")

        box = MessageBox('确认导出', f'确定导出 {len(paths)} 个表情到：\n{to_display_path(output_dir)}？', self)
        box.yesButton.setText('导出')
        box.cancelButton.setText('取消')
        if not box.exec():
            return
        self._start_export(paths, output_dir)

    def _start_export(self, paths, output_dir):
        if self._exporting:
            return
        self._exporting = True
        self.export_selected_button.setEnabled(False)
        self.export_all_button.setEnabled(False)
        self.tooltip.show('正在导出表情…', '0/{}'.format(len(paths)))
        signalBus.logMessage.emit('info', f'正在复制表情文件到: {output_dir}')

        worker = ExportWorker(self.generation, paths, output_dir, self.current_folder_key)
        worker.progress.connect(self._on_export_progress)
        worker.log.connect(self._on_export_log)
        worker.finished.connect(self._on_export_finished)
        self._workers['export'] = worker
        start_worker(worker, self)

    def _on_export_progress(self, current, total):
        self.tooltip.update(f'{current}/{total} 已导出…')

    def _on_export_log(self, level, message):
        signalBus.logMessage.emit(level, message)

    def _on_export_finished(self, gen, success, output_dir):
        if gen == self.generation:
            self.tooltip.finish('导出完成', f'成功导出 {success} 个表情')
            InfoBar.success('导出完成', f'成功导出 {success} 个表情', duration=5000, parent=self)
            signalBus.logMessage.emit('info', f'导出完成：成功 {success} 个 -> {to_display_path(output_dir)}')
            self._open_in_explorer(output_dir)
        self._exporting = False
        self.export_selected_button.setEnabled(True)
        self.export_all_button.setEnabled(True)

    # ---------- 杂项 ----------

    def _on_open_folder(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
        except Exception as e:
            signalBus.logMessage.emit('error', f'无法打开资源管理器: {e}\n{format_exc()}')

    def _open_in_explorer(self, directory):
        try:
            subprocess.Popen(['explorer', os.path.abspath(directory)])
        except Exception as e:
            signalBus.logMessage.emit('error', f'无法打开资源管理器: {e}\n{format_exc()}')

    def _on_open_large_image(self, path):
        """双击预览图：复用同一个大图查看窗口加载新图片（窗口尺寸随图片变化）。

        有且只有一个大图窗口；窗口关闭（Esc/X）仅隐藏，再次点击时复用并加载新图。
        """
        if not path or not os.path.exists(path):
            InfoBar.warning('提示', '文件不存在或已被移动', duration=5000, parent=self)
            return
        dialog = self._image_viewer
        if dialog is None:
            # 不设置 WA_DeleteOnClose：关闭仅隐藏，便于复用；随主窗口一起销毁
            dialog = LargeImageViewer(self)
            dialog.destroyed.connect(self._on_viewer_destroyed)
            self._image_viewer = dialog
        if self.current_folder_key == 'marketface':
            from src.core.marketface_handler import recover_marketface_preview
            data = recover_marketface_preview(path)
            dialog.show_payload({'kind': 'data', 'data': data} if data else None)
        else:
            ext = get_actual_extension(path) or os.path.splitext(path)[1].lstrip('.').lower()
            dialog.show_payload({'kind': 'path', 'path': path, 'ext': ext})
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_viewer_destroyed(self):
        """大图窗口被销毁（主窗口关闭）时清空引用，避免悬垂。"""
        self._image_viewer = None

    def _on_preview_status(self, loaded, total, selected):
        if total == 0:
            self.status_label.setText('请先选择用户与分类，然后点击「扫描表情包并预览」')
        else:
            self.status_label.setText(f'已加载 {loaded}/{total} · 已选中 {selected}')

    def _toggle_detail(self):
        collapsed = self.detail_widget.is_collapsed()
        self.detail_widget.set_collapsed(not collapsed, persist=False)
        if collapsed:
            self._animate_detail_expand()
        else:
            self._animate_detail_collapse()
        cfg.set(cfg.detailPanelExpanded, not collapsed)

    def _apply_detail_visibility(self, collapsed):
        # 收起时朝左（90°）、展开时朝右（-90°）；抽屉显隐由动画的 finished 回调控制
        self.detail_toggle_button.set_direction(90 if collapsed else -90)
        self.detail_toggle_button.setToolTip('展开详情面板' if collapsed else '收起详情面板')

    def _detail_drawer_width(self):
        """抽屉固定宽度：内容宽度 + 卡片边距，不随预览区宽度变化。

        注意：使用 layout().sizeHint() 而非 widget.sizeHint()——后者会触发
        ensurePolished → 父级事件派发 → 事件过滤器 → 本方法，形成递归导致栈溢出。
        """
        if self._drawer_width_cache <= 0:
            try:
                self._drawer_width_cache = self.detail_card.layout().sizeHint().width()
            except Exception:
                self._drawer_width_cache = 332
        return max(self._drawer_width_cache, 300)

    def _detail_drawer_top(self):
        """抽屉上边缘：预览卡头部（标题 + 全选/清空按钮）下方，避免遮挡按钮。

        注意：itemAt(0) 是头部 QHBoxLayout，geometry() 为激活布局后的实际区域；
        回退用 sizeHint（仅 layout 的，不会触发 ensurePolished 递归）。
        """
        try:
            layout = self.preview_card.layout()
            margins = layout.contentsMargins()
            header = layout.itemAt(0)
            rect = header.geometry()
            height = rect.height() if rect.height() > 0 else header.sizeHint().height()
            return margins.top() + height + layout.spacing()
        except Exception:
            return 0

    def _layout_detail_drawer(self, collapsed, animate=False):
        """定位悬浮详情抽屉：折叠时滑出右侧，展开时滑入覆盖预览区（不改变预览区宽度）。"""
        host = self.preview_host
        # 先同步激活布局，确保 host 尺寸已按最新窗口大小更新完毕
        self.content_layout.activate()
        if not collapsed:
            width = self._detail_drawer_width()
            top = self._detail_drawer_top()
            height = max(host.height() - top, 0)
            target = QRect(host.width() - width, top, width, height)
            if animate:
                if self._detail_anim is not None:
                    self._detail_anim.stop()
                    self._detail_anim = None
                self.detail_card.setVisible(True)
                self.detail_card.setGeometry(host.width(), top, width, height)
                anim = QPropertyAnimation(self.detail_card, b'geometry', self)
                anim.setDuration(250)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.setStartValue(self.detail_card.geometry())
                anim.setEndValue(target)
                anim.finished.connect(lambda: self.detail_card.setGeometry(target))
                anim.start()
                self._detail_anim = anim
            else:
                self.detail_card.setVisible(True)
                self.detail_card.setGeometry(target)
        else:
            if animate:
                if not self.detail_card.isVisible():
                    return
                if self._detail_anim is not None:
                    self._detail_anim.stop()
                    self._detail_anim = None
                start = self.detail_card.geometry()
                end = QRect(host.width(), start.y(), start.width(), start.height())
                anim = QPropertyAnimation(self.detail_card, b'geometry', self)
                anim.setDuration(250)
                anim.setEasingCurve(QEasingCurve.Type.InCubic)
                anim.setStartValue(start)
                anim.setEndValue(end)
                anim.finished.connect(lambda: self.detail_card.setVisible(False))
                anim.start()
                self._detail_anim = anim
            else:
                self.detail_card.setVisible(False)

    def _animate_detail_expand(self):
        self._layout_detail_drawer(False, animate=True)
        self._apply_detail_visibility(False)

    def _animate_detail_collapse(self):
        self._layout_detail_drawer(True, animate=True)
        self._apply_detail_visibility(True)

    def _on_detail_collapsed(self, collapsed):
        cfg.set(cfg.detailPanelExpanded, not collapsed)
        self._apply_detail_visibility(collapsed)
        # 详情控件内部折叠按钮触发的即时切换（不带动画）
        self._layout_detail_drawer(collapsed, animate=False)

    # ---------- 配置卡折叠 ----------

    def _toggle_config(self):
        if self.config_card.isVisible():
            self._collapse_config()
        else:
            self._expand_config()

    def _collapse_config(self):
        self.summary_row.setVisible(True)
        self.summary_label.setText(
            f'已选：{self.user_combo.currentText()} / {self.category_combo.currentText()}')
        target = self.config_card.height()
        self._animate_config(height_from=target, height_to=0,
                             on_finish=lambda: self.config_card.setVisible(False))
        # 收起后图标朝下（0°），提示点击可展开
        self.config_collapse_button.set_direction(0)
        self.config_collapse_button.setToolTip('展开配置面板')

    def _expand_config(self):
        self.config_card.setVisible(True)
        self.config_card.adjustSize()
        target = self.config_card.sizeHint().height()
        self._animate_config(height_from=0, height_to=target,
                             on_finish=lambda: self.summary_row.setVisible(False))
        # 展开后图标朝上（180°），提示点击可收起
        self.config_collapse_button.set_direction(180)
        self.config_collapse_button.setToolTip('收起配置面板')

    def _animate_config(self, height_from, height_to, on_finish=None):
        if self._config_anim is not None:
            self._config_anim.stop()
        anim = QPropertyAnimation(self.config_card, b'maximumHeight', self)
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(height_from)
        anim.setEndValue(height_to)

        def _finish():
            if on_finish is not None:
                on_finish()
            # 配置卡隐藏/显示等布局变化完成后，最终校准一次抽屉位置
            self._layout_detail_drawer(self.detail_widget.is_collapsed(), animate=False)

        # 配置区高度变化会改变预览区高度，悬浮详情抽屉需同步跟随，
        # 否则配置展开/收起后抽屉位置与图片错位
        anim.valueChanged.connect(
            lambda _v: self._layout_detail_drawer(self.detail_widget.is_collapsed(), animate=False))
        anim.finished.connect(_finish)
        anim.start()
        self._config_anim = anim

    def _show_preview_or_empty(self):
        self.stack.setCurrentIndex(1 if len(self.preview_widget.entries) > 0 else 0)

    # ---------- 线程管理 ----------

    def _cancel_worker(self, kind):
        worker = self._workers.pop(kind, None)
        if worker is not None:
            worker.cancel()

    def _cancel_all_workers(self):
        for worker in self._workers.values():
            worker.cancel()
        self._workers.clear()

    def _reset_workspace(self):
        self._cancel_all_workers()
        self.generation += 1
        self.is_loading = False
        self.preview_widget.set_entries([])
        self.detail_widget.show_placeholder('未选中表情')
        self._show_preview_or_empty()
        # 保持配置面板当前的折叠状态，避免下拉框选择项目时配置面板异常收起再展开

    def shutdown(self):
        """窗口关闭前调用：取消所有后台任务并等待线程安全结束，避免退出时崩溃。"""
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        # 线程由 _live_threads 持有（已结束的会自动移除），这里只等待仍在运行的线程
        threads = list(self._live_threads.values())
        for thread in threads:
            thread.quit()
        for thread in threads:
            if thread.isRunning():
                thread.wait(2000)
        self._workers.clear()
        self._live_threads.clear()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.tooltip.reposition()
        # 保持悬浮抽屉贴合预览区右侧边缘（不改变预览区宽度）
        self._layout_detail_drawer(self.detail_widget.is_collapsed(), animate=False)
        # 窗口变窄时自动收起详情面板（不覆盖用户手动折叠状态）
        if self.width() < 980 and not self.detail_widget.is_collapsed():
            self.detail_widget.set_collapsed(True, persist=False)
            self._animate_detail_collapse()

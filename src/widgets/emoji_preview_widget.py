# coding=utf-8
"""表情网格控件：QListWidget IconMode + 懒加载 + 右键菜单 + 排序 + 多选。"""

import os
from dataclasses import dataclass, field

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem,
                             QStyle, QStyledItemDelegate)

from qfluentwidgets import MenuAnimationType, themeColor

from src.widgets.sort_menu import build_context_menu


@dataclass
class EmojiEntry:
    """单个表情文件的元数据（含未加载部分）。"""
    path: str
    size: int = 0
    mtime: float = 0.0
    ext: str = ""
    is_animated: bool = False
    frame_count: int = 1
    is_apng: bool = False


class EmojiItemDelegate(QStyledItemDelegate):
    """自定义网格项绘制：缩略图居中 + 选中时仅在外部绘制圆角边框（无背景填充）。

    相比 QSS 高亮，此实现不会在图片周围产生半透明填充的「白色框框」。
    """

    ICON_SIZE = 100          # 与 workers.THUMBNAIL_SIZE 一致
    BORDER_MARGIN = 6        # 边框与缩略图外缘的间距
    BORDER_WIDTH = 2

    def paint(self, painter, option, index):
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon is None or icon.isNull():
            return

        painter.save()
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform)

        rect = option.rect
        pixmap = icon.pixmap(self.ICON_SIZE, self.ICON_SIZE)
        if not pixmap.isNull():
            x = rect.center().x() - pixmap.width() // 2
            y = rect.center().y() - pixmap.height() // 2
            painter.drawPixmap(x, y, pixmap)

        # 选中态：仅绘制外部圆角边框，不填充背景
        if option.state & QStyle.StateFlag.State_Selected:
            color = themeColor()
            pen = QPen(color, self.BORDER_WIDTH)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            margin = self.BORDER_MARGIN
            painter.drawRoundedRect(
                QRectF(rect).adjusted(margin, margin, -margin, -margin), 8, 8)

        painter.restore()


class EmojiPreviewWidget(QListWidget):
    """表情预览网格。

    职责：
    - 持有全量 EmojiEntry 元数据（含未加载部分）
    - 按批渲染缩略图（由外部工作线程解码后调用 append_batch）
    - 滚动懒加载（滚动条 90% 触发 loadMoreRequested）
    - 右键菜单：排序（RoundMenu + CheckableMenu）/ 快捷多选 / 提取
    """

    loadMoreRequested = pyqtSignal()
    sortRequested = pyqtSignal(str, str)      # (key, order)
    extractCurrentRequested = pyqtSignal()
    extractSelectedRequested = pyqtSignal()
    openFolderRequested = pyqtSignal(str)
    openLargeImageRequested = pyqtSignal(str)  # 双击某项：请求打开大图
    statusChanged = pyqtSignal(int, int, int)  # (loaded, total, selected)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.entries = []                # 全量元数据（含未加载部分）
        self._entry_map = {}             # path -> EmojiEntry
        self.loaded_count = 0            # 已渲染数量
        self.batch_size = 100
        self.sort_key = 'name'
        self.sort_order = 'asc'

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setIconSize(QSize(100, 100))
        self.setGridSize(QSize(120, 120))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(False)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 自定义绘制：缩略图居中 + 选中仅外侧圆角边框（避免白色框框）
        self.setItemDelegate(EmojiItemDelegate(self))

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.itemSelectionChanged.connect(self._emit_status)

        # 快捷键：Ctrl+A 全选已加载，Ctrl+D 清空选择
        QShortcut(QKeySequence('Ctrl+A'), self, activated=self.select_all_loaded,
                  context=Qt.ShortcutContext.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence('Ctrl+D'), self, activated=self.clear_selection,
                  context=Qt.ShortcutContext.WidgetWithChildrenShortcut)

    # ---------- 数据管理 ----------

    def set_entries(self, entries):
        """整体替换表情列表（扫描完成 / 排序完成后调用），并重置视图。"""
        self.clear()
        self.entries = list(entries)
        self._entry_map = {e.path: e for e in self.entries}
        self.loaded_count = 0
        self.scrollToTop()
        self._emit_status()

    def get_entry(self, path):
        return self._entry_map.get(path)

    def append_batch(self, items):
        """把工作线程解码好的一批缩略图渲染到网格中。"""
        for data in items:
            path = data['path']
            entry = self._entry_map.get(path)
            if entry is not None:
                entry.ext = data['ext']
                entry.is_animated = data['is_animated']
                entry.frame_count = data['frame_count']

            icon = QIcon(QPixmap.fromImage(data['image']))
            item = QListWidgetItem(icon, "")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setData(Qt.ItemDataRole.UserRole + 1, data['is_animated'])
            item.setToolTip(
                f"格式: {data['ext'].upper()}\n"
                f"路径: {os.path.basename(path)}"
            )
            self.addItem(item)
        self.loaded_count += len(items)
        self._emit_status()

    # ---------- 懒加载 ----------

    def request_load_more(self):
        if self.loaded_count < len(self.entries):
            self.loadMoreRequested.emit()

    def _on_scroll(self, value):
        scroll_bar = self.verticalScrollBar()
        if scroll_bar.maximum() > 0 and value > scroll_bar.maximum() * 0.9:
            self.request_load_more()

    # ---------- 多选操作 ----------

    def select_all_loaded(self):
        for i in range(self.count()):
            self.item(i).setSelected(True)
        self._emit_status()

    def clear_selection(self):
        self.clearSelection()

    def invert_selection(self):
        for i in range(self.count()):
            item = self.item(i)
            item.setSelected(not item.isSelected())
        self._emit_status()

    def select_animated(self, animated=True):
        for i in range(self.count()):
            item = self.item(i)
            is_animated = bool(item.data(Qt.ItemDataRole.UserRole + 1))
            if is_animated == animated:
                item.setSelected(True)
        self._emit_status()

    def get_selected_paths(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.selectedItems()
                if item.data(Qt.ItemDataRole.UserRole)]

    def get_current_path(self):
        item = self.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ---------- 右键菜单 ----------

    def contextMenuEvent(self, e):
        # 右键点击未选中项时自动选中该位置项（符合操作系统惯例）
        item = self.itemAt(e.pos())
        if item is not None and not item.isSelected():
            self.setCurrentItem(item)
            item.setSelected(True)
            self._emit_status()

        callbacks = {
            'on_sort': lambda key, order: self.sortRequested.emit(key, order),
            'on_select_all': self.select_all_loaded,
            'on_invert': self.invert_selection,
            'on_clear_selection': self.clear_selection,
            'on_select_animated': lambda: self.select_animated(True),
            'on_select_static': lambda: self.select_animated(False),
            'on_extract_current': self.extractCurrentRequested.emit,
            'on_extract_selected': self.extractSelectedRequested.emit,
            'on_open_folder': lambda: self.openFolderRequested.emit(self.get_current_path() or ''),
        }
        menu = build_context_menu(self, callbacks)
        menu.exec(e.globalPos(), aniType=MenuAnimationType.DROP_DOWN)

    # ---------- 双击 ----------

    def mouseDoubleClickEvent(self, e):
        item = self.itemAt(e.pos())
        if item is not None:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                self.openLargeImageRequested.emit(path)
        super().mouseDoubleClickEvent(e)

    # ---------- 状态 ----------

    def _emit_status(self):
        self.statusChanged.emit(self.loaded_count, len(self.entries), len(self.selectedItems()))

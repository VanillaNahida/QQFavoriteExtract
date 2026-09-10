# coding=utf-8
"""日志页：详细操作日志（清空 / 导出 txt）。"""

from datetime import datetime

from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from qfluentwidgets import (InfoBar, MessageBox, PrimaryPushButton, PushButton,
                            SubtitleLabel, isDarkTheme)

from src.app.signal_bus import signalBus
from src.core.app_settings import cfg


def _level_colors():
    if isDarkTheme():
        return {
            'info': QColor(220, 220, 220),
            'warn': QColor(230, 190, 60),
            'error': QColor(255, 90, 90),
        }
    return {
        'info': QColor(40, 40, 40),
        'warn': QColor(190, 140, 0),
        'error': QColor(210, 40, 40),
    }


class LogView(QWidget):
    """独立日志导航页：滚动跟随、清空、导出为 txt。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('logView')
        self._follow = True

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = SubtitleLabel('操作日志')
        header.addWidget(title)
        header.addStretch()
        self.clear_button = PrimaryPushButton('清空日志', self)
        self.export_button = PushButton('导出日志…', self)
        header.addWidget(self.clear_button)
        header.addWidget(self.export_button)
        root.addLayout(header)

        self.log_edit = QTextEdit(self)
        self.log_edit.setReadOnly(True)
        root.addWidget(self.log_edit, 1)

        self.clear_button.clicked.connect(self._clear_logs)
        self.export_button.clicked.connect(self._export_logs)
        signalBus.logMessage.connect(self.append_log)
        # 用户上翻时暂停自动滚动，回到底部恢复
        self.log_edit.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_scroll(self, value):
        scroll_bar = self.log_edit.verticalScrollBar()
        self._follow = value >= scroll_bar.maximum() - 30

    def append_log(self, level, message):
        if not cfg.get(cfg.logEnabled):
            return
        color = _level_colors().get(level, _level_colors()['info'])
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        char_format = QTextCharFormat()
        char_format.setForeground(color)
        cursor.insertText(message + '\n', char_format)
        if self._follow:
            scroll_bar = self.log_edit.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
            self.log_edit.ensureCursorVisible()

    def _clear_logs(self):
        box = MessageBox('清空日志', '确定清空当前全部日志吗？', self)
        box.yesButton.setText('清空')
        box.cancelButton.setText('取消')
        if box.exec():
            self.log_edit.clear()
            InfoBar.success('已清空', '日志已清空', parent=self)

    def _export_logs(self):
        default_name = f"日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, '导出日志', default_name, 'Text Files (*.txt);;All Files (*)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_edit.toPlainText())
            InfoBar.success('导出成功', f'日志已导出到 {path}', parent=self)
        except Exception as e:
            InfoBar.error('导出失败', str(e), parent=self)

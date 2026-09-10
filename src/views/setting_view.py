# coding=utf-8
"""设置页：主题、默认保存路径、昵称缓存、日志开关。"""

import os
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

from qfluentwidgets import (CaptionLabel, FluentIcon as FIF, InfoBar,
                            OptionsSettingCard, PushSettingCard, ScrollArea,
                            SettingCardGroup, SubtitleLabel, SwitchSettingCard,
                            qconfig, setTheme, Theme)

from src.core.app_settings import cfg, sync_theme_to_cfg
from src.utils.helpers import get_app_data_dir


class SettingView(ScrollArea):
    """应用设置页（qconfig 持久化）。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('settingView')
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        self.viewport().setStyleSheet('background-color: transparent;')

        content = QWidget()
        self.setWidget(content)

        v = QVBoxLayout(content)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(16)

        v.addWidget(SubtitleLabel('设置', content))
        v.addWidget(CaptionLabel('个性化应用外观、默认导出位置与日志行为。', content))

        # 个性化：主题（使用 qconfig.themeMode，与 qfluentwidgets 参考项目一致）
        personal_group = SettingCardGroup('个性化', content)
        self.theme_card = OptionsSettingCard(
            qconfig.themeMode,
            FIF.BRUSH,
            '应用主题',
            '切换应用外观（浅色 / 深色 / 跟随系统）',
            texts=['浅色', '深色', '跟随系统'],
            parent=personal_group,
        )
        personal_group.addSettingCard(self.theme_card)
        v.addWidget(personal_group)

        # 工作台：默认保存路径
        workspace_group = SettingCardGroup('工作台', content)
        self.save_path_card = PushSettingCard(
            '选择文件夹',
            FIF.DOWNLOAD,
            '默认保存路径',
            cfg.get(cfg.savePath) or '未设置',
            workspace_group,
        )
        workspace_group.addSettingCard(self.save_path_card)
        v.addWidget(workspace_group)

        # 数据：昵称缓存
        data_group = SettingCardGroup('数据', content)
        cache_path = os.path.join(get_app_data_dir(), '用户昵称缓存.json')
        self.cache_card = PushSettingCard(
            '清除缓存',
            FIF.DELETE,
            '昵称缓存',
            cache_path,
            data_group,
        )
        self.open_cache_button = PushSettingCard(
            '打开文件夹',
            FIF.FOLDER,
            '缓存位置',
            cache_path,
            data_group,
        )
        data_group.addSettingCard(self.cache_card)
        data_group.addSettingCard(self.open_cache_button)
        v.addWidget(data_group)

        # 日志
        log_group = SettingCardGroup('日志', content)
        self.log_enabled_card = SwitchSettingCard(
            FIF.DOCUMENT,
            '记录日志',
            '关闭后日志页不再记录日志，右上角信息通知不受影响，建议向开发者反馈时开启',
            cfg.logEnabled,
            log_group,
        )
        log_group.addSettingCard(self.log_enabled_card)
        v.addWidget(log_group)

        # 帮助：新手教程
        help_group = SettingCardGroup('帮助', content)
        self.tutorial_card = PushSettingCard(
            '重温教程',
            FIF.EDUCATION,
            '新手教程',
            '点击后重启软件时将再次弹出新手教程',
            help_group,
        )
        help_group.addSettingCard(self.tutorial_card)
        v.addWidget(help_group)

        v.addStretch(1)

        self._connect_signals()

    def _connect_signals(self):
        self.theme_card.optionChanged.connect(self._on_theme_changed)
        self.save_path_card.clicked.connect(self._choose_save_path)
        self.cache_card.clicked.connect(self._clear_cache)
        self.open_cache_button.clicked.connect(self._open_cache_folder)
        self.tutorial_card.clicked.connect(self._reset_tutorial)

    def _on_theme_changed(self, ci):
        """主题变更：应用主题并同步持久化到 cfg"""
        setTheme(qconfig.get(ci), lazy=True)
        sync_theme_to_cfg()

    def _choose_save_path(self):
        directory = QFileDialog.getExistingDirectory(self, '选择默认保存路径')
        if directory:
            cfg.set(cfg.savePath, directory)
            self.save_path_card.setContent(directory)
            InfoBar.success('已保存', f'默认保存路径：{directory}', parent=self)

    def _clear_cache(self):
        from src.core.user_service import UserService
        service = UserService(self)
        if service.clear_cache():
            InfoBar.success('已清除', '昵称缓存已清除', parent=self)
        else:
            InfoBar.info('提示', '缓存文件不存在或清除失败', parent=self)
        service.deleteLater()

    def _open_cache_folder(self):
        cache_path = os.path.join(get_app_data_dir(), '用户昵称缓存.json')
        if os.path.exists(cache_path):
            try:
                subprocess.Popen(['explorer', '/select,', os.path.normpath(cache_path)])
            except Exception as e:
                InfoBar.error('打开失败', f'无法打开缓存文件夹: {e}', parent=self)
        else:
            InfoBar.info('提示', '缓存文件不存在', parent=self)

    def _reset_tutorial(self):
        """重置新手教程标记：下次启动软件时重新弹出教程询问。"""
        cfg.set(cfg.tutorialDone, False)
        InfoBar.success('已重置', '下次启动软件时将重新弹出新手教程', parent=self)
# coding=utf-8
"""应用设置持久化（qconfig）。

重要：AppConfig 不能再自定义 themeMode —— 若在子类中重定义该属性，
会遮蔽 QConfig.themeMode，导致 qconfig.set() 内部 `item is self._cfg.themeMode`
身份判断失败（主题切换不生效）。因此主题直接复用 QConfig.themeMode。
"""

import os

from qfluentwidgets import ConfigItem, QConfig, qconfig

from src.utils.helpers import get_app_data_dir


class AppConfig(QConfig):
    """应用配置项定义"""

    # 工作台
    savePath = ConfigItem("Workspace", "savePath", "")
    lastDataPath = ConfigItem("Workspace", "lastDataPath", "")

    # 详情面板
    detailPanelExpanded = ConfigItem("Workspace", "detailPanelExpanded", True)

    # 日志
    logEnabled = ConfigItem("Log", "logEnabled", True)


cfg = AppConfig()
config_file = os.path.join(get_app_data_dir(), "config.json")
qconfig.load(config_file, cfg)


def sync_theme_from_cfg():
    """启动时应用 cfg 中保存的主题。cfg.themeMode 与 qconfig.themeMode 同源。"""
    from qfluentwidgets import setTheme
    setTheme(cfg.get(cfg.themeMode))


def sync_theme_to_cfg():
    """主题变更后持久化到配置文件（cfg.themeMode 与 qconfig.themeMode 为同一项）。"""
    qconfig.save()
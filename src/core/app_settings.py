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

    # 新手教程：是否已完成/关闭（False 时下次启动会弹出询问）
    tutorialDone = ConfigItem("App", "tutorialDone", False)

    # 更新：启动时自动检查 GitHub Release 是否有新版本（默认开启）
    autoCheckUpdate = ConfigItem("App", "autoCheckUpdate", True)


cfg = AppConfig()
config_file = os.path.join(get_app_data_dir(), "config.json")
qconfig.load(config_file, cfg)


def _ensure_default_theme_mode():
    """首次运行（配置文件中未保存过主题模式）时默认「跟随系统」。

    必须读取配置文件判断，而非 qconfig 内存值：qconfig.load 会用默认值
    初始化内存，无法区分「文件里没有该键」与「用户明确保存了浅色」。
    已保存过主题模式的用户保持其原有选择。
    """
    import json
    from qfluentwidgets import Theme

    try:
        with open(config_file, encoding='utf-8') as f:
            saved = json.load(f)
    except Exception:
        saved = {}
    group = saved.get('QFluentWidgets')
    if not isinstance(group, dict) or 'ThemeMode' not in group:
        qconfig.set(qconfig.themeMode, Theme.AUTO)


_ensure_default_theme_mode()


def sync_theme_from_cfg():
    """启动时应用 cfg 中保存的主题。cfg.themeMode 与 qconfig.themeMode 同源。"""
    from qfluentwidgets import setTheme
    setTheme(cfg.get(cfg.themeMode))


def sync_theme_to_cfg():
    """主题变更后持久化到配置文件（cfg.themeMode 与 qconfig.themeMode 为同一项）。"""
    qconfig.save()
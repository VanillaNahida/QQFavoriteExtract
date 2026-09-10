# coding=utf-8
"""主题常量与切换辅助。"""

from qfluentwidgets import Theme, setTheme, setThemeColor

# 品牌主题色（沿用原界面主色 #05B8CC）
BRAND_COLOR = "#05B8CC"


def apply_theme(theme: Theme):
    """应用主题（浅色/深色/跟随系统）"""
    setTheme(theme)


def apply_brand_color(color: str = BRAND_COLOR):
    """应用品牌主题色"""
    setThemeColor(color)

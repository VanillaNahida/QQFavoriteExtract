# coding=utf-8
"""新手教程：首次使用引导（TeachingTip 气泡序列）。

首次启动时询问用户是否查看；确认后以气泡弹窗形式逐项介绍
软件各功能按钮。设置页可重置 tutorialDone 标记，重启后重温。
"""

from dataclasses import dataclass

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from qfluentwidgets import (PrimaryPushButton, PushButton, TeachingTip,
                            TeachingTipTailPosition, TeachingTipView)

from src.core.app_settings import cfg


@dataclass
class TutorialStep:
    """一个教学气泡步骤：指向的控件、标题、正文、尾巴朝向。"""
    target: QWidget
    title: str
    content: str
    tail: TeachingTipTailPosition = TeachingTipTailPosition.TOP


class TutorialTipView(TeachingTipView):
    """带「下一步 / 跳过」按钮的教学气泡。"""

    nextClicked = pyqtSignal()
    skipClicked = pyqtSignal()

    def __init__(self, title, content, next_text, tail_position):
        super().__init__(title, content, isClosable=False, tailPosition=tail_position)

        # 基类按屏幕宽度预换行，与气泡固定宽度不匹配会导致长文本被裁切。
        # 这里恢复原始文本并开启 wordWrap，按气泡实际宽度自动换行，高度自适应。
        self.titleLabel.setText(title)
        self.titleLabel.setWordWrap(True)
        self.contentLabel.setText(content)
        self.contentLabel.setWordWrap(True)

        btn_row = QWidget(self)
        row = QHBoxLayout(btn_row)
        row.setContentsMargins(12, 8, 12, 12)
        row.setSpacing(8)
        self.skip_button = PushButton('跳过教程', btn_row)
        self.next_button = PrimaryPushButton(next_text, btn_row)
        self.next_button.setFixedWidth(96)
        row.addStretch()
        row.addWidget(self.skip_button)
        row.addWidget(self.next_button)

        self.addWidget(btn_row)
        self.skip_button.clicked.connect(self.skipClicked)
        self.next_button.clicked.connect(self.nextClicked)
        self.setFixedWidth(360)


class NewbieTutorial(QObject):
    """教学气泡序列控制器：串行展示步骤，支持跳过。"""

    def __init__(self, window, steps, on_finished=None):
        super().__init__(window)
        self.window = window
        self.steps = list(steps)
        self._index = 0
        self._tip = None
        self.on_finished = on_finished

    def start(self):
        self._index = 0
        self._show_step()

    def _show_step(self):
        if self._index >= len(self.steps):
            self._finish()
            return
        step = self.steps[self._index]
        is_last = self._index == len(self.steps) - 1
        view = TutorialTipView(step.title, step.content,
                               '完成' if is_last else '下一步', step.tail)
        view.nextClicked.connect(self._on_next)
        view.skipClicked.connect(self._on_skip)
        self._tip = TeachingTip.make(view, step.target, -1, step.tail, self.window)

    def _on_next(self):
        if self._tip is not None:
            self._tip.close()
            self._tip = None
        self._index += 1
        self._show_step()

    def _on_skip(self):
        if self._tip is not None:
            self._tip.close()
            self._tip = None
        self._finish()

    def _finish(self):
        cfg.set(cfg.tutorialDone, True)
        if self.on_finished:
            self.on_finished()
        self.deleteLater()


def run_newbie_tutorial(window, on_finished=None):
    """在 window（MainWindow）上串行展示新手教程气泡。"""
    ws = window.workspace_view
    # 确保配置面板展开，扫描按钮等目标控件可见
    if not ws.config_card.isVisible():
        ws._expand_config()

    steps = [
        TutorialStep(window.theme_button, '切换深浅色主题',
                     '点击标题栏右侧此按钮，可在浅色与深色主题之间切换。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.config_collapse_button, '展开 / 收起配置面板',
                     '点击此按钮可展开或收起上方配置面板，随时调整数据路径、用户与分类。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.user_combo, '选择用户',
                     '在这里选择要提取表情的QQ账号，昵称会自动回填显示。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.category_combo, '选择分类',
                     '选择表情包分类；选择「个人收藏表情」可提取聊天中添加收藏的表情包。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.scan_button, '扫描表情包',
                     '点击开始扫描所选分类，完成后自动在下方预览区展示全部表情。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.preview_card, '预览区',
                     '右键可排序与快捷多选；单击查看详情与动图，双击打开大图窗口。',
                     TeachingTipTailPosition.BOTTOM),
        TutorialStep(ws.detail_toggle_button, '展开 / 收起表情详细面板',
                     '单击预览区表情后，右侧会显示大图、动图与属性信息；点击导出栏右侧此按钮可随时展开或收起详情面板。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(ws.export_selected_button, '导出表情',
                     '先点选或框选多个表情，再点击「导出选中表情」批量导出；右侧按钮导出全部。',
                     TeachingTipTailPosition.TOP),
        TutorialStep(window.navigationInterface, '页面导航',
                     '左侧导航栏可随时切换工作台、日志、设置与关于页面。',
                     TeachingTipTailPosition.LEFT),
    ]

    controller = NewbieTutorial(window, steps, on_finished)
    # 等配置面板展开动画结束后再弹出第一个气泡，避免目标控件位置偏移
    QTimer.singleShot(400, controller.start)
    return controller

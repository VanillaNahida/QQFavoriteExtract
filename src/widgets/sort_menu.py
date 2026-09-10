# coding=utf-8
"""排序/操作右键菜单构建（RoundMenu + CheckableMenu）。"""

from qfluentwidgets import (Action, CheckableMenu, FluentIcon as FIF,
                            MenuIndicatorType, RoundMenu)

SORT_KEYS = [
    ('name', '文件名称'),
    ('size', '文件大小'),
    ('mtime', '修改时间'),
    ('type', '文件类型'),
]


def _radio_group(actions):
    """让一组 checkable action 表现为单选（点击一个取消其余）。"""
    def on_triggered(current):
        for action in actions:
            action.setChecked(action is current)
    for action in actions:
        action.triggered.connect(lambda checked=False, a=action: on_triggered(a))


def build_context_menu(widget, callbacks):
    """
    构建预览区右键菜单。

    :param widget: 宿主控件（用于菜单父对象与读取当前排序状态）
    :param callbacks: 回调字典：
        on_sort(key, order)
        on_select_all() / on_invert() / on_clear_selection()
        on_select_animated() / on_select_static()
        on_extract_current() / on_extract_selected()
        on_open_folder()
    """
    menu = RoundMenu(parent=widget)

    # ---- 排序子菜单 ----
    sort_menu = RoundMenu('排序', widget)
    sort_menu.setIcon(FIF.FILTER)

    way_menu = CheckableMenu('排序方式', widget, indicatorType=MenuIndicatorType.RADIO)
    way_actions = []
    for key, label in SORT_KEYS:
        action = Action(label, checkable=True, checked=(widget.sort_key == key))
        action.triggered.connect(
            lambda checked=False, k=key: callbacks['on_sort'](k, widget.sort_order))
        way_actions.append(action)
    way_menu.addActions(way_actions)
    _radio_group(way_actions)

    dir_menu = CheckableMenu('排序方向', widget, indicatorType=MenuIndicatorType.RADIO)
    asc_action = Action('升序', checkable=True, checked=(widget.sort_order == 'asc'))
    desc_action = Action('降序', checkable=True, checked=(widget.sort_order == 'desc'))
    asc_action.triggered.connect(
        lambda checked=False: callbacks['on_sort'](widget.sort_key, 'asc'))
    desc_action.triggered.connect(
        lambda checked=False: callbacks['on_sort'](widget.sort_key, 'desc'))
    dir_menu.addActions([asc_action, desc_action])
    _radio_group([asc_action, desc_action])

    sort_menu.addMenu(way_menu)
    sort_menu.addMenu(dir_menu)
    menu.addMenu(sort_menu)
    menu.addSeparator()

    # ---- 快捷多选 ----
    select_all = Action(FIF.CHECKBOX, '全选已加载', shortcut='Ctrl+A')
    select_all.triggered.connect(callbacks['on_select_all'])
    menu.addAction(select_all)

    invert = Action(FIF.SYNC, '反选选择')
    invert.triggered.connect(callbacks['on_invert'])
    menu.addAction(invert)

    clear_sel = Action(FIF.CLEAR_SELECTION, '清空选择', shortcut='Ctrl+D')
    clear_sel.triggered.connect(callbacks['on_clear_selection'])
    menu.addAction(clear_sel)

    only_animated = Action(FIF.MOVIE, '仅选动图')
    only_animated.triggered.connect(callbacks['on_select_animated'])
    menu.addAction(only_animated)

    only_static = Action(FIF.PHOTO, '仅选静态图')
    only_static.triggered.connect(callbacks['on_select_static'])
    menu.addAction(only_static)

    menu.addSeparator()

    # ---- 提取操作 ----
    selected_count = len(widget.selectedItems())

    extract_current = Action(FIF.DOWNLOAD, '提取当前表情')
    extract_current.triggered.connect(callbacks['on_extract_current'])
    if widget.currentItem() is None:
        extract_current.setEnabled(False)
    menu.addAction(extract_current)

    extract_selected = Action(FIF.IMAGE_EXPORT, f'提取所选表情 ({selected_count})')
    extract_selected.triggered.connect(callbacks['on_extract_selected'])
    extract_selected.setEnabled(selected_count > 0)
    menu.addAction(extract_selected)

    open_folder = Action(FIF.FOLDER, '定位文件')
    open_folder.triggered.connect(callbacks['on_open_folder'])
    menu.addAction(open_folder)

    return menu

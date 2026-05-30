"""SVG 图标加载工具。"""

import os
from PySide6.QtGui import QIcon


_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icons")


def load_icon(name: str) -> QIcon:
    """加载 resources/icons/ 下的 SVG 图标。"""
    path = os.path.join(_ICON_DIR, name)
    if os.path.exists(path):
        return QIcon(path)
    return QIcon()

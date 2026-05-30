#!/usr/bin/env python3
"""PySide6 + python-mpv 视频播放器入口。"""

import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.model.config import ConfigManager
from app.view.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    """加载 QSS 主题样式。"""
    qss_path = os.path.join(os.path.dirname(__file__), "resources", "styles", "theme.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    # 高 DPI 支持（Qt6 默认启用，但显式设置确保行为一致）
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("视频播放器")
    app.setOrganizationName("MediaPlayer")

    # 字体设置
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 加载主题
    load_stylesheet(app)

    # 加载配置
    config = ConfigManager.load()

    # 创建主窗口
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

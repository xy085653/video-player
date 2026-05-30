# app/view/volume_widget.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton)

from app.signals.bus import player_signals
from app.view.icon_helper import load_icon
from app.view.seek_slider import SeekSlider


class VolumeWidget(QWidget):
    """音量按钮 + 滑块组合控件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 50
        self._muted = False

        self._btn = QPushButton()
        self._btn.setFixedSize(32, 32)
        self._btn.setIconSize(QSize(20, 20))
        self._btn.setToolTip("音量 (M 键静音)")
        self._btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #ddd;
            }
            QPushButton:hover { color: #fff; }
        """)

        self._slider = SeekSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(50)
        self._slider.setFixedWidth(100)
        self._slider.setFixedHeight(20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._btn)
        layout.addWidget(self._slider)
        layout.addStretch()

        self._btn.clicked.connect(self._on_button_clicked)
        self._slider.valueChanged.connect(self._on_slider_changed)

        player_signals.volume_changed.connect(self._on_volume_changed)
        player_signals.muted_changed.connect(self._on_muted_changed)

        self._update_icon()

    def _on_button_clicked(self):
        if hasattr(self, '_controller'):
            self._controller.toggle_mute()

    def _on_slider_changed(self, value: int):
        if hasattr(self, '_controller'):
            self._controller.set_volume(value)

    def _on_volume_changed(self, vol: int):
        self._volume = vol
        self._slider.blockSignals(True)
        self._slider.setValue(vol)
        self._slider.blockSignals(False)
        self._update_icon()

    def _on_muted_changed(self, muted: bool):
        self._muted = muted
        self._update_icon()

    def _update_icon(self):
        if self._muted or self._volume == 0:
            name = "volume_mute"
        elif self._volume < 35:
            name = "volume_low"
        elif self._volume < 70:
            name = "volume_medium"
        else:
            name = "volume_high"
        self._btn.setIcon(load_icon(f"{name}.svg"))

    def set_controller(self, controller):
        self._controller = controller

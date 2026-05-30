# app/view/control_bar.py
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QFont
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QSlider, QLabel,
                               QMenu, QSizePolicy)

from app.signals.bus import player_signals
from app.view.volume_widget import VolumeWidget
from app.model.playlist_model import PlaylistModel


PLAY_MODE_SYMBOLS = {
    0: "➡️",   # SEQUENTIAL
    1: "🔁",   # LOOP_ALL
    2: "🔂",   # LOOP_ONE
    3: "🔀",   # SHUFFLE
}

PLAY_MODE_TOOLTIPS = {
    0: "顺序播放",
    1: "列表循环",
    2: "单曲循环",
    3: "随机播放",
}


class ControlBar(QWidget):
    """双行分离式底部控制栏。"""

    SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._dragging = False
        self._duration = 0.0
        self._sub_tracks = []
        self._audio_tracks = []
        self._speed_index = 2  # 1.0x
        self._play_mode = PlaylistModel.PlayMode.LOOP_ALL

        self.setFixedHeight(80)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 6)
        layout.setSpacing(4)

        # ── 第 1 行：进度条 + 时间 ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setFixedWidth(140)
        self._time_label.setAlignment(Qt.AlignCenter)
        self._time_label.setStyleSheet("color: #aaa; font-size: 12px;")

        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #444;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: #6c63ff;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c63ff, stop:1 #8b83ff);
                border-radius: 2px;
            }
        """)
        self._seek_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        row1.addWidget(self._time_label)
        row1.addWidget(self._seek_slider)

        # ── 第 2 行：控制按钮 ──
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 18px;
                padding: 4px 8px;
                color: #ddd;
            }
            QPushButton:hover { color: #fff; }
            QPushButton:pressed { color: #6c63ff; }
        """

        self._prev_btn = QPushButton("⏮")
        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedWidth(40)
        self._play_btn.setStyleSheet("""
            QPushButton {
                background: #6c63ff;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                padding: 4px 14px;
                color: white;
                min-height: 30px;
            }
            QPushButton:hover { background: #7b73ff; }
            QPushButton:pressed { background: #5b53ef; }
        """)
        self._next_btn = QPushButton("⏭")
        self._stop_btn = QPushButton("⏹")

        for btn in (self._prev_btn, self._play_btn, self._next_btn, self._stop_btn):
            btn.setFixedHeight(34)
            if btn != self._play_btn:
                btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)

        # 音量控件
        self._volume_widget = VolumeWidget()

        # 倍速
        self._speed_btn = QPushButton("1.0x")
        self._speed_btn.setStyleSheet(btn_style)
        self._speed_btn.setFixedWidth(48)
        self._speed_btn.setToolTip("点击切换倍速")

        # 字幕按钮
        self._sub_btn = QPushButton("📄")
        self._sub_btn.setStyleSheet(btn_style)
        self._sub_btn.setToolTip("字幕轨道")

        # 音轨按钮
        self._audio_btn = QPushButton("🎤")
        self._audio_btn.setStyleSheet(btn_style)
        self._audio_btn.setToolTip("音轨切换")

        # 截图
        self._screenshot_btn = QPushButton("📷")
        self._screenshot_btn.setStyleSheet(btn_style)
        self._screenshot_btn.setToolTip("截图 (S 键)")

        # 播放模式
        self._mode_btn = QPushButton(PLAY_MODE_SYMBOLS[self._play_mode])
        self._mode_btn.setStyleSheet(btn_style)
        self._mode_btn.setToolTip(PLAY_MODE_TOOLTIPS[self._play_mode])

        # 全屏
        self._fullscreen_btn = QPushButton("⛶")
        self._fullscreen_btn.setStyleSheet(btn_style)
        self._fullscreen_btn.setToolTip("全屏 (F 键)")

        # 组装第 2 行
        row2.addWidget(self._prev_btn)
        row2.addWidget(self._play_btn)
        row2.addWidget(self._next_btn)
        row2.addWidget(self._stop_btn)

        row2.addSpacing(12)
        row2.addWidget(self._volume_widget)

        row2.addSpacing(12)
        row2.addWidget(self._speed_btn)

        row2.addSpacing(8)
        row2.addWidget(self._sub_btn)
        row2.addWidget(self._audio_btn)
        row2.addWidget(self._screenshot_btn)
        row2.addWidget(self._mode_btn)

        row2.addStretch()
        row2.addWidget(self._fullscreen_btn)

        layout.addLayout(row1)
        layout.addLayout(row2)

        # ── 信号连接 ──
        self._seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self._seek_slider.sliderMoved.connect(self._on_seek_moved)
        self._seek_slider.sliderReleased.connect(self._on_seek_released)

        self._prev_btn.clicked.connect(self._on_prev)
        self._play_btn.clicked.connect(self._on_play)
        self._next_btn.clicked.connect(self._on_next)
        self._stop_btn.clicked.connect(self._on_stop)
        self._speed_btn.clicked.connect(self._on_speed)
        self._mode_btn.clicked.connect(self._on_mode)
        self._fullscreen_btn.clicked.connect(self._on_fullscreen)
        self._screenshot_btn.clicked.connect(self._on_screenshot)
        self._sub_btn.clicked.connect(self._on_sub_menu)
        self._audio_btn.clicked.connect(self._on_audio_menu)

        # 信号总线
        player_signals.position_changed.connect(self._on_position)
        player_signals.duration_changed.connect(self._on_duration)
        player_signals.play_state_changed.connect(self._on_play_state)
        player_signals.speed_changed.connect(self._on_speed_changed)
        player_signals.play_mode_changed.connect(self._on_play_mode_changed)
        player_signals.subtitle_tracks.connect(self._on_subtitle_tracks)
        player_signals.audio_tracks.connect(self._on_audio_tracks)
        player_signals.file_loaded.connect(lambda _: self._on_position(0))

    def set_controller(self, controller):
        self._controller = controller
        self._volume_widget.set_controller(controller)

    # ── 进度条 ──

    def _on_seek_pressed(self):
        self._dragging = True

    def _on_seek_moved(self, value: int):
        ratio = value / 1000.0
        self._time_label.setText(f"--- / ---")

    def _on_seek_released(self):
        self._dragging = False
        if self._controller:
            ratio = self._seek_slider.value() / 1000.0
            seconds = ratio * self._duration
            self._controller.seek(seconds)

    def _on_position(self, seconds: float):
        if self._dragging:
            return
        # 需要总时长来算进度
        self._seek_slider.blockSignals(True)
        if self._duration > 0 and seconds >= 0:
            ratio = min(1.0, seconds / self._duration)
            self._seek_slider.setValue(int(ratio * 1000))
        self._seek_slider.blockSignals(False)

    def _on_duration(self, duration: float):
        self._duration = duration
        cur = 0
        if self._controller:
            try:
                cur = self._controller.mpv.time_pos or 0
            except Exception:
                cur = 0
        self._time_label.setText(f"{self._fmt_time(cur)} / {self._fmt_time(duration)}")

    def _on_play_state(self, playing: bool):
        self._play_btn.setText("⏸" if playing else "▶")

    # ── 按钮点击 ──

    def _on_play(self):
        if self._controller:
            self._controller.toggle_play()

    def _on_prev(self):
        if self._controller:
            self._controller.prev_track()

    def _on_next(self):
        if self._controller:
            self._controller.next_track()

    def _on_stop(self):
        if self._controller:
            self._controller.stop()

    def _on_speed(self):
        self._speed_index = (self._speed_index + 1) % len(self.SPEEDS)
        rate = self.SPEEDS[self._speed_index]
        if self._controller:
            self._controller.set_speed(rate)

    def _on_mode(self):
        if self._controller:
            self._controller.cycle_play_mode()

    def _on_fullscreen(self):
        # MainWindow 会连接这个信号
        self._fullscreen_btn.setText("⛶")
        player_signals.fullscreen_changed.emit(True)

    def _on_screenshot(self):
        if self._controller:
            import os
            save_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "screenshots")
            self._controller.screenshot(save_dir)

    def _on_sub_menu(self):
        if not self._sub_tracks:
            return
        menu = QMenu(self)
        for t in self._sub_tracks:
            action = menu.addAction(f"{t['title']} ({t['lang']})" if t['lang'] else t['title'])
            action.setData(t['id'])
            action.triggered.connect(lambda checked, tid=t['id']: self._controller.set_subtitle_track(tid))
        menu.exec(self._sub_btn.mapToGlobal(self._sub_btn.rect().bottomLeft()))

    def _on_audio_menu(self):
        if not self._audio_tracks:
            return
        menu = QMenu(self)
        for t in self._audio_tracks:
            action = menu.addAction(f"{t['title']} ({t['lang']})" if t['lang'] else t['title'])
            action.setData(t['id'])
            action.triggered.connect(lambda checked, tid=t['id']: self._controller.set_audio_track(tid))
        menu.exec(self._audio_btn.mapToGlobal(self._audio_btn.rect().bottomLeft()))

    # ── 信号响应 ──

    def _on_speed_changed(self, rate: float):
        self._speed_btn.setText(f"{rate:.2f}x".rstrip("0").rstrip(".") + "x" if rate != 1.0 else "1.0x")

    def _on_play_mode_changed(self, mode: int):
        self._play_mode = mode
        self._mode_btn.setText(PLAY_MODE_SYMBOLS.get(mode, "🔁"))
        self._mode_btn.setToolTip(PLAY_MODE_TOOLTIPS.get(mode, ""))

    def _on_subtitle_tracks(self, tracks: list):
        self._sub_tracks = tracks

    def _on_audio_tracks(self, tracks: list):
        self._audio_tracks = tracks

    # ── 工具 ──

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        h, m = divmod(seconds, 3600)
        m, s = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ── 公开接口 ──

    def update_duration(self, duration: float):
        self._duration = duration

    @property
    def play_btn(self):
        return self._play_btn

    @property
    def fullscreen_btn(self):
        return self._fullscreen_btn

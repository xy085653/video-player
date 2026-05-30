# app/view/video_widget.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from mpv import MPV

from app.signals.bus import player_signals


class VideoWidget(QWidget):
    """将 mpv 渲染嵌入 Qt 窗口的视频显示控件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setMinimumSize(320, 180)
        self.setStyleSheet("background-color: #000;")

        self._mpv: MPV | None = None
        self._error_label = QLabel("等待文件打开...", self)
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.setStyleSheet("color: #666; font-size: 14px;")

    def init_mpv(self) -> MPV:
        """初始化 mpv 实例并嵌入到当前窗口。必须在 winId() 可用后调用。"""
        self._mpv = MPV(
            wid=str(int(self.winId())),
            vo="gpu",
            hwdec="auto",
            keepaspect=True,
            cache="yes",
            demuxer_max_bytes="150e6",
            osc="no",          # 用自绘控制栏，关闭 mpv OSD
            osd_level="0",
            input_default="no",
        )

        # 注册属性监听
        self._mpv.observe_property("time-pos", self._on_time_pos)
        self._mpv.observe_property("duration", self._on_duration)
        self._mpv.observe_property("pause", self._on_pause)
        self._mpv.observe_property("track-list", self._on_track_list)
        self._mpv.observe_property("volume", self._on_volume)
        self._mpv.observe_property("mute", self._on_mute)

        # 注册事件回调
        self._mpv.register_event_callback(self._on_event)

        return self._mpv

    @property
    def mpv(self) -> MPV:
        return self._mpv

    def _on_time_pos(self, name, value):
        if value is not None:
            player_signals.position_changed.emit(float(value))

    def _on_duration(self, name, value):
        if value is not None:
            player_signals.duration_changed.emit(float(value))

    def _on_pause(self, name, value):
        if value is not None:
            player_signals.play_state_changed.emit(not bool(value))

    def _on_volume(self, name, value):
        if value is not None:
            player_signals.volume_changed.emit(int(value))

    def _on_mute(self, name, value):
        if value is not None:
            player_signals.muted_changed.emit(bool(value))

    def _on_track_list(self, name, value):
        if value is None:
            return
        subs = []
        audios = []
        for track in value:
            if track.get("type") == "sub":
                subs.append({
                    "id": track.get("id"),
                    "title": track.get("title", track.get("lang", f"字幕 {track.get('id')}")),
                    "lang": track.get("lang", ""),
                })
            elif track.get("type") == "audio":
                audios.append({
                    "id": track.get("id"),
                    "title": track.get("title", track.get("lang", f"音轨 {track.get('id')}")),
                    "lang": track.get("lang", ""),
                })
        if subs:
            player_signals.subtitle_tracks.emit(subs)
        if audios:
            player_signals.audio_tracks.emit(audios)

    def _on_event(self, event):
        if event.get("event") == "end-file":
            reason = event.get("reason")
            if reason == "eof":
                player_signals.eos_reached.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._error_label:
            self._error_label.setGeometry(self.rect())

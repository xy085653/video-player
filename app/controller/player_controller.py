# app/controller/player_controller.py
import os
from typing import Optional

from mpv import MPV

from app.signals.bus import player_signals
from app.model.playlist_model import PlaylistModel


class PlayerController:
    """播放控制器，封装所有 mpv 操作，通过信号通知视图。"""

    def __init__(self, mpv: MPV, playlist: PlaylistModel):
        self._mpv = mpv
        self._playlist = playlist

    @property
    def mpv(self) -> MPV:
        return self._mpv

    # ── 文件操作 ──

    def load_file(self, path: str) -> None:
        if not os.path.exists(path):
            return
        self._mpv.play(path)
        self._playlist.add_file(path)
        player_signals.file_loaded.emit(path)

    def play_index(self, index: int) -> None:
        item = self._playlist.items[index] if 0 <= index < len(self._playlist.items) else None
        if item:
            self._playlist.set_current(index)
            self.load_file(item.path)

    # ── 播放控制 ──

    def toggle_play(self) -> None:
        self._mpv.pause = not self._mpv.pause

    def stop(self) -> None:
        self._mpv.stop()

    def seek(self, seconds: float, relative: bool = False) -> None:
        flag = "relative" if relative else "absolute"
        self._mpv.command("seek", str(seconds), flag)

    def set_speed(self, rate: float) -> None:
        rate = max(0.25, min(8.0, rate))
        self._mpv.speed = rate
        player_signals.speed_changed.emit(rate)

    # ── 上一曲 / 下一曲 ──

    def next_track(self) -> None:
        nxt = self._playlist.next_index()
        if nxt >= 0:
            self.play_index(nxt)

    def prev_track(self) -> None:
        prv = self._playlist.prev_index()
        if prv >= 0:
            self.play_index(prv)

    # ── 音量 ──

    def set_volume(self, vol: int) -> None:
        self._mpv.volume = max(0, min(100, vol))

    def toggle_mute(self) -> None:
        self._mpv.mute = not self._mpv.mute

    # ── 音轨/字幕 ──

    def cycle_subtitle(self, direction: int = 1) -> None:
        self._mpv.command("cycle", "sub", str(direction))

    def set_subtitle_track(self, track_id: int) -> None:
        self._mpv.sid = track_id
        player_signals.subtitle_track_changed.emit(track_id)

    def cycle_audio(self, direction: int = 1) -> None:
        self._mpv.command("cycle", "audio", str(direction))

    def set_audio_track(self, track_id: int) -> None:
        self._mpv.aid = track_id
        player_signals.audio_track_changed.emit(track_id)

    # ── 截图 ──

    def screenshot(self, save_dir: str) -> Optional[str]:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"screenshot_{int(__import__('time').time())}.png")
        self._mpv.command("screenshot-to-file", path)
        player_signals.screenshot_taken.emit(path)
        return path

    # ── 播放模式 ──

    def cycle_play_mode(self) -> None:
        from app.model.playlist_model import PlaylistModel
        modes = list(PlaylistModel.PlayMode)
        cur = self._playlist.mode
        idx = (modes.index(cur) + 1) % len(modes)
        self._playlist.mode = modes[idx]

# app/model/playlist_model.py
import os
import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from PySide6.QtCore import QObject
from app.signals.bus import player_signals


@dataclass
class PlaylistItem:
    path: str
    name: str = ""
    duration: float = 0.0
    thumbnail: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = os.path.basename(self.path)


class PlaylistModel(QObject):
    """播放列表数据模型，管理播放项和播放模式。"""

    class PlayMode(IntEnum):
        SEQUENTIAL = 0
        LOOP_ALL = 1
        LOOP_ONE = 2
        SHUFFLE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: list[PlaylistItem] = []
        self.current_index: int = -1
        self._mode: PlaylistModel.PlayMode = PlaylistModel.PlayMode.LOOP_ALL
        self._shuffle_order: list[int] = []   # 随机播放时的索引序列
        self._shuffle_pos: int = 0

    @property
    def mode(self) -> "PlaylistModel.PlayMode":
        return self._mode

    @mode.setter
    def mode(self, value: "PlaylistModel.PlayMode") -> None:
        self._mode = value
        self._rebuild_shuffle()
        player_signals.play_mode_changed.emit(value)

    def add_file(self, path: str) -> int:
        """添加单个文件，返回索引。重复路径跳过。"""
        for item in self.items:
            if item.path == path:
                return self.items.index(item)
        self.items.append(PlaylistItem(path=path))
        self._rebuild_shuffle()
        player_signals.playlist_changed.emit(self.items)
        return len(self.items) - 1

    def add_files(self, paths: list[str]) -> None:
        added = False
        for p in paths:
            if not any(item.path == p for item in self.items):
                self.items.append(PlaylistItem(path=p))
                added = True
        if added:
            self._rebuild_shuffle()
            player_signals.playlist_changed.emit(self.items)

    def remove(self, index: int) -> Optional[PlaylistItem]:
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                self.current_index = -1
            self._rebuild_shuffle()
            player_signals.playlist_changed.emit(self.items)
            return removed
        return None

    def move(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self.items) and 0 <= to_index < len(self.items):
            item = self.items.pop(from_index)
            self.items.insert(to_index, item)
            if self.current_index == from_index:
                self.current_index = to_index
            elif from_index < self.current_index <= to_index:
                self.current_index -= 1
            elif to_index <= self.current_index < from_index:
                self.current_index += 1
            self._rebuild_shuffle()
            player_signals.playlist_changed.emit(self.items)

    def set_current(self, index: int) -> bool:
        if 0 <= index < len(self.items):
            self.current_index = index
            player_signals.current_index_changed.emit(index)
            return True
        return False

    def get_current_item(self) -> Optional[PlaylistItem]:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def next_index(self) -> int:
        n = len(self.items)
        if n == 0:
            return -1
        match self._mode:
            case PM.LOOP_ONE:
                return self.current_index
            case PM.SHUFFLE:
                if self._shuffle_pos + 1 < len(self._shuffle_order):
                    self._shuffle_pos += 1
                else:
                    self._rebuild_shuffle()
                    self._shuffle_pos = 0
                return self._shuffle_order[self._shuffle_pos]
            case PM.SEQUENTIAL:
                nxt = self.current_index + 1
                return nxt if nxt < n else -1
            case PM.LOOP_ALL:
                return (self.current_index + 1) % n
            case _:
                return -1

    def prev_index(self) -> int:
        n = len(self.items)
        if n == 0:
            return -1
        match self._mode:
            case PM.LOOP_ONE:
                return self.current_index
            case PM.SHUFFLE:
                if self._shuffle_pos > 0:
                    self._shuffle_pos -= 1
                    return self._shuffle_order[self._shuffle_pos]
                return self.current_index
            case PM.SEQUENTIAL:
                prv = self.current_index - 1
                return prv if prv >= 0 else -1
            case PM.LOOP_ALL:
                return (self.current_index - 1) % n
            case _:
                return -1

    def clear(self) -> None:
        self.items.clear()
        self.current_index = -1
        self._rebuild_shuffle()
        player_signals.playlist_changed.emit(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def _rebuild_shuffle(self) -> None:
        n = len(self.items)
        self._shuffle_order = list(range(n))
        random.shuffle(self._shuffle_order)
        self._shuffle_pos = 0
        # 确保当前项在 shuffle 序列中的正确位置
        if self.current_index >= 0 and n > 0:
            try:
                pos = self._shuffle_order.index(self.current_index)
                self._shuffle_pos = pos
            except ValueError:
                pass


# Module-level alias for match/case patterns
PM = PlaylistModel.PlayMode

# app/model/history_model.py
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional

from app.model.config import DATA_DIR


HISTORY_PATH = os.path.join(DATA_DIR, "history.json")


@dataclass
class HistoryEntry:
    path: str
    name: str
    last_position: float = 0.0
    duration: float = 0.0
    timestamp: float = 0.0
    favorite: bool = False


class HistoryModel:
    """播放历史管理，自动持久化到 data/history.json。"""

    def __init__(self):
        self.entries: list[HistoryEntry] = []
        self._load()

    def record_stop(self, path: str, position: float, duration: float) -> None:
        """播放停止/切换时记录当前位置。"""
        if not path or position <= 0:
            return
        for entry in self.entries:
            if entry.path == path:
                entry.last_position = position
                entry.duration = duration
                entry.timestamp = time.time()
                self._save()
                return
        self.entries.append(HistoryEntry(
            path=path,
            name=os.path.basename(path),
            last_position=position,
            duration=duration,
            timestamp=time.time(),
        ))
        self._save()

    def get_resume_position(self, path: str, threshold: float = 30.0) -> float:
        """如果上次播放位置超过 threshold 秒，返回续播位置，否则返回 0。"""
        entry = self._find(path)
        if entry and entry.last_position > threshold:
            return entry.last_position
        return 0.0

    def toggle_favorite(self, path: str) -> bool:
        entry = self._find(path)
        if entry:
            entry.favorite = not entry.favorite
            self._save()
            return entry.favorite
        return False

    def remove_entry(self, path: str) -> None:
        self.entries = [e for e in self.entries if e.path != path]
        self._save()

    def get_all(self) -> list[HistoryEntry]:
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)

    def clear_all(self) -> None:
        self.entries.clear()
        self._save()

    def _find(self, path: str) -> Optional[HistoryEntry]:
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def _load(self) -> None:
        try:
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.entries = [HistoryEntry(**e) for e in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self.entries = []

    def _save(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(e) for e in self.entries],
                f, indent=2, ensure_ascii=False,
            )

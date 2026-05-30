# PySide6 + python-mpv 视频播放器 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个精美的桌面视频播放器，基于 PySide6 + python-mpv，支持经典布局、双行控制栏、分页式播放列表和历史记录。

**Architecture:** MVC + 信号总线模式。View 层通过 QSS 和 SVG 图标实现深色毛玻璃风格，通过 PlayerSignals 全局信号总线与 Controller 通信。Controller 封装所有 mpv 操作。Model 层处理播放列表、历史记录和配置的 JSON 持久化。

**Tech Stack:** PySide6 >= 6.6, python-mpv >= 1.0, mpv-1.dll (运行时), SVG 图标

---

## 文件结构

所有文件在项目根目录 `f:\deepseek-project\视频播放器\` 下：

```
.
├── main.py                          # 应用入口
├── requirements.txt                 # 依赖
├── resources/
│   └── styles/
│       └── theme.qss                # 全局样式表（深色毛玻璃）
├── app/
│   ├── __init__.py
│   ├── signals/
│   │   ├── __init__.py
│   │   └── bus.py                   # PlayerSignals 信号总线单例
│   ├── model/
│   │   ├── __init__.py
│   │   ├── config.py                # AppConfig + ConfigManager
│   │   ├── playlist_model.py        # PlaylistItem + PlaylistModel
│   │   └── history_model.py         # HistoryEntry + HistoryModel
│   ├── controller/
│   │   ├── __init__.py
│   │   └── player_controller.py     # PlayerController
│   └── view/
│       ├── __init__.py
│       ├── video_widget.py          # mpv 嵌入控件
│       ├── control_bar.py           # 双行控制栏
│       ├── playlist_panel.py        # 播放列表 + 历史 Tab
│       ├── volume_widget.py         # 音量按钮 + 滑块
│       └── main_window.py           # 主窗口组装
└── data/                            # 运行时数据目录（自动创建）
```

### 依赖关系图（自底向上）

```
signals/bus.py         → 无依赖
model/config.py        → 无依赖
model/playlist_model   → signals/bus (信号通知)
model/history_model    → 无依赖
view/video_widget      → 无直接依赖（纯 mpv 封装）
controller/*           → signals/bus, model/playlist_model
view/volume_widget     → signals/bus
view/control_bar       → signals/bus, view/volume_widget, controller
view/playlist_panel    → model/playlist_model, model/history_model, controller
view/main_window       → 所有 view 组件, controller, model 各模块
main.py                → view/main_window
```

---

### Task 1: 项目脚手架 + 依赖 + 信号总线

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/signals/__init__.py`
- Create: `app/signals/bus.py`
- Create: `app/model/__init__.py`
- Create: `app/controller/__init__.py`
- Create: `app/view/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
PySide6>=6.6.0
python-mpv>=1.0.0
```

- [ ] **Step 2: 创建包 `__init__.py` 文件**

所有包 init 文件为空文件，只需要让 Python 识别为包。

- [ ] **Step 3: 创建 PlayerSignals 信号总线**

```python
# app/signals/bus.py
from PySide6.QtCore import QObject, Signal


class PlayerSignals(QObject):
    """全局信号总线单例——View 和 Controller 之间通过信号通信。"""

    # 播放状态
    file_loaded = Signal(str)                     # path
    play_state_changed = Signal(bool)             # True=播放, False=暂停
    position_changed = Signal(float)              # 当前秒数
    duration_changed = Signal(float)              # 总时长秒数
    eos_reached = Signal()                        # 播放结束（触发下一曲）
    speed_changed = Signal(float)                 # 倍速变更

    # 播放列表
    playlist_changed = Signal(list)               # list[PlaylistItem]
    current_index_changed = Signal(int)           # -1 表示无播放项

    # 音量
    volume_changed = Signal(int)                  # 0-100
    muted_changed = Signal(bool)

    # 音轨/字幕
    subtitle_tracks = Signal(list)                # list[dict]
    audio_tracks = Signal(list)                   # list[dict]
    subtitle_track_changed = Signal(int)
    audio_track_changed = Signal(int)

    # 播放模式
    play_mode_changed = Signal(int)               # PlayMode 枚举值

    # 截图
    screenshot_taken = Signal(str)                # 截图保存路径

    # 全屏
    fullscreen_changed = Signal(bool)


# 模块级单例——整个应用共享同一个实例
player_signals = PlayerSignals()
```

- [ ] **Step 4: 创建 data/ 目录**

```bash
mkdir -p "f:/deepseek-project/视频播放器/data"
```

- [ ] **Step 5: Commit**

```bash
cd f:/deepseek-project/视频播放器
git init
git add requirements.txt app/__init__.py app/signals/ data/
git commit -m "chore: project scaffold with signal bus"
```

---

### Task 2: ConfigManager 模型

**Files:**
- Create: `app/model/config.py`

- [ ] **Step 1: 实现 AppConfig 和 ConfigManager**

```python
# app/model/config.py
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


@dataclass
class AppConfig:
    volume: int = 50
    speed: float = 1.0
    play_mode: int = 1          # PlayMode.LOOP_ALL
    window_geometry: str = ""   # QByteArray hex
    window_state: str = ""      # QByteArray hex
    last_dir: str = ""
    subtitle_enabled: bool = True
    remember_position: bool = True
    splitter_position: int = 300  # 播放列表宽度（像素）


class ConfigManager:
    @classmethod
    def load(cls) -> AppConfig:
        try:
            if not os.path.exists(CONFIG_PATH):
                return AppConfig()
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return AppConfig()

    @classmethod
    def save(cls, config: AppConfig) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Commit**

```bash
git add app/model/config.py app/model/__init__.py
git commit -m "feat: add AppConfig dataclass and ConfigManager"
```

---

### Task 3: PlaylistModel 模型

**Files:**
- Create: `app/model/playlist_model.py`

- [ ] **Step 1: 实现 PlaylistItem 和 PlaylistModel**

```python
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
        self._mode: PlayMode = PlayMode.LOOP_ALL
        self._shuffle_order: list[int] = []   # 随机播放时的索引序列
        self._shuffle_pos: int = 0

    @property
    def mode(self) -> PlayMode:
        return self._mode

    @mode.setter
    def mode(self, value: PlayMode) -> None:
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
            case PlayMode.LOOP_ONE:
                return self.current_index
            case PlayMode.SHUFFLE:
                if self._shuffle_pos + 1 < len(self._shuffle_order):
                    self._shuffle_pos += 1
                else:
                    self._rebuild_shuffle()
                    self._shuffle_pos = 0
                return self._shuffle_order[self._shuffle_pos]
            case PlayMode.SEQUENTIAL:
                nxt = self.current_index + 1
                return nxt if nxt < n else -1
            case PlayMode.LOOP_ALL:
                return (self.current_index + 1) % n
            case _:
                return -1

    def prev_index(self) -> int:
        n = len(self.items)
        if n == 0:
            return -1
        match self._mode:
            case PlayMode.LOOP_ONE:
                return self.current_index
            case PlayMode.SHUFFLE:
                if self._shuffle_pos > 0:
                    self._shuffle_pos -= 1
                    return self._shuffle_order[self._shuffle_pos]
                return self.current_index
            case PlayMode.SEQUENTIAL:
                prv = self.current_index - 1
                return prv if prv >= 0 else -1
            case PlayMode.LOOP_ALL:
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
```

- [ ] **Step 2: Commit**

```bash
git add app/model/playlist_model.py
git commit -m "feat: add PlaylistModel with PlayMode and shuffle support"
```

---

### Task 4: HistoryModel 模型

**Files:**
- Create: `app/model/history_model.py`

- [ ] **Step 1: 实现 HistoryEntry 和 HistoryModel**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/model/history_model.py
git commit -m "feat: add HistoryModel with resume position and favorites"
```

---

### Task 5: VideoWidget — mpv 嵌入控件

**Files:**
- Create: `app/view/video_widget.py`

- [ ] **Step 1: 实现 VideoWidget**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/view/video_widget.py app/view/__init__.py
git commit -m "feat: add VideoWidget with mpv embedding"
```

---

### Task 6: PlayerController

**Files:**
- Create: `app/controller/player_controller.py`

- [ ] **Step 1: 实现 PlayerController**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/controller/player_controller.py app/controller/__init__.py
git commit -m "feat: add PlayerController with playback, tracks and screenshot"
```

---

### Task 7: VolumeWidget

**Files:**
- Create: `app/view/volume_widget.py`

- [ ] **Step 1: 实现音量控件**

```python
# app/view/volume_widget.py
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton,
                               QSlider, QVBoxLayout)

from app.signals.bus import player_signals


class VolumeWidget(QWidget):
    """音量按钮 + 弹出滑块组合控件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 50
        self._muted = False

        self._btn = QPushButton()
        self._btn.setFixedSize(32, 32)
        self._btn.setToolTip("音量 (M 键静音)")
        self._update_icon()

        self._slider = QSlider(Qt.Horizontal)
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

    def _on_button_clicked(self):
        self._controller.toggle_mute() if hasattr(self, '_controller') else None

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
            text = "🔇"
        elif self._volume < 35:
            text = "🔈"
        elif self._volume < 70:
            text = "🔉"
        else:
            text = "🔊"
        self._btn.setText(text)

    def set_controller(self, controller):
        self._controller = controller
```

- [ ] **Step 2: Commit**

```bash
git add app/view/volume_widget.py
git commit -m "feat: add VolumeWidget with mute btn and slider"
```

---

### Task 8: ControlBar

**Files:**
- Create: `app/view/control_bar.py`

- [ ] **Step 1: 实现控制栏**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/view/control_bar.py
git commit -m "feat: add ControlBar with two-row layout"
```

---

### Task 9: PlaylistPanel

**Files:**
- Create: `app/view/playlist_panel.py`

- [ ] **Step 1: 实现播放列表+历史面板**

```python
# app/view/playlist_panel.py
import os
from typing import Optional

from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QListWidget, QListWidgetItem,
                               QTabWidget, QLabel, QMenu, QMessageBox)

from app.signals.bus import player_signals
from app.model.playlist_model import PlaylistModel, PlaylistItem
from app.model.history_model import HistoryModel


class PlaylistPanel(QWidget):
    """分页式播放列表面板：「列表」和「历史」两个 Tab。"""

    def __init__(self, playlist_model: PlaylistModel, history_model: HistoryModel, parent=None):
        super().__init__(parent)
        self._playlist = playlist_model
        self._history = history_model
        self._controller = None

        self.setMinimumWidth(240)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()

        # ── Tab 1: 播放列表 ──
        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._on_list_context_menu)
        self._list_widget.itemDoubleClicked.connect(self._on_list_double_click)
        self._list_widget.setAcceptDrops(True)
        self._list_widget.setDragDropMode(QListWidget.InternalMove)
        self._list_widget.setDragEnabled(True)
        self._list_widget.setDefaultDropAction(Qt.MoveAction)
        self._list_widget.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical { width: 6px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        list_toolbar = QHBoxLayout()
        list_toolbar.setContentsMargins(4, 4, 4, 4)
        clear_btn = QPushButton("🗑 清空")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet("QPushButton { background: transparent; color: #aaa; font-size: 12px; border: 1px solid #444; border-radius: 4px; padding: 2px 8px; } QPushButton:hover { color: #ff6b6b; border-color: #ff6b6b; }")
        list_toolbar.addStretch()
        list_toolbar.addWidget(clear_btn)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addLayout(list_toolbar)
        list_layout.addWidget(self._list_widget)

        # ── Tab 2: 历史记录 ──
        self._history_widget = QListWidget()
        self._history_widget.setAlternatingRowColors(True)
        self._history_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_widget.customContextMenuRequested.connect(self._on_history_context_menu)
        self._history_widget.itemDoubleClicked.connect(self._on_history_double_click)
        self._history_widget.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical { width: 6px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        history_toolbar = QHBoxLayout()
        history_toolbar.setContentsMargins(4, 4, 4, 4)
        clear_history_btn = QPushButton("🗑 清除历史")
        clear_history_btn.setFixedHeight(24)
        clear_history_btn.setStyleSheet(clear_btn.styleSheet())
        history_toolbar.addStretch()
        history_toolbar.addWidget(clear_history_btn)

        history_container = QWidget()
        history_layout = QVBoxLayout(history_container)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(0)
        history_layout.addLayout(history_toolbar)
        history_layout.addWidget(self._history_widget)

        self._tabs.addTab(list_container, "📋 列表")
        self._tabs.addTab(history_container, "🕐 历史")

        layout.addWidget(self._tabs)

        # ── 信号 ──
        player_signals.playlist_changed.connect(self._refresh_playlist)
        player_signals.current_index_changed.connect(self._highlight_current)

        clear_btn.clicked.connect(self._on_clear_playlist)
        clear_history_btn.clicked.connect(self._on_clear_history)

        # 初始刷新
        self._refresh_playlist(self._playlist.items)
        self._refresh_history()

    def set_controller(self, controller):
        self._controller = controller

    # ── 播放列表 ──

    def _refresh_playlist(self, items: list):
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        for i, item in enumerate(items):
            text = f"{'▶ ' if i == self._playlist.current_index else '   '}{item.name}"
            li = QListWidgetItem(text)
            li.setData(Qt.UserRole, i)
            li.setToolTip(item.path)
            self._list_widget.addItem(li)
        self._list_widget.blockSignals(False)

    def _highlight_current(self, index: int):
        items = self._playlist.items
        self._refresh_playlist(items)

    def _on_list_double_click(self, item: QListWidgetItem):
        idx = item.data(Qt.UserRole)
        if idx is not None and self._controller:
            self._controller.play_index(idx)

    def _on_list_context_menu(self, pos):
        item = self._list_widget.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.UserRole)
        menu = QMenu(self)
        play_action = menu.addAction("▶ 播放")
        remove_action = menu.addAction("🗑 移除")
        if idx >= 0:
            real_item = self._playlist.items[idx]
            menu.addSection(os.path.basename(real_item.path))

        action = menu.exec(self._list_widget.mapToGlobal(pos))
        if action == play_action:
            if self._controller:
                self._controller.play_index(idx)
        elif action == remove_action:
            self._playlist.remove(idx)

    def _on_clear_playlist(self):
        if self._list_widget.count() == 0:
            return
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空播放列表吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._playlist.clear()

    # ── 历史记录 ──

    def _refresh_history(self):
        self._history_widget.blockSignals(True)
        self._history_widget.clear()
        for entry in self._history.get_all():
            fav = "⭐ " if entry.favorite else ""
            text = f"{fav}{entry.name}"
            li = QListWidgetItem(text)
            li.setData(Qt.UserRole, entry.path)
            pos_str = self._fmt_time(entry.last_position)
            dur_str = self._fmt_time(entry.duration)
            li.setToolTip(f"{entry.path}\n上次播放: {pos_str} / {dur_str}")
            self._history_widget.addItem(li)
        self._history_widget.blockSignals(False)

    def _on_history_double_click(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path and self._controller and os.path.exists(path):
            self._controller.load_file(path)

    def _on_history_context_menu(self, pos):
        item = self._history_widget.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)

        # 查找收藏状态
        is_fav = any(e.favorite for e in self._history.get_all() if e.path == path)

        menu = QMenu(self)
        play_action = menu.addAction("▶ 播放")
        fav_action = menu.addAction("⭐ 取消收藏" if is_fav else "☆ 收藏")
        remove_action = menu.addAction("🗑 删除记录")

        action = menu.exec(self._history_widget.mapToGlobal(pos))
        if action == play_action:
            if self._controller and os.path.exists(path):
                self._controller.load_file(path)
        elif action == fav_action:
            self._history.toggle_favorite(path)
            self._refresh_history()
        elif action == remove_action:
            self._history.remove_entry(path)
            self._refresh_history()

    def _on_clear_history(self):
        if not self._history.get_all():
            return
        reply = QMessageBox.question(
            self, "确认清除", "确定要清除所有播放历史吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._history.clear_all()
            self._refresh_history()

    def show_history(self):
        self._tabs.setCurrentIndex(1)
        self._refresh_history()

    def show_playlist(self):
        self._tabs.setCurrentIndex(0)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        h, m = divmod(seconds, 3600)
        m, s = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
```

- [ ] **Step 2: Commit**

```bash
git add app/view/playlist_panel.py
git commit -m "feat: add PlaylistPanel with list and history tabs"
```

---

### Task 10: QSS 主题样式

**Files:**
- Create: `resources/styles/theme.qss`
- Create: `resources/__init__.py`（空文件，用于 `resources` 被识别为包）

- [ ] **Step 1: 编写深色毛玻璃 QSS 主题**

```css
/* resources/styles/theme.qss */

/* ── 全局 ── */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1a1a2e;
}

/* ── TabWidget ── */
QTabWidget::pane {
    border: none;
    background: #1e1e36;
    border-radius: 6px;
}
QTabBar::tab {
    background: transparent;
    color: #888;
    padding: 6px 14px;
    margin: 2px 0;
    border-radius: 4px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: rgba(108, 99, 255, 0.2);
    color: #b8b0ff;
}
QTabBar::tab:hover {
    color: #ccc;
}

/* ── 列表 ── */
QListWidget {
    background-color: #1e1e36;
    border: none;
    border-radius: 4px;
    padding: 2px;
    outline: none;
    font-size: 12px;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
    margin: 1px 0;
    color: #ccc;
}
QListWidget::item:selected {
    background: rgba(108, 99, 255, 0.25);
    color: #fff;
}
QListWidget::item:hover {
    background: rgba(108, 99, 255, 0.12);
}

/* ── 滚动条 ── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #444;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ── 菜单 ── */
QMenu {
    background-color: #22223a;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: rgba(108, 99, 255, 0.3);
    color: #fff;
}
QMenu::separator {
    height: 1px;
    background: #444;
    margin: 4px 8px;
}

/* ── 消息框 ── */
QMessageBox {
    background-color: #1e1e36;
}
QMessageBox QLabel {
    color: #e0e0e0;
}
QMessageBox QPushButton {
    background: #6c63ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 20px;
    min-width: 60px;
}
QMessageBox QPushButton:hover {
    background: #7b73ff;
}
QMessageBox QPushButton:pressed {
    background: #5b53ef;
}

/* ── ToolTip ── */
QToolTip {
    background: #22223a;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
```

- [ ] **Step 2: Commit**

```bash
git add resources/
git commit -m "feat: add dark glassmorphism QSS theme"
```

---

### Task 11: MainWindow

**Files:**
- Create: `app/view/main_window.py`

- [ ] **Step 1: 实现主窗口**

```python
# app/view/main_window.py
import os
import time

from PySide6.QtCore import Qt, QTimer, QByteArray
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QMenuBar, QFileDialog, QMessageBox,
                               QApplication)

from app.signals.bus import player_signals
from app.model.playlist_model import PlaylistModel
from app.model.history_model import HistoryModel
from app.model.config import ConfigManager, AppConfig
from app.controller.player_controller import PlayerController
from app.view.video_widget import VideoWidget
from app.view.control_bar import ControlBar
from app.view.playlist_panel import PlaylistPanel


class MainWindow(QMainWindow):
    """主窗口——组装所有视图组件。"""

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._playlist = PlaylistModel()
        self._history = HistoryModel()
        self._controller: PlayerController | None = None
        self._is_fullscreen = False
        self._was_maximized = False
        self._pending_resume: float = 0.0

        self.setWindowTitle("视频播放器")
        self.setMinimumSize(800, 500)
        self.setAcceptDrops(True)

        self._restore_geometry()
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._restore_config()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # 视频区域 + 控制栏（垂直）
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        self._video_widget = VideoWidget()
        video_layout.addWidget(self._video_widget, 1)

        self._control_bar = ControlBar()
        video_layout.addWidget(self._control_bar)

        # 播放列表面板
        self._playlist_panel = PlaylistPanel(self._playlist, self._history)

        # 分割器
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(video_container)
        self._splitter.addWidget(self._playlist_panel)
        self._splitter.setHandleWidth(2)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        split_sizes = [max(self.width() - self._config.splitter_position, 400),
                       self._config.splitter_position]
        self._splitter.setSizes(split_sizes)

        self.setCentralWidget(self._splitter)

        # 菜单栏
        self._setup_menu()

        # 延迟初始化 mpv（需要 winId 就绪）
        QTimer.singleShot(100, self._init_player)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        open_action = QAction("打开文件(&O)...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        open_dir_action = QAction("打开文件夹(&D)...", self)
        open_dir_action.setShortcut(QKeySequence("Ctrl+D"))
        open_dir_action.triggered.connect(self._on_open_dir)
        file_menu.addAction(open_dir_action)

        file_menu.addSeparator()
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图(&V)")
        self._toggle_playlist_action = QAction("播放列表", self)
        self._toggle_playlist_action.setCheckable(True)
        self._toggle_playlist_action.setChecked(True)
        self._toggle_playlist_action.triggered.connect(self._toggle_playlist)
        view_menu.addAction(self._toggle_playlist_action)

        history_action = QAction("播放历史(&H)", self)
        history_action.triggered.connect(lambda: self._playlist_panel.show_history())
        view_menu.addAction(history_action)

        play_menu = menubar.addMenu("播放(&P)")
        self._play_pause_action = QAction("播放/暂停", self)
        self._play_pause_action.setShortcut(QKeySequence(Qt.Key_Space))
        self._play_pause_action.triggered.connect(lambda: self._controller and self._controller.toggle_play())
        play_menu.addAction(self._play_pause_action)

    def _setup_shortcuts(self):
        # Space → 已在菜单中绑定
        # 方向键
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self._controller and self._controller.seek(-5, True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self._controller and self._controller.seek(5, True))
        QShortcut(QKeySequence(Qt.Key_Up), self, lambda: self._controller and self._controller.set_volume(
            min(100, (self._controller.mpv.volume or 50) + 10)))
        QShortcut(QKeySequence(Qt.Key_Down), self, lambda: self._controller and self._controller.set_volume(
            max(0, (self._controller.mpv.volume or 50) - 10)))
        QShortcut(QKeySequence("Ctrl+Left"), self, lambda: self._controller and self._controller.seek(-30, True))
        QShortcut(QKeySequence("Ctrl+Right"), self, lambda: self._controller and self._controller.seek(30, True))
        # F / Esc
        QShortcut(QKeySequence(Qt.Key_F), self, self._toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._exit_fullscreen)
        # S 截图
        QShortcut(QKeySequence(Qt.Key_S), self, self._on_screenshot_shortcut)
        # M 静音
        QShortcut(QKeySequence(Qt.Key_M), self, lambda: self._controller and self._controller.toggle_mute())
        # R 播放模式
        QShortcut(QKeySequence(Qt.Key_R), self, lambda: self._controller and self._controller.cycle_play_mode())
        # Delete 删除当前项
        QShortcut(QKeySequence(Qt.Key_Delete), self, self._on_delete_current)

    def _connect_signals(self):
        player_signals.eos_reached.connect(self._on_eos)
        player_signals.fullscreen_changed.connect(self._on_fullscreen_signal)

    def _init_player(self):
        try:
            mpv = self._video_widget.init_mpv()
            self._controller = PlayerController(mpv, self._playlist)
            self._control_bar.set_controller(self._controller)
            self._playlist_panel.set_controller(self._controller)
        except Exception as e:
            QMessageBox.critical(self, "初始化失败",
                                 f"无法初始化 mpv：{e}\n"
                                 "请确保已安装 mpv 并将 mpv-1.dll 放在 PATH 或项目目录中。")

    def _restore_geometry(self):
        if self._config.window_geometry:
            self.restoreGeometry(QByteArray.fromHex(self._config.window_geometry.encode()))
        else:
            self.resize(1200, 800)
            self.move(100, 100)

    def _restore_config(self):
        if self._controller:
            self._controller.set_volume(self._config.volume)
            self._controller.set_speed(self._config.speed)
            self._playlist.mode = PlaylistModel.PlayMode(self._config.play_mode)

    # ── 拖拽文件 ──

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
        videos = [p for p in paths if os.path.splitext(p)[1].lower() in video_exts]
        if videos:
            self._playlist.add_files(videos)
            if self._controller:
                self._controller.load_file(videos[0])

    # ── 文件打开 ──

    def _on_open_file(self):
        exts = "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v);;所有文件 (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "打开视频", self._config.last_dir, exts)
        if path:
            self._config.last_dir = os.path.dirname(path)
            if self._controller:
                self._controller.load_file(path)
                # 检查续播位置
                resume_pos = self._history.get_resume_position(path)
                if resume_pos > 0:
                    self._pending_resume = resume_pos
                    self._check_resume(path)

    def _on_open_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "打开文件夹", self._config.last_dir)
        if dir_path:
            self._config.last_dir = dir_path
            exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
            files = []
            for f in os.listdir(dir_path):
                if os.path.splitext(f)[1].lower() in exts:
                    files.append(os.path.join(dir_path, f))
            if files:
                self._playlist.add_files(files)
                if self._controller:
                    self._controller.load_file(files[0])

    def _check_resume(self, path: str):
        """播放后检查是否需要续播。"""
        QTimer.singleShot(500, self._do_resume)

    def _do_resume(self):
        if self._pending_resume > 0 and self._controller:
            reply = QMessageBox.question(
                self, "续播", f"是否从上次播放位置 ({self._fmt_time(self._pending_resume)}) 继续播放？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self._controller.seek(self._pending_resume)
            self._pending_resume = 0.0

    # ── 全屏 ──

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        self._was_maximized = self.isMaximized()
        self._is_fullscreen = True
        self._playlist_panel.hide()
        self._control_bar.hide()
        self.menuBar().hide()
        self.showFullScreen()

    def _exit_fullscreen(self):
        self._is_fullscreen = False
        self._playlist_panel.show()
        self._control_bar.show()
        self.menuBar().show()
        if self._was_maximized:
            self.showMaximized()
        else:
            self.showNormal()

    def _on_fullscreen_signal(self, enabled: bool):
        self._toggle_fullscreen()

    # ── 事件 ──

    def _on_eos(self):
        QTimer.singleShot(200, self._controller.next_track)

    def _on_screenshot_shortcut(self):
        if self._controller:
            save_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "screenshots")
            self._controller.screenshot(save_dir)

    def _on_delete_current(self):
        if self._playlist.current_index >= 0:
            self._playlist.remove(self._playlist.current_index)

    def _toggle_playlist(self):
        visible = self._playlist_panel.isVisible()
        self._playlist_panel.setVisible(not visible)

    # ── 窗口关闭 ──

    def closeEvent(self, event):
        # 保存播放位置
        if self._controller and self._playlist.current_index >= 0:
            item = self._playlist.get_current_item()
            if item:
                try:
                    pos = self._controller.mpv.time_pos or 0
                    self._history.record_stop(item.path, pos, self._controller.mpv.duration or 0)
                except Exception:
                    pass

        # 保存配置
        self._config.window_geometry = bytes(self.saveGeometry().toHex()).decode()
        self._config.splitter_position = self._splitter.sizes()[1]
        self._config.volume = int(self._controller.mpv.volume) if self._controller else 50
        self._config.play_mode = int(self._playlist.mode)
        ConfigManager.save(self._config)

        super().closeEvent(event)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
```

- [ ] **Step 2: Commit**

```bash
git add app/view/main_window.py
git commit -m "feat: add MainWindow with player assembly and shortcuts"
```

---

### Task 12: 应用入口 main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: 实现 main.py**

```python
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
```

- [ ] **Step 2: 确保 mpv-1.dll 可用**

在 Windows 上，python-mpv 需要找到 `mpv-1.dll`。将 mpv-1.dll 放在项目根目录，或通过系统 PATH 访问。

可以创建一个说明文件或在 README 中注明：

```bash
echo "下载 mpv-1.dll 并放置在项目根目录：https://sourceforge.net/projects/mpv-player-windows/files/libmpv/"
```

- [ ] **Step 3: 创建 .gitignore**

```gitignore
# .gitignore
__pycache__/
*.pyc
data/config.json
data/screenshots/
mpv-1.dll
.superpowers/
```

- [ ] **Step 4: Commit**

```bash
git add main.py .gitignore
git commit -m "feat: add application entry point"
```

---

## 执行顺序总结

| 任务 | 文件数 | 内容 |
|------|--------|------|
| Task 1 | 7 | 脚手架、依赖、信号总线 |
| Task 2 | 1 | ConfigManager (AppConfig + 读写 JSON) |
| Task 3 | 1 | PlaylistModel (播放列表 + 四种播放模式) |
| Task 4 | 1 | HistoryModel (历史记录 + 收藏 + 续播) |
| Task 5 | 1 | VideoWidget (mpv embedding) |
| Task 6 | 1 | PlayerController (播放控制 API) |
| Task 7 | 1 | VolumeWidget (音量控件) |
| Task 8 | 1 | ControlBar (双行控制栏 UI) |
| Task 9 | 1 | PlaylistPanel (分页式播放列表 + 历史) |
| Task 10 | 1 | theme.qss (深色毛玻璃样式) |
| Task 11 | 1 | MainWindow (主窗口 + 快捷键 + 拖拽 + 全屏) |
| Task 12 | 2 | main.py (入口) + .gitignore |

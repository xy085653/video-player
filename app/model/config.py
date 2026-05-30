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

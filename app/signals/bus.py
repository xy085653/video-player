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

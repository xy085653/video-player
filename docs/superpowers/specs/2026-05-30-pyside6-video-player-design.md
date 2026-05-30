# PySide6 + python-mpv 视频播放器设计文档

> 创建时间：2026-05-30
> 状态：已批准

## 1. 概述

基于 PySide6 桌面框架和 python-mpv 后端的高性能视频播放器，拥有精美深色毛玻璃 UI，支持本地视频播放、播放列表管理、播放历史记录等核心功能。

## 2. 技术选型

| 层面 | 选型 | 理由 |
|------|------|------|
| GUI 框架 | PySide6 (Qt6) | 成熟的桌面 GUI 框架，原生性能 |
| 播放后端 | python-mpv (libmpv) | GPU 渲染、硬件解码、格式支持全 |
| 视频嵌入 | winId 嵌入 QWidget | 零性能损失，原生窗口嵌入 |
| 通信模式 | QObject 信号总线单例 | 解耦 View 和 Controller |
| 持久化 | JSON 文件 | 简单可靠，无需 SQLite |
| 图标 | SVG 内嵌 | 高清缩放，免版权 |
| 样式 | QSS 全局样式表 | 灵活的主题控制 |

## 3. 功能清单

- [x] 核心播放：播放/暂停、进度条拖拽、音量控制、全屏切换
- [x] 播放列表：侧边栏列表、拖拽排序、删除/清空
- [x] 播放模式：顺序播放、列表循环、单曲循环、随机播放
- [x] 倍速播放：0.25x ~ 8.0x
- [x] 字幕支持：加载外挂字幕、切换字幕轨道
- [x] 音轨切换：多音轨视频切换
- [x] 视频截图：一键截图保存
- [x] 键盘快捷键：空格/方向键/F 等
- [x] 拖拽文件：从文件管理器拖入打开
- [x] 播放历史：记录上次播放位置、收藏

## 4. UI 布局

### 4.1 整体布局 — 经典布局

```
┌─────────────────────────────────────┐
│                                     │
│         VideoWidget                 │
│       (mpv 视频渲染区)               │
│                                     │
├──────────────────────┬──────────────┤
│                      │  播放列表     │
│    ControlBar        │  (带Tab:     │
│    (双行分离式)       │   列表/历史)  │
│                      │              │
└──────────────────────┴──────────────┘
```

### 4.2 控制栏 — 双行分离式

第 1 行：进度条 + 时间显示（当前/总时长）
第 2 行：播放控制按钮组（上一曲/播放暂停/下一曲/停止）+ 音量 + 倍速 + 字幕 + 音轨 + 截图 + 播放模式 + 全屏

### 4.3 播放列表 — 分页式

顶部 Tab 切换「列表」和「历史」两个视图。
- 列表视图：当前播放队列，支持拖拽排序、右键删除
- 历史视图：历史记录，自动保存播放位置，支持收藏和续播

### 4.4 视觉风格

- 深色毛玻璃（Dark Glassmorphism）
- 背景色：#1a1a2e（深蓝黑）
- 控制栏：半透明毛玻璃效果（QSS backdrop-filter 模拟）
- 强调色：#6c63ff（紫蓝）
- 圆角：8px 柔和

## 5. 项目结构

```
视频播放器/
├── main.py                     # 应用入口：QApplication + MainWindow
├── requirements.txt            # 依赖声明
├── resources/
│   ├── icons/                  # SVG 图标文件
│   └── styles/
│       └── theme.qss           # 全局 QSS 样式表
├── app/
│   ├── __init__.py
│   ├── controller/
│   │   ├── __init__.py
│   │   └── player_controller.py    # 播放控制核心
│   ├── model/
│   │   ├── __init__.py
│   │   ├── playlist_model.py       # 播放列表数据模型
│   │   ├── history_model.py        # 播放历史记录
│   │   └── config.py               # 应用配置管理
│   ├── view/
│   │   ├── __init__.py
│   │   ├── main_window.py          # 主窗口 (QMainWindow)
│   │   ├── video_widget.py         # mpv 视频嵌入控件
│   │   ├── control_bar.py          # 底部控制栏
│   │   ├── playlist_panel.py       # 播放列表面板
│   │   └── volume_widget.py        # 音量控制组件
│   └── signals/
│       ├── __init__.py
│       └── bus.py                  # PlayerSignals 单例
└── data/                           # 运行时数据（自动创建）
    ├── history.json
    └── config.json
```

## 6. 组件设计

### 6.1 VideoWidget (`app/view/video_widget.py`)

QWidget 子类，通过 winId() 将 mpv 渲染嵌入 Qt 窗口。

**关键属性：**
- `WA_DontCreateNativeAncestors` / `WA_NativeWindow` — 确保 winId 可用
- `WA_NoSystemBackground` / `WA_OpaquePaintEvent` — 禁止 Qt 绘制背景

**mpv 初始化参数：**
- `vo='gpu'` — GPU 渲染
- `hwdec='auto'` — 自动硬件解码
- `keepaspect=True` — 保持视频宽高比
- `cache=yes` — 启用网络缓存
- `demuxer_max_bytes=150e6` — 解复用器缓存上限

**监听的 mpv 属性：**
- `time-pos` → 更新进度条
- `duration` → 更新总时长
- `pause` → 更新播放按钮状态
- `track-list` → 更新字幕/音轨列表

### 6.2 PlayerController (`app/controller/player_controller.py`)

纯业务逻辑类，不继承 QObject。

**公开方法：**
- `load_file(path)` — 加载视频
- `toggle_play()` — 播放/暂停切换
- `seek(seconds, relative)` — 跳转
- `set_speed(rate)` — 设置倍速
- `set_volume(vol)` — 设置音量
- `screenshot(path)` — 截图
- `next_track()` / `prev_track()` — 切换播放列表项
- `cycle_subtitle(direction)` — 切换字幕轨道
- `cycle_audio(direction)` — 切换音轨
- `set_play_mode(mode)` — 设置播放模式
- `stop()` — 停止播放

### 6.3 PlayerSignals (`app/signals/bus.py`)

全局信号总线单例，继承 QObject。

**信号：**
- `file_loaded(path)` — 文件加载完成
- `play_state_changed(is_playing)` — 播放/暂停状态变更
- `position_changed(seconds)` — 播放进度变更
- `duration_changed(seconds)` — 总时长变更
- `volume_changed(vol)` — 音量变更
- `speed_changed(rate)` — 倍速变更
- `playlist_changed(items)` — 播放列表变更
- `current_index_changed(index)` — 当前播放项变更
- `play_mode_changed(mode)` — 播放模式变更
- `subtitle_tracks(tracks)` — 字幕轨道列表
- `audio_tracks(tracks)` — 音轨列表
- `screenshot_taken(path)` — 截图完成

### 6.4 PlaylistModel (`app/model/playlist_model.py`)

QObject 子类，管理播放列表数据。

**数据结构：** `list[PlaylistItem]`
**PlaylistItem 字段：** path, name, duration, thumbnail, last_position

**播放模式：**
- SEQUENTIAL (0) — 顺序播放
- LOOP_ALL (1) — 列表循环
- LOOP_ONE (2) — 单曲循环
- SHUFFLE (3) — 随机播放

**方法：** add_file, add_files, remove, move, next_index, prev_index, clear, get_current_item

### 6.5 HistoryModel (`app/model/history_model.py`)

纯 Python 类，管理播放历史持久化。

**HistoryEntry 字段：** path, name, last_position, duration, timestamp, favorite

**方法：** record_stop, get_resume_position, toggle_favorite, get_all, clear_history, _load, _save

### 6.6 ConfigManager (`app/model/config.py`)

纯 Python 类，管理应用配置持久化。

**AppConfig 字段：** volume, speed, play_mode, window_geometry, last_dir, subtitle_enabled, remember_position

**方法：** load (classmethod), save (classmethod)

### 6.7 MainWindow (`app/view/main_window.py`)

QMainWindow 子类，组装所有视图组件。

**组件布局：** QHBoxLayout（左侧 VideoWidget + ControlBar 垂直布局 ｜ 右侧 PlaylistPanel）
**ControlBar 使用 QVBoxLayout（第 1 行进度条 ｜ 第 2 行控制按钮）**
**PlaylistPanel 使用 QTabWidget（列表 Tab + 历史 Tab）**

**功能：** 拖拽文件接受、全屏切换、窗口几何保存/恢复、键盘快捷键注册

### 6.8 ControlBar (`app/view/control_bar.py`)

QWidget 子类，底部控制栏。

**第一行：**
- QSlider（进度条，自定义样式）
- QLabel（当前时间 / 总时长）

**第二行：**
- 上一曲、播放/暂停、下一曲、停止（QPushButton，SVG 图标）
- 音量按钮 + 音量滑块
- 倍速标签（点击循环切换 0.5x / 1.0x / 1.5x / 2.0x）
- 字幕按钮、音轨按钮（点击弹出 QMenu 切换轨道）
- 截图按钮
- 播放模式按钮（点击循环切换）
- 全屏按钮

## 7. 快捷键绑定

| 键 | 功能 |
|----|------|
| Space | 播放/暂停 |
| Left / Right | 快退/快进 5s |
| Up / Down | 音量 +10 / -10 |
| Ctrl+Left / Ctrl+Right | 快退/快进 30s |
| F / DoubleClick | 全屏切换 |
| Esc | 退出全屏 |
| S | 截图 |
| M | 静音切换 |
| R | 循环切换播放模式 |
| T | 切换字幕轨道 |
| A | 切换音轨 |
| Ctrl+O | 打开文件 |
| Delete | 从播放列表删除当前项 |

## 8. 数据流

### 8.1 打开文件

```
用户拖拽/双击/菜单打开文件
  → MainWindow 获取文件路径
  → PlayerController.load_file(path)
     → mpv.play(path)
     → PlaylistModel.add_file(path)
     → PlayerSignals.file_loaded.emit(path)
     → PlayerSignals.playlist_changed.emit(items)
  → mpv 回调 time-pos → position_changed → ControlBar 更新进度条
  → mpv 回调 duration → duration_changed → ControlBar 更新时间显示
```

### 8.2 播放下一曲

```
当前曲目播放结束（或用户点击下一曲）
  → PlayerController.next_track()
     → PlaylistModel.next_index()
     → mpv.play(new_path)
     → PlayerSignals.current_index_changed.emit(index)
     → PlayerSignals.file_loaded.emit(path)
  → 旧曲目 HistoryModel.record_stop() 保存位置
```

### 8.3 进度条拖拽

```
用户拖拽 ControlBar 的 QSlider
  → slider.sliderMoved → PlayerController.seek(value)
  → mpv 跳转 → time-pos 回调
  → position_changed.emit(pos)
  → ControlBar 更新 QSlider 显示（防止拖拽中信号循环）
```

## 9. 线程安全

mpv 的 `observe_property` 回调在 mpv 内部线程中触发。所有信号发送必须切换到 Qt 主线程。

**方案：** 在 VideoWidget 中，所有 mpv 回调内部使用 `QMetaObject.invokeMethod(obj, "slotName", Qt.QueuedConnection, args)` 将更新调度到主线程，或直接通过 `@Slot` 装饰器的自动排队机制。

```
mpv 线程 → observe_property 回调
         → QMetaObject.invokeMethod(..., Qt.QueuedConnection)
         → Qt 事件循环 → 主线程执行槽函数
         → PlayerSignals.xxx.emit()
```

## 10. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 文件不存在/损坏 | mpv 返回 error，通过 log 记录，不崩溃 |
| 不支持格式 | 显示 toast 提示，继续播放当前文件 |
| 硬件解码失败 | mpv 自动回退到软件解码 |
| 截图失败 | 静默记录日志，不打扰用户 |
| 配置文件损坏 | 删除损坏文件，恢复默认配置 |
| 播放列表为空时点击下一曲 | 忽略操作 |

## 11. 持久化

### config.json

```json
{
  "volume": 50,
  "speed": 1.0,
  "play_mode": 1,
  "window_geometry": "hex_encoded_qbytearray",
  "last_dir": "C:/Users/.../Videos",
  "subtitle_enabled": true,
  "remember_position": true
}
```

### history.json

```json
[
  {
    "path": "C:/Movies/example.mp4",
    "name": "example.mp4",
    "last_position": 1234.5,
    "duration": 3600.0,
    "timestamp": 1717056000.0,
    "favorite": false
  }
]
```

## 12. 依赖

```
PySide6>=6.6.0
python-mpv>=1.0.0
```

运行时需要 `mpv-1.dll`（Windows）在 PATH 或项目目录中。

# 🎬 PySide6 + python-mpv 视频播放器

一个精美实用的桌面视频播放器，基于 **PySide6 (Qt6)** 和 **python-mpv** 构建。

## ✨ 功能特性

- **核心播放** — 播放/暂停、进度条拖拽、音量控制、全屏切换
- **播放列表** — 侧边栏列表、拖拽排序、右键菜单、清空确认
- **播放模式** — 顺序播放、列表循环、单曲循环、随机播放
- **倍速播放** — 0.5x ~ 2.0x 循环切换
- **字幕/音轨** — 加载外挂字幕、切换字幕轨道、切换音轨
- **视频截图** — 一键截图保存
- **播放历史** — 自动记录播放位置，支持收藏和续播
- **键盘快捷键** — 空格/方向键/F/S/M/R 等
- **拖拽文件** — 从文件管理器拖入视频文件打开
- **配置持久化** — 窗口几何、音量、倍速等偏好自动保存
- **深色毛玻璃 UI** — 自定义 QSS 主题

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows (mpv-1.dll)

### 安装

```bash
# 克隆仓库
git clone https://github.com/xy085653/video-player.git
cd video-player

# 创建虚拟环境（可选）
python -m venv .venv

# 安装依赖
.venv/Scripts/pip install -r requirements.txt

# 放置 mpv-1.dll
# 下载地址：https://sourceforge.net/projects/mpv-player-windows/files/libmpv/
# 解压后将 mpv-1.dll（或 libmpv-2.dll 重命名为 mpv-1.dll）放到项目根目录
```

### 运行

```bash
.venv/Scripts/python main.py
```

## 🧩 项目结构

```
video-player/
├── main.py                   # 应用入口
├── requirements.txt          # 依赖
├── resources/
│   ├── icons/                # SVG 图标
│   └── styles/theme.qss     # QSS 主题样式
├── app/
│   ├── signals/bus.py        # 信号总线
│   ├── model/                # 数据层
│   │   ├── config.py         # 配置管理
│   │   ├── playlist_model.py # 播放列表模型
│   │   └── history_model.py  # 播放历史模型
│   ├── controller/
│   │   └── player_controller.py  # 播放控制器
│   └── view/                 # 视图层
│       ├── video_widget.py   # mpv 视频嵌入
│       ├── control_bar.py    # 底部控制栏
│       ├── seek_slider.py    # 可点击进度条
│       ├── volume_widget.py  # 音量控件
│       ├── playlist_panel.py # 播放列表面板
│       ├── icon_helper.py    # 图标加载工具
│       └── main_window.py    # 主窗口
└── data/                     # 运行时数据
```

## 🎮 快捷键

| 键 | 功能 |
|----|------|
| `Space` | 播放/暂停 |
| `←` / `→` | 快退/快进 5s |
| `Ctrl+←` / `Ctrl+→` | 快退/快进 30s |
| `↑` / `↓` | 音量 +10 / -10 |
| `F` / 双击 | 全屏切换 |
| `Esc` | 退出全屏 |
| `S` | 截图 |
| `M` | 静音切换 |
| `R` | 循环切换播放模式 |
| `Delete` | 从播放列表删除 |

## 🛠️ 技术栈

- **GUI**: PySide6 (Qt6)
- **播放后端**: python-mpv (libmpv)
- **图标**: SVG 矢量图标
- **样式**: QSS 自定义主题（深色毛玻璃风格）
- **持久化**: JSON 文件

## 📄 许可

MIT

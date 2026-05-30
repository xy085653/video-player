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
        self._play_pause_action = QAction("播放/暂停\tSpace", self)
        self._play_pause_action.triggered.connect(lambda: self._controller and self._controller.toggle_play())
        play_menu.addAction(self._play_pause_action)

    def _setup_shortcuts(self):
        # Space → 播放/暂停（用 QShortcut 而非 QAction，避免全屏时菜单栏冲突）
        QShortcut(QKeySequence(Qt.Key_Space), self, lambda: self._controller and self._controller.toggle_play())
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

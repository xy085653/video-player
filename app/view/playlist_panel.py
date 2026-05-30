# app/view/playlist_panel.py
import os
from typing import Optional

from PySide6.QtCore import Qt, QMimeData, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QListWidget, QListWidgetItem,
                               QTabWidget, QLabel, QMenu, QMessageBox)

from app.signals.bus import player_signals
from app.model.playlist_model import PlaylistModel, PlaylistItem
from app.model.history_model import HistoryModel
from app.view.icon_helper import load_icon


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
        clear_btn = QPushButton(" 清空")
        clear_btn.setIcon(load_icon("clear.svg"))
        clear_btn.setIconSize(QSize(14, 14))
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
        clear_history_btn = QPushButton(" 清除历史")
        clear_history_btn.setIcon(load_icon("clear.svg"))
        clear_history_btn.setIconSize(QSize(14, 14))
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

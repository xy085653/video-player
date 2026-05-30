# app/view/seek_slider.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class SeekSlider(QSlider):
    """支持鼠标点击直接跳转到指定位置的滑动条。"""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = self._pick_value_from_click(event.position().x())
            self.setValue(val)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            val = self._pick_value_from_click(event.position().x())
            self.setValue(val)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _pick_value_from_click(self, click_x: float) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
        )
        handle = self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
        )
        # 有效点击区域 = 滑槽范围 - 半个手柄宽度
        groove_left = groove.x() + handle.width() // 2
        groove_right = groove.x() + groove.width() - handle.width() // 2
        width = groove_right - groove_left

        if width <= 0:
            return self.minimum()

        ratio = (click_x - groove_left) / width
        ratio = max(0.0, min(1.0, ratio))

        val_range = self.maximum() - self.minimum()
        return self.minimum() + int(ratio * val_range)

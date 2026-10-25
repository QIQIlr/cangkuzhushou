# 职责：全软件统一的“悬浮细滚动条”（规范 v1.3，参考 macOS / iOS 的滚动条：苹果 HIG “Scroll views”）。
#   - 盖在内容上面，不占宽度：内容区宽度永远不变（小柒 2026-10-25：滚动条一出来白色块往回缩一截，很突兀）。
#   - 平时看不见；鼠标移进区域、或者在滚动时才出现，停下 1 秒后淡出。
#   - 细（6px，鼠标放上去 8px）、圆头、半透明灰。
# 用法：程序启动时 装上(应用)，之后所有滚动区域（列表、表格、文本框、滚动页）自动换成这种，不用每处单独写。
from PySide6.QtCore import QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QAbstractScrollArea, QGraphicsOpacityEffect, QScrollBar

from 公共.界面.主题 import 色

宽 = 10          # 滚动条占的区域（细条本身 6px，左右各留 2px）
_样式 = f"""
QScrollBar#悬浮条 {{ background: transparent; width: {宽}px; margin: 2px 0; border: none; }}
QScrollBar#悬浮条::handle:vertical {{ background: {色['滚动条']}; border-radius: 3px; min-height: 36px;
    margin: 0 2px; }}
QScrollBar#悬浮条::handle:vertical:hover {{ background: {色['滚动条悬停']}; margin: 0 1px; border-radius: 4px; }}
QScrollBar#悬浮条::add-line, QScrollBar#悬浮条::sub-line {{ height: 0; width: 0; }}
QScrollBar#悬浮条::add-page, QScrollBar#悬浮条::sub-page {{ background: transparent; }}
"""


class 悬浮条(QScrollBar):
    """盖在滚动区域右边的细条。真正的滚动条藏起来，这根条和它同步。"""

    def __init__(self, 区域):
        super().__init__(Qt.Vertical, 区域)
        self.区域 = 区域
        self.setObjectName("悬浮条")
        self.setStyleSheet(_样式)
        self.setCursor(Qt.ArrowCursor)
        真 = 区域.verticalScrollBar()
        self.setRange(真.minimum(), 真.maximum())
        self.setPageStep(真.pageStep())
        self.setSingleStep(真.singleStep())
        self.setValue(真.value())
        真.rangeChanged.connect(self._范围)
        真.valueChanged.connect(self._跟)
        self.valueChanged.connect(真.setValue)
        self.透明 = QGraphicsOpacityEffect(self)
        self.透明.setOpacity(0.0)
        self.setGraphicsEffect(self.透明)
        self.动画 = QPropertyAnimation(self.透明, b"opacity", self)
        self.动画.setDuration(180)
        self.计时 = QTimer(self)
        self.计时.setSingleShot(True)
        self.计时.setInterval(1000)
        self.计时.timeout.connect(self.淡出)
        self.放好()
        self.hide() if 真.maximum() <= 真.minimum() else self.show()

    def _范围(self, 小, 大):
        self.setRange(小, 大)
        self.setPageStep(self.区域.verticalScrollBar().pageStep())
        self.setVisible(大 > 小)
        self.放好()

    def _跟(self, 值):
        if self.value() != 值:
            self.blockSignals(True)
            self.setValue(值)
            self.blockSignals(False)
        self.露出()

    def 放好(self):
        r = self.区域.rect()
        self.setGeometry(r.right() - 宽 + 1, r.top() + 2, 宽, max(0, r.height() - 4))
        self.raise_()

    def 露出(self):
        if self.maximum() <= self.minimum():
            return
        if self.透明.opacity() < 1.0:
            self.动画.stop()
            self.动画.setStartValue(self.透明.opacity())
            self.动画.setEndValue(1.0)
            self.动画.start()
        self.计时.start()

    def 淡出(self):
        if self.underMouse():
            self.计时.start()
            return
        self.动画.stop()
        self.动画.setStartValue(self.透明.opacity())
        self.动画.setEndValue(0.0)
        self.动画.start()


class _装配(QObject):
    """看到新的滚动区域就把它的竖滚动条换成悬浮条；区域大小变了、鼠标进来了，就摆好、露出来。"""

    def eventFilter(self, 对象, 事件):
        类型 = 事件.type()
        if 类型 == QEvent.Polish and isinstance(对象, QAbstractScrollArea) and not hasattr(对象, "_悬浮条"):
            if 对象.objectName() not in ("不要悬浮条",) and 对象.verticalScrollBarPolicy() != Qt.ScrollBarAlwaysOff:
                对象.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)   # 真的那根不占地方
                对象._悬浮条 = 悬浮条(对象)
                对象.installEventFilter(self)
        elif hasattr(对象, "_悬浮条") and isinstance(对象, QAbstractScrollArea):
            if 类型 in (QEvent.Resize, QEvent.Show):
                对象._悬浮条.放好()
            elif 类型 in (QEvent.Enter, QEvent.Wheel):
                对象._悬浮条.露出()
        return False


_装配器 = None


def 装上(应用):
    global _装配器
    _装配器 = _装配(应用)
    应用.installEventFilter(_装配器)

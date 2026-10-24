# 职责：各页面共用的小部件：卡片、状态小标签、页眉、开关、分段按钮、空白提示。
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from 公共.界面.主题 import 图标, 图码, 图标字体对象, 状态样子, 色


# 样式表只认英文的属性值，这里把中文叫法换过去
_角色码 = {"眉": "eyebrow", "大标题": "title", "副标题": "subtitle", "小标题": "heading", "组名": "group", "说明": "hint"}
_类型码 = {"主": "primary", "淡": "ghost", "图标": "icon"}


def 标签(文字="", 角色=None, 换行=False, 可选=False):
    l = QLabel(文字)
    if 角色:
        l.setProperty("role", _角色码.get(角色, 角色))
    l.setWordWrap(换行)
    if 可选:
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return l


def 按钮(文字="", 类型=None, 图=None, 图色=None, 提示=None):
    b = QPushButton(文字)
    if 类型:
        b.setProperty("kind", _类型码.get(类型, 类型))
    if 图:
        b.setIcon(图标(图, 图色 or ("#FFFFFF" if 类型 == "主" else 色["次字"]), 16))
        b.setIconSize(QSize(16, 16))
    if 提示:
        b.setToolTip(提示)
    b.setCursor(Qt.PointingHandCursor)
    return b


class 卡片(QFrame):
    """白色圆角卡片。内容放在 self.层 里。"""

    def __init__(self, 边距=16, 间距=10, 横=False):
        super().__init__()
        self.setProperty("card", "1")
        self.层 = QHBoxLayout(self) if 横 else QVBoxLayout(self)
        self.层.setContentsMargins(边距, 边距, 边距, 边距)
        self.层.setSpacing(间距)


def 图标字(名, 颜色=None, 大小=14):
    l = QLabel(图码.get(名, 名))
    l.setFont(图标字体对象(大小))
    l.setStyleSheet(f"color:{颜色 or 色['次字']}; background:transparent;")
    l.setAlignment(Qt.AlignCenter)
    return l


def 状态标签(状态, 文字=None, 小=False):
    """彩色小标签：✔ 成功 / ○ 无数据 / ⚠ 不完整 / ✖ 失败 / 等待 / 正在运行。"""
    默认字, 种, 图 = 状态样子.get(状态, (状态, "次", "圆"))
    l = QLabel(f"<span style='font-family:\"Segoe Fluent Icons\",\"Segoe MDL2 Assets\"; font-size:{8 if 小 else 9}pt'>"
               f"{图码[图]}</span>&nbsp;&nbsp;{文字 or 默认字}")
    l.setTextFormat(Qt.RichText)
    l.setStyleSheet(f"background:{色[种 + '底']}; color:{色[种]}; border-radius:{9 if 小 else 11}px;"
                    f"padding:{'1px 8px' if 小 else '3px 10px'}; font-weight:bold; font-size:{8.5 if 小 else 9.5}pt;")
    l.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return l


class 页眉(QWidget):
    """页面最上面：小字（眉）+ 大标题 + 副标题，右边放按钮。参考 Moneta / Norix 的页眉。"""

    def __init__(self, 眉, 标题, 副标题=""):
        super().__init__()
        层 = QHBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(12)
        左 = QVBoxLayout()
        左.setSpacing(2)
        self.眉 = 标签(眉, "眉")
        self.标题 = 标签(标题, "大标题")
        self.副标题 = 标签(副标题, "副标题", 换行=True)
        左.addWidget(self.眉)
        左.addWidget(self.标题)
        左.addWidget(self.副标题)
        self.副标题.setVisible(bool(副标题))
        层.addLayout(左, 1)
        self.右 = QHBoxLayout()
        self.右.setSpacing(8)
        层.addLayout(self.右)
        self.右.setAlignment(Qt.AlignBottom)

    def 设副标题(self, 文字):
        self.副标题.setText(文字)
        self.副标题.setVisible(bool(文字))


class 开关(QAbstractButton):
    """iOS / Windows 11 那种开关，代替勾选框表示“开 / 关”。用法和 QCheckBox 一样（toggled、isChecked）。"""

    def __init__(self, 文字="", 父=None):
        super().__init__(父)
        self.setCheckable(True)
        self.setText(文字)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        宽 = 40 + (self.fontMetrics().horizontalAdvance(self.text()) + 10 if self.text() else 0)
        return QSize(宽, 24)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        开 = self.isChecked()
        可用 = self.isEnabled()
        轨 = QRectF(1, (self.height() - 20) / 2, 38, 20)
        p.setPen(Qt.NoPen if 开 else QPen(QColor(色["灰"]), 1))
        p.setBrush(QColor(色["主"] if 开 else 色["面"]) if 可用 else QColor(色["线深"] if 开 else 色["底"]))
        p.drawRoundedRect(轨, 10, 10)
        r = 7 if 开 else 6
        x = 轨.right() - 10 if 开 else 轨.left() + 10
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF" if 开 else 色["弱字"]))
        p.drawEllipse(QRectF(x - r, 轨.center().y() - r, 2 * r, 2 * r))
        if self.text():
            p.setPen(QColor(色["字"] if 可用 else 色["灰"]))
            p.drawText(QRectF(48, 0, self.width() - 48, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class 分段(QFrame):
    """灰底轨道里的几个按钮，选中那个变白（参考 Watchlist 的 1D/7D/1M）。选中变化时发 选了(序号)。"""
    选了 = Signal(int)

    def __init__(self, 名们, 当前=0):
        super().__init__()
        self.setObjectName("分段")
        层 = QHBoxLayout(self)
        层.setContentsMargins(3, 3, 3, 3)
        层.setSpacing(2)
        self.组 = QButtonGroup(self)
        self.钮们 = []
        for i, 名 in enumerate(名们):
            b = QPushButton(名)
            b.setProperty("seg", "1")
            b.setCheckable(True)
            b.setChecked(i == 当前)
            b.setCursor(Qt.PointingHandCursor)
            self.组.addButton(b, i)
            层.addWidget(b)
            self.钮们.append(b)
        self.组.idClicked.connect(self.选了)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


def 空白提示(图, 标题, 说明="", 按钮们=()):
    """没有内容时显示：一个大图标 + 一句话 + 说明 + 按钮。"""
    w = QWidget()
    层 = QVBoxLayout(w)
    层.addStretch(1)
    圈 = 图标字(图, 色["主"], 22)
    圈.setFixedSize(52, 52)
    圈.setStyleSheet(f"color:{色['主']}; background:{色['主浅']}; border-radius:26px;")
    层.addWidget(圈, 0, Qt.AlignHCenter)
    层.addSpacing(8)
    t = 标签(标题, "小标题")
    t.setAlignment(Qt.AlignCenter)
    层.addWidget(t)
    if 说明:
        s = 标签(说明, "说明", 换行=True)
        s.setAlignment(Qt.AlignCenter)
        层.addWidget(s)
    if 按钮们:
        行 = QHBoxLayout()
        行.addStretch(1)
        for b in 按钮们:
            行.addWidget(b)
        行.addStretch(1)
        层.addSpacing(6)
        层.addLayout(行)
    层.addStretch(2)
    return w


def 分隔线():
    线 = QFrame()
    线.setFixedHeight(1)
    线.setStyleSheet(f"background:{色['线']}; border:none;")
    return 线

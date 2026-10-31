# 职责：各页面共用的零件（按《仓库助手设计规范》iOS 风格，2026-10-25）。
#   标签、按钮（主 / 次要 / 文字 / 危险）、分组块（灰色小标题 + 白色圆角块 + 行间细线 + 灰色脚注）、
#   勾选行（多选：选中的行末尾蓝色 ✓）、开关（开是绿色）、分段控件、状态（● 圆点 + 文字）、页眉、空白提示。
# 新页面、新模块、新设置都先从这里挑零件；不够时按规范补一个，写回规范。颜色只从 主题.色 取。
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from 公共.界面.主题 import 图标, 图码, 图标字体对象, 字号, 状态样子, 色, 行高最小

# 样式表只认英文的属性值，这里把中文叫法换过去
_角色码 = {"眉": "eyebrow", "大标题": "title", "副标题": "subtitle", "小标题": "heading", "组名": "group", "说明": "hint",
        "面板标题": "paneltitle", "脚注": "foot"}
_类型码 = {"主": "primary", "淡": "ghost", "文字": "ghost", "图标": "icon", "危险": "danger", "小": "small", "危险胶囊": "dangerpill"}


def 标签(文字="", 角色=None, 换行=False, 可选=False):
    l = QLabel(文字)
    if 角色:
        l.setProperty("role", _角色码.get(角色, 角色))
    l.setWordWrap(换行)
    if 可选:
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return l


def 按钮(文字="", 类型=None, 图=None, 图色=None, 提示=None):
    """类型：None = 次要按钮（灰底蓝字）；"主" = 主按钮（蓝底白字，一页最多一个）；"淡"/"文字" = 只有蓝字；"危险" = 红字；"图标"。"""
    b = QPushButton(文字)
    if 类型:
        b.setProperty("kind", _类型码.get(类型, 类型))
    if 图:
        b.setIcon(图标(图, 图色 or (色["白"] if 类型 == "主" else 色["坏"] if 类型 == "危险" else 色["主"]), 16))
        b.setIconSize(QSize(16, 16))
    if 提示:
        b.setToolTip(提示)
    b.setCursor(Qt.PointingHandCursor)
    return b


class 卡片(QFrame):
    """白色圆角块（规范的“分组块”的块本身）。内容放在 self.层 里。"""

    def __init__(self, 边距=16, 间距=10, 横=False):
        super().__init__()
        self.setProperty("card", "1")
        self.层 = QHBoxLayout(self) if 横 else QVBoxLayout(self)
        self.层.setContentsMargins(边距, 边距, 边距, 边距)
        self.层.setSpacing(间距)


class 图标标签(QLabel):
    """显示一个图标字。样式表里总带上图标字体：不然全局样式的“微软雅黑”会盖掉它（2026-10-24 发现）。"""

    def __init__(self, 文字, 大小):
        super().__init__(文字)
        self.大小 = 大小
        self.setFont(图标字体对象(大小))

    def setStyleSheet(self, 样式):
        super().setStyleSheet(f'font-family:"Segoe Fluent Icons","Segoe MDL2 Assets"; font-size:{self.大小}px; ' + 样式)


def 图标字(名, 颜色=None, 大小=14):
    l = 图标标签(图码.get(名, 名), 大小)
    l.setStyleSheet(f"color:{颜色 or 色['弱字']}; background:transparent;")
    l.setAlignment(Qt.AlignCenter)
    return l


def 状态标签(状态, 文字=None, 小=False, 醒目=False):
    """规范：状态只用 ● 圆点 + 文字；醒目=True 时加同色很淡的底。"""
    默认字, 种, _ = 状态样子.get(状态, (状态, "次", "圆"))
    l = QLabel(f"<span style='font-size:{9 if 小 else 11}px'>●</span>&nbsp;{文字 or 默认字}")
    l.setTextFormat(Qt.RichText)
    字色 = 色.get(种 + "字", 色[种]) if 醒目 else 色[种]
    # 规范 v1.3“角标”：胶囊形（高 22、圆角 11）、同色淡底 + 同色字 + 圆点，全软件一个样子
    l.setStyleSheet(f"color:{字色}; font-size:{字号['说明'] if (小 or 醒目) else 字号['正文'] - 1}px;"
                    + (f"background:{色[种 + '底']}; border-radius:11px; padding:0 10px; min-height:22px; max-height:22px;"
                       if 醒目 else "background:transparent;"))
    l.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return l


class 页眉(QWidget):
    """页面最上面：灰色小字（日期等）+ 大标题 + 灰色副标题，右边放按钮。
    副标题独占一整行（跨整行宽），右上的按钮跨三行垂直居中（2026-10-31）：
    以前副标题夹在左列里，窄窗口下只剩 253px 宽，工作台的运行说明要折三行、把模块列表挤掉 18px；
    改成整行宽后 1000×640 里副标题一行写得下，宽窗口的样子不变。"""

    def __init__(self, 眉, 标题, 副标题=""):
        super().__init__()
        外 = QGridLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        外.setHorizontalSpacing(12)
        外.setVerticalSpacing(2)
        self.眉 = 标签(眉, "眉")
        self.标题 = 标签(标题, "大标题")
        self.副标题 = 标签(副标题, "副标题", 换行=True)
        外.addWidget(self.眉, 0, 0)
        外.addWidget(self.标题, 1, 0)
        外.addWidget(self.副标题, 2, 0, 1, 2)          # 第 2 行、跨两列 = 整行宽
        self.右 = QHBoxLayout()
        self.右.setSpacing(12)
        self.右.setContentsMargins(0, 0, 0, 0)     # 不加这句，Qt 会给“装在 QWidget 里的布局”套 9px 默认边距，按钮会整体左移 9px
        self.右.setAlignment(Qt.AlignVCenter)
        self.右块 = QWidget()
        self.右块.setLayout(self.右)
        外.addWidget(self.右块, 0, 1, 3, 1, Qt.AlignVCenter)   # 按钮跨三行、垂直居中
        外.setColumnStretch(0, 1)
        外.setColumnStretch(1, 0)
        self.副标题.setVisible(bool(副标题))      # 先放进窗口里再决定显不显示（不然会闪出 pythonw 小窗）

    def 设副标题(self, 文字):
        self.副标题.setText(文字)
        self.副标题.setVisible(bool(文字))


def 画开关(p, 轨, 开, 可用=True):
    """iOS 开关：开是绿色，关是浅灰；白色小圆钮带一点阴影（规范里唯一允许的阴影）。工作台卡片也用它画。"""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    底 = 色["开关开"] if 开 else 色["开关关"]
    p.setBrush(QColor(底))
    if not 可用:
        p.setOpacity(0.5)
    p.drawRoundedRect(轨, 轨.height() / 2, 轨.height() / 2)
    r = 轨.height() / 2 - 2
    x = 轨.right() - r - 2 if 开 else 轨.left() + r + 2
    影 = QColor(色["字"])
    影.setAlpha(40)
    p.setBrush(影)
    p.drawEllipse(QPointF(x, 轨.center().y() + 1), r, r)
    p.setBrush(QColor(色["白"]))
    p.drawEllipse(QPointF(x, 轨.center().y()), r, r)
    p.restore()


class 开关(QAbstractButton):
    """iOS 开关，代替勾选框表示“开 / 关”。用法和 QCheckBox 一样（toggled、isChecked）。有文字时文字在左边。"""

    def __init__(self, 文字="", 父=None):
        super().__init__(父)
        self.setCheckable(True)
        self.setText(文字)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        宽 = 46 + (self.fontMetrics().horizontalAdvance(self.text()) + 12 if self.text() else 0)
        return QSize(宽, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        轨 = QRectF(self.width() - 46, (self.height() - 26) / 2, 44, 26)
        画开关(p, 轨, self.isChecked(), self.isEnabled())
        if self.text():
            p.setPen(QColor(色["字"] if self.isEnabled() else 色["灰"]))
            p.drawText(QRectF(0, 0, 轨.left() - 12, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class 分段(QFrame):
    """iOS 分段控件：灰色轨道里的几段，选中那段白底。选中变化时发 选了(序号)。"""
    选了 = Signal(int)

    def __init__(self, 名们, 当前=0):
        super().__init__()
        self.setObjectName("分段")
        层 = QHBoxLayout(self)
        层.setContentsMargins(2, 2, 2, 2)
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
    """规范“空状态”：区域中间一个浅灰图标 + 一行灰字说明，可以带按钮。"""
    w = QWidget()
    层 = QVBoxLayout(w)
    层.addStretch(1)
    圈 = 图标字(图, 色["灰"], 34)
    圈.setFixedSize(52, 52)
    层.addWidget(圈, 0, Qt.AlignHCenter)
    层.addSpacing(4)
    t = 标签(标题)
    t.setStyleSheet(f"color:{色['弱字']}; font-size:{字号['行标题']}px;")
    t.setAlignment(Qt.AlignCenter)
    t.setWordWrap(True)
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
        层.addSpacing(8)
        层.addLayout(行)
    层.addStretch(2)
    return w


def 分隔线(左缩进=0):
    """细分隔线。左缩进 = 从文字起头处开始（规范：不通到最左边）。"""
    外 = QWidget()
    层 = QHBoxLayout(外)
    层.setContentsMargins(左缩进, 0, 0, 0)
    线 = QFrame()
    线.setObjectName("行线")
    线.setFixedHeight(1)
    层.addWidget(线)
    外.setFixedHeight(1)
    return 外


# ---------------- 分组列表 ----------------
class 分组块(QWidget):
    """规范“分组列表”：块外面一行灰色小标题 → 白色圆角块（一行一行，行间细线从文字起头处开始）→ 块下面一行灰色说明。
    用法：组 = 分组块("查询范围", "改动会自动保存。")；组.加行(勾选行("瑞江仓库"))。"""

    def __init__(self, 标题="", 脚注=""):
        super().__init__()
        外 = QVBoxLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        外.setSpacing(6)
        self.标题 = 标签(标题, "组名")
        外.addWidget(self.标题)
        self.标题.setVisible(bool(标题))          # 先放进窗口里再决定显不显示（不然会闪出 pythonw 小窗）
        self.块 = 卡片(0, 0)
        外.addWidget(self.块)
        self.脚注 = 标签(脚注, "脚注", 换行=True)
        外.addWidget(self.脚注)
        self.脚注.setVisible(bool(脚注))
        self.行们 = []

    def 加行(self, 行):
        if self.行们:
            线 = 分隔线(16)
            self.块.层.addWidget(线)
            行._线 = 线
        else:
            行._线 = None
        self.块.层.addWidget(行)
        self.行们.append(行)
        return 行

    def 排线(self):
        """有的行藏起来以后，重新决定哪几条分隔线要显示（第一条看得见的行上面不画线）。"""
        有前 = False
        for 行 in self.行们:
            if 行._线 is not None:
                行._线.setVisible(有前 and not 行.isHidden())
            if not 行.isHidden():
                有前 = True

    def 设脚注(self, 文字, 颜色=None):
        self.脚注.setText(文字)
        self.脚注.setStyleSheet(f"color:{颜色};" if 颜色 else "")
        self.脚注.setVisible(bool(文字))


def 行(主文字, 右边=None, 说明=""):
    """分组块里的一行：左边文字（可带一行灰色说明），右边放开关、按钮或灰字。至少 44px 高，左右留 16px。"""
    w = QWidget()
    w.setMinimumHeight(行高最小)
    层 = QHBoxLayout(w)
    层.setContentsMargins(16, 8, 16, 8)
    层.setSpacing(12)
    字层 = QVBoxLayout()
    字层.setSpacing(2)
    w.主字 = 标签(主文字, 换行=True)
    字层.addWidget(w.主字)
    w.说明字 = 标签(说明, "说明", 换行=True)
    字层.addWidget(w.说明字)
    层.addLayout(字层, 1)
    w.说明字.setVisible(bool(说明))             # 字层挂到 w 上以后再设，不然这行字会变成独立的小窗闪一下
    if 右边 is not None:
        for x in (右边 if isinstance(右边, (list, tuple)) else [右边]):
            层.addWidget(x, 0, Qt.AlignVCenter)
    return w


class 勾选行(QAbstractButton):
    """规范“多选”：分组块里的一行，点一下选中 / 取消，选中时行末尾显示蓝色 ✓（不用方框勾选框）。
    用法和 QCheckBox 一样：toggled、isChecked、setChecked。"""

    def __init__(self, 文字="", 父=None):
        super().__init__(父)
        self.setCheckable(True)
        self.setText(文字)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(行高最小)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + 64, 行高最小)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isDown():
            p.fillRect(self.rect(), QColor(色["面2"]))
        p.setPen(QColor(色["字"] if self.isEnabled() else 色["灰"]))
        p.setFont(self.font())
        p.drawText(QRectF(16, 0, self.width() - 56, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        if self.isChecked():
            p.setPen(QColor(色["主"]))
            p.setFont(图标字体对象(16))
            p.drawText(QRectF(self.width() - 44, 0, 28, self.height()), Qt.AlignCenter, 图码["勾"])

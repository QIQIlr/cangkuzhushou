# 职责：仓库助手所有的弹窗（规范 v1.3“窗口内弹窗”，参考苹果 HIG “Alerts” 和 iOS 弹窗的样子，2026-10-25）。
#   主窗口压暗一层，中间出现白色圆角卡片（没有 Windows 标题栏）；标题、说明居中；
#   底部按钮：主操作 = 蓝底白字胶囊，次操作 = 灰底蓝字胶囊，危险操作 = 灰底红字胶囊；两个按钮时等宽并排。
#   Esc = 取消，回车 = 主操作。窗口还没打开时（例如“仓库助手已经打开了”）用一个独立的小窗显示同样的卡片。
# 用法：
#   信息(父, "标题", "说明")                    只有一个“好”
#   警告 / 出错                                  同上（状态靠文字说，不放彩色图标）
#   询问(父, "标题", "说明", 是="确定", 否="取消", 危险=False) -> True / False
#   选择(父, "标题", "说明", [("取消这次运行", "取消"), ("我登录好了", "主")]) -> 点了第几个（Esc / 关掉 = 取消）
#   窗内弹窗：需要放列表、输入框的弹窗（选择任务、设置飞书）继承它，用法和 QDialog 一样（exec / accept / reject）。
from PySide6.QtCore import QEvent, QEventLoop, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from 公共.界面.主题 import 字号, 色

接受, 拒绝 = QDialog.Accepted, QDialog.Rejected


def 胶囊钮(文字, 种="次"):
    """规范按钮：种 = "主"（蓝底白字）/ "次"（灰底蓝字）/ "危险"（灰底红字）/ "取消"（= 次）。"""
    b = QPushButton(文字)
    b.setCursor(Qt.PointingHandCursor)
    b.setAutoDefault(False)
    if 种 == "主":
        b.setProperty("kind", "primary")
    elif 种 == "危险":
        b.setProperty("kind", "dangerpill")
    b.setMinimumHeight(36)
    return b


class 窗内弹窗(QWidget):
    """盖在主窗口上的一层：压暗背景 + 中间白色圆角卡片。内容放在 self.卡层 里。"""

    def __init__(self, 父, 宽=420):
        窗 = 父.window() if 父 is not None else None
        self._独立 = 窗 is None or not 窗.isVisible()
        if self._独立:                    # 主窗口还没有：用一个独立的小窗装同样的卡片
            self._外 = QDialog()
            self._外.setWindowTitle("仓库助手")
            self._外.setStyleSheet(f"QDialog {{ background:{色['底']}; }}")
            super().__init__(self._外)
            外层 = QVBoxLayout(self._外)
            外层.setContentsMargins(12, 12, 12, 12)
            外层.addWidget(self)
        else:
            super().__init__(窗)
            self._窗 = 窗
            窗.installEventFilter(self)
        self.setObjectName("窗内弹窗")
        self.结果 = 拒绝
        self._圈 = None
        总 = QVBoxLayout(self)
        总.setContentsMargins(0, 0, 0, 0)
        总.addStretch(1)
        横 = QHBoxLayout()
        横.addStretch(1)
        self.卡 = QFrame(self)
        self.卡.setObjectName("弹窗卡")
        self.卡.setStyleSheet(f"QFrame#弹窗卡 {{ background:{色['面']}; border-radius:14px; }}")
        self.卡.setFixedWidth(宽)
        self.卡层 = QVBoxLayout(self.卡)
        self.卡层.setContentsMargins(24, 22, 24, 18)
        self.卡层.setSpacing(8)
        横.addWidget(self.卡)
        横.addStretch(1)
        总.addLayout(横)
        总.addStretch(1)
        self.hide()

    # ---- 和 QDialog 一样的用法 ----
    def exec(self):
        if self._独立:
            self._外.exec()
            return self.结果
        self.setGeometry(self._窗.rect())
        self.show()
        self.raise_()
        self.setFocus()
        self._圈 = QEventLoop()
        self._圈.exec()
        return self.结果

    def accept(self):
        self._完(接受)

    def reject(self):
        self._完(拒绝)

    def _完(self, 结果):
        self.结果 = 结果
        if self._独立:
            self._外.done(结果)
        else:
            self.hide()
            self._窗.removeEventFilter(self)
            if self._圈 is not None:
                self._圈.quit()
        self.deleteLater()

    def setWindowTitle(self, 标题):          # 子类沿用 QDialog 的写法；窗内弹窗没有标题栏，标题写在卡片里
        if self._独立:
            self._外.setWindowTitle(标题)

    def resize(self, 宽, 高):
        self.卡.setFixedWidth(min(宽, 1000))
        self.卡.setMinimumHeight(min(高, 900))

    def 默认动作(self):
        """回车：子类可以改成点主按钮。"""
        self.accept()

    # ---- 画压暗的一层、跟着窗口变大小、键盘 ----
    def paintEvent(self, _):
        if not self._独立:
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(0, 0, 0, 72))       # 压暗一层（色值同 主题.色["遮罩"]）

    def eventFilter(self, 对象, 事件):
        if 事件.type() == QEvent.Resize and not self._独立:
            self.setGeometry(self._窗.rect())
        return False

    def mousePressEvent(self, 事件):
        事件.accept()                       # 点卡片外面不做什么，也不会点到下面的东西

    def keyPressEvent(self, 事件):
        if 事件.key() == Qt.Key_Escape:
            self.reject()
        elif 事件.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.默认动作()
        else:
            super().keyPressEvent(事件)


class 提示框(窗内弹窗):
    def __init__(self, 父, 标题, 文字, 按钮们):
        super().__init__(父, 400 if len(按钮们) <= 2 else 460)
        # Esc / 关掉 = 点了“取消”那个按钮（没有取消按钮时 = 最后一个）
        self.取消序号 = next((i for i, (_, 种) in enumerate(按钮们) if 种 == "取消"), len(按钮们) - 1)
        self.主序号 = next((i for i, (_, 种) in enumerate(按钮们) if 种 in ("主", "危险")), len(按钮们) - 1)
        self.点了 = self.取消序号
        题 = QLabel(标题)
        题.setAlignment(Qt.AlignCenter)
        题.setWordWrap(True)
        题.setStyleSheet(f"font-size:{字号['弹窗标题']}px; font-weight:bold; color:{色['字']}; background:transparent;")
        self.卡层.addWidget(题)
        字 = QLabel(文字)
        字.setAlignment(Qt.AlignCenter)
        字.setWordWrap(True)
        字.setTextInteractionFlags(Qt.TextSelectableByMouse)
        字.setStyleSheet(f"font-size:{字号['正文'] - 1}px; color:{色['次字']}; background:transparent;")
        self.卡层.addWidget(字)
        self.卡层.addSpacing(14)
        行 = QHBoxLayout()
        行.setSpacing(10)
        self.钮们 = []
        for i, (名, 种) in enumerate(按钮们):
            b = 胶囊钮(名, 种)
            b.clicked.connect(lambda _=False, n=i: self._点(n))
            行.addWidget(b, 1)              # 等宽并排
            self.钮们.append(b)
        self.卡层.addLayout(行)

    def _点(self, n):
        self.点了 = n
        self.accept()

    def reject(self):
        self.点了 = self.取消序号
        super().reject()

    def 默认动作(self):
        self._点(self.主序号)


def 选择(父, 标题, 文字, 按钮们, 默认=None):
    框 = 提示框(父, 标题, 文字, 按钮们)
    if 默认 is not None:
        框.主序号 = 默认
    框.exec()
    return 框.点了


def 信息(父, 标题, 文字):
    选择(父, 标题, 文字, [("好", "主")], 默认=0)


警告 = 信息
出错 = 信息


def 询问(父, 标题, 文字, 是="确定", 否="取消", 危险=False):
    """返回 True = 点了“是”。回车 = “是”，Esc = “否”。"""
    return 选择(父, 标题, 文字, [(否, "取消"), (是, "危险" if 危险 else "主")]) == 1


def 活动窗口():
    return QApplication.activeWindow()

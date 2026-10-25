# 职责：仓库助手所有的确认、提示、出错小窗口（规范“弹窗”，iOS 风格，2026-10-25）。
#   白色、标题 17px 加粗居中、说明文字居中；按钮横排在底部：主操作蓝色加粗，取消是普通蓝字，危险操作红字。
#   窗口边框和右上角关闭按钮保持 Windows 原样（规范例外：不自己画窗口边框）。
# 用法：
#   信息(父, "标题", "说明")                    只有一个“好”
#   警告(父, ...) / 出错(父, ...)                同上（标题前没有彩色图标，状态靠文字说）
#   询问(父, "标题", "说明", 是="确定", 否="取消", 危险=False) -> True / False（默认按钮是“否”，回车不会误点）
#   选择(父, "标题", "说明", [("取消这次运行", "取消"), ("我登录好了", "主")]) -> 点了第几个（关窗口 = 取消）
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from 公共.界面.主题 import 字号, 色


class 提示框(QDialog):
    def __init__(self, 父, 标题, 文字, 按钮们):
        super().__init__(父)
        self.setWindowTitle(标题)
        self.setObjectName("提示框")
        self.setStyleSheet(f"QDialog#提示框 {{ background:{色['面']}; }}")
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)
        # 直接关窗口 = 点了“取消”那个按钮（没有取消按钮时 = 最后一个）
        self.点了 = next((i for i, (_, 种) in enumerate(按钮们) if 种 == "取消"), len(按钮们) - 1)
        层 = QVBoxLayout(self)
        层.setContentsMargins(24, 20, 24, 16)
        层.setSpacing(8)
        题 = QLabel(标题)
        题.setAlignment(Qt.AlignCenter)
        题.setWordWrap(True)
        题.setStyleSheet(f"font-size:{字号['弹窗标题']}px; font-weight:bold; color:{色['字']};")
        层.addWidget(题)
        字 = QLabel(文字)
        字.setAlignment(Qt.AlignCenter)
        字.setWordWrap(True)
        字.setTextInteractionFlags(Qt.TextSelectableByMouse)
        字.setStyleSheet(f"font-size:{字号['正文'] - 1}px; color:{色['次字']};")
        层.addWidget(字)
        层.addSpacing(12)
        行 = QHBoxLayout()
        行.setSpacing(8)
        行.addStretch(1)
        self.钮们 = []
        for i, (名, 种) in enumerate(按钮们):
            b = QPushButton(名)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("kind", "danger" if 种 == "危险" else "ghost")
            if 种 == "主":
                b.setStyleSheet("font-weight:bold;")
            b.setAutoDefault(False)
            b.clicked.connect(lambda _=False, n=i: self._点(n))
            行.addWidget(b)
            self.钮们.append(b)
        行.addStretch(1)
        层.addLayout(行)

    def _点(self, n):
        self.点了 = n
        self.accept()


def 选择(父, 标题, 文字, 按钮们, 默认=None):
    框 = 提示框(父, 标题, 文字, 按钮们)
    if 默认 is not None:
        框.钮们[默认].setDefault(True)
        框.钮们[默认].setFocus()
    框.exec()
    return 框.点了


def 信息(父, 标题, 文字):
    选择(父, 标题, 文字, [("好", "主")], 默认=0)


警告 = 信息
出错 = 信息


def 询问(父, 标题, 文字, 是="确定", 否="取消", 危险=False):
    """返回 True = 点了“是”。默认焦点在“否”上，回车不会误点。"""
    return 选择(父, 标题, 文字, [(否, "取消"), (是, "危险" if 危险 else "主")], 默认=0) == 1

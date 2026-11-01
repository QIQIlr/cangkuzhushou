# 职责：结果页数量表上的“格子小卡片”——鼠标停在某区某天的格子上（或点一下），旁边浮出一张小白卡片，
#   写清这一格是“合箱增值多少 + 单箱增值多少 = 合计”。只做显示，不改表格、不改布局、不改任何数字。
# 规范：设计规范第 6 节新零件「格子小卡片」（v1.8 候选，2026-11-01 待小柒看效果图确认）。
#   白底、圆角 12、1px 细分隔线色细边（白卡片盖在白表格上，没有边就看不见；规范不许阴影，所以用细边）。
#   字号/颜色只从 主题.py 取；不做动画；设 WA_TransparentForMouseEvents，不挡鼠标、不抢焦点。
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from 公共.界面 import 主题

色, 字号 = 主题.色, 主题.字号
最宽 = 320
最窄 = 180
间距 = 16                    # 字段名和字段内容之间


def _量宽(文字, 像素, 粗=False):
    """这段字排成一行要多宽（用来决定卡片最小宽度；不靠 QLabel 的 sizeHint，换行时它算不准）。"""
    f = QFont(主题.字体)
    f.setPixelSize(像素)
    f.setBold(粗)
    return QFontMetrics(f).horizontalAdvance(str(文字))


class 格子卡片(QFrame):
    """数据 = {"标题": "E区 · 10/30 周四",
               "行们": [["合箱增值", "120 单"], ["单箱增值", "35 单"]],
               "合计": "155 单",
               "提醒": None}          # 核对没通过时才有：橙字一行
    值是字符串，颜色按字符串自己判断（和变化表同一条规矩，不给数字另外加参数）：
      “—” → 次要字灰；“没查到” → 坏字红；其余正文黑。"""

    def __init__(self, 数据=None, 父=None):
        super().__init__(父)
        self.setObjectName("格子卡片")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)      # 不挡鼠标
        self.setStyleSheet(f"QFrame#格子卡片 {{ background: {色['面']};"
                          f" border: 1px solid {色['线']}; border-radius: {主题.圆角}px; }}")
        self.setMinimumWidth(最窄)
        self.setMaximumWidth(最宽)
        self._层 = QVBoxLayout(self)
        self._层.setContentsMargins(16, 12, 16, 12)             # 规范间距只用 4/8/12/16/20/24
        self._层.setSpacing(8)
        self._内容 = None
        if 数据:
            self.设(数据)

    # ---------------- 内容 ----------------
    def 设(self, 数据):
        """换内容（同一张卡复用，不重建控件以外的东西）。"""
        if self._内容 is not None:
            self._内容.setParent(None)
            self._内容.deleteLater()
        盒 = QFrame(self)
        层 = QVBoxLayout(盒)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(8)

        标题 = QLabel(str(数据.get("标题") or ""))
        标题.setWordWrap(True)
        标题.setStyleSheet(f"color:{色['弱字']}; font-size:{字号['说明']}px;")
        层.addWidget(标题)

        格 = QGridLayout()
        格.setContentsMargins(0, 0, 0, 0)
        格.setHorizontalSpacing(16)
        格.setVerticalSpacing(6)
        for r, (名, 值) in enumerate(数据.get("行们") or []):
            左 = QLabel(str(名))
            左.setStyleSheet(f"color:{色['弱字']}; font-size:{字号['字段名']}px;")
            右 = QLabel(str(值))
            右.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            右.setStyleSheet(f"color:{_值色(值)}; font-size:{字号['字段值']}px;")
            格.addWidget(左, r, 0)
            格.addWidget(右, r, 1)
        格.setColumnStretch(1, 1)
        层.addLayout(格)

        线 = QFrame()
        线.setFixedHeight(1)
        线.setStyleSheet(f"background:{色['线']};")
        层.addWidget(线)

        合 = QGridLayout()
        合.setContentsMargins(0, 0, 0, 0)
        合.setHorizontalSpacing(16)
        左 = QLabel("合计")
        左.setStyleSheet(f"color:{色['弱字']}; font-size:{字号['字段名']}px;")
        右 = QLabel(str(数据.get("合计") or "—"))
        右.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        右.setStyleSheet(f"color:{_值色(数据.get('合计'))}; font-size:{字号['字段值']}px; font-weight:bold;")
        合.addWidget(左, 0, 0)
        合.addWidget(右, 0, 1)
        合.setColumnStretch(1, 1)
        层.addLayout(合)

        if 数据.get("提醒"):
            提醒 = QLabel(str(数据["提醒"]))
            提醒.setWordWrap(True)
            提醒.setStyleSheet(f"color:{色['注意字']}; font-size:{字号['说明']}px;")
            层.addWidget(提醒)

        self._层.addWidget(盒)
        self._内容 = 盒
        # 宽度跟内容走：先量一量最长的那一行，再夹在 180～320 之间（太长就换行）
        要 = [_量宽(数据.get("标题") or "", 字号["说明"])]
        for 名, 值 in 数据.get("行们") or []:
            要.append(_量宽(名, 字号["字段名"]) + 间距 + _量宽(值, 字号["字段值"]))
        要.append(_量宽("合计", 字号["字段名"]) + 间距 + _量宽(数据.get("合计") or "—", 字号["字段值"], True))
        if 数据.get("提醒"):
            要.append(_量宽(数据["提醒"], 字号["说明"]))
        self.setMinimumWidth(max(最窄, min(最宽, max(要) + 32)))
        盒.adjustSize()
        self.adjustSize()

    def 设位置(self, 格子全局矩形, 窗口):
        """格子右下角 8px；会超出窗口右边就放到格子左边，超出下边就放到上面；永远完整在窗口里。"""
        边 = 8
        self.adjustSize()
        窗 = 窗口.rect()
        角 = 窗口.mapFromGlobal(格子全局矩形.bottomRight())
        角左 = 窗口.mapFromGlobal(格子全局矩形.topLeft())
        x, y = 角.x() + 边, 角左.y() + 边
        if x + self.width() > 窗.width() - 12:
            x = 角左.x() - self.width() - 边
        if y + self.height() > 窗.height() - 12:
            y = 角左.y() - self.height() - 边
        self.move(max(12, min(x, 窗.width() - self.width() - 12)),
                  max(12, min(y, 窗.height() - self.height() - 12)))


def _值色(值):
    文字 = str(值 or "")
    if 文字 == "—":
        return 色["弱字"]
    if "没查到" in 文字:
        return 色["坏字"]
    return 色["字"]

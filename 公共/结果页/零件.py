# 职责：结果页的通用小零件——通用标签/徽章/分组名/小按钮、结论条、错误框、提醒框、底部那一行。
#   从 公共\结果页.py 拆出来的（2026-10-31，纯搬家，函数体一个字没改）。
#   只被同包的 数量页 / 单号页 / 面单页 / __init__ 使用，外面不要直接 import 这里的下划线名字。

import html
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from 公共.界面 import 主题
from 公共.界面.组件 import 状态标签

色 = 主题.色


def _字(文字):
    return html.escape(str(文字)).replace("\n", "<br>")


def _标签(文字, 样子="", 可选=True, 换行=True):
    l = QLabel(文字)
    l.setWordWrap(换行)
    if 样子:
        l.setStyleSheet(样子)
    if 可选:
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return l


# ---------------- 小部件：结论、红框橙框、底部一行 ----------------


def _色(十六进制):
    from PySide6.QtGui import QBrush, QColor
    return QBrush(QColor(十六进制))


def _白块(内容, 边距=0):
    """规范的白色圆角块（分组块的“块”）。"""
    块 = QFrame()
    块.setProperty("card", "1")
    层 = QVBoxLayout(块)
    层.setContentsMargins(边距, 边距, 边距, 边距)
    层.setSpacing(0)
    层.addWidget(内容)
    return 块


def _组名(文字):
    l = QLabel(文字)
    l.setProperty("role", "group")
    return l


def _小钮(文字):
    b = QPushButton(文字)
    b.setProperty("kind", "small")
    b.setCursor(Qt.PointingHandCursor)
    return b


# ---------------- 样子 C：任务和面单 ----------------


def _文字钮(文字):
    """规范“文字按钮”：只有蓝字（打开 Excel、发到飞书、打开日志）。"""
    b = QPushButton(文字)
    b.setProperty("kind", "ghost")
    b.setCursor(Qt.PointingHandCursor)
    return b


class 换行文字钮(QLabel):
    """像“文字按钮”但文字长时能换行（面单页「评论和其他信息」那种收起段按钮，2026-11-01）。
    蓝字、手型；点一下发出 clicked，和 QPushButton 一样用法（setText / clicked）。"""
    clicked = Signal()

    def __init__(self, 文字=""):
        super().__init__(文字)
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"color:{色['主']}; font-size:{主题.字号['正文']}px; background:transparent; padding-left:16px;")

    def mousePressEvent(self, _e):
        self.clicked.emit()


def _文字钮换行(文字):
    return 换行文字钮(文字)


def _打开(路径):
    try:
        os.startfile(路径)
    except Exception:
        pass


# ---------------- 小部件：结论、红框橙框、底部一行 ----------------
def 提醒们(项):
    """橙框里的句子。模块给了 “提醒们” 就用它；老模块从 备注 里去掉状态、日志、出错原句（这些另有地方显示）。"""
    if "提醒们" in 项:
        句们 = 项["提醒们"] or []
    else:
        句们 = [s for s in 项.get("备注", []) if not (s.startswith("⚠ 状态") or s.startswith("日志：") or "建议：" in s)]
    return [str(s).lstrip("⚠ ").strip() for s in 句们 if str(s).strip()]


def 要看数(项):
    return 项.get("要看数") or 0


def 标签字(项):
    """标签：失败 ✖；不完整或有要看的 ⚠；无数据 ○；其他 ✔。后面带主要数字。"""
    状 = 项["状态"]
    符 = "✖" if 状 == "失败" else "⚠" if 状 == "不完整" or 要看数(项) or 提醒们(项) else "○" if 状 in ("无数据", "未运行") else "✔"
    数 = 项.get("数量")
    后 = f"  {数}" + (" 条" if 项.get("面单") is not None else "") if 数 is not None and 状 != "失败" else ""
    return f"{符} {项['显示名']}{后}"


def 飞书说明(状态, 说明, 手动=False):
    """底部那一行的飞书说明，用平常的话。返回 (文字, 是不是出了问题)。"""
    if 状态 == "成功":
        return "已发到飞书 ✔" + ("（刚才手动发的）" if 手动 else ""), False
    if 状态 == "未发送":
        if "本次选择不发送" in 说明:
            return "没自动发飞书（工作台右上角的“跑完自动发飞书”关着）。想发就点右边的“发到飞书”。", False
        if "设置为不发" in 说明:
            return "没自动发飞书（这个模块设成跑完不自动发）。想发就点右边的“发到飞书”。", False
        if "还没设置好飞书" in 说明:
            return "没发飞书：还没设置飞书（到“设置”页点“设置飞书”）", False
        return f"没发飞书（{说明}）", False
    if 状态 == "未知":
        return f"不确定飞书发出去没有：{说明}（先去群里看一眼）", True
    return f"飞书没发成功：{说明}", True


def _结论条(项):
    """结果页最上面（规范“结论条”）：第一行 模块名 + 状态（同色淡底）+ 要看几条，右边查询时间；第二行一句话结论。
    不完整 / 失败时结论那句话用状态色，整条不再铺淡底（状态靠角标和这句话的颜色；2026-10-29 界面评审 B2，小柒同意）。"""
    状 = 项["状态"]
    种 = "坏" if 状 == "失败" else "注意" if 状 == "不完整" else None
    条 = QFrame()
    条.setObjectName("结论条")
    外 = QVBoxLayout(条)
    外.setContentsMargins(0, 0, 0, 0)
    外.setSpacing(6)
    眉 = QHBoxLayout()
    眉.setSpacing(12)
    眉.addWidget(_标签(项["显示名"], f"font-size:{主题.字号['标题']}px; font-weight:bold; background:transparent;",
                     可选=False, 换行=False))
    眉.addWidget(状态标签(状, 醒目=True))
    if 要看数(项):
        眉.addWidget(状态标签("不完整", f"{要看数(项)} 条要看", 醒目=True))
    眉.addStretch(1)
    if 项.get("时间"):
        眉.addWidget(_标签(f"查询时间 {项['时间']:%m/%d %H:%M}", f"color:{色['说明']}; background:transparent;", 换行=False))
    外.addLayout(眉)
    结论 = _标签(项.get("结论") or 项.get("标题") or 项["显示名"],
               f"font-size:{主题.字号['结论']}px; background:transparent;" + (f"color:{色[种 + '字']};" if 种 else ""))
    外.addWidget(结论)
    return 条


def _错误框(错误们, 种, 日志文件夹, 提醒句们=()):
    """失败（红）或不完整（橙）：每个问题分三行“卡在哪一步 / 原因 / 怎么办”，自动换行。一样的问题只写一次。
    提醒句们：有出错时，提醒（如“E区 没查到（不是 0）”）并在这一块里、细线下面，不再另起一块（2026-10-29 界面评审 B2）。"""
    框 = QFrame()
    框.setObjectName("坏框" if 种 == "坏" else "注意框")
    层 = QVBoxLayout(框)
    层.setContentsMargins(12, 8, 12, 8)
    去重, 见过 = [], set()
    for e in 错误们:
        键 = (e.get("原因"), e.get("建议"))
        if 键 not in 见过:
            见过.add(键)
            去重.append(e)
    for i, e in enumerate(去重[:3]):
        格 = QGridLayout()
        格.setHorizontalSpacing(14)
        格.setVerticalSpacing(2)
        for r, (名, 值) in enumerate((("卡在哪一步", e.get("步骤") or "（还没开始查）"), ("原因", e.get("原因", "")),
                                    ("怎么办", e.get("建议", "")))):
            名字 = _标签(名, "font-weight:bold;", 换行=False)
            格.addWidget(名字, r, 0, Qt.AlignTop)
            格.addWidget(_标签(值), r, 1)
        格.setColumnStretch(1, 1)
        if i:
            线 = QFrame()
            线.setFrameShape(QFrame.HLine)
            线.setStyleSheet(f"color:{色['坏线' if 种 == '坏' else '注意线']}; background:transparent;")
            层.addWidget(线)
        层.addLayout(格)
    if len(去重) > 3:
        层.addWidget(_标签(f"还有 {len(去重) - 3} 个别的问题，详细的在日志里。"))
    if 提醒句们:
        线 = QFrame()
        线.setFrameShape(QFrame.HLine)
        线.setStyleSheet(f"color:{色['坏线' if 种 == '坏' else '注意线']}; background:transparent;")
        层.addWidget(线)
        for s in 提醒句们:
            层.addWidget(_标签("● " + s))
    if 日志文件夹:
        行 = QHBoxLayout()
        钮 = _文字钮("打开这次的日志")
        钮.clicked.connect(lambda: _打开(日志文件夹))
        行.addWidget(钮)
        行.addStretch(1)
        层.addLayout(行)
    框.setMaximumWidth(640)        # 一行字太长读不动，宽窗口时右边留白（2026-10-29 界面评审 A4，小柒同意）
    return 框


def _提醒框(句们):
    框 = QFrame()
    框.setObjectName("注意框")
    层 = QVBoxLayout(框)
    层.setContentsMargins(12, 6, 12, 6)
    层.setSpacing(2)
    for s in 句们:
        层.addWidget(_标签("● " + s))
    return 框


def _底部(项, 发送):
    行 = QHBoxLayout()
    if 项["状态"] == "未运行":
        行.addWidget(_标签("没有运行，所以没有结果可发。", f"color:{色['说明']};"), 1)
    elif 项.get("不发飞书"):
        行.addWidget(_标签("只在窗口里看，不发飞书", f"color:{色['说明']};"), 1)
    else:
        文字, 坏 = 飞书说明(*项["飞书"])
        字 = _标签(文字, f"color:{色['坏'] if 坏 else 色['说明']};")
        行.addWidget(字, 1)
        钮 = _文字钮("再发一次到飞书" if 项["飞书"][0] == "成功" else "发到飞书")
        钮.setToolTip("手动把这个结果发到飞书群一次，不看“跑完自动发飞书”的开关。")
        钮.clicked.connect(lambda _=False: 发送(项, 字, 钮))
        行.addWidget(钮)
    if 项.get("附件"):
        b = _文字钮("打开 Excel")
        b.clicked.connect(lambda _=False, p=项["附件"]: _打开(p))
        行.addWidget(b)
    if 项.get("日志文件夹"):
        b = _文字钮("打开这次的日志")
        b.clicked.connect(lambda _=False, p=项["日志文件夹"]: _打开(p))
        行.addWidget(b)
    return 行


# ---------------- 样子 A：数量表 ----------------

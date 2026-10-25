# 职责：仓库助手窗口里“结果”这一块，每个模块一页，所有模块同一个样子（小柒 2026-10-24 确认的改版方案）。
#   ① 结论：状态（图标 + 文字 + 颜色）+ 一句话结果 + 查询时间
#   ② 要注意的：失败是红框（哪一步 / 原因 / 怎么办），不完整和提醒是橙框；没有就不显示
#   ③ 内容：三种样子选一种
#        数量表（待审核、待拣货、待增值）：模块给 "数量表们"（旧模块给 "表们" 也能显示）
#        区域和单号（无任务包裹）：模块给 "分组"
#        任务和面单（转寄退货任务）：模块给 "面单"
#   ④ 底部一行：飞书发了没有、发到飞书、打开 Excel、打开这次的日志
# 规则：不出现左右滚动条；一块区域只一个滚动条；数字靠右、表格不拉满；不加动画；文字用平常的话。
# 新模块：在 组成消息 里给 "结论"（一句话）和上面三种内容之一，窗口自动排好。
import html
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from 公共.界面 import 主题  # noqa: E402
from 公共.界面.组件 import 状态标签  # noqa: E402

# 颜色、状态写法、样式表全部来自 公共\界面\主题.py（全软件只有那一份），这里不写颜色值
色 = 主题.色
等宽 = 主题.等宽
状态样子 = 主题.结果状态字
样式表 = 主题.结果页样式表


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


def _徽章(文字, 种):
    底 = {"好": 色["好底"], "注意": 色["注意底"], "坏": 色["坏底"]}.get(种, 色["次底"])
    return _标签(文字, f"background:{底}; color:{色[种]}; border-radius:10px; padding:2px 10px; font-weight:bold;",
               可选=False, 换行=False)


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


def _结论条(项):
    """结果页最上面（规范“结论条”）：第一行 模块名 + 状态（同色淡底）+ 要看几条，右边查询时间；第二行一句话结论。
    不完整 / 失败时整条用对应状态色的淡底 + 状态色文字。"""
    状 = 项["状态"]
    种 = "坏" if 状 == "失败" else "注意" if 状 == "不完整" else None
    条 = QFrame()
    if 种:
        条.setStyleSheet(f"QFrame#结论条 {{ background:{色[种 + '底']}; border-radius:12px; }}")
    条.setObjectName("结论条")
    外 = QVBoxLayout(条)
    外.setContentsMargins(16, 12, 16, 12) if 种 else 外.setContentsMargins(0, 0, 0, 0)
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
               f"font-size:17px; background:transparent;" + (f"color:{色[种 + '字']};" if 种 else ""))
    外.addWidget(结论)
    return 条

def _文字钮(文字):
    """规范“文字按钮”：只有蓝字（打开 Excel、发到飞书、打开日志）。"""
    b = QPushButton(文字)
    b.setProperty("kind", "ghost")
    b.setCursor(Qt.PointingHandCursor)
    return b

def _打开(路径):
    try:
        os.startfile(路径)
    except Exception:
        pass


def _错误框(错误们, 种, 日志文件夹):
    """失败（红）或不完整（橙）：每个问题分三行“卡在哪一步 / 原因 / 怎么办”，自动换行。一样的问题只写一次。"""
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
    if 日志文件夹:
        行 = QHBoxLayout()
        钮 = _文字钮("打开这次的日志")
        钮.clicked.connect(lambda: _打开(日志文件夹))
        行.addWidget(钮)
        行.addStretch(1)
        层.addLayout(行)
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
class _表格行画法(QStyledItemDelegate):
    """数量表的格子：先画这一行的底色（今天浅蓝），再画字，最后画行间细线（规范：没有竖线格子）。"""

    def paint(self, p, 选项, 索引):
        底 = 索引.data(Qt.BackgroundRole)
        if 底 is not None:
            p.fillRect(选项.rect, 底)
        super().paint(p, 选项, 索引)
        p.save()
        p.setPen(QColor(色["线"]))
        p.drawLine(选项.rect.bottomLeft(), 选项.rect.bottomRight())
        p.restore()


class 数量表格(QTableWidget):
    """只读的数量表：数字靠右、列宽跟内容走、不拉满；今天浅蓝、合计加粗、0 浅灰、失败红字。
    单击选中一格，双击或 Ctrl+C 复制。"""

    def __init__(self, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.setObjectName("数量表")
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.ClickFocus)
        self.horizontalHeader().setHighlightSections(False)
        self.setShowGrid(False)              # 规范：没有竖线格子，只有行间细线
        self.setItemDelegate(_表格行画法(self))
        self.itemDoubleClicked.connect(lambda _: self.复制())

    def 填(self, 列名, 行们, 起点=False):
        self.clear()
        self.setColumnCount(len(列名))
        self.setRowCount(len(行们))
        self.setHorizontalHeaderLabels(list(列名))
        for c in range(len(列名)):
            self.horizontalHeaderItem(c).setTextAlignment((Qt.AlignLeft if c == 0 else Qt.AlignRight) | Qt.AlignVCenter)
        粗体 = QFont(self.font())
        粗体.setBold(True)
        for r, 行 in enumerate(行们):
            合计行 = str(行[0]).startswith("**")
            名 = str(行[0]).replace("**", "")
            是起点 = 起点 and r == 0 and len(行们) > 2 and all(str(v) == "0" for v in 行[1:])
            if 是起点:
                名 += "（这天及以前都是 0）"
            今天 = "（今天）" in 名
            for c, 值 in enumerate([名] + list(行[1:])):
                s = str(值).replace("**", "")
                格 = QTableWidgetItem(s)
                格.setTextAlignment((Qt.AlignLeft if c == 0 else Qt.AlignRight) | Qt.AlignVCenter)
                if 合计行:
                    格.setFont(粗体)
                    格.setData(Qt.BackgroundRole, _色(色["合计底"]))
                elif 今天:
                    格.setData(Qt.BackgroundRole, _色(色["今天"]))
                if s == "失败":
                    格.setForeground(_色(色["坏"]))
                    格.setFont(粗体)
                elif c > 0 and ("+" in s or s == "—"):
                    格.setForeground(_色(色["注意"]))
                elif 是起点 or (c > 0 and s == "0"):
                    格.setForeground(_色(色["灰"]))
                self.setItem(r, c, 格)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        for c in range(len(列名)):
            self.setColumnWidth(c, self.columnWidth(c) + (16 if c == 0 else 22))
        宽 = sum(self.columnWidth(c) for c in range(len(列名))) + 2 * self.frameWidth()
        高 = self.horizontalHeader().height() + sum(self.rowHeight(r) for r in range(len(行们))) + 2 * self.frameWidth()
        self.setFixedSize(宽, 高)

    def keyPressEvent(self, 事件):
        if 事件.matches(QKeySequence.Copy):
            self.复制()
        else:
            super().keyPressEvent(事件)

    def 复制(self):
        格们 = sorted(self.selectedItems(), key=lambda g: (g.row(), g.column()))
        if not 格们:
            return
        行们 = {}
        for g in 格们:
            行们.setdefault(g.row(), []).append(g.text())
        文字 = "\n".join("\t".join(v) for v in 行们.values())
        QApplication.clipboard().setText(文字)
        self.状态栏.showMessage(f"已复制 {文字}" if len(格们) == 1 else f"已复制 {len(格们)} 格", 4000)


def _色(十六进制):
    from PySide6.QtGui import QBrush, QColor
    return QBrush(QColor(十六进制))


字段名宽 = 84


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


class 表格排列(QWidget):
    """数量表并排放（瑞江、松户两张表并排）；窗口太窄放不下时自动改成上下排。整页只有一个滚动条，这里不滚。"""

    def __init__(self, 块们):
        super().__init__()
        self.块们 = 块们
        self.格 = QGridLayout(self)
        self.格.setContentsMargins(0, 0, 0, 0)
        self.格.setHorizontalSpacing(16)
        self.格.setVerticalSpacing(20)
        self.列数 = 0
        self._排(len(块们))

    def _排(self, 列数):
        if 列数 == self.列数:
            return
        self.列数 = 列数
        for 块 in self.块们:
            self.格.removeWidget(块)
        for i, 块 in enumerate(self.块们):
            self.格.addWidget(块, i // 列数, i % 列数, Qt.AlignLeft | Qt.AlignTop)
        self.格.setColumnStretch(列数, 1)
        self.格.setRowStretch(len(self.块们), 1)

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        总宽 = sum(块.sizeHint().width() for 块 in self.块们) + 16 * (len(self.块们) - 1)
        self._排(len(self.块们) if 总宽 <= self.width() else 1)


def _数量内容(项, 状态栏):
    表们 = 项.get("数量表们") or [{"名": 名, "视图们": [("合计", 列, 行)], "起点": False}
                             for 名, 列, 行 in 项.get("表们", []) if 行]
    if not 表们:
        return None
    块们 = []
    for 表 in 表们:
        块 = QWidget()
        层 = QVBoxLayout(块)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(6)
        头 = QHBoxLayout()
        头.setSpacing(12)
        头.addWidget(_组名(表["名"]))
        格 = 数量表格(状态栏)
        视图们 = 表["视图们"]
        if len(视图们) > 1:
            轨 = QFrame()                  # 规范“分段控件”：灰色轨道，选中那段白底
            轨.setObjectName("分段")
            轨层 = QHBoxLayout(轨)
            轨层.setContentsMargins(2, 2, 2, 2)
            轨层.setSpacing(2)
            头.addWidget(轨)
            组 = QButtonGroup(块)
            for k, (视图名, 列, 行) in enumerate(视图们):
                钮 = QPushButton(视图名)
                钮.setProperty("seg", "1")
                钮.setCheckable(True)
                钮.setChecked(k == 0)
                钮.setCursor(Qt.PointingHandCursor)
                钮.clicked.connect(lambda _=False, 列=列, 行=行, 起=表["起点"], 格=格: 格.填(列, 行, 起))
                组.addButton(钮)
                轨层.addWidget(钮)
        头.addStretch(1)
        层.addLayout(头)
        格.填(视图们[0][1], 视图们[0][2], 表["起点"])
        层.addWidget(_白块(格, 8), 0, Qt.AlignLeft)
        块们.append(块)
    return 表格排列(块们)


# ---------------- 样子 B：区域和单号 ----------------
class 单号列表(QListWidget):
    """单号排成几列、等宽字；双击复制一个，多选后 Ctrl+C 复制选中的（每行一个）。
    高度跟着单号多少走，自己不出滚动条（整页只有一个滚动条）。"""
    格宽, 格高 = 210, 32

    def __init__(self, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.setObjectName("单号列表")
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.Adjust)
        self.setUniformItemSizes(True)
        self.setGridSize(QSize(self.格宽, self.格高))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFont(主题.像素字(主题.字号["行标题"], 族=等宽))
        self.itemDoubleClicked.connect(lambda 条: self._复制([条]))

    def 调高(self):
        列 = max(1, (self.viewport().width() or self.width()) // self.格宽)
        行 = -(-self.count() // 列) if self.count() else 1
        self.setFixedHeight(行 * self.格高 + 12)

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self.调高()

    def keyPressEvent(self, 事件):
        if 事件.matches(QKeySequence.Copy):
            self._复制(sorted(self.selectedItems(), key=self.row))
        else:
            super().keyPressEvent(事件)

    def _复制(self, 条们):
        号们 = [条.data(Qt.UserRole) for 条 in 条们]
        if not 号们:
            return
        QApplication.clipboard().setText("\n".join(号们))
        self.状态栏.showMessage(f"已复制 {号们[0]}" if len(号们) == 1 else f"已复制 {len(号们)} 个单号", 4000)


class 区域单号页(QWidget):
    """左边各区数量（0 个灰色、没查到红色），右边选中那个区的单号 + “复制这个区全部单号”。"""
    行高 = 44

    def __init__(self, 分组, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.明细 = {区: (单号们, 文字) for 区, 单号们, 文字 in 分组["明细"]}
        层 = QHBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(16)
        左 = QVBoxLayout()
        左.setSpacing(6)
        左.addWidget(_组名("区域"))
        self.列表 = QListWidget()
        self.列表.setObjectName("区域列表")
        self.列表.setFixedWidth(220)
        self.列表.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.区们 = []
        _, 总行 = 分组["总览"]
        for 区, 数, 标 in 总行:
            区名, 数字 = str(区).replace("**", ""), str(数).replace("**", "")
            if 数字 == "失败":
                说, 颜色 = "没查到", 色["坏"]
            elif 数字 == "0":
                说, 颜色 = "没有", 色["弱字"]
            else:
                说, 颜色 = f"{数字} 个" + (" · 不完整" if "不完整" in str(标) else ""), None
            合计行 = str(区).startswith("**")
            牌 = QWidget()
            牌.setAttribute(Qt.WA_TransparentForMouseEvents)
            横 = QHBoxLayout(牌)
            横.setContentsMargins(16, 0, 16, 0)
            样 = ("font-weight:bold;" if 合计行 else "") + f"font-size:{主题.字号['行标题']}px; background:transparent;"
            横.addWidget(_标签(区名, 样, 可选=False, 换行=False))
            横.addStretch(1)
            横.addWidget(_标签(说, 样 + (f"color:{颜色};" if 颜色 else ""), 可选=False, 换行=False))
            条 = QListWidgetItem()
            条.setSizeHint(QSize(200, self.行高))
            if 合计行:
                条.setFlags(Qt.ItemIsEnabled)
            self.列表.addItem(条)
            self.列表.setItemWidget(条, 牌)
            self.区们.append((区名, 数字))
        self.列表.setFixedHeight(max(1, self.列表.count()) * self.行高 + 4)
        self.列表.currentRowChanged.connect(self._换区)
        左.addWidget(self.列表)
        左.addStretch(1)
        层.addLayout(左)
        右 = QVBoxLayout()
        右.setSpacing(6)
        头 = QHBoxLayout()
        self.标题 = _组名("")
        self.标题.setMinimumWidth(40)               # 窄的时候标题让位，复制按钮的字不被挤掉
        self.标题.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        头.addWidget(self.标题, 1)
        self.复制钮 = _文字钮("")
        self.复制钮.clicked.connect(self._复制全部)
        头.addWidget(self.复制钮)
        右.addLayout(头)
        self.单号们 = 单号列表(状态栏)
        self.单号块 = self.单号们              # 单号列表自己就是白色圆角块（不再套一层，高度才跟得上）
        右.addWidget(self.单号块)
        self.空 = _标签("", f"color:{色['说明']}; font-size:{主题.字号['行标题']}px; padding:12px 4px;")
        self.空.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        右.addWidget(self.空)
        self.提示 = _标签("双击一个单号就复制这一个；按住 Ctrl 点几个，再按 Ctrl+C 复制选中的。",
                        f"color:{色['说明']}; font-size:{主题.字号['说明']}px; padding-left:16px;")
        右.addWidget(self.提示)
        右.addStretch(1)
        层.addLayout(右, 1)
        self.当前区 = None
        for r, (区名, _) in enumerate(self.区们):
            if 区名 in self.明细:
                self.列表.setCurrentRow(r)
                break
        else:
            self._换区(-1)

    def _换区(self, 行):
        区名, 数字 = self.区们[行] if 0 <= 行 < len(self.区们) else (None, None)
        self.当前区 = 区名 if 区名 in self.明细 else None
        有 = self.当前区 is not None
        for w in (self.单号块, self.复制钮, self.提示):
            w.setVisible(有)
        self.空.setVisible(not 有)
        if not 有:
            self.标题.setText(区名 or "")
            self.空.setText("这个区没查到（不是 0），原因见上面。" if 数字 == "失败" else
                           "这个区没有。" if 区名 else "所选区域都没有。")
            return
        单号们, _ = self.明细[区名]
        self.标题.setText(f"{区名} 的转运单号（{len(单号们)} 个）")
        self.复制钮.setText(f"复制 {区名} 全部 {len(单号们)} 个单号")
        self.单号们.clear()
        位数 = max(2, len(str(len(单号们))))
        for i, 号 in enumerate(单号们, 1):
            条 = QListWidgetItem(f"{str(i).zfill(位数)}  {号}")
            条.setData(Qt.UserRole, 号)
            self.单号们.addItem(条)
        self.单号们.调高()

    def _复制全部(self):
        if self.当前区 is None:
            return
        单号们, 文字 = self.明细[self.当前区]
        QApplication.clipboard().setText(文字)
        self.状态栏.showMessage(f"已复制 {self.当前区} {len(单号们)} 个单号", 5000)


# ---------------- 样子 C：任务和面单 ----------------
def _字段行(x):
    """明细里的一行“字段名 + 内容”（规范 v1.1：字段名 13px 灰、内容 15px 黑，全软件只用这一对；
    电话、单号、邮编用等宽字，大小相同）。要看的字段内容用橙色，提醒写在下面。"""
    w = QWidget()
    w.setMinimumHeight(主题.行高最小)
    层 = QHBoxLayout(w)
    层.setContentsMargins(16, 10, 16, 10)
    层.setSpacing(12)
    名 = _标签(x["名"], f"color:{色['说明']}; font-size:13px; background:transparent;", 可选=False, 换行=False)
    名.setFixedWidth(字段名宽)
    层.addWidget(名, 0, Qt.AlignTop)
    值层 = QVBoxLayout()
    值层.setSpacing(4)
    颜色值 = 色["注意字"] if x.get("提醒") else 色["弱字"] if x.get("灰") else 色["字"]
    字族 = f"font-family:'{等宽}';" if x.get("等宽") else ""
    值样 = f"font-size:15px; color:{颜色值}; {字族} background:transparent;"
    有预览 = bool(x.get("预览"))
    值 = _标签(x["预览"] if 有预览 else x["值"], 值样)
    值层.addWidget(值)
    if x.get("注"):
        值层.addWidget(_标签(x["注"], f"color:{色['说明']}; font-size:12px; background:transparent;"))
    if x.get("提醒"):
        值层.addWidget(_标签("● " + str(x["提醒"]), f"color:{色['注意字']}; font-size:13px; background:transparent;"))
    if 有预览:
        钮 = _文字钮(x.get("还有") or "点开看全部")
        钮.setStyleSheet("text-align:left; padding:0;")

        def 切换(_=False, 值=值, 钮=钮, x=x):
            开 = 钮.property("开") != "1"
            钮.setProperty("开", "1" if 开 else "0")
            值.setText(x["值"] if 开 else x["预览"])
            钮.setText("收起" if 开 else (x.get("还有") or "点开看全部"))
        钮.clicked.connect(切换)
        值层.addWidget(钮, 0, Qt.AlignLeft)
    层.addLayout(值层, 1)
    return w


def _分组(标题, 项们):
    """灰色小标题 + 白色圆角块 + 一行一个字段，行间细线从文字处开始。"""
    外 = QWidget()
    层 = QVBoxLayout(外)
    层.setContentsMargins(0, 0, 0, 0)
    层.setSpacing(6)
    if 标题:
        层.addWidget(_组名(标题))
    块 = QFrame()
    块.setProperty("card", "1")
    块层 = QVBoxLayout(块)
    块层.setContentsMargins(0, 0, 0, 0)
    块层.setSpacing(0)
    for i, x in enumerate(项们):
        if i:
            线外 = QWidget()
            线层 = QHBoxLayout(线外)
            线层.setContentsMargins(16, 0, 0, 0)
            线 = QFrame()
            线.setObjectName("行线")
            线.setFixedHeight(1)
            线层.addWidget(线)
            线外.setFixedHeight(1)
            块层.addWidget(线外)
        块层.addWidget(_字段行(x))
    层.addWidget(块)
    外.块 = 块
    return 外


class 面单页(QWidget):
    """转寄退货任务：左边任务小清单，右边按佐川面单从上往下抄的顺序（分组列表）。
    收件人一块；寄件人和品名一块；参考一块；评论和其他信息平时收起。手写面单用，不做复制按钮。
    整页只有一个滚动条（外面那个），这里的清单和详情都不自己滚。"""

    def __init__(self, 项):
        super().__init__()
        self.页们 = 项["面单"]
        层 = QHBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(16)
        左 = QVBoxLayout()
        左.setSpacing(6)
        左.addWidget(_组名("任务"))
        self.列表 = QListWidget()
        self.列表.setObjectName("任务列表")
        self.列表.setFixedWidth(220)
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        总高 = 4
        for 页 in self.页们:
            字 = f"<b>{页['序']}. {_字(页['类型'])}</b><br>"
            if 页["失败"]:
                字 += f"<span style='color:{色['坏']}'>● 没读到</span>"
            else:
                字 += f"<span style='font-family:{等宽}; color:{色['单号字']}'>{_字(页['单号']) or '&nbsp;'}</span>"
                if 页["要看数"]:
                    字 += f"<br><span style='color:{色['注意字']}'>● {页['要看数']} 处要看</span>"
            牌 = QLabel(字)
            牌.setWordWrap(True)          # 没有类型的任务（客诉、已回复…）标题长，换行显示，不截断
            牌.setContentsMargins(12, 8, 12, 8)
            牌.setStyleSheet(f"font-size:{主题.字号['正文']}px; background:transparent;")
            牌.setAttribute(Qt.WA_TransparentForMouseEvents)
            条 = QListWidgetItem()
            条.setToolTip(页["标题"])
            高 = 牌.heightForWidth(212) + 4
            条.setSizeHint(QSize(212, 高))
            总高 += 高
            self.列表.addItem(条)
            self.列表.setItemWidget(条, 牌)
        self.列表.setFixedHeight(max(总高, 48))
        self.列表.currentRowChanged.connect(self._显示)
        左.addWidget(self.列表)
        左.addStretch(1)
        层.addLayout(左)
        self.详情 = QWidget()
        self.详情层 = QVBoxLayout(self.详情)
        self.详情层.setContentsMargins(0, 0, 0, 0)
        self.详情层.setSpacing(16)
        层.addWidget(self.详情, 1)
        if self.页们:
            self.列表.setCurrentRow(0)
        else:
            self.详情层.addWidget(_标签("（这次没有读取任务）", f"color:{色['说明']};"))

    def _清空(self):
        while self.详情层.count():
            w = self.详情层.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()

    def _条(self, 文字, 种):
        l = _标签(文字, f"background:{色[种 + '底']}; color:{色[种 + '字']}; border-radius:12px; padding:10px 16px;"
                      f"font-size:{主题.字号['正文']}px;")
        return l

    def _显示(self, 行):
        if not (0 <= 行 < len(self.页们)):
            return
        页 = self.页们[行]
        self._清空()
        if 页["失败"]:
            self.详情层.addWidget(self._条("● " + 页["失败"], "坏"))
        if 页["总结"]:
            self.详情层.addWidget(self._条("● " + "\n".join(页["总结"]), "注意"))
        段们 = list(页["段们"])
        合并 = []
        i = 0
        while i < len(段们):              # 寄件人和品名合成一块（小柒 2026-10-25 示意图）
            名, 项们 = 段们[i]
            if 名.startswith("ご依頼主") and i + 1 < len(段们) and 段们[i + 1][0] == "品名":
                合并.append((f"{名} · 品名", list(项们) + list(段们[i + 1][1])))
                i += 2
                continue
            合并.append((名, 项们))
            i += 1
        for 名, 项们 in 合并:
            self.详情层.addWidget(_分组(名, 项们))
        for 段名, 说明, 项们 in 页["收起段"]:
            组 = _分组("", 项们)
            组.setVisible(False)
            钮 = _文字钮(f"› {段名}（{说明}，点开看）")
            钮.setStyleSheet("text-align:left; padding-left:16px;")

            def 切换(_=False, 组=组, 钮=钮, 段名=段名, 说明=说明):
                开 = not 组.isVisible()
                组.setVisible(开)
                钮.setText(f"˅ {段名}（{说明}，点这里收起）" if 开 else f"› {段名}（{说明}，点开看）")
            钮.clicked.connect(切换)
            self.详情层.addWidget(钮, 0, Qt.AlignLeft)
            self.详情层.addWidget(组)
        self.详情层.addStretch(1)


# ---------------- 一页 ----------------
def _内容(项, 状态栏):
    if 项.get("面单") is not None:
        return 面单页(项) if 项["面单"] else None
    if 项.get("分组") and 项["状态"] != "失败":
        return 区域单号页(项["分组"], 状态栏)
    if 项.get("数量表们") or any(行 for _, _, 行 in 项.get("表们", [])):
        return _数量内容(项, 状态栏)
    if 项["状态"] != "失败" and 项.get("文字") and not 项.get("结论"):
        字 = _标签(项["文字"])          # 只给文字的老模块
        字.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        return 字
    return None


def 一页(项, 状态栏, 发送):
    """一个模块的结果页（分栏视图的右边，小柒 2026-10-25）：
    整个详情只有一个滚动条；里面 结论 → 出错 / 提醒 → 内容（分组列表、表格）；最下面一行 飞书说明 + 文字按钮。
    发送(项, 说明字, 按钮)：点“发到飞书”时窗口去发。"""
    外 = QWidget()
    外.setStyleSheet(样式表)
    外层 = QVBoxLayout(外)
    外层.setContentsMargins(0, 0, 0, 0)
    外层.setSpacing(0)
    滚 = QScrollArea()
    滚.setWidgetResizable(True)
    滚.setFrameShape(QFrame.NoFrame)
    滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    内 = QWidget()
    内.setObjectName("页面")
    层 = QVBoxLayout(内)
    层.setContentsMargins(24, 20, 24, 16)
    层.setSpacing(16)
    层.addWidget(_结论条(项))
    if 项.get("错误们"):
        层.addWidget(_错误框(项["错误们"], "坏" if 项["状态"] == "失败" else "注意", 项.get("日志文件夹")))
    句们 = 提醒们(项)
    if 句们:
        层.addWidget(_提醒框(句们))
    内容 = _内容(项, 状态栏)
    if 内容 is not None:
        层.addWidget(内容)
    层.addStretch(1)
    滚.setWidget(内)
    外层.addWidget(滚, 1)
    底 = QWidget()
    底层 = QVBoxLayout(底)
    底层.setContentsMargins(24, 8, 24, 12)
    底层.addLayout(_底部(项, 发送))
    外层.addWidget(底)
    return 外

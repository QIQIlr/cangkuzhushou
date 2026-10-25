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

from PySide6.QtCore import QSize, Qt, Signal
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
            是起点 = 起点 and r == 0 and len(行们) > 2 and all(str(v) in ("0", "") for v in 行[1:])   # "" = 补的空区位
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
        self._自然列 = [self.columnWidth(c) for c in range(len(列名))]
        if getattr(self, "_最大列", None) and len(self._最大列) == len(self._自然列):   # 切换合计 / 合箱 / 单箱时不跳
            self._自然列 = [max(a, b) for a, b in zip(self._自然列, self._最大列)]
        self.自然宽 = sum(self._自然列) + 2 * self.frameWidth()       # 完整显示需要的最小宽度
        self.自然高 = self.horizontalHeader().height() + sum(self.rowHeight(r) for r in range(len(行们))) + 2 * self.frameWidth()
        强制 = getattr(self, "末合计强制", None)
        self.末合计 = 强制 if 强制 is not None else (len(列名) > 2 and "合计" in str(列名[-1]))
        self.拉到(getattr(self, "目标宽", 0))

    def _基础列(self):
        列们 = list(self._自然列)
        统一 = getattr(self, "_统一列", None)
        if 统一 and len(统一) == len(列们):            # 一页里所有表用同一套列宽（小柒 2026-10-25 补充 2）
            列们 = [max(a, b) for a, b in zip(列们, 统一)]
        return 列们

    def 拉到(self, 目标宽, 统一列=None):
        """自动排版用（2026-10-25 第三轮）：一页里所有表一样宽、各列对齐。
        每一列取全页同一位置那一列的最大宽度；多出来的宽度平均分给中间各区的列（日期列和合计列不动，各表对齐）。
        永远不比完整宽度窄。"""
        self.目标宽 = 目标宽
        if 统一列 is not None:
            self._统一列 = 统一列
        if not getattr(self, "_自然列", None):
            return
        列们 = self._基础列()
        n = len(列们)
        中间 = list(range(1, n - 1)) if self.末合计 and n > 2 else (list(range(1, n)) or [0])
        自然 = sum(列们) + 2 * self.frameWidth()
        多 = max(0, 目标宽 - 自然)
        for i, c in enumerate(中间):
            列们[c] += 多 // len(中间) + (多 % len(中间) if i == 0 else 0)
        for c, w in enumerate(列们):
            self.setColumnWidth(c, w)
        self.setFixedSize(max(自然, 目标宽), self.自然高)

    def 统一前宽(self):
        """按全页统一的列宽算，这张表完整显示要多宽。"""
        if not getattr(self, "_自然列", None):
            return 0
        return sum(self._基础列()) + 2 * self.frameWidth()
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


class 表块(QWidget):
    """一个仓库（或一个单独的区）的数量表：上面一行“名字 …… 合计 / 合箱拣货 / 单箱拣货”，下面白色圆角块里是表。
    宽度和高度由 表格排列 统一给（同一行的表一样宽、一样高）；表永远不比完整显示需要的宽度窄。"""

    def __init__(self, 表, 状态栏, 末合计=None):
        super().__init__()
        层 = QVBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(6)
        头 = QHBoxLayout()
        头.setSpacing(12)
        名 = _组名(表["名"])
        self.名宽 = 名.sizeHint().width()
        头.addWidget(名)
        头.addStretch(1)
        self.格 = 数量表格(状态栏)
        self.格.末合计强制 = 末合计
        self.段钮们 = []
        视图们 = 表["视图们"]
        if len(视图们) > 1:
            轨 = QFrame()                  # 规范“分段控件”：灰色轨道，选中那段白底；放在标题行右边
            轨.setObjectName("分段")
            轨层 = QHBoxLayout(轨)
            轨层.setContentsMargins(2, 2, 2, 2)
            轨层.setSpacing(2)
            头.addWidget(轨)
            组 = QButtonGroup(self)
            for k, (视图名, 列, 行) in enumerate(视图们):
                钮 = QPushButton(视图名)
                钮.setProperty("seg", "1")
                钮.setCheckable(True)
                钮.setChecked(k == 0)
                钮.setCursor(Qt.PointingHandCursor)
                钮.clicked.connect(lambda _=False, 列=列, 行=行, 起=表["起点"]: self.格.填(列, 行, 起))
                组.addButton(钮)
                轨层.addWidget(钮)
                self.段钮们.append(钮)
        层.addLayout(头)
        # 切到合箱 / 单箱后表的宽度、高度不跳：先把每种看法都填一遍，记下最大的，再回到第一种
        宽们, 高们, 列们 = [], [], []
        for _, 列, 行 in 视图们:
            self.格.填(列, 行, 表["起点"])
            宽们.append(self.格.自然宽)
            高们.append(self.格.自然高)
            列们.append(list(self.格._自然列))
        self.格.填(视图们[0][1], 视图们[0][2], 表["起点"])
        self.格._自然列 = self.格._最大列 = [max(c) for c in zip(*列们)]   # 每列取各种看法里最宽的，切换时不跳
        self.格.自然宽, self.格.自然高 = max(宽们), max(高们)
        self.统一列 = None
        self.格.拉到(0)
        self.卡 = _白块(self.格, 8)
        层.addWidget(self.卡, 0, Qt.AlignLeft | Qt.AlignTop)
        层.addStretch(1)
        self.头高 = 32

    def 最小宽(self):
        段宽 = sum(b.width() for b in self.段钮们) + 4 * len(self.段钮们) + 4 if self.段钮们 else 0
        return max(self.格.统一前宽() + 16, self.名宽 + 12 + 段宽)

    def 自然高(self):
        return self.头高 + 6 + self.格.自然高 + 16

    def 定大小(self, 宽, 高):
        self.格.拉到(宽 - 16, self.统一列)
        self.卡.setFixedSize(宽, 高 - self.头高 - 6)
        self.setFixedSize(宽, 高)


class 表格排列(QWidget):
    """数量表自动排版（规范 v1.4“自动排版”，小柒 2026-10-25 第三轮）：
    先算每张表完整显示要多宽；当前宽度放得下几张完整的表，一行就放几张（全放得下就全并排，一张都放不下就一张一行）；
    同一行的表一样宽、一样高（矮的补空白）；窗口大小一变就重新排。任何宽度都不会出现左右滚动、不会截掉列。"""
    间距 = 16

    def __init__(self, 块们):
        super().__init__()
        self.块们 = 块们
        for 块 in 块们:
            块.setParent(self)
        # 所有表的切换按钮一样大
        钮们 = [b for 块 in 块们 for b in 块.段钮们]
        if 钮们:
            宽 = max(b.sizeHint().width() for b in 钮们)
            for b in 钮们:
                b.setFixedWidth(宽)
        # 一页里所有表用同一套列（小柒 2026-10-25 补充 2）：同一位置的列在每张表里一样宽，日期对日期、区对区、合计对合计
        长们 = {len(块.格._最大列) for 块 in 块们}
        if len(长们) == 1:
            统一列 = [max(c) for c in zip(*(块.格._最大列 for 块 in 块们))]
            for 块 in 块们:
                块.统一列 = 统一列
                块.格._统一列 = 统一列
        self._上次宽 = None
        self._排(900)

    def _每行几张(self, 总宽):
        统一宽 = max(b.最小宽() for b in self.块们)          # 一页里所有白框一样宽
        n = len(self.块们)
        for k in range(n, 0, -1):
            if k * 统一宽 + self.间距 * (k - 1) <= 总宽:
                return k
        return 1

    def _排(self, 总宽):
        if 总宽 == self._上次宽 or 总宽 <= 0:
            return
        self._上次宽 = 总宽
        k = self._每行几张(总宽)
        y = 0
        for i in range(0, len(self.块们), k):
            行 = self.块们[i:i + k]
            最宽 = max(b.最小宽() for b in self.块们)            # 全页统一，上下排时右边也对齐
            # 一行几张平分这一行的宽度，但最多拉宽到完整宽度的 1.5 倍（不然全屏时一张表会被拉得很稀）
            宽 = max(最宽, min((总宽 - self.间距 * (k - 1)) // k, int(最宽 * 1.5)))
            高 = max(b.自然高() for b in self.块们[i:i + k])
            for j, b in enumerate(行):
                b.定大小(宽, 高)
                b.move(j * (宽 + self.间距), y)
                b.show()
            y += 高 + 20
        self.setFixedHeight(max(0, y - 20))

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self._排(self.width())


def _数量内容(项, 状态栏):
    表们 = 项.get("数量表们") or [{"名": 名, "视图们": [("合计", 列, 行)], "起点": False}
                             for 名, 列, 行 in 项.get("表们", []) if 行]
    if not 表们:
        return None

    def 区数(列):
        合 = len(列) > 2 and "合计" in str(列[-1])
        return len(列) - 1 - (1 if 合 else 0), 合

    槽 = max(区数(列)[0] for 表 in 表们 for _, 列, _ in 表["视图们"])
    要合计 = any(区数(列)[1] for 表 in 表们 for _, 列, _ in 表["视图们"])

    def 补(列, 行们):
        """区少的表：区从左往右排，后面空着的区位补空格，合计放最后一格（小柒 2026-10-25 补充 2）。表里的数字不变。"""
        n, 合 = 区数(列)
        空 = 槽 - n
        if 空 <= 0 and 合 == 要合计:
            return 列, 行们
        def 一行(r):
            r = list(r)
            头, 区们, 尾 = r[:1], r[1:1 + n], (r[1 + n:] if 合 else [])
            return 头 + 区们 + [""] * 空 + (尾 if 合 else ([""] if 要合计 else []))
        return 一行(列), [一行(r) for r in 行们]

    if len(表们) > 1:
        表们 = [{**表, "视图们": [(名,) + 补(列, 行们) for 名, 列, 行们 in 表["视图们"]]} for 表 in 表们]
    return 表格排列([表块(表, 状态栏, 要合计 if len(表们) > 1 else None) for 表 in 表们])

# ---------------- 样子 B：区域和单号（无任务包裹，2026-10-25 第三轮整页重做） ----------------
class 单号格(QLabel):
    """一个单号格子：灰色序号 + 单号。单击选中（按住 Ctrl 可以多选），双击复制这一个。"""

    def __init__(self, 页, 序, 号, 位数):
        super().__init__(f"<span style='color:{色['说明']}'>{str(序).zfill(位数)}</span>&nbsp;&nbsp;{_字(号)}")
        self.页, self.号 = 页, 号
        self.选中 = False
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("双击复制这个单号；按住 Ctrl 点几个，再按 Ctrl+C 复制选中的")
        # 宽度完全由“每行几个”平分决定、不看文字长短：各区的格子上下对齐，也不会把页面撑宽
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._上色()

    def _上色(self):
        self.setStyleSheet(f"QLabel {{ font-size:{主题.字号['行标题']}px; padding:6px 10px; border-radius:8px;"
                           f" background:{色['选中'] if self.选中 else 'transparent'}; }}")

    def 设选中(self, 选):
        self.选中 = 选
        self._上色()

    def mousePressEvent(self, 事件):
        self.页.点格(self, bool(事件.modifiers() & Qt.ControlModifier))

    def mouseDoubleClickEvent(self, 事件):
        self.页.复制([self.号], f"已复制 {self.号}")


class 区域单号页(QWidget):
    """无任务包裹：一页全部列出（小柒 2026-10-25 第三轮）。
    最上面一块总览（每个区几个 + 合计，0 个灰色、没查到红色）；下面每个有单号的区一块：
    块外“E区 3 个”+ 右边“复制 E区 全部”；块里单号排成格子，每行几个跟窗口宽度走，全页所有区每行个数一样（上下对齐）。
    复制：双击一个单号复制一个；Ctrl 多选后 Ctrl+C；每区“复制全部”；顶部“复制全部区”。复制出来的格式和以前一样。"""

    def __init__(self, 分组, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.setFocusPolicy(Qt.ClickFocus)
        self.明细 = {区: (单号们, 文字) for 区, 单号们, 文字 in 分组["明细"]}
        self.格们 = []                  # 全部单号格子（按区、按顺序）
        self.区格们 = []                # [(网格布局, [格子…])]，每个区一个
        self.列数 = 0
        层 = QVBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(16)

        # —— 总览：每个区一格 + 合计，一行排开（窄了自动换行）——
        头 = QHBoxLayout()
        头.addWidget(_组名("各区数量"))
        头.addStretch(1)
        if len(self.明细) > 1:
            全 = _小钮("复制全部区")
            全.clicked.connect(lambda: self.复制(None, "已复制全部区的单号"))
            头.addWidget(全)
        层.addLayout(头)
        总览块 = QFrame()
        总览块.setProperty("card", "1")
        self.总览格 = QGridLayout(总览块)
        self.总览格.setContentsMargins(8, 8, 8, 8)
        self.总览格.setSpacing(0)
        self.总览项 = []
        _, 总行 = 分组["总览"]
        self.区们 = []
        for 区, 数, 标 in 总行:
            区名, 数字 = str(区).replace("**", ""), str(数).replace("**", "")
            合计 = str(区).startswith("**")
            颜色 = 色["坏"] if 数字 == "失败" else 色["灰"] if 数字 == "0" else 色["字"]
            说 = "没查到" if 数字 == "失败" else 数字
            格 = QLabel(f"<span style='color:{色['说明']}; font-size:{主题.字号['说明'] + 1}px'>{_字(区名)}</span><br>"
                       f"<span style='color:{颜色}; font-size:{主题.字号['大数字']}px; font-weight:bold'>{_字(说)}</span>")
            格.setAlignment(Qt.AlignCenter)
            格.setMinimumWidth(84)
            格.setStyleSheet("padding:6px 4px;" + (f"background:{色['面2']}; border-radius:8px;" if 合计 else ""))
            self.总览项.append(格)
            if not 合计:
                self.区们.append((区名, 数字, str(标)))
        层.addWidget(总览块)

        # —— 每个区一块 ——
        位数 = max(2, len(str(max([len(v[0]) for v in self.明细.values()] or [1]))))
        测 = QLabel(f"{'0' * 位数}  261012-001766")
        测.setStyleSheet(f"font-size:{主题.字号['行标题']}px; padding:6px 10px;")
        self.格宽 = 测.sizeHint().width() + 16
        for 区名, 数字, 标 in self.区们:
            if 区名 not in self.明细 and 数字 != "失败":
                continue                         # 0 个的区只在总览里显示
            块头 = QHBoxLayout()
            块头.setSpacing(10)
            块头.addWidget(_组名(f"{区名}  {len(self.明细[区名][0])} 个" if 区名 in self.明细 else 区名))
            if 数字 == "失败":
                块头.addWidget(状态标签("失败", "没查到", 醒目=True))
            elif "不完整" in 标:
                块头.addWidget(状态标签("不完整", 醒目=True))
            块头.addStretch(1)
            if 区名 in self.明细:
                钮 = _小钮(f"复制 {区名} 全部")
                钮.clicked.connect(lambda _=False, 区=区名: self.复制(区, f"已复制 {区} {len(self.明细[区][0])} 个单号"))
                块头.addWidget(钮)
            层.addLayout(块头)
            if 区名 in self.明细:
                块 = QFrame()
                块.setProperty("card", "1")
                网 = QGridLayout(块)
                网.setContentsMargins(8, 8, 8, 8)
                网.setHorizontalSpacing(4)
                网.setVerticalSpacing(2)
                单号们 = self.明细[区名][0]
                格们 = [单号格(self, i, 号, 位数) for i, 号 in enumerate(单号们, 1)]
                self.格们 += 格们
                self.区格们.append((网, 格们))
                层.addWidget(块)
            说明 = ("这个区没查到（不是 0），原因见上面。" if 数字 == "失败" else
                  "读到的单号比页面上的总数少，请到 WMS 核对。" if "不完整" in 标 else "")
            if 说明:
                脚 = _标签(说明, f"color:{色['说明']}; font-size:{主题.字号['说明']}px; padding-left:16px;")
                层.addWidget(脚)
        层.addWidget(_标签("双击一个单号就复制这一个；按住 Ctrl 点几个，再按 Ctrl+C 复制选中的。",
                         f"color:{色['说明']}; font-size:{主题.字号['说明']}px; padding-left:16px;"))
        self._排(900)

    def _排(self, 宽):
        """全页统一的每行个数：按可用宽度能放下几个完整的格子算；总览也按同样的规则排。"""
        列 = max(1, (宽 - 16) // self.格宽)

        if 列 == self.列数:
            return
        self.列数 = 列
        for 网, 格们 in self.区格们:
            for 格 in 格们:
                网.removeWidget(格)
            for 空 in getattr(网, "_空们", []):
                网.removeWidget(空)
                空.deleteLater()
            for i, 格 in enumerate(格们):
                网.addWidget(格, i // 列, i % 列)
            # 单号比一行少的区：后面补看不见的空格子，这样列宽和别的区一样，格子上下对齐
            网._空们 = []
            for c in range(len(格们), 列):
                空 = QWidget(网.parentWidget())
                空.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                网.addWidget(空, 0, c)
                网._空们.append(空)
            for c in range(列):                 # 空着的列也占同样宽度：各区格子上下对齐
                网.setColumnStretch(c, 1)
            for c in range(列, 60):
                网.setColumnStretch(c, 0)
        总列 = max(1, min(len(self.总览项), (宽 - 16) // 90))
        for 项 in self.总览项:
            self.总览格.removeWidget(项)
        for i, 项 in enumerate(self.总览项):
            self.总览格.addWidget(项, i // 总列, i % 总列)

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self._排(self.width())

    # —— 选中和复制 ——
    def 点格(self, 格, 多选):
        if not 多选:
            for g in self.格们:
                if g is not 格 and g.选中:
                    g.设选中(False)
            格.设选中(True)
        else:
            格.设选中(not 格.选中)
        self.setFocus()

    def keyPressEvent(self, 事件):
        if 事件.matches(QKeySequence.Copy):
            号们 = [g.号 for g in self.格们 if g.选中]
            if 号们:
                self.复制(号们, f"已复制 {号们[0]}" if len(号们) == 1 else f"已复制 {len(号们)} 个单号")
        else:
            super().keyPressEvent(事件)

    def 复制(self, 内容, 提示):
        """内容：单号列表（每行一个）；区名（这个区的“标题行 + 序号<Tab>单号”，和以前一样）；None = 全部区。"""
        if isinstance(内容, list):
            文字 = "\n".join(内容)
        elif 内容 is None:
            文字 = "\n\n".join(v[1] for v in self.明细.values())
        else:
            文字 = self.明细[内容][1]
        QApplication.clipboard().setText(文字)
        if self.状态栏 is not None:
            self.状态栏.showMessage(提示, 4000)


def _小钮(文字):
    b = QPushButton(文字)
    b.setProperty("kind", "small")
    b.setCursor(Qt.PointingHandCursor)
    return b


# ---------------- 样子 C：任务和面单 ----------------
def _字段行(x):
    """明细里的一行“字段名 + 内容”（规范 v1.1：字段名 13px 灰、内容 15px 黑，全软件只用这一对；
    电话、单号、邮编也用同一种字，v1.3 起不再换等宽字）。要看的字段内容用橙色，提醒写在下面。"""
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
    字族 = ""          # 规范 v1.3：明细里所有内容同一种字体（微软雅黑 UI）、同一字号、同一粗细，不再换等宽字
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


class 任务清单(QFrame):
    """转寄退货任务左边的任务小清单（2026-10-25 第二轮：原来用列表控件拼的，第一条下面会露出一条白条）。
    白色圆角块里一行一个任务：粗体“序号. 类型”、单号、橙色“几处要看”；选中那行浅蓝底；行间细线从文字处开始。
    用法和列表一样：count()、currentRow()、setCurrentRow(i)、currentRowChanged 信号。"""
    currentRowChanged = Signal(int)

    def __init__(self, 页们):
        super().__init__()
        self.setProperty("card", "1")
        self.setFixedWidth(220)
        层 = QVBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(0)
        self.行们 = []
        self._当前 = -1
        for i, 页 in enumerate(页们):
            if i:
                线外 = QWidget()
                线层 = QHBoxLayout(线外)
                线层.setContentsMargins(12, 0, 0, 0)
                线 = QFrame()
                线.setObjectName("行线")
                线.setFixedHeight(1)
                线层.addWidget(线)
                线外.setFixedHeight(1)
                层.addWidget(线外)
            字 = f"<b>{页['序']}. {_字(页['类型'])}</b><br>"
            if 页["失败"]:
                字 += f"<span style='color:{色['坏字']}'>● 没读到</span>"
            else:
                字 += f"<span style='color:{色['次字']}'>{_字(页['单号']) or '&nbsp;'}</span>"
                if 页["要看数"]:
                    字 += f"<br><span style='color:{色['注意字']}'>● {页['要看数']} 处要看</span>"
            行 = QLabel(字)
            行.setWordWrap(True)              # 没有类型的任务（客诉、已回复…）标题长，换行显示，不截断
            行.setToolTip(页["标题"])
            行.setCursor(Qt.PointingHandCursor)
            行.setContentsMargins(12, 10, 12, 10)
            行.mousePressEvent = lambda _e, n=i: self.setCurrentRow(n)
            层.addWidget(行)
            self.行们.append(行)
        self._上色()

    def count(self):
        return len(self.行们)

    def currentRow(self):
        return self._当前

    def setCurrentRow(self, i):
        if i == self._当前 or not (0 <= i < len(self.行们)):
            return
        self._当前 = i
        self._上色()
        self.currentRowChanged.emit(i)

    def _上色(self):
        末 = len(self.行们) - 1
        for i, 行 in enumerate(self.行们):
            圆 = ("border-top-left-radius:12px; border-top-right-radius:12px;" if i == 0 else "") + \
                 ("border-bottom-left-radius:12px; border-bottom-right-radius:12px;" if i == 末 else "")
            底 = 色["选中"] if i == self._当前 else "transparent"
            行.setStyleSheet(f"QLabel {{ background:{底}; font-size:{主题.字号['正文']}px; {圆} }}")


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
        self.列表 = 任务清单(self.页们)          # 自己画的清单：每一行的底色、选中、分隔线连成一体，不会露出白条
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

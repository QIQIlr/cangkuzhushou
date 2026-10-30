# 职责：数量表那一块——只读的数量表（QTableWidget）、表块、自动排版（一页里所有表一样宽、各列对齐）。
#   从 公共\结果页.py 拆出来的（2026-10-31，纯搬家，函数体一个字没改）。


from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QFrame, QHBoxLayout, QPushButton, QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from 公共.结果页.零件 import _色, _白块, _组名, 色


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

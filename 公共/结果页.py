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
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from 公共.界面 import 主题  # noqa: E402
from 公共.界面.组件 import 状态标签  # noqa: E402

# 颜色统一来自 公共\界面\主题.py（2026-10-24 整体重新设计）；这里只是起个结果页用惯的名字
_主 = 主题.色
色 = {"好": _主["好"], "好底": _主["好底"], "注意": _主["注意"], "注意底": _主["注意底"], "注意线": _主["注意线"],
     "注意字": _主["注意字"], "坏": _主["坏"], "坏底": _主["坏底"], "坏线": _主["坏线"], "坏字": _主["坏字"],
     "次": _主["次"], "次底": _主["次底"], "灰": _主["灰"], "说明": _主["弱字"],
     "选中": _主["主浅"], "今天": _主["主浅"], "合计底": _主["面2"], "段": _主["底"], "线": _主["线"], "字": _主["字"]}
等宽 = 主题.等宽
状态样子 = {"成功": ("✔ 成功", "好"), "无数据": ("○ 无数据", "次"), "不完整": ("⚠ 不完整", "注意"), "失败": ("✖ 失败", "坏")}
样式表 = f"""
QTableWidget#数量表 {{ gridline-color:{色['线']}; border:1px solid {色['线']}; border-radius:8px;
    selection-background-color:{色['选中']}; selection-color:{色['字']}; }}
QListWidget#任务列表, QListWidget#区域列表, QListWidget#单号列表 {{ border:1px solid {色['线']}; border-radius:8px; }}
QListWidget#任务列表::item, QListWidget#区域列表::item {{ border-bottom:1px solid {色['线']}; }}
QListWidget#任务列表::item:selected, QListWidget#区域列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
QListWidget#单号列表::item {{ border-radius:6px; }}
QListWidget#单号列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
"""

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
    符 = "✖" if 状 == "失败" else "⚠" if 状 == "不完整" or 要看数(项) or 提醒们(项) else "○" if 状 == "无数据" else "✔"
    数 = 项.get("数量")
    后 = f"  {数}" + (" 条" if 项.get("面单") is not None else "") if 数 is not None and 状 != "失败" else ""
    return f"{符} {项['显示名']}{后}"


def _结论条(项):
    行 = QHBoxLayout()
    行.setSpacing(10)
    左 = QVBoxLayout()
    左.setSpacing(4)
    眉 = QHBoxLayout()
    眉.setSpacing(8)
    眉.addWidget(状态标签(项["状态"]))
    if 要看数(项):
        眉.addWidget(状态标签("不完整", f"其中 {要看数(项)} 条要看一下"))
    眉.addWidget(_标签(项["显示名"], f"color:{色['说明']};", 可选=False, 换行=False))
    眉.addStretch(1)
    if 项.get("时间"):
        眉.addWidget(_标签(f"查询时间 {项['时间']:%m/%d %H:%M}", f"color:{色['说明']};", 换行=False))
    左.addLayout(眉)
    结论 = _标签(项.get("结论") or 项.get("标题") or 项["显示名"], "font-size:15pt; font-weight:bold;")
    左.addWidget(结论)
    行.addLayout(左, 1)
    return 行


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
            线.setStyleSheet(f"color:{色['坏线' if 种 == '坏' else '注意线']};")
            层.addWidget(线)
        层.addLayout(格)
    if len(去重) > 3:
        层.addWidget(_标签(f"还有 {len(去重) - 3} 个别的问题，详细的在日志里。"))
    if 日志文件夹:
        行 = QHBoxLayout()
        钮 = QPushButton("打开这次的日志")
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
        层.addWidget(_标签("⚠ " + s))
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
        return f"⚠ 不确定飞书发出去没有：{说明}（先去群里看一眼）", True
    return f"⚠ 飞书没发成功：{说明}", True


def _底部(项, 发送):
    行 = QHBoxLayout()
    if 项.get("不发飞书"):
        行.addWidget(_标签("只在窗口里看，不发飞书", f"color:{色['说明']};"), 1)
    else:
        文字, 坏 = 飞书说明(*项["飞书"])
        字 = _标签(文字, f"color:{色['坏'] if 坏 else 色['说明']};")
        行.addWidget(字, 1)
        钮 = QPushButton("再发一次到飞书" if 项["飞书"][0] == "成功" else "发到飞书")
        钮.setToolTip("手动把这个结果发到飞书群一次，不看“跑完自动发飞书”的开关。")
        钮.clicked.connect(lambda _=False: 发送(项, 字, 钮))
        行.addWidget(钮)
    if 项.get("附件"):
        b = QPushButton("打开 Excel")
        b.clicked.connect(lambda _=False, p=项["附件"]: _打开(p))
        行.addWidget(b)
    if 项.get("日志文件夹"):
        b = QPushButton("打开这次的日志")
        b.clicked.connect(lambda _=False, p=项["日志文件夹"]: _打开(p))
        行.addWidget(b)
    return 行


# ---------------- 样子 A：数量表 ----------------
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


def _数量内容(项, 状态栏):
    表们 = 项.get("数量表们") or [{"名": 名, "视图们": [("合计", 列, 行)], "起点": False}
                             for 名, 列, 行 in 项.get("表们", []) if 行]
    if not 表们:
        return None
    面板 = QWidget()
    层 = QVBoxLayout(面板)
    层.setContentsMargins(0, 0, 0, 0)
    层.setSpacing(6)
    for i, 表 in enumerate(表们):
        头 = QHBoxLayout()
        头.setSpacing(0)
        名 = _标签(表["名"], "font-weight:bold; font-size:11pt;" + ("margin-top:10px;" if i else ""), 换行=False)
        头.addWidget(名)
        头.addSpacing(14)
        格 = 数量表格(状态栏)
        视图们 = 表["视图们"]
        if len(视图们) > 1:
            轨 = QFrame()                  # 灰底轨道，选中那段变白（主题里的“分段”）
            轨.setObjectName("分段")
            轨层 = QHBoxLayout(轨)
            轨层.setContentsMargins(3, 3, 3, 3)
            轨层.setSpacing(2)
            头.addWidget(轨)
            组 = QButtonGroup(面板)
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
        层.addWidget(格, 0, Qt.AlignLeft)
    层.addStretch(1)
    滚 = QScrollArea()
    滚.setWidgetResizable(True)
    滚.setFrameShape(QFrame.NoFrame)
    滚.setWidget(面板)
    滚.viewport().setAutoFillBackground(False)
    面板.setAutoFillBackground(False)
    return 滚


# ---------------- 样子 B：区域和单号 ----------------
class 单号列表(QListWidget):
    """单号排成几列、大字等宽；双击复制一个，多选后 Ctrl+C 复制选中的（每行一个）。"""

    def __init__(self, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.setObjectName("单号列表")
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.Adjust)
        self.setUniformItemSizes(True)
        self.setGridSize(QSize(210, 30))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        字体 = QFont(等宽)
        字体.setPointSize(12)
        self.setFont(字体)
        self.itemDoubleClicked.connect(lambda 条: self._复制([条]))

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

    def __init__(self, 分组, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.明细 = {区: (单号们, 文字) for 区, 单号们, 文字 in 分组["明细"]}
        层 = QHBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        self.列表 = QListWidget()
        self.列表.setObjectName("区域列表")
        self.列表.setFixedWidth(230)
        self.区们 = []
        _, 总行 = 分组["总览"]
        for 区, 数, 标 in 总行:
            区名, 数字 = str(区).replace("**", ""), str(数).replace("**", "")
            if 数字 == "失败":
                说, 颜色 = "没查到", 色["坏"]
            elif 数字 == "0":
                说, 颜色 = "没有", 色["灰"]
            else:
                说, 颜色 = f"{数字} 个" + (" ⚠ 不完整" if "不完整" in str(标) else ""), None
            合计行 = str(区).startswith("**")
            牌 = QWidget()
            牌.setAttribute(Qt.WA_TransparentForMouseEvents)
            横 = QHBoxLayout(牌)
            横.setContentsMargins(10, 4, 12, 4)
            样 = ("font-weight:bold;" if 合计行 else "") + "font-size:11pt;"
            横.addWidget(_标签(区名, 样, 可选=False, 换行=False))
            横.addStretch(1)
            横.addWidget(_标签(说, 样 + (f"color:{颜色};" if 颜色 else ""), 可选=False, 换行=False))
            条 = QListWidgetItem()
            条.setSizeHint(QSize(200, 36))
            if 合计行:
                条.setFlags(Qt.ItemIsEnabled)
                条.setBackground(_色(色["合计底"]))
            self.列表.addItem(条)
            self.列表.setItemWidget(条, 牌)
            self.区们.append((区名, 数字))
        self.列表.currentRowChanged.connect(self._换区)
        层.addWidget(self.列表)
        右 = QVBoxLayout()
        头 = QHBoxLayout()
        self.标题 = _标签("", "font-weight:bold; font-size:11pt;", 换行=False)
        self.标题.setMinimumWidth(40)               # 窄的时候标题让位，复制按钮的字不被挤掉
        self.标题.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        头.addWidget(self.标题, 1)
        self.复制钮 = QPushButton("")
        self.复制钮.clicked.connect(self._复制全部)
        头.addWidget(self.复制钮)
        右.addLayout(头)
        self.单号们 = 单号列表(状态栏)
        右.addWidget(self.单号们, 1)
        self.空 = _标签("", f"color:{色['说明']}; font-size:11pt; padding:20px 4px;")
        self.空.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        右.addWidget(self.空, 1)
        self.提示 = _标签("双击一个单号就复制这一个；按住 Ctrl 点几个，再按 Ctrl+C 复制选中的。", f"color:{色['说明']}; font-size:9pt;")
        右.addWidget(self.提示)
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
        for w in (self.单号们, self.复制钮, self.提示):
            w.setVisible(有)
        self.空.setVisible(not 有)
        if not 有:
            self.标题.setText(区名 or "")
            self.空.setText("这个区没查到（不是 0），原因见上面的框。" if 数字 == "失败" else
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

    def _复制全部(self):
        if self.当前区 is None:
            return
        单号们, 文字 = self.明细[self.当前区]
        QApplication.clipboard().setText(文字)
        self.状态栏.showMessage(f"已复制 {self.当前区} {len(单号们)} 个单号", 5000)


# ---------------- 样子 C：任务和面单 ----------------
class 面单页(QWidget):
    """左边任务（两行：类型 / 单号，要看的标橙），右边按佐川面单从上往下抄的顺序；要抄的字大；
    提醒写在那一项下面；评论和其他信息平时收起。手写面单用，不做复制按钮。"""

    def __init__(self, 项):
        super().__init__()
        self.页们 = 项["面单"]
        self.展开 = set()
        层 = QHBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        分 = QSplitter(Qt.Horizontal)
        self.列表 = QListWidget()
        self.列表.setObjectName("任务列表")
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for 页 in self.页们:
            字 = f"<b>{页['序']}. {_字(页['类型'])}</b><br>"
            if 页["失败"]:
                字 += f"<span style='color:{色['坏']}'>✖ 没读到</span>"
            else:
                字 += f"<span style='font-family:{等宽}; color:#444'>{_字(页['单号']) or '&nbsp;'}</span>"
                if 页["要看数"]:
                    字 += f"&nbsp;&nbsp;<span style='color:{色['注意']}'>⚠ {页['要看数']} 处要看</span>"
            牌 = QLabel(字)
            牌.setWordWrap(True)          # 没有类型的任务（客诉、已回复…）标题长，换行显示，不截断
            牌.setContentsMargins(8, 6, 8, 6)
            牌.setAttribute(Qt.WA_TransparentForMouseEvents)
            条 = QListWidgetItem()
            条.setToolTip(页["标题"])
            条.setSizeHint(QSize(240, 牌.heightForWidth(240) + 2))
            self.列表.addItem(条)
            self.列表.setItemWidget(条, 牌)
        self.列表.currentRowChanged.connect(self._显示)
        右 = QScrollArea()
        右.setWidgetResizable(True)
        右.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.详情 = QLabel()
        self.详情.setWordWrap(True)
        self.详情.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.详情.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.详情.linkActivated.connect(self._点链接)
        self.详情.setContentsMargins(12, 8, 12, 12)
        右.setWidget(self.详情)
        分.addWidget(self.列表)
        分.addWidget(右)
        分.setStretchFactor(1, 3)
        分.setSizes([270, 730])
        层.addWidget(分)
        if self.页们:
            self.列表.setCurrentRow(0)
        else:
            self.详情.setText("（这次没有读取任务）")

    def _点链接(self, 键):
        行 = self.列表.currentRow()
        self.展开 ^= {(行, 键)}
        self._显示(行)

    def _框(self, 内容, 底, 线, 字色):
        return (f"<table width='100%' cellspacing='0' cellpadding='6' border='1' bgcolor='{底}' "
                f"style='border-color:{线}; border-style:solid; margin-bottom:6px'><tr><td style='color:{字色}'>{内容}</td></tr></table>")

    def _行(self, 行, 键前, x):
        展开 = (行, f"{键前}|{x['名']}") in self.展开
        if x.get("预览") and not 展开:
            值 = _字(x["预览"]) + f"<br><a href='{_字(键前 + '|' + x['名'])}'>{_字(x['还有'])}</a>"
        elif x.get("预览"):
            值 = _字(x["值"]) + f"<br><a href='{_字(键前 + '|' + x['名'])}'>收起</a>"
        else:
            值 = _字(x["值"])
        样 = f"font-size:{'15pt' if x.get('大') else '10.5pt'};"
        样 += f"font-family:{等宽};" if x.get("等宽") else ""
        样 += f"color:{色['灰'] if x.get('灰') else '#111111'};"
        内容 = f"<span style='{样}'>{值}</span>"
        if x.get("注"):
            内容 += f"<span style='color:{色['说明']}; font-size:9.5pt'>　{_字(x['注'])}</span>"
        if x.get("提醒"):
            内容 += f"<br><span style='color:{色['注意']}; font-size:10pt'>⚠ {_字(x['提醒'])}</span>"
        上 = "8" if x.get("大") else "2"
        return (f"<tr><td valign='top' width='84' style='color:{色['说明']}; font-size:10pt; padding-top:{上}px'>"
                f"{_字(x['名'])}</td><td valign='top'>{内容}</td></tr>")

    def _显示(self, 行):
        if not (0 <= 行 < len(self.页们)):
            return
        页 = self.页们[行]
        h = []
        if 页["失败"]:
            h.append(self._框("✖ " + _字(页["失败"]), 色["坏底"], 色["坏线"], 色["坏字"]))
        if 页["总结"]:
            h.append(self._框("⚠ " + "<br>".join(_字(s) for s in 页["总结"]), 色["注意底"], 色["注意线"], 色["注意字"]))
        for 段名, 项们 in 页["段们"]:
            h.append(f"<table width='100%' cellspacing='0' cellpadding='3' bgcolor='{色['段']}' style='margin-top:8px'>"
                     f"<tr><td><b>{_字(段名)}</b></td></tr></table>")
            h.append("<table cellspacing='0' cellpadding='3' width='100%'>"
                     + "".join(self._行(行, 段名, x) for x in 项们) + "</table>")
        for 段名, 说明, 项们 in 页["收起段"]:
            键 = f"段|{段名}"
            开 = (行, 键) in self.展开
            h.append(f"<p style='margin-top:12px'><a href='{_字(键)}'>{'▾' if 开 else '▸'} {_字(段名)}</a>"
                     f"<span style='color:{色['说明']}'>　{_字(说明)}，{'点这里收起' if 开 else '点开看'}</span></p>")
            if 开:
                h.append("<table cellspacing='0' cellpadding='3' width='100%'>"
                         + "".join(self._行(行, 段名, x) for x in 项们) + "</table>")
        self.详情.setText("".join(h))


# ---------------- 一页 ----------------
def _内容(项, 状态栏):
    if 项.get("面单") is not None:
        return 面单页(项) if 项["面单"] else None
    if 项.get("分组") and 项["状态"] != "失败":
        return 区域单号页(项["分组"], 状态栏)
    if 项.get("数量表们") or any(行 for _, _, 行 in 项.get("表们", [])):
        return _数量内容(项, 状态栏)
    if 项["状态"] != "失败" and 项.get("文字") and not 项.get("结论"):
        滚 = QScrollArea()          # 只给文字的老模块
        滚.setWidgetResizable(True)
        滚.setFrameShape(QFrame.NoFrame)
        字 = _标签(项["文字"])
        字.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        滚.setWidget(字)
        return 滚
    return None


def 一页(项, 状态栏, 发送):
    """一个模块的结果页。发送(项, 说明字, 按钮)：点“发到飞书”时窗口去发。"""
    外 = QWidget()
    外.setStyleSheet(样式表)
    层 = QVBoxLayout(外)
    层.setContentsMargins(22, 18, 22, 14)
    层.setSpacing(12)
    层.addLayout(_结论条(项))
    if 项.get("错误们"):
        层.addWidget(_错误框(项["错误们"], "坏" if 项["状态"] == "失败" else "注意", 项.get("日志文件夹")))
    句们 = 提醒们(项)
    if 句们:
        层.addWidget(_提醒框(句们))
    内容 = _内容(项, 状态栏)
    if 内容 is not None:
        层.addWidget(内容, 1)
    else:
        层.addStretch(1)
    线 = QFrame()
    线.setFrameShape(QFrame.HLine)
    线.setFixedHeight(1)
    线.setStyleSheet(f"background:{色['线']}; border:none;")
    层.addWidget(线)
    层.addLayout(_底部(项, 发送))
    return 外

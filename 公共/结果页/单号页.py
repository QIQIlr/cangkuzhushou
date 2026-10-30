# 职责：区域和单号那一块——单号格、区域单号页（总览 + 每个区一格一格的单号 + 复制 + 找单号）。
#   从 公共\结果页.py 拆出来的（2026-10-31，纯搬家，函数体一个字没改）。


from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from 公共.界面 import 主题
from 公共.界面.组件 import 状态标签
from 公共.结果页.零件 import _字, _标签, _组名, _小钮

色 = 主题.色


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
        self.搜索 = None
        if self.明细:              # 找单号（2026-10-29 界面评审 B4）：输入后几位，回车跳到那一格、选中并复制
            self.搜索 = QLineEdit()
            self.搜索.setPlaceholderText("找单号：输入后几位，回车")
            self.搜索.setFixedWidth(220)
            self.搜索.setClearButtonEnabled(True)
            self.搜索.returnPressed.connect(self._找单号)
            self.搜索.textChanged.connect(lambda 字: None if 字 else self._标红(False))
            头.addWidget(self.搜索)
        if len(self.明细) > 1:
            全 = _小钮("复制全部区")
            全.clicked.connect(lambda: self.复制(None, "已复制全部区的单号", 全))
            头.addWidget(全)
        层.addLayout(头)
        总览块 = QFrame()
        总览块.setProperty("card", "1")
        self.总览格 = QGridLayout(总览块)
        self.总览格.setContentsMargins(8, 8, 8, 8)
        self.总览格.setSpacing(0)
        self.总览格.setHorizontalSpacing(8)
        # 各区数量靠左挨着排，多出来的宽度留在右边（以前平分整行，几个数字隔得很远；2026-10-29 界面评审 B3）
        self.总览格.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.总览项 = []
        _, 总行 = 分组["总览"]
        self.区们 = []
        for 区, 数, 标 in 总行:
            区名, 数字 = str(区).replace("**", ""), str(数).replace("**", "")
            合计 = str(区).startswith("**")
            # “30+” = 有区没查到、至少这么多：橙色（小柒 2026-10-28 确认效果图）
            颜色 = 色["坏"] if 数字 == "失败" else 色["灰"] if 数字 == "0" else 色["注意"] if 数字.endswith("+") else 色["字"]
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
                钮.clicked.connect(lambda _=False, 区=区名, b=钮: self.复制(区, f"已复制 {区} {len(self.明细[区][0])} 个单号", b))
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

    # —— 找单号 ——
    def _标红(self, 红):
        self.搜索.setStyleSheet(f"QLineEdit {{ border: 1px solid {色['坏']}; }}" if 红 else "")

    def _找单号(self):
        """完整单号或后几位：找到就选中那一格、滚过去、复制；这次结果里没有就把框标红（只是这次结果里没有，不代表 WMS 里没有）。"""
        找 = self.搜索.text().strip().upper()
        if not 找:
            return
        中 = next((g for g in self.格们 if g.号.upper() == 找), None) or \
            next((g for g in self.格们 if g.号.upper().endswith(找)), None)
        if 中 is None:
            self._标红(True)
            if self.状态栏 is not None:
                self.状态栏.showMessage(f"这次的结果里没有“{找}”", 4000)
            return
        self._标红(False)
        for g in self.格们:
            if g is not 中 and g.选中:
                g.设选中(False)
        中.设选中(True)
        滚 = self.parentWidget()
        while 滚 is not None and not isinstance(滚, QScrollArea):
            滚 = 滚.parentWidget()
        if 滚 is not None:
            滚.ensureWidgetVisible(中, 40, 80)
        self.复制([中.号], f"已复制 {中.号}")

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

    def 复制(self, 内容, 提示, 钮=None):
        """内容：单号列表（每行一个）；区名（这个区的“标题行 + 序号<Tab>单号”，和以前一样）；None = 全部区。"""
        if isinstance(内容, list):
            文字 = "\n".join(内容)
        elif 内容 is None:
            文字 = "\n\n".join(v[1] for v in self.明细.values())
        else:
            文字 = self.明细[内容][1]
        QApplication.clipboard().setText(文字)
        if 钮 is not None:
            self._复制好了(钮)
        if self.状态栏 is not None:
            self.状态栏.showMessage(提示, 4000)

    @staticmethod
    def _复制好了(钮):
        """点了“复制”的按钮自己变成“已复制 ✓”1.5 秒再变回来：眼睛在单号区，不用去看窗口最底下（2026-10-29 界面评审 A5）。"""
        if 钮.property("原文") is None:            # 连点两下：记住的还是最早的字，不会变不回来
            钮.setProperty("原文", 钮.text())
            钮.setMinimumWidth(钮.width())          # 钉住宽度，换字时按钮不缩、旁边的东西不跳
        钮.setText("已复制 ✓")
        次 = (钮.property("复制次") or 0) + 1
        钮.setProperty("复制次", 次)

        def 还原():
            try:
                if 钮.property("复制次") != 次:     # 中间又点了一次：等最后那次的计时
                    return
                钮.setText(钮.property("原文"))
                钮.setProperty("原文", None)
                钮.setMinimumWidth(0)
            except RuntimeError:                   # 已经切到别的结果、按钮没了
                pass
        QTimer.singleShot(1500, 还原)

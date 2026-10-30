# 职责：任务和面单那一块——面单明细的一行、分组、左侧任务清单、面单页。
#   从 公共\结果页.py 拆出来的（2026-10-31，纯搬家，函数体一个字没改）。


from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from 公共.界面 import 主题
from 公共.结果页.零件 import 要看数, _字, _标签, _组名, _文字钮

色 = 主题.色
字段名宽 = 84        # 面单明细里“字段名”那一列的固定宽度（数字再长也不挤）


# ---------------- 样子 C：任务和面单 ----------------
def _字段行(x):
    """明细里的一行“字段名 + 内容”（规范 v1.1：字段名 13px 灰、内容 15px 黑，全软件只用这一对；
    电话、单号、邮编也用同一种字，v1.3 起不再换等宽字）。要看的字段内容用橙色，提醒写在下面。"""
    w = QWidget()
    w.setMinimumHeight(主题.行高最小)
    层 = QHBoxLayout(w)
    层.setContentsMargins(16, 10, 16, 10)
    层.setSpacing(12)
    名 = _标签(x["名"], f"color:{色['说明']}; font-size:{主题.字号['字段名']}px; background:transparent;", 可选=False, 换行=False)
    名.setFixedWidth(字段名宽)
    层.addWidget(名, 0, Qt.AlignTop)
    值层 = QVBoxLayout()
    值层.setSpacing(4)
    颜色值 = 色["注意字"] if x.get("提醒") else 色["弱字"] if x.get("灰") else 色["字"]
    字族 = ""          # 规范 v1.3：明细里所有内容同一种字体（微软雅黑 UI）、同一字号、同一粗细，不再换等宽字
    值样 = f"font-size:{主题.字号['字段值']}px; color:{颜色值}; {字族} background:transparent;"
    有预览 = bool(x.get("预览"))
    值 = _标签(x["预览"] if 有预览 else x["值"], 值样)
    值层.addWidget(值)
    if x.get("注"):
        值层.addWidget(_标签(x["注"], f"color:{色['说明']}; font-size:{主题.字号['说明']}px; background:transparent;"))
    if x.get("提醒"):
        值层.addWidget(_标签("● " + str(x["提醒"]), f"color:{色['注意字']}; font-size:{主题.字号['字段名']}px; background:transparent;"))
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
        if 页.get("没存") and not 页["失败"]:          # 上一次的结果：面单没存（不留客户信息，2026-10-29）
            self.详情层.addWidget(_标签(f"{页.get('标题', '')}\n（面单内容没有保存，要看请重新运行一次）",
                                     f"color:{色['说明']};"))
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

# 职责：工作台（打开软件看到的第一页）。
#   页眉：问候 + 日期 + 上次运行情况；右上：跑完自动发飞书（总开关，只在这里有）、只运行选中的、运行已启用模块（主按钮）
#   需要注意：上次运行有问题的模块、模块设置文件的提醒（都没有就不显示）
#   模块卡片：排列 = 运行顺序（拖动或上移/下移），开关 = 启用，改动立即保存到 模块设置.txt（和改版前一样）
#   右侧：选中模块的设置面板（就地改名、查询范围、这个模块跑完自动发；改动即保存）
#   飞书怎么发（小柒 2026-10-24 确认）：总开关 + 每个模块自己的开关，两个都开才自动发；卡片上写的是最终会不会发。
# 参考：Taskless（右侧编辑面板、一个主按钮）、Norix（问候、需要注意清单）、Watchlist（卡片上一个大数字 + 一行小字）。
from datetime import datetime

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QRegularExpression, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QRegularExpressionValidator
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QSizePolicy, QStyle, QToolTip,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

from 公共 import 模块参数, 模块设置, 查询范围
from 公共.界面 import 运行历史
from 公共.界面.主题 import 像素字, 字, 画图标, 状态样子, 色
from 公共.界面.弹窗 import 模块信息, 模块设置面板
from 公共.界面.组件 import 分组块, 卡片, 图标字, 开关, 按钮, 标签, 状态标签, 画开关, 页眉
from 公共.模块参数 import 显示名

星期 = "一二三四五六日"
# 每个模块一句话说明（来自 模块清单.md）；模块文件里写了 说明 = "……" 时优先用模块自己的
说明表 = {
    "无任务包裹": "已挂起、任务小类 = 无任务的包裹：各区数量和转运单号",
    "待审核": "任务状态 = 待审核的任务，按创建时间一天天列到今天",
    "待拣货": "合箱拣货 + 单箱拣货的待处理任务，按创建时间逐日列出",
    "待增值": "增值服务的待处理任务，按待增值时间逐日列出",
    "飞书任务明细": "读飞书“我负责的”，勾选后按佐川面单顺序显示，带邮编核对和日语品名参考",
}
说明角, 范围角, 飞书角, 上次角 = Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3, Qt.UserRole + 4
行高 = 80          # 2026-10-29 界面评审 B1：86 → 80，最小窗口 1000×640 时 5 个模块正好放得下（里面的字整体上移 3px，样子不变）


def _开着(索引):
    值 = 索引.data(Qt.CheckStateRole)
    return 值 is not None and Qt.CheckState(值) == Qt.Checked


def 模块说明(原名):
    _, _, 自己的 = 模块信息(原名)
    return 自己的 or 说明表.get(原名, "")


自动发字 = "跑完自动发飞书"


def 范围文字(原名, 总开关):
    """卡片上的两个小标签：查询范围、飞书最终会不会自动发（总开关和模块开关都开才发）。"""
    默认, 可发, _ = 模块信息(原名)
    参数 = 模块参数.读取(原名, 默认)
    if "查询范围" in 参数:
        范围 = "、".join(查询范围.整理(参数["查询范围"])[0]) or "没选范围，不会跑"
    elif 原名 == "飞书任务明细":
        范围 = "飞书 · 我负责的"
    else:
        范围 = ""
    if not 可发:
        飞 = "只在窗口看"
    elif 参数.get("发到飞书", True) and 总开关:
        飞 = 自动发字
    else:
        飞 = "不自动发"
    return 范围, 飞


class 名字编辑框(QLineEdit):
    """卡片上原地改名用的输入框：最多 20 个字，不能打 \\ / : * ? " < > |（Windows 文件名不允许，日志文件夹会用到名字）。"""

    def __init__(self, 父):
        super().__init__(父)
        self.setMaxLength(模块参数.最长)
        self.setValidator(QRegularExpressionValidator(QRegularExpression('[^\\\\/:*?"<>|]*'), self))
        self.setFont(像素字("行标题", 半粗=True))
        self.setToolTip("回车或点别处 = 保存；Esc = 不改")


class 模块卡片画法(QStyledItemDelegate):
    """把列表的每一行画成 iOS 分组列表里的一行（规范“模块行”）：
    浅灰 ≡ 拖动把手、开关在左，中间模块名 + 一行描述 + 一行灰色“范围 · 是否自动发”，右边大数字 + “● 成功 · 时间”，最右浅灰 ›。
    行与行之间细线从文字起头处开始。双击粗体名字 = 原地改名（小柒 2026-10-24）：回车或点别处保存，Esc 不改。"""

    def __init__(self, 父, 改名):
        super().__init__(父)
        self.改名 = 改名            # 改名(原名, 新名字)：工作台去检查、保存

    def _区(self, 选项):
        r = QRectF(选项.rect)
        开关区 = QRectF(r.left() + 36, r.center().y() - 13, 44, 26)
        return r, 开关区

    def _文左(self, 选项):
        return self._区(选项)[1].right() + 16

    def _名区(self, 选项, 索引=None, 编辑=False):
        """粗体名字所在的位置。编辑=True 时给输入框留宽一点。"""
        r, _ = self._区(选项)
        左 = self._文左(选项)
        可用 = r.right() - 160 - 左
        if 编辑:
            return QRectF(左 - 6, r.top() + 5, min(260, 可用 + 6), 30).toRect()
        名 = (索引.data(Qt.DisplayRole) or "") if 索引 is not None else ""
        宽 = min(QFontMetrics(像素字("行标题", 半粗=True)).horizontalAdvance(名) + 10, 可用)
        return QRectF(左 - 4, r.top() + 7, 宽 + 8, 26)

    def sizeHint(self, 选项, 索引):
        return QSize(选项.rect.width(), 行高)

    def paint(self, p, 选项, 索引):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r, 开关区 = self._区(选项)
        列表 = self.parent()
        外框 = QPainterPath()
        外框.addRoundedRect(QRectF(列表.viewport().rect()), 12, 12)
        p.setClipPath(外框)                       # 选中底色在第一行、最后一行也跟着圆角
        选中 = bool(选项.state & QStyle.State_Selected)
        开 = _开着(索引)
        if 选中:
            p.fillRect(r, QColor(色["选中"]))
        画图标(p, "拖", QPointF(r.left() + 18, r.center().y()), 12, 色["灰"])
        画开关(p, 开关区, 开)
        # 右边：› 和上次结果
        画图标(p, "右", QPointF(r.right() - 20, r.center().y()), 11, 色["灰"])
        右宽 = 124
        上次 = 索引.data(上次角)
        右区 = QRectF(r.right() - 36 - 右宽, r.top() + 11, 右宽, r.height() - 22)
        if 上次:
            种 = 状态样子.get(上次["状态"], (上次["状态"], "次", "圆"))[1]
            数 = 上次["数量"] if 上次["数量"] not in ("", None) else ("—" if 上次["状态"] != "失败" else "没查到")
            p.setFont(像素字("大数字", 半粗=True))
            p.setPen(QColor(色["坏"] if 上次["状态"] == "失败" else 色["字"]))
            p.drawText(右区.adjusted(0, 0, 0, -22), Qt.AlignRight | Qt.AlignVCenter, str(数))
            p.setFont(像素字("说明"))
            文 = f"{上次['状态']} · {上次['时间']:%m/%d %H:%M}"
            宽 = QFontMetrics(p.font()).horizontalAdvance(文)
            p.setPen(QColor(色.get(种 + "字", 色[种])))
            p.drawText(右区.adjusted(0, 右区.height() - 20, 0, 0), Qt.AlignRight | Qt.AlignVCenter, 文)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(色[种]))
            p.drawEllipse(QPointF(右区.right() - 宽 - 8, 右区.bottom() - 10), 3.5, 3.5)
        else:
            p.setFont(像素字("说明"))
            p.setPen(QColor(色["弱字"]))
            p.drawText(右区, Qt.AlignRight | Qt.AlignVCenter, "还没运行过")
        # 中间：名字、说明、范围 · 飞书
        左 = self._文左(选项)
        文宽 = int(右区.left() - 左 - 12)
        p.setFont(像素字("行标题", 半粗=True))
        p.setPen(QColor(色["字"] if 开 else 色["弱字"]))
        名 = 索引.data(Qt.DisplayRole) or ""
        p.drawText(QRectF(左, r.top() + 7, 文宽, 24), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(名, Qt.ElideRight, 文宽))
        p.setFont(像素字("说明"))
        p.setPen(QColor(色["弱字"]))
        说明 = 索引.data(说明角) or ""
        p.drawText(QRectF(左, r.top() + 32, 文宽, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(说明, Qt.ElideRight, 文宽))
        范围, 飞 = 索引.data(范围角) or ("", "")
        小字 = " · ".join(x for x in (范围, 飞) if x)
        p.setPen(QColor(色["主"] if 飞 == 自动发字 else 色["弱字"]))
        p.drawText(QRectF(左, r.top() + 52, 文宽, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(小字, Qt.ElideRight, 文宽))
        # 行间细线：从文字起头处开始，最后一行不画
        if 索引.row() < 索引.model().rowCount() - 1:
            p.setPen(QPen(QColor(色["线"]), 1))
            p.drawLine(QPointF(左, r.bottom()), QPointF(r.right(), r.bottom()))
        p.restore()
    # ---- 原地改名 ----
    def createEditor(self, 父, 选项, 索引):
        return 名字编辑框(父)

    def setEditorData(self, 编辑框, 索引):
        编辑框.setText(索引.data(Qt.DisplayRole) or "")
        编辑框.selectAll()

    def updateEditorGeometry(self, 编辑框, 选项, 索引):
        编辑框.setGeometry(self._名区(选项, 编辑=True))

    def setModelData(self, 编辑框, 模型, 索引):
        """回车或点别处：交给工作台检查、保存（卡片上的字由工作台在保存成功后更新）。"""
        self.改名(索引.data(Qt.UserRole), 编辑框.text().strip(), 编辑框)

    def editorEvent(self, 事件, 模型, 选项, 索引):
        """点开关 = 切换启用；空格键也可以。双击粗体名字 = 原地改名。其他点击交给列表（选中、拖动）。"""
        if 事件.type() == QEvent.MouseButtonDblClick and 事件.button() == Qt.LeftButton:
            if self._名区(选项, 索引).contains(事件.position()):
                self.parent().edit(索引)
            return True                     # 双击卡片其他地方：什么都不做
        if 事件.type() == QEvent.MouseButtonRelease and 事件.button() == Qt.LeftButton:
            _, 开关区 = self._区(选项)
            if 开关区.adjusted(-6, -8, 6, 8).contains(事件.position()):
                self._切换(模型, 索引)
                return True
        if 事件.type() == QEvent.KeyPress and 事件.key() in (Qt.Key_Space, Qt.Key_Select):
            self._切换(模型, 索引)
            return True
        return False

    def _切换(self, 模型, 索引):
        开 = _开着(索引)
        模型.setData(索引, Qt.Unchecked if 开 else Qt.Checked, Qt.CheckStateRole)


class 工作台(QWidget):
    运行请求 = Signal(list)          # 要运行的原名列表（按顺序）
    去看记录 = Signal()

    def __init__(self, 自动发设置值):
        super().__init__()
        self.setObjectName("页面")
        总 = QVBoxLayout(self)
        总.setContentsMargins(24, 20, 24, 16)
        总.setSpacing(16)

        self.头 = 页眉("", "")
        self.运行选中按钮 = 按钮("只运行选中的")
        self.运行选中按钮.setToolTip("先点选一个模块，或按住 Ctrl 点几个。没开的模块也会运行。")
        self.运行全部按钮 = 按钮("运行已启用模块", "主")
        self.自动发 = 开关("跑完自动发飞书")
        self.自动发.setChecked(bool(自动发设置值))
        self.自动发.setToolTip("总开关。打开：跑完后，标着“跑完自动发飞书”的模块会自动发到飞书群。\n"
                            "关上：哪个模块都不自动发；想发的时候，在结果下面点“发到飞书”。")
        self.头.右.addWidget(self.自动发)
        self.头.右.addSpacing(4)
        self.头.右.addWidget(self.运行选中按钮)
        self.头.右.addWidget(self.运行全部按钮)
        总.addWidget(self.头)

        中 = QHBoxLayout()
        中.setSpacing(24)
        左 = QVBoxLayout()
        左.setSpacing(16)
        self.左层 = 左
        # 需要注意（分组块；没有就不显示）
        self.注意组 = 分组块("需要注意")
        看 = 按钮("看运行记录", "文字")
        看.clicked.connect(self.去看记录)
        注意头 = QHBoxLayout()
        注意头.setContentsMargins(0, 0, 0, 0)
        self.注意组.layout().removeWidget(self.注意组.标题)
        注意头.addWidget(self.注意组.标题)
        注意头.addStretch(1)
        注意头.addWidget(看)
        self.注意组.layout().insertLayout(0, 注意头)
        左.addWidget(self.注意组)
        # 模块（分组列表）
        模块区 = QVBoxLayout()
        模块区.setSpacing(6)
        self.模块区 = 模块区
        行 = QHBoxLayout()
        行.setContentsMargins(0, 0, 0, 0)
        self.数量字 = 标签("", "组名")
        行.addWidget(self.数量字)
        行.addStretch(1)
        self.上移钮 = 按钮("", "图标", 图="上", 提示="上移（选中的模块往前跑）")
        self.下移钮 = 按钮("", "图标", 图="下", 提示="下移")
        self.上移钮.clicked.connect(lambda: self.移动(-1))
        self.下移钮.clicked.connect(lambda: self.移动(1))
        行.addWidget(self.上移钮)
        行.addWidget(self.下移钮)
        模块区.addLayout(行)
        self.提醒 = 标签("", 换行=True)            # 模块设置.txt 写错、发现新模块
        self.提醒.setStyleSheet(f"color:{色['注意字']}; background:{色['注意底']}; border-radius:12px; padding:8px 16px;")
        模块区.addWidget(self.提醒)
        self.列表 = QListWidget()
        self.列表.setStyleSheet("QListWidget::item, QListWidget::item:selected, QListWidget::item:hover "
                                "{ background: transparent; }")
        self.列表.setItemDelegate(模块卡片画法(self.列表, self._卡片改名))
        self.列表.setEditTriggers(QAbstractItemView.NoEditTriggers)   # 只有双击粗体名字才进入改名
        self.列表.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.列表.setDragDropMode(QAbstractItemView.InternalMove)
        self.列表.setDefaultDropAction(Qt.MoveAction)
        self.列表.setMouseTracking(True)
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.列表.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.列表.itemChanged.connect(lambda _: self.保存模块())
        self.列表.model().rowsMoved.connect(lambda *_: self.保存模块())
        self.列表.currentItemChanged.connect(self._选中变了)
        模块区.addWidget(self.列表)
        # 只留一行脚注（2026-10-29 界面评审 A3，小柒同意）：原来第二行“哪些模块会自动发飞书”去掉，
        # 每个模块发不发写在卡片第三行，总开关的解释在右上角开关的鼠标提示里，当前模块的写在右侧面板。
        模块区.addWidget(标签("拖动调整运行顺序（上面的先跑）；点开关启用或停用；按住 Ctrl 可以选多个。", "脚注", 换行=True))
        左.addLayout(模块区)
        左.addStretch(1)
        中.addLayout(左, 1)

        self.面板 = 模块设置面板()
        self.面板.setFixedWidth(320)
        self.面板.已保存.connect(self._设置保存了)
        中.addWidget(self.面板)
        self.自动发.toggled.connect(self._总开关变了)
        总.addLayout(中, 1)

        self.运行全部按钮.clicked.connect(lambda: self.运行请求.emit([名 for 名, 开 in self.当前清单() if 开]))
        self.运行选中按钮.clicked.connect(self._运行选中)
        self.刷新模块()

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self._列表高度()
        QTimer.singleShot(0, self._列表高度)      # 排版完、脚注按新宽度换好行以后再算一次

    def _列表高度(self):
        """白色块只包住这几个模块，下面不留一大块空白；模块多到放不下时才出滚动条。
        可用高度 = 页面高度 − 列表上下每一块的实际高度（页眉、需要注意、数量行、提醒、脚注和它们之间的间距）。
        以前减的是写死的 150，窗口一矮、文字一换行就不够，最小窗口时第 5 个模块被挤出去（2026-10-29 界面评审 B1）。"""
        需要 = max(1, self.列表.count()) * 行高 + 2
        总 = self.layout()
        边 = 总.contentsMargins()

        def 高(w, 宽):
            return w.heightForWidth(宽) if w.hasHeightForWidth() else w.sizeHint().height()

        占 = 边.top() + 边.bottom() + 高(self.头, self.width() - 边.left() - 边.right()) + 总.spacing()
        if not self.注意组.isHidden():
            占 += self.注意组.sizeHint().height() + self.左层.spacing()
        宽 = self.列表.width()
        块数 = 0
        for i in range(self.模块区.count()):
            项 = self.模块区.itemAt(i)
            w = 项.widget()
            if w is self.列表:
                块数 += 1
            elif w is None:
                占 += 项.sizeHint().height()       # 数量行（数量字 + 上移/下移）
                块数 += 1
            elif not w.isHidden():
                占 += 高(w, 宽)
                块数 += 1
        占 += self.模块区.spacing() * (块数 - 1)
        可用 = self.height() - 占
        self.列表.setFixedHeight(max(行高 * 2, min(需要, 可用)))
    # ---------- 模块列表（读写和改版前一样） ----------
    def 刷新模块(self):
        清单, 提醒 = 模块设置.读取()
        原名们 = [名 for 名, _ in 清单]
        self.上次 = 运行历史.上次结果们(原名们)
        当前 = self.列表.currentItem().data(Qt.UserRole) if self.列表.currentItem() else None
        self.列表.blockSignals(True)
        self.列表.clear()
        for 名, 开 in 清单:
            项 = QListWidgetItem(显示名(名))
            项.setData(Qt.UserRole, 名)          # 原名：程序靠它认模块，显示的字可以改
            项.setData(说明角, 模块说明(名))
            项.setData(范围角, 范围文字(名, self.自动发.isChecked()))
            项.setData(上次角, self.上次.get(名))
            项.setToolTip(模块说明(名) + (f"\n原名：{名}" if 显示名(名) != 名 else ""))
            项.setFlags(项.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)
            项.setFlags(项.flags() & ~Qt.ItemIsDropEnabled)
            项.setCheckState(Qt.Checked if 开 else Qt.Unchecked)
            self.列表.addItem(项)
            if 名 == 当前:
                self.列表.setCurrentItem(项)
        if self.列表.currentItem() is None and self.列表.count():
            self.列表.setCurrentRow(0)     # 打开就选中第一个，右边直接显示它的设置（2026-10-29 界面评审 A1，小柒同意）
        self.列表.blockSignals(False)
        提醒 = "\n".join(x for x in (模块参数.问题, 提醒) if x)   # 模块参数.json 读不出来时也在这里说
        self.提醒.setText(提醒)
        self.提醒.setVisible(bool(提醒))
        self._更新数字()
        self.面板.设总开关(self.自动发.isChecked())
        self._更新注意(清单)
        self._更新页眉()
        self._列表高度()
        self._选中变了(self.列表.currentItem())

    def 当前清单(self):
        return [[self.列表.item(i).data(Qt.UserRole), self.列表.item(i).checkState() == Qt.Checked]
                for i in range(self.列表.count())]

    def 保存模块(self):
        模块设置.保存(self.当前清单())
        self._更新数字()

    def 移动(self, 方向):
        行 = self.列表.currentRow()
        目标 = 行 + 方向
        if 行 < 0 or not (0 <= 目标 < self.列表.count()):
            return
        self.列表.blockSignals(True)
        项 = self.列表.takeItem(行)
        self.列表.insertItem(目标, 项)
        self.列表.setCurrentRow(目标)
        self.列表.blockSignals(False)
        self.保存模块()

    def 选中的(self):
        选中 = {项.data(Qt.UserRole) for 项 in self.列表.selectedItems()}
        return [名 for 名, _ in self.当前清单() if 名 in 选中]

    def _运行选中(self):
        self.运行请求.emit(self.选中的())

    def 设可用(self, 可用):
        for w in (self.运行全部按钮, self.运行选中按钮, self.列表, self.面板, self.上移钮, self.下移钮, self.自动发):
            w.setEnabled(可用)

    def _选中变了(self, 项, _旧=None):
        if 项 is None:
            self.面板.显示(None)
        else:
            self.面板.显示(项.data(Qt.UserRole), 项.data(说明角))

    def _设置保存了(self, 名):
        """右侧面板改了名字、范围或飞书开关：只更新这张卡片，不重搭面板（不然正在改的东西会跳）。"""
        for i in range(self.列表.count()):
            项 = self.列表.item(i)
            if 项.data(Qt.UserRole) == 名:
                项.setText(显示名(名))
                项.setData(范围角, 范围文字(名, self.自动发.isChecked()))
                项.setToolTip(模块说明(名) + (f"\n原名：{名}" if 显示名(名) != 名 else ""))
        self.列表.viewport().update()        # 卡片第三行“跑完自动发飞书 / 不自动发”马上跟着变

    def _卡片改名(self, 原名, 新名, 编辑框=None):
        """卡片上原地改名：和右边铅笔改的是同一个名字，检查规则也一样。"""
        问题 = self.面板.应用新名字(原名, 新名)
        if 问题 and 编辑框 is not None:
            QToolTip.showText(编辑框.mapToGlobal(编辑框.rect().bottomLeft()), "没改名：" + 问题, self.列表)

    def _总开关变了(self, 开):
        for i in range(self.列表.count()):
            项 = self.列表.item(i)
            项.setData(范围角, 范围文字(项.data(Qt.UserRole), 开))
        self.面板.设总开关(开)
        self.列表.viewport().update()

    # ---------- 页眉、数字、需要注意 ----------
    def _更新数字(self):
        清单 = self.当前清单()
        开数 = sum(1 for _, 开 in 清单 if 开)
        self.数量字.setText(f"模块 · 共 {len(清单)} 个，已启用 {开数} 个")
        self.运行全部按钮.setText(f"运行已启用模块（{开数}）")

    def _更新页眉(self):
        现在 = datetime.now()
        问候 = "早上好" if 现在.hour < 11 else "中午好" if 现在.hour < 13 else "下午好" if 现在.hour < 18 else "晚上好"
        self.头.眉.setText(f"{现在.month}月{现在.day}日  周{星期[现在.weekday()]}")
        self.头.标题.setText(f"{问候}，小柒")
        if self.上次:
            最近 = max(r["时间"] for r in self.上次.values())
            同批 = [r for r in self.上次.values() if abs((r["时间"] - 最近).total_seconds()) < 600]
            坏 = [r for r in 同批 if r["状态"] not in ("成功", "无数据", "未运行")]
            谁 = "、".join(显示名(名) for 名, r in self.上次.items() if r in 同批)
            self.头.设副标题(f"上次运行 {最近:%m/%d %H:%M}（{谁}），"
                           + ("都正常。" if not 坏 else f"{len(坏)} 个有问题，见下面“需要注意”。"))
        else:
            self.头.设副标题("还没有运行记录。打开要跑的模块，点右上角“运行已启用模块”。")

    def _更新注意(self, 清单):
        层 = self.注意组.块.层
        while 层.count():
            w = 层.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.注意组.行们 = []
        条们 = []
        for 名, _ in 清单:
            r = self.上次.get(名)
            if r and r["状态"] not in ("成功", "无数据", "未运行"):
                摘要 = r["摘要"].split(" → 建议")[0] if r["摘要"] else ""
                if 摘要.startswith(r["名字"] + " → "):
                    摘要 = 摘要[len(r["名字"]) + 3:]
                条们.append((r["状态"], f"{显示名(名)}：上次（{r['时间']:%m/%d %H:%M}）{r['状态']}" + (f"，{摘要}" if 摘要 else "")))
        for 状态, 文字 in 条们[:4]:
            w = QWidget()
            横 = QHBoxLayout(w)
            横.setContentsMargins(16, 10, 16, 10)
            横.setSpacing(12)
            横.addWidget(状态标签(状态), 0, Qt.AlignTop)
            字条 = 标签(文字, 换行=True)
            横.addWidget(字条, 1)
            self.注意组.加行(w)
        self.注意组.setVisible(bool(条们))

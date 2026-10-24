# 职责：工作台（打开软件看到的第一页）。
#   页眉：问候 + 日期 + 上次运行情况；右上：运行已启用模块（主按钮）、只运行选中的、运行完自动发飞书（开关）
#   需要注意：上次运行有问题的模块、模块设置文件的提醒（都没有就不显示）
#   模块卡片：排列 = 运行顺序（拖动或上移/下移），开关 = 启用，改动立即保存到 模块设置.txt（和改版前一样）
#   右侧：选中模块的设置面板（双击模块也会打开）
# 参考：Taskless（右侧编辑面板、一个主按钮）、Norix（问候、需要注意清单）、Watchlist（卡片上一个大数字 + 一行小字）。
from datetime import datetime

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QListWidget, QListWidgetItem, QStyle,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

from 公共 import 模块参数, 模块设置
from 公共.界面 import 运行历史
from 公共.界面.主题 import 字, 画图标, 状态样子, 色
from 公共.界面.弹窗 import 模块信息, 模块设置面板
from 公共.界面.组件 import 卡片, 图标字, 开关, 按钮, 标签, 状态标签, 页眉
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
行高 = 86


def _开着(索引):
    值 = 索引.data(Qt.CheckStateRole)
    return 值 is not None and Qt.CheckState(值) == Qt.Checked


def 模块说明(原名):
    _, _, 自己的 = 模块信息(原名)
    return 自己的 or 说明表.get(原名, "")


def 范围文字(原名):
    默认, 可发, _ = 模块信息(原名)
    参数 = 模块参数.读取(原名, 默认)
    if 参数.get("查询范围"):
        范围 = "、".join(参数["查询范围"])
    elif 参数.get("区域"):
        范围 = "、".join(参数["区域"])
    elif 原名 == "飞书任务明细":
        范围 = "飞书 · 我负责的"
    else:
        范围 = ""
    飞 = "发飞书" if (可发 and 参数.get("发到飞书", True)) else "只在窗口看"
    return 范围, 飞


class 模块卡片画法(QStyledItemDelegate):
    """把列表的每一行画成一张卡片：拖动把手、开关、名字、说明、范围，右边是上次结果。"""

    def sizeHint(self, 选项, 索引):
        return QSize(选项.rect.width(), 行高)

    def _区(self, 选项):
        r = QRectF(选项.rect).adjusted(2, 4, -4, -4)
        开关区 = QRectF(r.left() + 34, r.center().y() - 10, 38, 20)
        return r, 开关区

    def paint(self, p, 选项, 索引):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r, 开关区 = self._区(选项)
        选中 = bool(选项.state & QStyle.State_Selected)
        悬停 = bool(选项.state & QStyle.State_MouseOver)
        开 = _开着(索引)
        p.setPen(QPen(QColor(色["主"] if 选中 else (色["线深"] if 悬停 else 色["线"])), 1.5 if 选中 else 1))
        p.setBrush(QColor("#F7F9FF" if 选中 else 色["面"]))
        p.drawRoundedRect(r, 10, 10)
        画图标(p, "拖", QPointF(r.left() + 17, r.center().y()), 13, 色["灰"])
        # 开关
        p.setPen(Qt.NoPen if 开 else QPen(QColor(色["灰"]), 1))
        p.setBrush(QColor(色["主"] if 开 else 色["面"]))
        p.drawRoundedRect(开关区, 10, 10)
        半 = 7 if 开 else 6
        x = 开关区.right() - 10 if 开 else 开关区.left() + 10
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF" if 开 else 色["弱字"]))
        p.drawEllipse(QPointF(x, 开关区.center().y()), 半, 半)
        # 右边：上次结果
        右宽 = 150
        上次 = 索引.data(上次角)
        右区 = QRectF(r.right() - 右宽 - 14, r.top() + 12, 右宽, r.height() - 24)
        if 上次:
            种 = 状态样子.get(上次["状态"], (上次["状态"], "次", "圆"))[1]
            数 = 上次["数量"] if 上次["数量"] not in ("", None) else ("—" if 上次["状态"] != "失败" else "没查到")
            p.setFont(字(15, True))
            p.setPen(QColor(色["坏"] if 上次["状态"] == "失败" else 色["字"]))
            p.drawText(右区.adjusted(0, 0, 0, -22), Qt.AlignRight | Qt.AlignVCenter, str(数))
            p.setFont(字(8.5))
            文 = f"{上次['状态']} · {上次['时间']:%m/%d %H:%M}"
            宽 = QFontMetrics(p.font()).horizontalAdvance(文)
            p.setPen(QColor(色[种]))
            p.drawText(右区.adjusted(0, 右区.height() - 20, 0, 0), Qt.AlignRight | Qt.AlignVCenter, 文)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(色[种]))
            p.drawEllipse(QPointF(右区.right() - 宽 - 8, 右区.bottom() - 10), 3.5, 3.5)
        else:
            p.setFont(字(9))
            p.setPen(QColor(色["灰"]))
            p.drawText(右区, Qt.AlignRight | Qt.AlignVCenter, "还没运行过")
        # 中间：名字、说明、范围
        左 = 开关区.right() + 14
        文区 = QRectF(左, r.top() + 10, 右区.left() - 左 - 12, r.height() - 20)
        p.setFont(字(11, True))
        p.setPen(QColor(色["字"] if 开 else 色["弱字"]))
        名 = 索引.data(Qt.DisplayRole) or ""
        p.drawText(QRectF(文区.left(), 文区.top(), 文区.width(), 22), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(名, Qt.ElideRight, int(文区.width())))
        p.setFont(字(9))
        p.setPen(QColor(色["弱字"]))
        说明 = 索引.data(说明角) or ""
        p.drawText(QRectF(文区.left(), 文区.top() + 23, 文区.width(), 18), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(说明, Qt.ElideRight, int(文区.width())))
        范围, 飞 = 索引.data(范围角) or ("", "")
        p.setFont(字(8.5))
        x = 文区.left()
        for 文, 底, 前 in ((范围, 色["底"], 色["次字"]), (飞, 色["主浅"] if 飞 == "发飞书" else 色["底"],
                                                       色["主"] if 飞 == "发飞书" else 色["弱字"])):
            if not 文:
                continue
            宽 = QFontMetrics(p.font()).horizontalAdvance(文) + 14
            if x + 宽 > 文区.right():
                break
            框 = QRectF(x, 文区.bottom() - 18, 宽, 18)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(底))
            p.drawRoundedRect(框, 9, 9)
            p.setPen(QColor(前))
            p.drawText(框, Qt.AlignCenter, 文)
            x += 宽 + 6
        p.restore()

    def editorEvent(self, 事件, 模型, 选项, 索引):
        """点开关 = 切换启用；空格键也可以。其他点击交给列表（选中、拖动、双击）。"""
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
        总.setContentsMargins(28, 22, 28, 22)
        总.setSpacing(16)

        self.头 = 页眉("", "")
        self.运行选中按钮 = 按钮("只运行选中的", 图="运行")
        self.运行选中按钮.setToolTip("先点选一个模块，或按住 Ctrl 点几个。没开的模块也会运行。")
        self.运行全部按钮 = 按钮("运行已启用模块", "主", 图="运行")
        self.运行全部按钮.setMinimumHeight(38)
        self.运行选中按钮.setMinimumHeight(38)
        self.头.右.addWidget(self.运行选中按钮)
        self.头.右.addWidget(self.运行全部按钮)
        总.addWidget(self.头)

        中 = QHBoxLayout()
        中.setSpacing(16)
        左 = QVBoxLayout()
        左.setSpacing(12)
        # 需要注意
        self.注意卡 = 卡片(14, 6)
        注意头 = QHBoxLayout()
        注意头.addWidget(图标字("铃", 色["注意"], 14))
        注意头.addWidget(标签("需要注意", "小标题"))
        注意头.addStretch(1)
        看 = 按钮("看运行记录", "淡", 图="记录")
        看.clicked.connect(self.去看记录)
        注意头.addWidget(看)
        self.注意卡.层.addLayout(注意头)
        self.注意层 = QVBoxLayout()
        self.注意层.setSpacing(4)
        self.注意卡.层.addLayout(self.注意层)
        左.addWidget(self.注意卡)
        # 模块
        模块卡 = 卡片(14, 8)
        行 = QHBoxLayout()
        行.addWidget(标签("模块", "小标题"))
        self.数量字 = 标签("", "说明")
        行.addWidget(self.数量字)
        行.addStretch(1)
        self.上移钮 = 按钮("", "图标", 图="上", 提示="上移（选中的模块往前跑）")
        self.下移钮 = 按钮("", "图标", 图="下", 提示="下移")
        self.上移钮.clicked.connect(lambda: self.移动(-1))
        self.下移钮.clicked.connect(lambda: self.移动(1))
        行.addWidget(self.上移钮)
        行.addWidget(self.下移钮)
        模块卡.层.addLayout(行)
        self.提醒 = 标签("", 换行=True)            # 模块设置.txt 写错、发现新模块
        self.提醒.setStyleSheet(f"color:{色['注意字']}; background:{色['注意底']}; border-radius:8px; padding:6px 10px;")
        模块卡.层.addWidget(self.提醒)
        self.列表 = QListWidget()
        self.列表.setStyleSheet("QListWidget { border: none; background: transparent; }"
                                "QListWidget::item, QListWidget::item:selected, QListWidget::item:hover "
                                "{ background: transparent; }")
        self.列表.setItemDelegate(模块卡片画法(self.列表))
        self.列表.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.列表.setDragDropMode(QAbstractItemView.InternalMove)
        self.列表.setDefaultDropAction(Qt.MoveAction)
        self.列表.setMouseTracking(True)
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.列表.itemChanged.connect(lambda _: self.保存模块())
        self.列表.model().rowsMoved.connect(lambda *_: self.保存模块())
        self.列表.currentItemChanged.connect(self._选中变了)
        self.列表.itemDoubleClicked.connect(lambda _: self.面板.聚焦())
        模块卡.层.addWidget(self.列表, 1)
        模块卡.层.addWidget(标签("拖动卡片调整运行顺序（上面的先跑）· 点开关启用或停用 · 按住 Ctrl 可以选多个", "说明", 换行=True))
        左.addWidget(模块卡, 1)
        底行 = QHBoxLayout()
        self.自动发 = 开关("运行完自动发到飞书（按各模块的设置）")
        self.自动发.setChecked(bool(自动发设置值))
        底行.addWidget(self.自动发)
        底行.addStretch(1)
        左.addLayout(底行)
        中.addLayout(左, 1)

        self.面板 = 模块设置面板()
        self.面板.setFixedWidth(350)
        self.面板.已保存.connect(self._设置保存了)
        中.addWidget(self.面板)
        总.addLayout(中, 1)

        self.运行全部按钮.clicked.connect(lambda: self.运行请求.emit([名 for 名, 开 in self.当前清单() if 开]))
        self.运行选中按钮.clicked.connect(self._运行选中)
        self.刷新模块()

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
            项.setData(范围角, 范围文字(名))
            项.setData(上次角, self.上次.get(名))
            项.setToolTip(模块说明(名) + (f"`n原名：{名}" if 显示名(名) != 名 else ""))
            项.setFlags(项.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            项.setFlags(项.flags() & ~Qt.ItemIsDropEnabled)
            项.setCheckState(Qt.Checked if 开 else Qt.Unchecked)
            self.列表.addItem(项)
            if 名 == 当前:
                self.列表.setCurrentItem(项)
        self.列表.blockSignals(False)
        self.提醒.setText(提醒)
        self.提醒.setVisible(bool(提醒))
        self._更新数字()
        self._更新注意(清单)
        self._更新页眉()
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
        for w in (self.运行全部按钮, self.运行选中按钮, self.列表, self.面板, self.上移钮, self.下移钮):
            w.setEnabled(可用)

    def _选中变了(self, 项, _旧=None):
        if 项 is None:
            self.面板.显示(None)
        else:
            self.面板.显示(项.data(Qt.UserRole), 项.data(说明角))

    def _设置保存了(self, 名):
        self.刷新模块()          # 名字、范围可能改了；选中的还是这个模块

    # ---------- 页眉、数字、需要注意 ----------
    def _更新数字(self):
        清单 = self.当前清单()
        开数 = sum(1 for _, 开 in 清单 if 开)
        self.数量字.setText(f"共 {len(清单)} 个，已启用 {开数} 个")
        self.运行全部按钮.setText(f"运行已启用模块（{开数}）")

    def _更新页眉(self):
        现在 = datetime.now()
        问候 = "早上好" if 现在.hour < 11 else "中午好" if 现在.hour < 13 else "下午好" if 现在.hour < 18 else "晚上好"
        self.头.眉.setText(f"{现在.month}月{现在.day}日  周{星期[现在.weekday()]}")
        self.头.标题.setText(f"{问候}，小柒")
        if self.上次:
            最近 = max(r["时间"] for r in self.上次.values())
            同批 = [r for r in self.上次.values() if abs((r["时间"] - 最近).total_seconds()) < 600]
            坏 = [r for r in 同批 if r["状态"] not in ("成功", "无数据")]
            self.头.设副标题(f"上次运行 {最近:%m/%d %H:%M}，" + ("全部正常。" if not 坏 else f"{len(坏)} 个模块有问题，见下面“需要注意”。"))
        else:
            self.头.设副标题("还没有运行记录。打开要跑的模块，点右上角“运行已启用模块”。")

    def _更新注意(self, 清单):
        while self.注意层.count():
            w = self.注意层.takeAt(0).widget()
            if w:
                w.deleteLater()
        条们 = []
        for 名, _ in 清单:
            r = self.上次.get(名)
            if r and r["状态"] not in ("成功", "无数据"):
                摘要 = r["摘要"].split(" → 建议")[0] if r["摘要"] else ""
                if 摘要.startswith(r["名字"] + " → "):
                    摘要 = 摘要[len(r["名字"]) + 3:]
                条们.append((r["状态"], f"{显示名(名)}：上次（{r['时间']:%m/%d %H:%M}）{r['状态']}" + (f"，{摘要}" if 摘要 else "")))
        for 状态, 文字 in 条们[:4]:
            行 = QWidget()
            横 = QHBoxLayout(行)
            横.setContentsMargins(0, 2, 0, 2)
            横.setSpacing(10)
            横.addWidget(状态标签(状态, 小=True), 0, Qt.AlignTop)
            字条 = 标签(文字, 换行=True)
            字条.setStyleSheet(f"color:{色['次字']};")
            横.addWidget(字条, 1)
            self.注意层.addWidget(行)
        self.注意卡.setVisible(bool(条们))

# 职责：运行结果页（点运行后自动切到这里）。参考 Incident Tracking 的“左边列表、右边详情”。
#   顶部进度卡：正在运行第几个、哪一步、进度条；跑完显示总结和“打开这次的日志”
#   左边：这次运行的模块（等待 / 正在运行 / 成功 / 无数据 / 不完整 / 失败 + 主要数字）
#   右边：选中模块的结果页（公共\结果页.py，内容和改版前一样）
#   最下面：运行过程（逐行记录，可展开）
# 2026-10-24（小柒）：每个模块查完马上显示完整结果，不等后面的模块；你点过哪个模块，就不会被自动跳走。
#   打开仓库助手时，这里显示上一次运行的结果（公共\上次结果.py），并标明是什么时候跑的。
import os
import time

from PySide6.QtCore import QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar, QSizePolicy,
                               QStackedWidget, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from 公共 import 结果页
from 公共.界面.主题 import 像素字, 字号, 字, 状态样子, 画图标, 色
from 公共.界面.组件 import 卡片, 图标字, 按钮, 标签, 空白提示, 页眉
from 公共.模块参数 import 显示名

状态角, 数字角, 要看角 = Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3


class 运行项画法(QStyledItemDelegate):
    """左边这次运行的模块：iOS 分组列表的一行——● 状态圆点、模块名、一行状态字，右边数字；行间细线从文字处开始。"""

    def sizeHint(self, 选项, 索引):
        return QSize(选项.rect.width(), 60)

    def paint(self, p, 选项, 索引):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(选项.rect)
        选中 = bool(选项.state & QStyle.State_Selected)
        状态 = 索引.data(状态角) or "等待"
        _, 种, _ = 状态样子.get(状态, (状态, "次", "圆"))
        if 索引.data(要看角) and 状态 == "成功":
            种 = "注意"
        if 选中:                                  # 选中那行整行蓝底白字（和导航一样）
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(色["主"]))
            p.drawRoundedRect(r.adjusted(0, 2, 0, -2), 10, 10)
        字色 = 色["白"] if 选中 else 色["字"]
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(色[种]))
        p.drawEllipse(QPointF(r.left() + 20, r.top() + 21), 4, 4)
        数 = 索引.data(数字角)
        右宽 = 64 if 数 not in (None, "") else 0
        左 = r.left() + 34
        文宽 = int(r.right() - 左 - 右宽 - 16)
        p.setFont(像素字("行标题", 半粗=True))
        p.setPen(QColor(色["字"]))
        p.drawText(QRectF(左, r.top() + 9, 文宽, 24), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(索引.data(Qt.DisplayRole) or "", Qt.ElideRight, 文宽))
        p.setFont(像素字("说明"))
        p.setPen(QColor(色["白"] if 选中 else 色.get(种 + "字", 色[种])))
        说 = 状态样子.get(状态, (状态,))[0]
        if 索引.data(要看角) and 状态 == "成功":
            说 = f"成功 · {索引.data(要看角)} 条要看"
        p.drawText(QRectF(左, r.top() + 33, 文宽, 18), Qt.AlignLeft | Qt.AlignVCenter, 说)
        if 右宽:
            p.setFont(像素字(17, 半粗=True))
            p.setPen(QColor(字色))
            p.drawText(QRectF(r.right() - 右宽 - 16, r.top(), 右宽, r.height()), Qt.AlignRight | Qt.AlignVCenter, str(数))
        p.restore()

class 运行页(QWidget):
    去工作台 = Signal()

    def __init__(self, 状态栏, 手动发送):
        super().__init__()
        self.setObjectName("页面")
        self.状态栏, self.手动发送 = 状态栏, 手动发送
        self.本次日志 = None
        总 = QVBoxLayout(self)
        总.setContentsMargins(0, 0, 0, 0)
        总.setSpacing(0)
        # 顶部一行运行状态条（小柒 2026-10-25：运行过程不重要，运行中也只占一行）：● 状态 + 细进度条 + 当前步骤 + 运行过程 ›
        顶 = QFrame()
        顶.setObjectName("顶条")
        顶层 = QHBoxLayout(顶)
        顶层.setContentsMargins(20, 8, 12, 8)
        顶层.setSpacing(12)
        self.进度图 = 标签("●")              # 规范：状态只用 ● 圆点
        顶层.addWidget(self.进度图)
        self.进度文字 = 标签("还没有运行。")
        self.进度文字.setStyleSheet(f"font-size:{字号['正文']}px;")
        顶层.addWidget(self.进度文字)
        self.进度条 = QProgressBar()
        self.进度条.setTextVisible(False)
        顶层.addWidget(self.进度条, 1)              # 进度条拉满这一行剩下的宽度（小柒 2026-10-25 第三轮）
        self.百分比 = 标签("0%", "说明")
        self.百分比.setMinimumWidth(40)
        顶层.addWidget(self.百分比)
        self.进度条.valueChanged.connect(lambda v: self.百分比.setText(f"{round(v / 10)}%"))
        # 运行中才显示（体检 2026-10-28）：程序已请 Windows 别自动睡眠，但合盖挡不住
        self.合盖提醒 = 标签("运行中请勿合盖", "说明")
        self.合盖提醒.setToolTip("运行期间仓库助手已请 Windows 不要自动睡眠、不要自动关屏；合上盖子还是会睡，查询会中断。")
        顶层.addWidget(self.合盖提醒)
        self.合盖提醒.setVisible(False)
        # 当前步骤、第几个不再单独占位置：第几个写进左边的字，当前步骤放在鼠标停留提示和“运行过程”里
        self.步骤文字 = QLabel(self)
        self.步骤文字.hide()
        self.计数 = QLabel(self)
        self.计数.hide()
        self.日志钮 = 按钮("打开这次的日志", "文字")
        self.日志钮.clicked.connect(lambda: self.本次日志 and os.startfile(self.本次日志))
        self.日志钮.setVisible(False)
        顶层.addWidget(self.日志钮)
        self.过程钮 = 按钮("运行过程 ›", "文字")
        self.过程钮.clicked.connect(self._展开过程)
        顶层.addWidget(self.过程钮)
        总.addWidget(顶)
        self.顶条 = 顶
        self.过程框 = QWidget()
        过层 = QVBoxLayout(self.过程框)
        过层.setContentsMargins(20, 8, 20, 8)
        self.过程 = QPlainTextEdit()
        self.过程.setReadOnly(True)
        self.过程.setMaximumBlockCount(2000)
        self.过程.setFixedHeight(150)
        过层.addWidget(self.过程)
        self.过程框.setVisible(False)
        总.addWidget(self.过程框)

        self.页们 = QStackedWidget()
        空页 = QWidget()
        空层 = QVBoxLayout(空页)
        空层.setContentsMargins(24, 20, 24, 20)
        空层.addWidget(页眉("", "运行结果"))
        空层.addWidget(空白提示("运行", "这次打开后还没有运行",
                           "到工作台打开要跑的模块，点“运行已启用模块”。运行时会自动切到这一页。",
                           [self._去工作台钮()]), 1)
        self.页们.addWidget(空页)

        # 分栏视图（苹果“邮件”式）：中间模块清单，右边详情占满剩下的地方
        工作区 = QWidget()
        工层 = QHBoxLayout(工作区)
        工层.setContentsMargins(0, 0, 0, 0)
        工层.setSpacing(0)
        中栏 = QFrame()
        中栏.setObjectName("清单栏")
        中栏.setFixedWidth(250)
        中层 = QVBoxLayout(中栏)
        中层.setContentsMargins(8, 16, 8, 8)
        中层.setSpacing(8)
        self.眉 = 标签("运行结果", "说明")
        self.眉.setWordWrap(True)
        self.眉.setContentsMargins(12, 0, 8, 0)
        中层.addWidget(self.眉)
        self.列表 = QListWidget()
        self.列表.setObjectName("模块清单")
        self.列表.setItemDelegate(运行项画法(self.列表))
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.currentRowChanged.connect(self._换页)
        self.列表.itemClicked.connect(lambda _: setattr(self, "用户点过", True))
        中层.addWidget(self.列表, 1)
        工层.addWidget(中栏)
        self.详情 = QStackedWidget()
        工层.addWidget(self.详情, 1)
        self.页们.addWidget(工作区)
        总.addWidget(self.页们, 1)
        self.名们 = []
        self.结果们 = {}
        self.已显示 = set()        # 已经显示完整结果的行号
        self.用户点过 = False      # 运行中点过左边的模块：之后不再自动跳
        self._计时 = QTimer(self)
        self._计时.setInterval(200)
        self._计时.timeout.connect(self._走)
        self._动画 = QPropertyAnimation(self.进度条, b"value", self)
        self._动画.setDuration(220)
        self._段, self._预计, self._当前, self._起 = [], [], None, 0.0
    # ---------- 丝滑进度条（小柒 2026-10-25）----------
    # 每个模块按它最近几次的用时分一段（运行总表里有记录；没有就按 30 秒），跑的时候在自己那段里慢慢往前走，
    # 最多走到这段的 95%，真做完才补满；整个条只用一个每 0.2 秒一次的计时器，不碰后台运行。失败时停在原地。
    def _准备进度(self, 名列表, 实时):
        from 公共.界面 import 运行历史
        self._计时.stop()
        self._动画.stop()
        self.进度条.setMaximum(1000)
        self.进度条.setValue(0)
        self._当前, self._起 = None, time.monotonic()
        用时们 = {}
        try:
            for 行 in 运行历史.读全部(名列表):
                if 行["原名"] in 名列表 and str(行["用时"]).isdigit() and 行["状态"] != "失败":
                    用时们.setdefault(行["原名"], []).append(int(行["用时"]))
        except Exception:
            pass
        self._预计 = [max(5.0, sum(用时们[名][:3]) / len(用时们[名][:3])) if 用时们.get(名) else 30.0 for 名 in 名列表]
        总 = sum(self._预计) or 1
        起 = 0.0
        self._段 = []
        for 秒 in self._预计:
            长 = 1000 * 秒 / 总
            self._段.append((起, 长))
            起 += 长
        if 实时:
            self._计时.start()

    def _走(self):
        if self._当前 is None or self._当前 >= len(self._段):
            return
        起, 长 = self._段[self._当前]
        比 = min(0.95, (time.monotonic() - self._起) / self._预计[self._当前])
        self._走到(起 + 长 * 比)

    def _走到(self, 值):
        值 = int(min(1000, 值))
        if 值 <= self.进度条.value():
            return
        self._动画.stop()
        self._动画.setStartValue(self.进度条.value())
        self._动画.setEndValue(值)
        self._动画.start()
    def _去工作台钮(self):
        b = 按钮("去工作台", "主", 图="首页")
        b.clicked.connect(self.去工作台)
        return b

    def _展开过程(self):
        开 = not self.过程框.isVisible()
        self.过程框.setVisible(开)
        self.过程钮.setText("运行过程 ˅" if 开 else "运行过程 ›")

    # ---------- 运行时窗口调用 ----------
    def 开始(self, 名列表, 开始字, 实时=True):
        self.页们.setCurrentIndex(1)
        self.名们 = list(名列表)
        self.结果们 = {}
        self.已显示 = set()
        self.用户点过 = False
        self.本次日志 = None
        self.日志钮.setVisible(False)
        self.合盖提醒.setVisible(实时)
        self.过程.clear()
        self._准备进度(名列表, 实时)
        self.进度文字.setText("正在打开浏览器 ……")
        self.步骤文字.setText("")
        self.计数.setText(f"0 / {len(名列表)}")
        self._进度图("同步", "运行")
        self.眉.setText("正在运行 · " + " → ".join(map(显示名, 名列表)))
        while self.详情.count():
            w = self.详情.widget(0)
            self.详情.removeWidget(w)
            w.deleteLater()
        self.列表.clear()
        for 名 in 名列表:
            项 = QListWidgetItem(显示名(名))
            项.setData(Qt.UserRole, 名)
            项.setData(状态角, "等待")
            self.列表.addItem(项)
            self.详情.addWidget(空白提示("时钟", "还在排队", "前面的模块跑完就轮到它。"))
        self._列表高度()
        self.列表.setCurrentRow(0)
        self.加一行(开始字)

    def 加一行(self, 文字):
        self.过程.appendPlainText(文字)

    def 步骤(self, 文字):
        self.步骤文字.setText(文字.rstrip(" …"))
        self.进度文字.setToolTip(文字.rstrip(" …"))

    def 模块开始(self, 序号, 总数, 名):
        self.进度文字.setText(f"正在运行：{显示名(名)}（{序号}/{总数}）")
        self.步骤文字.setText("")
        self.计数.setText(f"{序号} / {总数}")
        i = 序号 - 1
        self._当前, self._起 = i, time.monotonic()
        if 0 <= i < self.列表.count():
            self.列表.item(i).setData(状态角, "运行中")
            self._换详情(i, 空白提示("同步", f"正在运行 {显示名(名)}", "当前步骤显示在上面的进度里。"))
            if not self.用户点过:
                self.列表.setCurrentRow(i)

    def 模块完成(self, 名, 结果):
        for i in range(self.列表.count()):
            项 = self.列表.item(i)
            if 项.data(Qt.UserRole) == 名 and 项.data(状态角) in ("运行中", "等待"):
                if i < len(self._段):                   # 这个模块真正做完：补满它那一段
                    self._走到(sum(self._段[i]))
                self._当前 = None
                项.setData(状态角, 结果["状态"])
                项.setData(数字角, 结果.get("数量") if 结果["状态"] != "失败" else None)
                self._换详情(i, 空白提示("勾" if 结果["状态"] in ("成功", "无数据", "未运行") else "警告",
                                       f"{显示名(名)} 已经查完：{结果['状态']}", "正在整理结果……"))
                break

    def 显示一个(self, 项):
        """一个模块整理好了（飞书也按设置发完了）：马上显示它的完整结果。"""
        for i in range(self.列表.count()):
            if i not in self.已显示 and self.列表.item(i).data(Qt.UserRole) == 项["模块"]:
                self._显示行(i, 项)
                break

    def 全部完成(self, 消息们, 日志文件夹, 有问题数):
        self.本次日志 = 日志文件夹
        self.日志钮.setVisible(bool(日志文件夹))
        self.合盖提醒.setVisible(False)
        self._计时.stop()
        self._走到(1000)
        self.计数.setText(f"{len(消息们)} / {len(self.名们)}")
        self.步骤文字.setText("")
        if 有问题数:
            self.进度文字.setText(f"完成：{有问题数} 个模块有问题，点左边看原因和建议")
            self._进度图("警告", "注意")
        else:
            self.进度文字.setText("完成：全部正常")
            self._进度图("勾", "好")
        self.眉.setText("这次运行 · " + " → ".join(map(显示名, self.名们)))
        self.显示结果(消息们)

    def 显示结果(self, 消息们):
        """每个模块一页，样子统一，见 公共\结果页.py。已经显示过的不重做（不打断正在看的人）。"""
        for 项 in 消息们:
            self.显示一个(项)
        if not self.用户点过:   # 有问题的先给人看：选中第一个失败/不完整的，没有就选第一个
            先看 = next((i for i in range(self.列表.count()) if self.列表.item(i).data(状态角) not in ("成功", "无数据", "未运行")), 0)
            self.列表.setCurrentRow(先看)
            self.详情.setCurrentIndex(先看)

    def _显示行(self, i, 项):
        条 = self.列表.item(i)
        条.setData(状态角, 项["状态"])
        条.setData(数字角, 项.get("数量") if 项["状态"] != "失败" else None)
        条.setData(要看角, 结果页.要看数(项) or (len(结果页.提醒们(项)) if 结果页.提醒们(项) else 0))
        条.setText(项["显示名"])
        self._换详情(i, 结果页.一页(项, self.状态栏, self.手动发送))
        self.已显示.add(i)

    def 显示上次(self, 数据):
        """打开仓库助手时：显示上一次运行的结果（公共\上次结果.py 存的），标明是什么时候跑的。"""
        结果们 = 数据["结果们"]
        名们 = 数据.get("模块们") or [项["模块"] for 项 in 结果们]
        self.开始(名们, f"这是 {数据['开始']:%m/%d %H:%M} 那次运行的结果（打开仓库助手时自动显示）。", 实时=False)
        self.显示结果(结果们)
        没跑 = len(名们) - len(结果们)
        有问题 = sum(1 for 项 in 结果们 if 项["状态"] not in ("成功", "无数据", "未运行"))
        self.进度条.setValue(1000 if 数据.get("完成") else int(1000 * len(结果们) / max(1, len(名们))))
        self.计数.setText(f"{len(结果们)} / {len(名们)}")
        self.眉.setText(f"上一次运行 · {数据['开始']:%m/%d %H:%M} 开始 · " + " → ".join(map(显示名, 名们)))
        self.进度文字.setText(f"上一次运行的结果（{数据['开始']:%m/%d %H:%M}）"
                          + ("" if 数据.get("完成") else f"：那次没有跑完，{没跑} 个模块没有结果")
                          + (f"，{有问题} 个模块有问题" if 有问题 else ""))
        self.进度文字.setToolTip("")
        self._进度图("记录", "注意" if 有问题 or not 数据.get("完成") else "次")
        for i in range(self.列表.count()):
            if i not in self.已显示:
                self.列表.item(i).setData(状态角, "没跑到")
                self._换详情(i, 空白提示("时钟", "那次没有跑到这个模块", "要看它的结果，到工作台运行一次。"))
        先看 = next((i for i in sorted(self.已显示) if self.列表.item(i).data(状态角) not in ("成功", "无数据", "未运行")),
                  min(self.已显示) if self.已显示 else 0)
        self.列表.setCurrentRow(先看)
        self.详情.setCurrentIndex(先看)

    def 出错(self):
        self._计时.stop()                               # 停在当时的位置，不假装走完
        self.合盖提醒.setVisible(False)
        self.进度文字.setText("运行时出现意外错误（详情在 日志\\窗口错误.txt，请告诉 Claude）")
        self._进度图("错", "坏")

    def _换详情(self, i, 新):
        旧 = self.详情.widget(i)
        self.详情.insertWidget(i, 新)
        if 旧 is not None:
            self.详情.removeWidget(旧)
            旧.deleteLater()
        if self.列表.currentRow() == i:
            self.详情.setCurrentIndex(i)

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self._列表高度()

    def _换页(self, 行):
        if 0 <= 行 < self.详情.count():
            self.详情.setCurrentIndex(行)

    def _进度图(self, 图, 种):
        """进度卡左上角的状态圆点：蓝 = 正在运行、绿 = 全部正常、橙 = 有要看的、红 = 出错、灰 = 以前的结果。"""
        self.进度图.setStyleSheet(f"color:{色[种]}; font-size:{字号['说明']}px;")

    def _列表高度(self):
        pass                          # 分栏版面里清单占满中间一栏，不用再算高度


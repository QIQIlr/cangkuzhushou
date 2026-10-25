# 职责：运行结果页（点运行后自动切到这里）。参考 Incident Tracking 的“左边列表、右边详情”。
#   顶部进度卡：正在运行第几个、哪一步、进度条；跑完显示总结和“打开这次的日志”
#   左边：这次运行的模块（等待 / 正在运行 / 成功 / 无数据 / 不完整 / 失败 + 主要数字）
#   右边：选中模块的结果页（公共\结果页.py，内容和改版前一样）
#   最下面：运行过程（逐行记录，可展开）
# 2026-10-24（小柒）：每个模块查完马上显示完整结果，不等后面的模块；你点过哪个模块，就不会被自动跳走。
#   打开仓库助手时，这里显示上一次运行的结果（公共\上次结果.py），并标明是什么时候跑的。
import os

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
                               QStackedWidget, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from 公共 import 结果页
from 公共.界面.主题 import 字, 状态样子, 画图标, 色
from 公共.界面.组件 import 卡片, 图标字, 按钮, 标签, 空白提示, 页眉
from 公共.模块参数 import 显示名

状态角, 数字角, 要看角 = Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3


class 运行项画法(QStyledItemDelegate):
    def sizeHint(self, 选项, 索引):
        return QSize(选项.rect.width(), 64)

    def paint(self, p, 选项, 索引):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(选项.rect).adjusted(2, 3, -4, -3)
        选中 = bool(选项.state & QStyle.State_Selected)
        状态 = 索引.data(状态角) or "等待"
        _, 种, 图 = 状态样子.get(状态, (状态, "次", "圆"))
        if 索引.data(要看角) and 状态 == "成功":
            种, 图 = "注意", "警告"
        p.setPen(QPen(QColor(色["主"] if 选中 else 色["线"]), 1.5 if 选中 else 1))
        p.setBrush(QColor(色["选中卡底"] if 选中 else 色["面"]))
        p.drawRoundedRect(r, 10, 10)
        圆心 = QPointF(r.left() + 24, r.center().y())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(色[种 + "底"]))
        p.drawEllipse(圆心, 14, 14)
        画图标(p, 图, 圆心, 12, 色[种])
        数 = 索引.data(数字角)
        右宽 = 70 if 数 not in (None, "") else 0
        p.setFont(字(10.5, True))
        p.setPen(QColor(色["字"]))
        文宽 = int(r.width() - 52 - 右宽 - 12)
        p.drawText(QRectF(r.left() + 48, r.top() + 9, 文宽, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(索引.data(Qt.DisplayRole) or "", Qt.ElideRight, 文宽))
        p.setFont(字(8.5))
        p.setPen(QColor(色[种]))
        说 = 状态样子.get(状态, (状态,))[0]
        if 索引.data(要看角) and 状态 == "成功":
            说 = f"成功 · {索引.data(要看角)} 条要看"
        p.drawText(QRectF(r.left() + 48, r.top() + 31, 文宽, 20), Qt.AlignLeft | Qt.AlignVCenter, 说)
        if 右宽:
            p.setFont(字(13, True))
            p.setPen(QColor(色["字"]))
            p.drawText(QRectF(r.right() - 右宽 - 12, r.top(), 右宽, r.height()), Qt.AlignRight | Qt.AlignVCenter, str(数))
        p.restore()


class 运行页(QWidget):
    去工作台 = Signal()

    def __init__(self, 状态栏, 手动发送):
        super().__init__()
        self.setObjectName("页面")
        self.状态栏, self.手动发送 = 状态栏, 手动发送
        self.本次日志 = None
        总 = QVBoxLayout(self)
        总.setContentsMargins(24, 18, 24, 18)
        总.setSpacing(12)
        self.日志钮 = 按钮("打开这次的日志", 图="文件夹")
        self.日志钮.clicked.connect(lambda: self.本次日志 and os.startfile(self.本次日志))
        self.日志钮.setVisible(False)

        self.页们 = QStackedWidget()
        空页 = QWidget()
        空层 = QVBoxLayout(空页)
        空层.setContentsMargins(4, 4, 4, 4)
        空层.addWidget(页眉("运行结果", "这次运行"))
        空层.addWidget(空白提示("运行", "这次打开后还没有运行",
                           "到工作台打开要跑的模块，点“运行已启用模块”。运行时会自动切到这一页。",
                           [self._去工作台钮()]), 1)
        self.页们.addWidget(空页)

        工作区 = QWidget()
        工层 = QVBoxLayout(工作区)
        工层.setContentsMargins(0, 0, 0, 0)
        工层.setSpacing(12)
        # 进度卡（兼当页眉）：图标、这次的情况、跑到哪一步；右边计数、运行过程、打开日志
        进度卡 = 卡片(16, 8)
        行 = QHBoxLayout()
        行.setSpacing(12)
        self.进度图 = 图标字("同步", 色["主"], 16)
        self.进度图.setFixedSize(38, 38)
        行.addWidget(self.进度图)
        字层 = QVBoxLayout()
        字层.setSpacing(1)
        self.眉 = 标签("运行结果", "眉")
        self.进度文字 = 标签("还没有运行。", "小标题")
        self.进度文字.setStyleSheet("font-size:13pt; font-weight:bold;")
        self.步骤文字 = 标签("", "说明")
        字层.addWidget(self.眉)
        字层.addWidget(self.进度文字)
        字层.addWidget(self.步骤文字)
        行.addLayout(字层, 1)
        self.计数 = 标签("", "说明")
        行.addWidget(self.计数)
        self.过程钮 = 按钮("运行过程", "淡", 图="右")
        self.过程钮.clicked.connect(self._展开过程)
        行.addWidget(self.过程钮)
        行.addWidget(self.日志钮)
        进度卡.层.addLayout(行)
        self.进度条 = QProgressBar()
        self.进度条.setTextVisible(False)
        进度卡.层.addWidget(self.进度条)
        self.过程 = QPlainTextEdit()
        self.过程.setReadOnly(True)
        self.过程.setMaximumBlockCount(2000)
        self.过程.setFixedHeight(140)
        self.过程.setVisible(False)
        进度卡.层.addWidget(self.过程)
        工层.addWidget(进度卡)
        # 列表 + 详情
        中 = QHBoxLayout()
        中.setSpacing(12)
        self.列表 = QListWidget()
        self.列表.setFixedWidth(224)
        self.列表.setItemDelegate(运行项画法(self.列表))
        self.列表.setStyleSheet("QListWidget { border: none; background: transparent; }"
                                "QListWidget::item, QListWidget::item:selected, QListWidget::item:hover { background: transparent; }")
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.currentRowChanged.connect(self._换页)
        self.列表.itemClicked.connect(lambda _: setattr(self, "用户点过", True))
        中.addWidget(self.列表)
        self.详情卡 = 卡片(0, 0)
        self.详情 = QStackedWidget()
        self.详情卡.层.addWidget(self.详情)
        中.addWidget(self.详情卡, 1)
        工层.addLayout(中, 1)
        self.页们.addWidget(工作区)
        总.addWidget(self.页们, 1)
        self.名们 = []
        self.结果们 = {}
        self.已显示 = set()        # 已经显示完整结果的行号
        self.用户点过 = False      # 运行中点过左边的模块：之后不再自动跳

    def _去工作台钮(self):
        b = 按钮("去工作台", "主", 图="首页")
        b.clicked.connect(self.去工作台)
        return b

    def _展开过程(self):
        开 = not self.过程.isVisible()
        self.过程.setVisible(开)
        from 公共.界面.主题 import 图标
        self.过程钮.setIcon(图标("展开" if 开 else "右", 色["次字"]))

    # ---------- 运行时窗口调用 ----------
    def 开始(self, 名列表, 开始字):
        self.页们.setCurrentIndex(1)
        self.名们 = list(名列表)
        self.结果们 = {}
        self.已显示 = set()
        self.用户点过 = False
        self.本次日志 = None
        self.日志钮.setVisible(False)
        self.过程.clear()
        self.进度条.setMaximum(len(名列表))
        self.进度条.setValue(0)
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
        self.列表.setCurrentRow(0)
        self.加一行(开始字)

    def 加一行(self, 文字):
        self.过程.appendPlainText(文字)

    def 步骤(self, 文字):
        self.步骤文字.setText(文字.rstrip(" …"))

    def 模块开始(self, 序号, 总数, 名):
        self.进度文字.setText(f"正在运行：{显示名(名)}")
        self.步骤文字.setText("")
        self.计数.setText(f"{序号} / {总数}")
        i = 序号 - 1
        if 0 <= i < self.列表.count():
            self.列表.item(i).setData(状态角, "运行中")
            self._换详情(i, 空白提示("同步", f"正在运行 {显示名(名)}", "当前步骤显示在上面的进度里。"))
            if not self.用户点过:
                self.列表.setCurrentRow(i)

    def 模块完成(self, 名, 结果):
        self.进度条.setValue(self.进度条.value() + 1)
        for i in range(self.列表.count()):
            项 = self.列表.item(i)
            if 项.data(Qt.UserRole) == 名 and 项.data(状态角) in ("运行中", "等待"):
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
        self.进度条.setValue(self.进度条.maximum())
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
        self.开始(名们, f"这是 {数据['开始']:%m/%d %H:%M} 那次运行的结果（打开仓库助手时自动显示）。")
        self.显示结果(结果们)
        没跑 = len(名们) - len(结果们)
        有问题 = sum(1 for 项 in 结果们 if 项["状态"] not in ("成功", "无数据", "未运行"))
        self.进度条.setValue(len(结果们))
        self.计数.setText(f"{len(结果们)} / {len(名们)}")
        self.眉.setText(f"上一次运行 · {数据['开始']:%m/%d %H:%M} 开始 · " + " → ".join(map(显示名, 名们)))
        self.进度文字.setText(f"上一次运行的结果（{数据['开始']:%m/%d %H:%M}）"
                          + ("" if 数据.get("完成") else f"：那次没有跑完，{没跑} 个模块没有结果")
                          + (f"，{有问题} 个模块有问题" if 有问题 else ""))
        self.步骤文字.setText("这不是现在的数字。要最新的，到工作台点运行。")
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
        self.进度文字.setText("运行时出现意外错误")
        self.步骤文字.setText("详情已保存到 日志\\窗口错误.txt，请告诉 Claude。")
        self._进度图("错", "坏")

    def _换详情(self, i, 新):
        旧 = self.详情.widget(i)
        self.详情.insertWidget(i, 新)
        if 旧 is not None:
            self.详情.removeWidget(旧)
            旧.deleteLater()
        if self.列表.currentRow() == i:
            self.详情.setCurrentIndex(i)

    def _换页(self, 行):
        if 0 <= 行 < self.详情.count():
            self.详情.setCurrentIndex(行)

    def _进度图(self, 图, 种):
        from 公共.界面.主题 import 图码
        self.进度图.setText(图码[图])
        self.进度图.setStyleSheet(f"color:{色[种]}; background:{色[种 + '底']}; border-radius:17px;")

# 职责：仓库助手 窗口版（测试版）。双击 仓库助手（测试版）.vbs 打开，不出现黑色命令行窗口。
# 内容：左边模块列表（勾选=启用，拖动或上移/下移=调顺序，改动立即保存到 模块设置.txt）；
#       右边运行按钮、进度、运行过程、结果（和发到飞书的一样）、打开日志；
#       下面设置：飞书、登录 WMS、登录飞书。
# 说明：查询在后台线程里跑，窗口不会卡住；掉线时弹窗请你登录；
#       飞书任务明细运行中会弹出“选择要读取的任务”窗口。
#       业务逻辑全部复用 公共\运行.py 和各模块，这里只是“外壳”。
import os
import re
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))

from PySide6.QtCore import QLockFile, QObject, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QFont, QKeySequence  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog, QFormLayout, QGroupBox,  # noqa: E402
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QSplitter, QVBoxLayout, QWidget)

from 公共 import 模块设置, 飞书  # noqa: E402
from 公共.wms import WMS首页, 专用配置目录, 专用窗口开着  # noqa: E402
from 公共.日志 import 日志根, 运行记录  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
测试不发送 = os.environ.get("仓库助手_测试不发送") == "1"


class 传话(QObject):
    """后台线程 → 窗口 的消息（Qt 会自动排队到窗口线程）。"""
    步骤 = Signal(str, str)
    开始模块 = Signal(int, int, str)
    模块完成 = Signal(str, object)
    全部完成 = Signal(object)
    出错 = Signal(str)
    需要登录 = Signal(int)
    需要选择 = Signal(object)


class 可复制表格(QTableWidget):
    """结果表格：只读；单击选中一格，Ctrl+C 或双击就把这一格的内容复制到剪贴板，状态栏提示“已复制 XXX”。
    多行=True：文字靠左靠上、自动换行、表格按内容撑开高度（飞书任务明细这种“项目｜内容”的表用）。"""

    def __init__(self, 列名, 行们, 状态栏, 多行=False):
        super().__init__(len(行们), len(列名))
        self.状态栏 = 状态栏
        self.setHorizontalHeaderLabels(列名)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        粗体 = QFont()
        粗体.setBold(True)
        for r, 行 in enumerate(行们):
            加粗 = any(str(x).startswith("**") for x in 行)
            for c, 值 in enumerate(行):
                if isinstance(值, dict):        # 可展开的格子：平时显示预览，单击展开全部
                    格 = QTableWidgetItem(值["预览"])
                    格.setData(Qt.UserRole, 值["全部"])
                    格.setData(Qt.UserRole + 1, 值["预览"])
                    格.setToolTip("单击展开 / 收起；双击复制全部内容")
                    格.setForeground(Qt.black)
                    格.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                    self.setItem(r, c, 格)
                    continue
                格 = QTableWidgetItem(str(值).replace("**", ""))
                if 多行:
                    格.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                else:
                    格.setTextAlignment((Qt.AlignLeft if c == 0 or isinstance(值, str) and "-" in str(值) else Qt.AlignRight) | Qt.AlignVCenter)
                if 加粗:
                    格.setFont(粗体)
                if "⚠" in str(值) or str(值) == "失败":
                    格.setForeground(Qt.darkRed)
                self.setItem(r, c, 格)
        self.多行 = 多行
        if 多行:
            self.setWordWrap(True)
            self.resizeColumnToContents(0)
            self.horizontalHeader().setStretchLastSection(True)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._按宽度排行(620)
        else:
            self.resizeColumnsToContents()
            self.horizontalHeader().setStretchLastSection(True)
            高 = self.horizontalHeader().height() + sum(self.rowHeight(r) for r in range(min(len(行们), 15))) + 6
            self.setMinimumHeight(min(高, 460))
            self.setMaximumHeight(高 if len(行们) <= 15 else 460)
        self.itemDoubleClicked.connect(lambda _: self.复制())
        self.itemClicked.connect(self._展开收起)

    def _展开收起(self, 格):
        全部, 预览 = 格.data(Qt.UserRole), 格.data(Qt.UserRole + 1)
        if not 全部 or not 预览:
            return
        格.setText(全部 + "\n……单击收起" if 格.text() == 预览 else 预览)
        self._按宽度排行(self.columnWidth(self.columnCount() - 1))

    def _按宽度排行(self, 内容宽):
        """多行表：最后一列宽度跟着窗口走，按这个宽度自动换行，再把整个表格撑到正好放下所有行。"""
        if self.columnCount() > 1:
            self.setColumnWidth(self.columnCount() - 1, max(200, 内容宽))
        self.resizeRowsToContents()
        高 = self.horizontalHeader().height() + sum(self.rowHeight(r) for r in range(self.rowCount())) + 2 * self.frameWidth() + 2
        self.setMinimumHeight(高)
        self.setMaximumHeight(高)

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        if getattr(self, "多行", False):
            宽 = self.viewport().width() - sum(self.columnWidth(c) for c in range(self.columnCount() - 1))
            if abs(宽 - self.columnWidth(self.columnCount() - 1)) > 4:
                self._按宽度排行(宽)

    def keyPressEvent(self, 事件):
        if 事件.matches(QKeySequence.Copy):
            self.复制()
        else:
            super().keyPressEvent(事件)

    def 复制(self):
        """复制选中的格子：一格就只复制这一格；多格按行排好（同一行用 Tab 隔开，每行一行）。"""
        格们 = sorted(self.selectedItems(), key=lambda g: (g.row(), g.column()))
        if not 格们:
            return
        行们 = {}
        for g in 格们:
            行们.setdefault(g.row(), []).append(g.data(Qt.UserRole) or g.text())
        文字 = "\n".join("\t".join(v) for v in 行们.values())
        QApplication.clipboard().setText(文字)
        self.状态栏.showMessage(f"已复制 {文字}" if len(格们) == 1 else f"已复制 {len(格们)} 格", 4000)


class 分组视图(QWidget):
    """无任务包裹这类结果：上面总览（区域｜数量｜状态），点某个区 → 下面换成这个区的单号；
    “复制本区全部单号”按钮复制成文字表（标题 + 每行 序号<Tab>单号）。"""

    def __init__(self, 分组, 状态栏):
        super().__init__()
        self.状态栏 = 状态栏
        self.明细 = {区: (单号们, 文字) for 区, 单号们, 文字 in 分组["明细"]}
        层 = QVBoxLayout(self)
        层.setContentsMargins(0, 0, 0, 0)
        层.addWidget(QLabel("各区域数量（点某一行，下面显示这个区的单号）："))
        列名, 行们 = 分组["总览"]
        self.总览 = 可复制表格(列名, 行们, 状态栏)
        self.总览.setSelectionMode(QAbstractItemView.SingleSelection)
        self.总览.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.总览.itemSelectionChanged.connect(self._换区)
        层.addWidget(self.总览)
        头 = QHBoxLayout()
        self.明细标题 = QLabel("")
        self.明细标题.setStyleSheet("font-weight:bold")
        头.addWidget(self.明细标题, 1)
        self.复制按钮 = QPushButton("复制本区全部单号")
        self.复制按钮.clicked.connect(self._复制全部)
        头.addWidget(self.复制按钮)
        层.addLayout(头)
        self.明细层 = QVBoxLayout()
        层.addLayout(self.明细层)
        self.当前区 = None
        # 默认显示第一个有单号的区
        for r in range(self.总览.rowCount()):
            if self.总览.item(r, 0).text() in self.明细:
                self.总览.selectRow(r)
                break
        else:
            self._显示(None)

    def _换区(self):
        行 = self.总览.currentRow()
        区 = self.总览.item(行, 0).text() if 行 >= 0 else None
        self._显示(区)

    def _显示(self, 区):
        while self.明细层.count():
            w = self.明细层.takeAt(0).widget()
            if w:
                w.hide()          # 先藏起来，不然换区的一瞬间旧表格还在
                w.deleteLater()
        self.当前区 = 区 if 区 in self.明细 else None
        if self.当前区 is None:
            self.明细标题.setText("（这个区没有单号）" if 区 else "（没有单号）")
            self.复制按钮.setEnabled(False)
            return
        单号们, _ = self.明细[区]
        self.明细标题.setText(f"{区} 的转运单号（{len(单号们)} 个；单击 + Ctrl+C 复制一个）")
        self.复制按钮.setEnabled(True)
        位数 = max(2, len(str(len(单号们))))
        self.明细层.addWidget(可复制表格(["序号", "转运单号"],
                                     [[str(i).zfill(位数), 号] for i, 号 in enumerate(单号们, 1)], self.状态栏))

    def _复制全部(self):
        if self.当前区 is None:
            return
        单号们, 文字 = self.明细[self.当前区]
        QApplication.clipboard().setText(文字)
        self.状态栏.showMessage(f"已复制 {self.当前区} {len(单号们)} 个单号", 5000)


class 任务选择窗口(QDialog):
    """飞书任务明细：按飞书“我负责的”里的顺序列出全部标题，点一行勾选/取消，再点“开始读取”。
    不分组、不排序、默认不勾（小柒 2026-10-24 确认）。"""

    def __init__(self, 父, 清单):
        super().__init__(父)
        self.setWindowTitle("飞书任务明细：选择要读取的任务")
        self.resize(1000, 660)
        层 = QVBoxLayout(self)
        行们, 应有 = 清单["行们"], 清单.get("应有")
        头 = QLabel(f"“我负责的”共读到 {len(行们)} 条" + (f"，和页面显示的 {应有} 条一致 ✔" if 应有 == len(行们) else ""))
        头.setStyleSheet("font-weight:bold; font-size:11pt")
        层.addWidget(头)
        for 句 in 清单.get("提醒", []):
            注 = QLabel(句)
            注.setWordWrap(True)
            注.setStyleSheet("color:#b35c00")
            层.addWidget(注)
        层.addWidget(QLabel("按飞书里的顺序列出。点一行就勾选或取消（可以选多条），再点“开始读取”。每条大约 6～11 秒。"))
        self.列表 = QListWidget()
        self.列表.setStyleSheet("QListWidget::item { padding: 5px 2px; border-bottom: 1px solid #e6e6e6; }")
        位数 = len(str(len(行们)))
        for i, (编号, 标题, _) in enumerate(行们, 1):
            项 = QListWidgetItem(f"{str(i).rjust(位数)}.  {标题}")
            项.setData(Qt.UserRole, 编号)
            项.setToolTip(标题)
            项.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            项.setCheckState(Qt.Unchecked)
            self.列表.addItem(项)
        self.列表.itemClicked.connect(self._切换)
        层.addWidget(self.列表, 1)
        行 = QHBoxLayout()
        self.开始 = QPushButton("开始读取（已选 0 条）")
        self.开始.setEnabled(False)
        self.开始.setMinimumHeight(36)
        self.开始.clicked.connect(self.accept)
        取消 = QPushButton("取消（这次不读）")
        取消.clicked.connect(self.reject)
        行.addStretch(1)
        行.addWidget(取消)
        行.addWidget(self.开始)
        层.addLayout(行)

    def _切换(self, 项):
        项.setCheckState(Qt.Unchecked if 项.checkState() == Qt.Checked else Qt.Checked)
        数 = len(self.选中())
        self.开始.setText(f"开始读取（已选 {数} 条）")
        self.开始.setEnabled(数 > 0)

    def 选中(self):
        return [self.列表.item(i).data(Qt.UserRole) for i in range(self.列表.count())
                if self.列表.item(i).checkState() == Qt.Checked]


class 飞书设置窗口(QDialog):
    def __init__(self, 父):
        super().__init__(父)
        self.setWindowTitle("设置飞书群机器人")
        self.setMinimumWidth(520)
        层 = QVBoxLayout(self)
        层.addWidget(QLabel("在飞书群设置 → 群机器人 → 你的机器人 里复制 Webhook 地址，粘贴到下面。\n"
                           "点“测试并保存”会发一条测试消息，成功才保存。"))
        表 = QFormLayout()
        self.网址 = QLineEdit()
        self.网址.setEchoMode(QLineEdit.Password)
        self.网址.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/……（输入时不显示）")
        self.关键词 = QLineEdit(飞书.读设置().get("飞书关键词", ""))
        self.关键词.setPlaceholderText("机器人“安全设置”里的自定义关键词；没有就空着")
        表.addRow("Webhook 地址：", self.网址)
        表.addRow("自定义关键词：", self.关键词)
        层.addLayout(表)
        if 飞书.可以发送():
            层.addWidget(QLabel("✔ 目前已经设置好。只有换群或换机器人时才需要重新填。"))
        按钮 = QPushButton("测试并保存")
        按钮.clicked.connect(self.测试)
        层.addWidget(按钮)

    def 测试(self):
        网址 = self.网址.text().strip()
        if not 飞书.格式.match(网址):
            QMessageBox.warning(self, "地址不对", "这不像飞书 Webhook 地址，应该以\nhttps://open.feishu.cn/open-apis/bot/v2/hook/ 开头。")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            状态, 说明 = 飞书.发送("【测试】仓库助手 飞书连接测试", 网址=网址, 关键词=self.关键词.text().strip())
        finally:
            QApplication.restoreOverrideCursor()
        if 状态 == "成功":
            飞书.写设置({"飞书Webhook": 网址, "飞书关键词": self.关键词.text().strip(), "飞书已测通": "是"})
            QMessageBox.information(self, "成功", "✔ 成功！飞书群里应该收到了一条测试消息。\n设置已保存。")
            self.accept()
        else:
            QMessageBox.warning(self, "没有成功", f"测试没有成功（{状态}）：{说明}\n\n设置没有保存。")


class 模块设置窗口(QDialog):
    """一个模块自己的设置：查询区域或查询范围（模块有这项时）、发到飞书。改完点“保存”。"""

    def __init__(self, 父, 模块名):
        super().__init__(父)
        import importlib
        from 公共 import 模块参数
        self.模块参数, self.模块名 = 模块参数, 模块名
        try:
            默认 = getattr(importlib.import_module(f"模块.{模块名}"), "默认参数", {})
        except Exception:
            默认 = {}
        self.参数 = 模块参数.读取(模块名, 默认)
        self.setWindowTitle(f"模块设置：{模块名}")
        self.setMinimumWidth(420)
        层 = QVBoxLayout(self)
        self.区域框 = {}
        self.范围框 = {}
        if "查询范围" in self.参数:
            from 公共.待处理 import 仓库, 范围选项
            组 = QGroupBox("查询范围（每个勾选项单独一张表、一张飞书卡片）")
            格 = QVBoxLayout(组)
            for 名 in 范围选项:
                说明 = f"{名}（{' + '.join(仓库[名])}）" if 名 in 仓库 else (f"{名}（测试区）" if 名 == "B区" else f"{名}（单独）")
                框 = QCheckBox(说明)
                框.setChecked(名 in self.参数["查询范围"])
                self.范围框[名] = 框
                格.addWidget(框)
            层.addWidget(组)
            层.addWidget(QLabel("一般勾仓库就行；想单独看某个区时再勾那个区。"))
        if "区域" in self.参数:
            组 = QGroupBox("查询区域（勾选要查的区域；表格/结果按这里的顺序）")
            行 = QHBoxLayout(组)
            for 区 in 模块参数.区域选项():
                框 = QCheckBox(区)
                框.setChecked(区 in self.参数["区域"])
                self.区域框[区] = 框
                行.addWidget(框)
            层.addWidget(组)
            层.addWidget(QLabel("区域选项来自 WMS 的“所属区域”下拉（运行待审核、待拣货、待增值时会自动更新）。"))
        self.发送框 = QCheckBox("结果发到飞书")
        self.发送框.setChecked(self.参数.get("发到飞书", True))
        层.addWidget(self.发送框)
        保存 = QPushButton("保存")
        保存.clicked.connect(self.保存)
        层.addWidget(保存)

    def 保存(self):
        if self.范围框:
            选中 = [名 for 名, 框 in self.范围框.items() if 框.isChecked()]
            if not 选中:
                QMessageBox.warning(self, "至少选一个", "请至少勾选一个仓库或区域。")
                return
            self.参数["查询范围"] = 选中
        if self.区域框:
            选中 = [区 for 区, 框 in self.区域框.items() if 框.isChecked()]
            if not 选中:
                QMessageBox.warning(self, "至少选一个区域", "请至少勾选一个区域。")
                return
            self.参数["区域"] = 选中
        self.参数["发到飞书"] = self.发送框.isChecked()
        self.模块参数.保存(self.模块名, self.参数)
        self.accept()


class 主窗口(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("仓库助手（测试版）")
        self.resize(1100, 720)
        self.运行中 = False
        self.本次日志 = None
        self.登录回答 = None
        self.登录事件 = threading.Event()
        self.选择回答 = None
        self.选择事件 = threading.Event()
        self.传话 = 传话()
        self.传话.步骤.connect(self._显示步骤)
        self.传话.开始模块.connect(self._开始模块)
        self.传话.模块完成.connect(self._模块完成)
        self.传话.全部完成.connect(self._全部完成)
        self.传话.出错.connect(self._运行出错)
        self.传话.需要登录.connect(self._请登录)
        self.传话.需要选择.connect(self._请选择)
        self._搭界面()
        self.刷新模块()

    # ---------- 界面 ----------
    def _搭界面(self):
        中心 = QWidget()
        总 = QVBoxLayout(中心)
        分 = QSplitter(Qt.Horizontal)

        # 左：模块列表
        左框 = QGroupBox("模块（勾选 = 启用；拖动或用按钮调顺序）")
        左 = QVBoxLayout(左框)
        self.列表 = QListWidget()
        self.列表.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.列表.setDragDropMode(QAbstractItemView.InternalMove)
        self.列表.itemChanged.connect(lambda _: self.保存模块())
        self.列表.model().rowsMoved.connect(lambda *_: self.保存模块())
        左.addWidget(self.列表)
        行 = QHBoxLayout()
        for 文字, 方向 in (("▲ 上移", -1), ("▼ 下移", 1)):
            b = QPushButton(文字)
            b.clicked.connect(lambda _=False, d=方向: self.移动(d))
            行.addWidget(b)
        设 = QPushButton("⚙ 设置（区域等）")
        设.clicked.connect(self.模块设置)
        行.addWidget(设)
        self.列表.itemDoubleClicked.connect(lambda _: self.模块设置())
        左.addLayout(行)
        self.提醒 = QLabel("")
        self.提醒.setWordWrap(True)
        self.提醒.setStyleSheet("color:#b35c00")
        左.addWidget(self.提醒)
        self.运行全部按钮 = QPushButton("▶ 运行已启用模块")
        self.运行选中按钮 = QPushButton("▶ 只运行选中的模块")
        for b in (self.运行全部按钮, self.运行选中按钮):
            b.setMinimumHeight(40)
        self.运行全部按钮.clicked.connect(self.运行全部)
        self.运行选中按钮.clicked.connect(self.运行选中)
        左.addWidget(self.运行全部按钮)
        左.addWidget(self.运行选中按钮)
        from 公共 import 模块参数
        self.自动发 = QCheckBox("运行完自动发到飞书（按各模块的设置）")
        self.自动发.setChecked(bool(模块参数.界面设置("运行完自动发飞书", True)))
        self.自动发.toggled.connect(lambda 开: 模块参数.保存界面设置("运行完自动发飞书", 开))
        左.addWidget(self.自动发)
        左.addWidget(QLabel("不勾选时：结果只在窗口里显示，想发哪个就点那个结果下面的“发到飞书”。"))
        左.addWidget(QLabel("提示：按住 Ctrl 可以选多个；“只运行选中的”时，禁用的模块也会运行。"))
        分.addWidget(左框)

        # 右：进度、过程、结果
        右 = QWidget()
        右层 = QVBoxLayout(右)
        self.进度文字 = QLabel("还没有运行。")
        self.进度条 = QProgressBar()
        self.进度条.setValue(0)
        右层.addWidget(self.进度文字)
        右层.addWidget(self.进度条)
        右层.addWidget(QLabel("运行过程："))
        self.过程 = QPlainTextEdit()
        self.过程.setReadOnly(True)
        self.过程.setMaximumBlockCount(2000)
        右层.addWidget(self.过程, 1)
        右层.addWidget(QLabel("结果（和发到飞书的一样；单击选中一格，Ctrl+C 或双击即可复制）："))
        self.结果区 = QScrollArea()
        self.结果区.setWidgetResizable(True)
        self.结果区.setWidget(QWidget())
        右层.addWidget(self.结果区, 3)
        行2 = QHBoxLayout()
        self.飞书状态 = QLabel("")
        行2.addWidget(self.飞书状态, 1)
        self.开本次日志按钮 = QPushButton("打开本次日志文件夹")
        self.开本次日志按钮.setEnabled(False)
        self.开本次日志按钮.clicked.connect(lambda: self.本次日志 and os.startfile(self.本次日志))
        行2.addWidget(self.开本次日志按钮)
        右层.addLayout(行2)
        分.addWidget(右)
        分.setSizes([380, 720])
        总.addWidget(分, 1)

        # 下：设置
        设置框 = QGroupBox("设置")
        设 = QHBoxLayout(设置框)
        for 文字, 函数 in (("设置飞书", self.设置飞书),
                         ("登录 WMS", self.登录WMS), ("登录飞书", self.登录飞书),
                         ("打开日志文件夹", lambda: os.startfile(日志根)),
                         ("刷新模块列表", self.刷新模块)):
            b = QPushButton(文字)
            b.clicked.connect(函数)
            设.addWidget(b)
        总.addWidget(设置框)
        self.setCentralWidget(中心)
        if 测试不发送:
            self.statusBar().showMessage("测试模式：不发飞书")

    # ---------- 模块列表 ----------
    def 刷新模块(self):
        清单, 提醒 = 模块设置.读取()
        self.列表.blockSignals(True)
        self.列表.clear()
        for 名, 开 in 清单:
            项 = QListWidgetItem(名)
            项.setFlags(项.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            项.setFlags(项.flags() & ~Qt.ItemIsDropEnabled)
            项.setCheckState(Qt.Checked if 开 else Qt.Unchecked)
            self.列表.addItem(项)
        self.列表.blockSignals(False)
        self.提醒.setText(("⚠ " + 提醒) if 提醒 else "")

    def 当前清单(self):
        return [[self.列表.item(i).text(), self.列表.item(i).checkState() == Qt.Checked]
                for i in range(self.列表.count())]

    def 保存模块(self):
        模块设置.保存(self.当前清单())

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

    def 模块设置(self):
        项 = self.列表.currentItem()
        if 项 is None:
            QMessageBox.information(self, "模块设置", "请先在左边点选一个模块。")
            return
        模块设置窗口(self, 项.text()).exec()

    # ---------- 运行 ----------
    def 运行全部(self):
        self.开始运行([名 for 名, 开 in self.当前清单() if 开])

    def 运行选中(self):
        选中 = {项.text() for 项 in self.列表.selectedItems()}
        self.开始运行([名 for 名, _ in self.当前清单() if 名 in 选中])

    def _设可用(self, 可用):
        for b in (self.运行全部按钮, self.运行选中按钮):
            b.setEnabled(可用)
        self.列表.setEnabled(可用)

    def 开始运行(self, 名列表):
        if self.运行中:
            return
        if not 名列表:
            QMessageBox.information(self, "没有模块", "没有要运行的模块。\n（运行全部：请先勾选启用；运行选中：请先点选模块。）")
            return
        if 专用窗口开着():
            QMessageBox.warning(self, "请先关闭专用 Chrome", "“自动化专用 Chrome”窗口还开着（登录 WMS 时打开的那个）。\n请先关掉它，再点运行。")
            return
        self.运行中 = True
        self._设可用(False)
        self.过程.clear()
        self.结果区.setWidget(QWidget())
        self.飞书状态.setText("")
        self.开本次日志按钮.setEnabled(False)
        self.进度条.setMaximum(len(名列表))
        self.进度条.setValue(0)
        self.进度文字.setText("正在打开浏览器 ……")
        self.过程.appendPlainText(f"{datetime.now():%H:%M:%S} 开始：{' → '.join(名列表)}")
        运行记录.观察者 = lambda 模块名, 文字: self.传话.步骤.emit(模块名, 文字)
        self._本次发送 = self.自动发.isChecked() and not 测试不发送   # 在窗口线程里读好，后台线程只用这个值
        threading.Thread(target=self._后台运行, args=(名列表,), daemon=True).start()

    def _后台运行(self, 名列表):
        try:
            from 公共.运行 import 运行模块们
            总结 = 运行模块们(名列表, 发送=self._本次发送, 显示=False, 等待登录=self._等登录,
                          回报=lambda 事件, 内容: self._回报(事件, 内容), 选择=self._等选择)
            self.传话.全部完成.emit(总结)
        except Exception:
            self.传话.出错.emit(traceback.format_exc())

    def _回报(self, 事件, 内容):
        if 事件 == "开始模块":
            self.传话.开始模块.emit(*内容)
        elif 事件 == "模块完成":
            self.传话.模块完成.emit(*内容)

    def _显示步骤(self, 模块名, 文字):
        if 文字.startswith("-" * 10):
            return
        self.过程.appendPlainText(f"[{模块名}] {文字}")
        if re.match(r"第\d+步", 文字):
            self.进度文字.setText(self.进度文字.text().split("｜")[0] + "｜" + 文字.rstrip(" …"))

    def _开始模块(self, 序号, 总数, 名):
        self.进度文字.setText(f"正在运行 [{序号}/{总数}] {名}")

    def _模块完成(self, 名, 结果):
        self.进度条.setValue(self.进度条.value() + 1)
        好 = 结果["状态"] in ("成功", "无数据")
        数量 = f"，数量 {结果['数量']}" if 结果.get("数量") is not None else ""
        self.过程.appendPlainText(f"{'✔' if 好 else '⚠'} {名}：{结果['状态']}{数量}")

    def _全部完成(self, 总结):
        运行记录.观察者 = None
        self.运行中 = False
        self._设可用(True)
        飞书们, 坏的 = [], []
        for 项 in 总结["消息们"]:
            状态, 说明 = 项["飞书"]
            飞书们.append(f"{项['模块']} {状态}")
            if 状态 in ("失败", "未知"):
                坏的.append(f"{项['模块']}：{状态}，{说明}")
        self._显示结果(总结["消息们"])
        self.飞书状态.setText("飞书：" + "；".join(飞书们))
        self.本次日志 = 总结["日志文件夹"]
        self.开本次日志按钮.setEnabled(True)
        有问题 = [r for r in 总结["结果们"] if r["状态"] not in ("成功", "无数据")]
        self.进度文字.setText("完成：全部正常 ✔" if not 有问题 else f"完成：{len(有问题)} 个模块有问题 ⚠（看下面的结果和建议）")
        if 坏的:
            QMessageBox.warning(self, "飞书没发成功", "\n".join(坏的))

    def _显示结果(self, 消息们):
        """每个模块：标题 + 表格（可复制）+ 备注 + 飞书/Excel。没有表格的模块就显示文字。"""
        面板 = QWidget()
        层 = QVBoxLayout(面板)
        for 项 in 消息们:
            标题 = QLabel(项.get("标题") or 项["模块"])
            标题.setStyleSheet("font-weight:bold; font-size:11pt; margin-top:6px")
            层.addWidget(标题)
            if 项.get("分组"):
                层.addWidget(分组视图(项["分组"], self.statusBar()))
                for 句 in 项.get("备注", []):
                    注 = QLabel(句)
                    注.setWordWrap(True)
                    注.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    注.setStyleSheet("color:#b35c00" if "⚠" in 句 else "")
                    层.addWidget(注)
            elif 项.get("表们"):
                for 表名, 列名, 行们 in 项["表们"]:
                    if not 行们:
                        continue
                    if len(项["表们"]) > 1:
                        名 = QLabel(表名)
                        名.setTextInteractionFlags(Qt.TextSelectableByMouse)
                        if 项.get("左对齐多行"):
                            名.setStyleSheet("font-weight:bold; margin-top:8px")
                        层.addWidget(名)
                    层.addWidget(可复制表格(列名, 行们, self.statusBar(), 多行=bool(项.get("左对齐多行"))))
                for 句 in 项.get("备注", []):
                    注 = QLabel(句)
                    注.setWordWrap(True)
                    注.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    注.setStyleSheet("color:#b35c00" if "⚠" in 句 else "")
                    层.addWidget(注)
            else:
                文 = QLabel(项["文字"])
                文.setTextInteractionFlags(Qt.TextSelectableByMouse)
                层.addWidget(文)
            状态, 说明 = 项["飞书"]
            尾 = QHBoxLayout()
            飞书字 = QLabel(f"飞书：{状态}" + (f"（{说明}）" if 状态 != "成功" else ""))
            尾.addWidget(飞书字, 1)
            发 = QPushButton("发到飞书" if 状态 != "成功" else "再发一次到飞书")
            发.clicked.connect(lambda _=False, 项=项, 字=飞书字, 钮=发: self._手动发送(项, 字, 钮))
            尾.addWidget(发)
            if 项.get("附件"):
                b = QPushButton("打开 Excel")
                b.clicked.connect(lambda _=False, p=项["附件"]: os.startfile(p))
                尾.addWidget(b)
            层.addLayout(尾)
            线 = QLabel("")
            线.setStyleSheet("border-bottom:1px solid #ccc")
            层.addWidget(线)
        层.addStretch(1)
        self.结果区.setWidget(面板)

    def _手动发送(self, 项, 字, 钮):
        """把某个模块这次的结果发到飞书（运行时没发、或想再发一次时用）。发送情况记进这个模块的日志。"""
        if not 飞书.可以发送():
            QMessageBox.information(self, "飞书", "还没设置好飞书，请先点下面的“设置飞书”。")
            return
        之前 = 项["飞书"][0]
        if 之前 in ("成功", "未知"):
            提示 = "这个结果已经发到飞书了，确定要再发一次吗？" if 之前 == "成功" else \
                "上次发送结果“未知”（可能已经发出去了）。请先到飞书群里看一眼。\n确定要再发一次吗？"
            if QMessageBox.question(self, "再发一次？", 提示, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            状态, 说明 = 飞书.发送全部(项.get("卡片们") or [], 项["文字"])
        finally:
            QApplication.restoreOverrideCursor()
        项["飞书"] = (状态, 说明)
        字.setText(f"飞书：{状态}" + (f"（{说明}）" if 状态 != "成功" else "（手动发送）"))
        钮.setText("再发一次到飞书" if 状态 == "成功" else "发到飞书")
        try:
            from 公共.日志 import 遮掩
            with open(Path(项["日志文件夹"]) / "运行记录.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%H:%M:%S}] 窗口里手动发送飞书：{状态}（{遮掩(说明)}）\n")
        except Exception:
            pass
        self.statusBar().showMessage(f"{项['模块']}：飞书 {状态}", 5000)
        if 状态 != "成功":
            QMessageBox.warning(self, "飞书没发成功", f"{状态}：{说明}")

    def _运行出错(self, 详情):
        运行记录.观察者 = None
        self.运行中 = False
        self._设可用(True)
        _记下窗口错误(详情)
        self.进度文字.setText("运行时出现意外错误 ⚠")
        QMessageBox.critical(self, "意外错误", "运行时出现意外错误。\n详情已保存到 日志\\窗口错误.txt，请把这件事告诉 Claude。")

    # ---------- 掉线登录 ----------
    def _等登录(self, 次数):
        """后台线程调用：请窗口弹窗，等人点按钮。"""
        self.登录事件.clear()
        self.传话.需要登录.emit(次数)
        self.登录事件.wait()
        return self.登录回答

    def _请登录(self, 次数):
        框 = QMessageBox(self)
        框.setWindowTitle("需要登录 WMS")
        框.setIcon(QMessageBox.Warning)
        框.setText(("还没有检测到登录成功，请再试一次。\n\n" if 次数 == 2 else "")
                  + "WMS 已掉线。已经弹出一个 Chrome 窗口，请在里面登录 WMS。\n登录完成后点“我登录好了”。")
        好了 = 框.addButton("我登录好了", QMessageBox.AcceptRole)
        框.addButton("取消这次运行", QMessageBox.RejectRole)
        框.exec()
        self.登录回答 = 框.clickedButton() is 好了
        self.登录事件.set()

    # ---------- 运行中勾选（飞书任务明细） ----------
    def _等选择(self, 清单):
        """后台线程调用：请窗口弹出勾选窗口，等人选好。返回勾选的编号列表；取消返回 None。"""
        self.选择事件.clear()
        self.传话.需要选择.emit(清单)
        self.选择事件.wait()
        return self.选择回答

    def _请选择(self, 清单):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        QApplication.alert(self)
        窗 = 任务选择窗口(self, 清单)
        self.选择回答 = 窗.选中() if 窗.exec() == QDialog.Accepted else None
        self.选择事件.set()

    # ---------- 设置 ----------
    def 设置飞书(self):
        飞书设置窗口(self).exec()

    def 登录WMS(self):
        if self.运行中:
            QMessageBox.information(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            QMessageBox.information(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        subprocess.Popen([CHROME, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", WMS首页])
        QMessageBox.information(self, "登录 WMS", "已打开自动化专用 Chrome。\n请在里面登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。\n\n注意：这个 Chrome 开着时不能运行查询。")

    def 登录飞书(self):
        if self.运行中:
            QMessageBox.information(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            QMessageBox.information(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        from 公共.飞书网页 import 任务列表网址
        subprocess.Popen([CHROME, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", 任务列表网址])
        QMessageBox.information(self, "登录飞书", "已打开自动化专用 Chrome，进入飞书“我负责的”任务页。\n"
                                "如果出现登录页，请扫码或输入账号登录；看到任务列表就说明登录好了。\n"
                                "然后关掉那个 Chrome 窗口。\n\n注意：这个 Chrome 开着时不能运行查询。")

    # ---------- 关闭 ----------
    def closeEvent(self, 事件):
        if self.运行中:
            答 = QMessageBox.question(self, "正在运行", "查询还在运行。现在关闭会中止这次运行，结果不会发到飞书。\n确定要关闭吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if 答 != QMessageBox.Yes:
                事件.ignore()
                return
            _记下窗口错误("用户在运行中关闭了窗口，本次运行被中止。")
            os._exit(0)
        事件.accept()


def _记下窗口错误(文字):
    try:
        日志根.mkdir(exist_ok=True)
        with open(日志根 / "窗口错误.txt", "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{文字}\n")
    except Exception:
        pass


def _意外(类型, 值, 追踪):
    _记下窗口错误("".join(traceback.format_exception(类型, 值, 追踪)))
    try:
        QMessageBox.critical(None, "意外错误", f"仓库助手出现意外错误：{值}\n详情已保存到 日志\\窗口错误.txt，请告诉 Claude。")
    except Exception:
        pass


def main():
    sys.excepthook = _意外
    应用 = QApplication(sys.argv)
    应用.setFont(QFont("Microsoft YaHei UI", 10))
    日志根.mkdir(exist_ok=True)
    锁 = QLockFile(str(日志根 / "仓库助手窗口.lock"))
    if not 锁.tryLock(100):
        QMessageBox.information(None, "仓库助手", "仓库助手已经打开了（看看任务栏）。")
        return 0
    窗 = 主窗口()
    窗.show()
    if "--截图" in sys.argv:   # 测试用：打开 2 秒后截图并退出
        def 截图():
            窗.grab().save(str(日志根 / "界面截图.png"))
            应用.quit()
        QTimer.singleShot(2000, 截图)
    return 应用.exec()


if __name__ == "__main__":
    sys.exit(main())

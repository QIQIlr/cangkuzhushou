# 职责：运行记录页。把 日志\运行总表.csv（每次运行一行，以前只能用 Excel 打开）显示在窗口里，只读。
#   按模块筛选；双击一行（或点“打开日志”）打开那次的日志文件夹。
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from 公共 import 模块参数, 模块设置
from 公共.界面 import 运行历史
from 公共.界面.主题 import 字, 状态样子, 颜色, 色
from 公共.界面.组件 import 分段, 卡片, 按钮, 标签, 页眉
from 公共.日志 import 日志根


class 记录页(QWidget):
    def __init__(self, 状态栏):
        super().__init__()
        self.setObjectName("页面")
        self.状态栏 = 状态栏
        总 = QVBoxLayout(self)
        总.setContentsMargins(24, 20, 24, 20)
        总.setSpacing(16)
        self.头 = 页眉("", "运行记录", "来自 日志\\运行总表.csv。双击一行打开那次的日志。日志保留 90 天。")
        刷 = 按钮("刷新", "文字")
        刷.clicked.connect(self.刷新)
        夹 = 按钮("打开日志文件夹")
        夹.clicked.connect(lambda: os.startfile(日志根))
        self.头.右.addWidget(刷)
        self.头.右.addWidget(夹)
        总.addWidget(self.头)
        self.筛选行 = QHBoxLayout()            # 分段控件放在白色块上面（iOS 的样子）
        self.筛选行.addStretch(1)
        总.addLayout(self.筛选行)
        卡 = 卡片(8, 0)
        self.表 = QTableWidget()
        self.表.setColumnCount(6)
        self.表.setHorizontalHeaderLabels(["时间", "模块", "状态", "数量", "用时", "问题"])
        self.表.verticalHeader().setVisible(False)
        self.表.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.表.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.表.setSelectionMode(QAbstractItemView.SingleSelection)
        self.表.setShowGrid(False)
        self.表.setWordWrap(False)
        self.表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.表.setStyleSheet(f"QTableWidget {{ border: none; }} QTableWidget::item {{ border-bottom: 1px solid {色['线']}; padding: 0 8px; }}")
        头 = self.表.horizontalHeader()
        头.setSectionResizeMode(5, QHeaderView.Stretch)     # 前 5 列的宽度在填完表后一次调好（见 _填）
        头.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.表.verticalHeader().setDefaultSectionSize(40)
        self.表.cellDoubleClicked.connect(self._打开)
        卡.层.addWidget(self.表, 1)
        self.空字 = 标签("还没有运行记录。", "说明")
        self.空字.setAlignment(Qt.AlignCenter)
        卡.层.addWidget(self.空字)
        总.addWidget(卡, 1)
        self.筛选 = None
        self.当前筛选 = None
        self.行们 = []

    def 刷新(self):
        原名们 = [名 for 名, _ in 模块设置.读取(写回=False)[0]]   # 只是看一眼，不写设置文件
        self.行们 = 运行历史.读全部(原名们)
        有的 = [名 for 名 in 原名们 if any(r["原名"] == 名 for r in self.行们)]
        if self.筛选 is not None:
            self.筛选.setParent(None)
            self.筛选.deleteLater()
        self.选项 = [None] + 有的
        当前 = self.选项.index(self.当前筛选) if self.当前筛选 in self.选项 else 0
        self.筛选 = 分段(["全部"] + [模块参数.显示名(名) for 名 in 有的], 当前)
        self.筛选.选了.connect(self._选筛选)
        self.筛选行.insertWidget(0, self.筛选)
        self._填()

    def _选筛选(self, i):
        self.当前筛选 = self.选项[i]
        self._填()

    def _填(self):
        行们 = [r for r in self.行们 if self.当前筛选 is None or r["原名"] == self.当前筛选]
        self.显示中 = 行们
        改名 = 模块参数.显示名表()               # 一次读好，不要每行读一次设置文件
        # 卡顿的原因（2026-10-24 实测）：表格里已有上次的行时逐格替换，每换一格 Qt 都把“随内容调宽”的整列重量一遍，
        # 124 行要 3 秒、500 行要 50 秒。所以先清空旧行、填的时候不调列宽，填完再一次调好。
        头 = self.表.horizontalHeader()
        self.表.setUpdatesEnabled(False)
        self.表.setRowCount(0)
        for c in range(5):
            头.setSectionResizeMode(c, QHeaderView.Interactive)
        self.表.setRowCount(len(行们))
        for i, r in enumerate(行们):
            名 = 改名.get(r["原名"], r["原名"]) if r["原名"] in self.选项 else r["名字"]
            文们 = [f"{r['时间']:%m/%d %H:%M}", 名 + ("（测试）" if r["测试"] else ""),
                  r["状态"], r["数量"], f"{r['用时']} 秒" if r["用时"] else "", r["摘要"]]
            for c, 文 in enumerate(文们):
                格 = QTableWidgetItem(str(文))
                格.setTextAlignment((Qt.AlignRight if c in (3, 4) else Qt.AlignLeft) | Qt.AlignVCenter)
                if c == 2:
                    种 = 状态样子.get(文, (文, "次"))[1]
                    格.setText(f"●  {文}")
                    格.setForeground(颜色(色.get(种 + "字", 色[种])))
                elif c == 5:
                    格.setForeground(颜色(色["坏字"] if 文 else 色["弱字"]))
                    格.setToolTip(文)
                elif c == 0:
                    格.setForeground(颜色(色["弱字"]))
                if r["测试"]:                    # Claude 自测的运行：整行灰色，工作台不算它
                    格.setForeground(颜色(色["灰"]))
                    if c == 1:
                        格.setToolTip("这是 Claude 测试时跑的，不是你跑的。工作台的“上次结果”不算它。")
                self.表.setItem(i, c, 格)
        self.表.resizeColumnsToContents()
        self.表.setUpdatesEnabled(True)
        self.空字.setVisible(not 行们)

    def _打开(self, 行, _列):
        if 0 <= 行 < len(self.显示中):
            夹 = 运行历史.日志文件夹(self.显示中[行])
            if 夹 and 夹.exists():
                os.startfile(夹)
            else:
                self.状态栏.showMessage("那次的日志文件夹已经不在了（超过 90 天会自动删除）。", 5000)

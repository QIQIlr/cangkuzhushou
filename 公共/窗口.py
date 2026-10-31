# 职责：仓库助手 窗口版（测试版）。双击 仓库助手（测试版）.vbs 打开，不出现黑色命令行窗口。
# 2026-10-24 整体重新设计（小柒要求）：左侧导航 + 四个页面，样子统一见 公共\界面\主题.py。
#   工作台：模块卡片（开关 = 启用，拖动 = 顺序，改动立即保存到 模块设置.txt）、运行按钮、需要注意、右侧模块设置
#   运行结果：进度、这次运行的模块列表、每个模块的结果页（公共\结果页.py）、运行过程
#     每个模块查完马上显示（不等后面的）；打开时显示上一次的结果（公共\上次结果.py，小柒 2026-10-24）
#   运行记录：日志\运行总表.csv
#   设置：飞书（机器人；自动发的说明——总开关只在工作台右上角）、登录 WMS / 飞书、邮编数据、日志文件夹、刷新模块列表
# 这个文件只管：程序入口、窗口外壳和导航、后台运行、掉线登录和运行中选任务的等待、关闭。
# 查询在后台线程里跑，窗口不会卡住；业务逻辑全部复用 公共\运行.py 和各模块。
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

from PySide6.QtCore import QEvent, QLockFile, QObject, QSize, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QHBoxLayout, QMainWindow,  # noqa: E402
                               QStackedWidget, QVBoxLayout, QWidget)

from 公共 import 结果页, 飞书  # noqa: E402
from 公共.界面 import 主题  # noqa: E402
from 公共.界面 import 提示 as 提示框  # noqa: E402
from 公共.界面.主题 import 图标, 色  # noqa: E402
from 公共.界面.弹窗 import 任务选择窗口, 飞书设置窗口  # noqa: E402,F401  （测试脚本也从这里拿）
from 公共.界面.组件 import 按钮, 标签  # noqa: E402
from 公共.界面.工作台 import 工作台  # noqa: E402
from 公共.界面.记录页 import 记录页  # noqa: E402
from 公共.界面.设置页 import 设置页  # noqa: E402
from 公共.界面.运行页 import 运行页  # noqa: E402
from 公共.模块参数 import 显示名  # noqa: E402
from 公共.wms import WMS首页, 专用配置目录, 专用窗口开着, 找Chrome, 找不到Chrome说明  # noqa: E402
from 公共.日志 import 日志根, 运行记录  # noqa: E402

测试不发送 = os.environ.get("仓库助手_测试不发送") == "1"


class 传话(QObject):
    """后台线程 → 窗口 的消息（Qt 会自动排队到窗口线程）。"""
    步骤 = Signal(str, str)
    开始模块 = Signal(int, int, str)
    模块完成 = Signal(str, object)
    模块结果 = Signal(object)
    全部完成 = Signal(object)
    出错 = Signal(str)
    需要登录 = Signal(int)
    需要选择 = Signal(object)


class 主窗口(QMainWindow):
    页名 = ["工作台", "运行结果", "运行记录", "设置"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("仓库助手（测试版）")
        self.resize(1180, 760)
        self.setMinimumSize(1000, 640)
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
        self.传话.模块结果.connect(self._模块结果)
        self.传话.全部完成.connect(self._全部完成)
        self.传话.出错.connect(self._运行出错)
        self.传话.需要登录.connect(self._请登录)
        self.传话.需要选择.connect(self._请选择)
        try:   # 无任务包裹以前存的“区域”换成同样的“查询范围”（只做一次，查的区不变）
            from 公共 import 查询范围
            查询范围.迁移旧设置()
        except Exception:
            _记下窗口错误(traceback.format_exc())
        self._搭界面()

    # ---------- 外壳：左侧导航 + 页面 ----------
    def _搭界面(self):
        from 公共 import 模块参数
        中心 = QWidget()
        总 = QHBoxLayout(中心)
        总.setContentsMargins(0, 0, 0, 0)
        总.setSpacing(0)

        # 左侧菜单可以收起（小柒 2026-10-25）：收起只剩图标（约 64px），展开是图标 + 文字（约 212px）；
        # 顶部 ☰ 切换，记住上次的样子；进“运行结果”时自动收起，离开时自动展开回来（2026-10-31），手动展开过就不再自动收或展。
        self.侧 = 侧 = QFrame()
        侧.setObjectName("侧栏")
        侧层 = QVBoxLayout(侧)
        侧层.setContentsMargins(12, 16, 12, 16)
        侧层.setSpacing(4)
        头行 = QHBoxLayout()
        头行.setContentsMargins(0, 0, 0, 0)
        self.折叠钮 = 按钮("", "图标", 图="列表", 图色=色["字"], 提示="收起 / 展开菜单")
        self.折叠钮.setIconSize(QSize(20, 20))
        self.折叠钮.setFixedSize(40, 36)
        self.折叠钮.clicked.connect(lambda: self.设菜单收起(not self.菜单收起, 手动=True))
        头行.addWidget(self.折叠钮)
        头行.addStretch(1)
        侧层.addLayout(头行)
        侧层.addSpacing(8)
        self.软件名 = 标签("仓库助手")
        self.软件名.setObjectName("软件名")
        侧层.addWidget(self.软件名)
        self.软件说明 = 标签("测试版 · 只查询不改数据", "说明")
        侧层.addWidget(self.软件说明)
        侧层.addSpacing(16)
        self.导航组 = QButtonGroup(self)
        self.导航钮 = []
        self.导航图 = ["首页", "运行", "记录", "设置"]
        for i, 页 in enumerate(self.页名):
            b = 按钮(页, 图=self.导航图[i])
            b.setProperty("nav", "1")
            b.setCheckable(True)
            self.导航组.addButton(b, i)
            self.导航钮.append(b)
            if 页 == "设置":
                侧层.addStretch(1)
                self.运行中标 = 标签("", "说明")
                self.运行中标.setWordWrap(True)
                侧层.addWidget(self.运行中标)
                侧层.addSpacing(8)
            侧层.addWidget(b)
        self.导航组.idClicked.connect(self.去)
        总.addWidget(侧)

        self.页们 = QStackedWidget()
        self.工作台 = 工作台(模块参数.界面设置("运行完自动发飞书", True))
        self.工作台.自动发.toggled.connect(lambda 开: 模块参数.保存界面设置("运行完自动发飞书", 开))
        self.工作台.运行请求.connect(self.开始运行)
        self.工作台.去看记录.connect(lambda: self.去(2))
        self.运行页 = 运行页(self.statusBar(), self._手动发送)
        self.运行页.去工作台.connect(lambda: self.去(0))
        self.记录页 = 记录页(self.statusBar())
        self.设置页 = 设置页({"设置飞书": self.设置飞书, "登录WMS": self.登录WMS, "登录飞书": self.登录飞书,
                          "更新邮编": self.更新邮编, "打开日志": lambda: os.startfile(日志根),
                          "刷新模块": self.刷新模块, "样板": lambda: self.去(4)}, self.工作台.自动发, 测试不发送)
        from 公共.界面.样板页 import 样板页
        self.样板页 = 样板页()
        self.样板页.返回.connect(lambda: self.去(3))
        for 页 in (self.工作台, self.运行页, self.记录页, self.设置页, self.样板页):
            self.页们.addWidget(页)
        总.addWidget(self.页们, 1)
        self.setCentralWidget(中心)
        self.自动发 = self.工作台.自动发
        # 底部状态栏只在有话说的时候出现（复制成功、测试模式等），平时不占一条横杠
        self.statusBar().messageChanged.connect(lambda 字: self.statusBar().setVisible(bool(字) or 测试不发送))
        self.statusBar().showMessage("测试模式：不发飞书" if 测试不发送 else "")
        self.statusBar().setVisible(测试不发送)
        self._本次 = None
        self.菜单手动展开过 = False
        self.自动收起 = False            # 记住当前这个“收起”是程序自动做的，不是用户点的
        self.设菜单收起(bool(模块参数.界面设置("菜单收起", False)))
        try:   # 打开时：运行结果页先显示上一次的结果（标明时间）
            from 公共 import 上次结果
            数据 = 上次结果.读取()
            if 数据:
                self.运行页.显示上次(数据)
        except Exception:
            _记下窗口错误("显示上一次的结果时出错：\n" + traceback.format_exc())
        self.去(0)

    def 设菜单收起(self, 收起, 手动=False):
        """收起 = 只剩图标（鼠标停在图标上显示文字）；展开 = 图标 + 文字。记进 模块参数.json 的“界面”。"""
        from 公共 import 模块参数
        self.菜单收起 = bool(收起)
        if 手动 and not 收起:
            self.菜单手动展开过 = True
        self.侧.setFixedWidth(64 if 收起 else 212)
        for w in (self.软件名, self.软件说明):
            w.setVisible(not 收起)
        self.运行中标.setVisible(not 收起 and bool(self.运行中标.text()))
        for i, b in enumerate(self.导航钮):
            b.setText("" if 收起 else self.页名[i])
            b.setToolTip(self.页名[i] if 收起 else "")
            b.setProperty("narrow", "1" if 收起 else "0")
            b.style().unpolish(b)
            b.style().polish(b)
        if 手动:                       # 只记你自己点 ☰ 的结果；进结果页时自动收起不记
            self.自动收起 = False      # 用户主动点了 ☰，程序就别再插手
            模块参数.保存界面设置("菜单收起", self.菜单收起)

    def 去(self, 序号):
        self.导航钮[min(序号, 3)].setChecked(True)          # 第 5 页“界面样板”从设置进去，导航上亮着“设置”
        self.页们.setCurrentIndex(序号)
        self._导航图标()
        if 序号 == 1:
            if not self.菜单收起 and not self.菜单手动展开过:
                self.设菜单收起(True)          # 看结果时把地方让给结果
                self.自动收起 = True           # 记下这是程序收的，离开结果页要还回去
        elif self.自动收起:
            self.设菜单收起(False)             # 离开结果页：自动收的自动展开（2026-10-31 修）
            self.自动收起 = False
        if 序号 == 2:
            self.记录页.刷新()
        elif 序号 == 3:
            self.设置页.刷新()

    def 刷新模块(self):
        self.工作台.刷新模块()

    def _导航图标(self):
        """选中的那行蓝底白字，图标也是白的；没选中的是黑色图标（正在运行时“运行结果”是蓝色）。"""
        for i, b in enumerate(self.导航钮):
            if b.isChecked():
                颜色值 = 色["白"]
            elif i == 1 and getattr(self, "_运行色", None):
                颜色值 = self._运行色
            else:
                颜色值 = 色["字"]
            b.setIcon(图标(self.导航图[i], 颜色值, 16))

    def _运行标(self, 文字, 种="运行"):
        self.运行中标.setText(文字)
        self.运行中标.setVisible(bool(文字) and not getattr(self, "菜单收起", False))
        self.运行中标.setStyleSheet(f"color:{色.get(种 + '字', 色[种])}; background:{色[种 + '底']}; border-radius:8px; padding:8px 12px;"
                                  if 文字 else "")
        self._运行色 = 色[种] if 文字 else None
        self._导航图标()

    # ---------- 运行 ----------
    def 开始运行(self, 名列表):
        if self.运行中:
            return
        if not 名列表:
            提示框.信息(self, "没有模块", "没有要运行的模块。\n（运行已启用：请先打开模块的开关；只运行选中的：请先点选模块。）")
            return
        if 专用窗口开着():
            提示框.警告(self, "请先关闭专用 Chrome", "“自动化专用 Chrome”窗口还开着（登录 WMS 时打开的那个）。\n请先关掉它，再点运行。")
            return
        self.运行中 = True
        self._本次 = {"开始": datetime.now(), "模块们": list(名列表), "结果们": []}
        self.工作台.设可用(False)
        self.运行页.开始(名列表, f"{datetime.now():%H:%M:%S} 开始：{' → '.join(map(显示名, 名列表))}")
        self._运行标(f"正在运行 0/{len(名列表)}")
        self.去(1)
        运行记录.观察者 = lambda 模块名, 文字: self.传话.步骤.emit(模块名, 文字)
        self._本次发送 = self.自动发.isChecked() and not 测试不发送   # 在窗口线程里读好，后台线程只用这个值
        self._总数 = len(名列表)
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
        elif 事件 == "模块结果":
            self.传话.模块结果.emit(内容)

    def _显示步骤(self, 模块名, 文字):
        if 文字.startswith("-" * 10):
            return
        self.运行页.加一行(f"[{模块名}] {文字}")
        if re.match(r"第\d+步", 文字):
            self.运行页.步骤(文字)

    def _开始模块(self, 序号, 总数, 名):
        self.运行页.模块开始(序号, 总数, 名)
        self._运行标(f"正在运行 {序号}/{总数}\n{显示名(名)}")

    def _模块完成(self, 名, 结果):
        好 = 结果["状态"] in ("成功", "无数据", "未运行")
        数量 = f"，数量 {结果['数量']}" if 结果.get("数量") is not None else ""
        self.运行页.加一行(f"{'✔' if 好 else '⚠'} {显示名(名)}：{结果['状态']}{数量}")
        self.运行页.模块完成(名, 结果)

    def _模块结果(self, 项):
        """一个模块整理好、按设置发完飞书：马上显示，并存进“上一次的结果”。"""
        self.运行页.显示一个(项)
        if self._本次 is not None:
            self._本次["结果们"].append(项)
            self._存上次(完成=False)

    def _存上次(self, 完成):
        if self._本次 is None:
            return
        try:
            from 公共 import 上次结果
            上次结果.保存(self._本次["开始"], self._本次["模块们"], self._本次["结果们"], 完成)
        except Exception:
            _记下窗口错误("保存“上一次的结果”时出错：\n" + traceback.format_exc())

    def _全部完成(self, 总结):
        运行记录.观察者 = None
        self.运行中 = False
        self.工作台.设可用(True)
        坏的 = []
        for 项 in 总结["消息们"]:
            状态, 说明 = 项["飞书"]
            if 状态 in ("失败", "未知"):
                坏的.append(f"{项['显示名']}：{状态}，{说明}")
        self.本次日志 = 总结["日志文件夹"]
        if self._本次 is not None:
            self._本次["结果们"] = list(总结["消息们"])
            self._存上次(完成=True)
        有问题 = [r for r in 总结["结果们"] if r["状态"] not in ("成功", "无数据", "未运行")]
        self.运行页.全部完成(总结["消息们"], self.本次日志, len(有问题))
        self._运行标(f"上次运行：{len(有问题)} 个模块有问题" if 有问题 else "上次运行：全部正常",
                    "注意" if 有问题 else "好")
        self.工作台.刷新模块()          # 卡片上的“上次结果”、需要注意
        if 坏的:
            提示框.警告(self, "飞书没发成功", "\n".join(坏的))

    def _显示结果(self, 消息们):
        """测试用：直接把一组结果显示在运行结果页。"""
        self.运行页.开始([项["模块"] for 项 in 消息们], "")
        self.运行页.全部完成(消息们, 消息们[0].get("日志文件夹") if 消息们 else None,
                         sum(1 for 项 in 消息们 if 项["状态"] not in ("成功", "无数据", "未运行")))
        self.去(1)

    def _手动发送(self, 项, 字, 钮):
        """把某个模块这次的结果发到飞书（运行时没发、或想再发一次时用）。发送情况记进这个模块的日志。"""
        if not 飞书.可以发送():
            提示框.信息(self, "飞书", "还没设置好飞书，请先到“设置”里点“设置飞书”。")
            return
        之前 = 项["飞书"][0]
        if 之前 in ("成功", "未知"):
            提示 = "这个结果已经发到飞书了，确定要再发一次吗？" if 之前 == "成功" else \
                "上次发送结果“未知”（可能已经发出去了）。请先到飞书群里看一眼。\n确定要再发一次吗？"
            if not 提示框.询问(self, "再发一次？", 提示, 是="再发一次", 否="不发了"):
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            状态, 说明 = 飞书.发送全部(项.get("卡片们") or [], 项["文字"])
        finally:
            QApplication.restoreOverrideCursor()
        项["飞书"] = (状态, 说明)
        文字, 坏 = 结果页.飞书说明(状态, 说明, 手动=True)
        字.setText(文字)
        字.setStyleSheet(f"color:{结果页.色['坏'] if 坏 else 结果页.色['说明']};")
        钮.setText("再发一次到飞书" if 状态 == "成功" else "发到飞书")
        try:
            from 公共.日志 import 遮掩
            with open(Path(项["日志文件夹"]) / "运行记录.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%H:%M:%S}] 窗口里手动发送飞书：{状态}（{遮掩(说明)}）\n")
        except Exception:
            pass
        self.statusBar().showMessage(f"{项['显示名']}：飞书 {状态}", 5000)
        if 状态 != "成功":
            提示框.警告(self, "飞书没发成功", f"{状态}：{说明}")

    def _运行出错(self, 详情):
        运行记录.观察者 = None
        self.运行中 = False
        self.工作台.设可用(True)
        _记下窗口错误(详情)
        self._存上次(完成=False)
        self.运行页.出错()
        self._运行标("上次运行出现意外错误", "坏")
        提示框.出错(self, "意外错误", "运行时出现意外错误。\n详情已保存到 日志\\窗口错误.txt，请把这件事告诉 Claude。")

    # ---------- 掉线登录 ----------
    def _等登录(self, 次数):
        """后台线程调用：请窗口弹窗，等人点按钮。"""
        self.登录事件.clear()
        self.传话.需要登录.emit(次数)
        self.登录事件.wait()
        return self.登录回答

    def _请登录(self, 次数):
        文字 = (("还没有检测到登录成功，请再试一次。\n\n" if 次数 == 2 else "")
                + "WMS 已掉线。已经弹出一个 Chrome 窗口，请在里面登录 WMS。\n"
                  "登录完成后不要关闭这个 Chrome 窗口，点“我登录好了”，程序会自动继续。")
        self.登录回答 = 提示框.选择(self, "需要登录 WMS", 文字, [("取消这次运行", "取消"), ("我登录好了", "主")], 默认=1) == 1
        self.登录事件.set()

    # ---------- 运行中勾选（转寄退货任务） ----------
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
        self.设置页.刷新()

    def 登录WMS(self):
        if self.运行中:
            提示框.信息(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            提示框.信息(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        if not self._开专用Chrome(WMS首页):
            return
        提示框.信息(self, "登录 WMS", "已打开自动化专用 Chrome。\n请在里面登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。\n\n"
                                  "注意：这个 Chrome 开着时不能运行查询。\n"
                                  "（这是手动登录才要关。运行中掉线时程序自己弹出的 Chrome，登录后不要关。）")

    def _开专用Chrome(self, 网址):
        """手动登录用：打开自动化专用 Chrome。找不到 Chrome 时用中文说明原因，不报英文错误。"""
        路径 = 找Chrome()
        if not 路径:
            提示框.警告(self, "找不到 Chrome", 找不到Chrome说明)
            return False
        subprocess.Popen([路径, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", 网址])
        return True

    def 更新邮编(self):
        from 公共 import 邮编
        日期 = 邮编.数据日期()
        问 = (f"现在的邮编数据是 {日期:%Y-%m-%d} 下载的。\n" if 日期 else "电脑上还没有邮编数据。\n") + \
            "要从日本邮政官网下载最新的邮编数据吗？（约 2 MB，需要联网，官方每月更新一次）"
        if not 提示框.询问(self, "更新邮编数据", 问, 是="下载", 否="不用了"):
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            好, 说明 = 邮编.更新数据()
        finally:
            QApplication.restoreOverrideCursor()
        提示框.信息(self, "更新邮编数据", 说明)
        self.设置页.刷新()

    def 登录飞书(self):
        if self.运行中:
            提示框.信息(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            提示框.信息(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        from 公共.飞书网页 import 任务列表网址
        if not self._开专用Chrome(任务列表网址):
            return
        提示框.信息(self, "登录飞书", "已打开自动化专用 Chrome，进入飞书“我负责的”任务页。\n"
                                "如果出现登录页，请扫码或输入账号登录；看到任务列表就说明登录好了。\n"
                                "然后关掉那个 Chrome 窗口。\n\n注意：这个 Chrome 开着时不能运行查询。")

    # ---------- 关闭 ----------
    def closeEvent(self, 事件):
        if self.运行中:
            if not 提示框.询问(self, "正在运行", "查询还在运行。现在关闭会中止这次运行，结果不会发到飞书。\n确定要关闭吗？",
                              是="关闭", 否="不关", 危险=True):
                事件.ignore()
                return
            self._中止并退出()
        事件.accept()

    def _中止并退出(self, 退出=True):
        """运行中关窗口（2026-10-29）：先给正在跑的模块在运行总表补一行“被中止”，再尽量关掉运行用的 Chrome
        （最多等几秒，关不掉也照常退出），最后退出。每一步出错都不挡住退出。"""
        _记下窗口错误("用户在运行中关闭了窗口，本次运行被中止。")
        for 记录 in (运行记录.正在, 运行记录.本次主控):
            try:
                if 记录 is not None:
                    记录.中止("运行中关闭窗口")
            except Exception:
                _记下窗口错误("补“被中止”记录时出错：\n" + traceback.format_exc())
        try:
            from 公共.wms import 关掉自动化Chrome
            if not 关掉自动化Chrome(超时秒=4):
                _记下窗口错误("关闭运行用的 Chrome 超时，照常退出。")
        except Exception:
            _记下窗口错误("关闭运行用的 Chrome 时出错：\n" + traceback.format_exc())
        if 退出:
            os._exit(0)


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
        提示框.出错(None, "意外错误", f"仓库助手出现意外错误：{值}\n详情已保存到 日志\\窗口错误.txt，请告诉 Claude。")
    except Exception:
        pass


class 小窗检查(QObject):
    """闪出“pythonw”小窗的检查（2026-10-25）：界面零件还没放进窗口就被设成“显示”，Windows 就把它当成一个
    没标题的独立小窗弹出来（标题栏显示程序名 pythonw）。正常情况下除了主窗口和弹窗不该有别的顶层窗口；
    一旦出现，把它是什么、在哪行代码出现的写进 日志\\窗口错误.txt，方便找到并从根上修（这里只记录，不去遮掩）。"""

    def eventFilter(self, 对象, 事件):
        try:
            if 事件.type() == QEvent.Show and isinstance(对象, QWidget) and 对象.isWindow() \
                    and not isinstance(对象, (QMainWindow, QDialog)) \
                    and 对象.metaObject().className() not in ("QTipLabel", "QMenu", "QComboBoxPrivateContainer",
                                                              "QRollEffect"):   # Qt 自带的下拉“卷出”动画小窗，正常（体检 2026-10-28）
                栈 = "".join(traceback.format_stack(limit=12)[:-1])
                文字 = 对象.text() if hasattr(对象, "text") else ""
                _记下窗口错误(f"出现了意外的小窗口：{对象.metaObject().className()}（文字：{文字!r}）\n{栈}")
        except Exception:
            pass
        return False


def _设应用身份():
    """给仓库助手一个自己的“应用身份”（Windows 的 AppUserModelID）：
    不设的话，用 pythonw 运行时任务栏会把它算成 Python，显示 Python 的图标。"""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("1LR.仓库助手.测试版")
    except Exception:
        pass


def main():
    sys.excepthook = _意外
    _设应用身份()
    应用 = QApplication(sys.argv)
    主题.套用(应用)
    图标文件 = 根目录 / "公共" / "界面" / "图标" / "仓库助手.ico"     # 小柒 2026-10-25 选的 D（深色货架）
    if 图标文件.exists():
        from PySide6.QtGui import QIcon
        应用.setWindowIcon(QIcon(str(图标文件)))      # 窗口左上角、任务栏、弹窗都用它
    检查 = 小窗检查(应用)
    应用.installEventFilter(检查)
    日志根.mkdir(exist_ok=True)
    锁 = QLockFile(str(日志根 / "仓库助手窗口.lock"))
    if not 锁.tryLock(100):
        提示框.信息(None, "仓库助手", "仓库助手已经打开了（看看任务栏）。")
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

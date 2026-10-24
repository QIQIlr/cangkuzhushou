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

from PySide6.QtCore import QLockFile, QObject, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QHBoxLayout, QMainWindow,  # noqa: E402
                               QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from 公共 import 结果页, 飞书  # noqa: E402
from 公共.界面 import 主题  # noqa: E402
from 公共.界面.主题 import 图标, 色  # noqa: E402
from 公共.界面.弹窗 import 任务选择窗口, 飞书设置窗口  # noqa: E402,F401  （测试脚本也从这里拿）
from 公共.界面.组件 import 图标字, 按钮, 标签  # noqa: E402
from 公共.界面.工作台 import 工作台  # noqa: E402
from 公共.界面.记录页 import 记录页  # noqa: E402
from 公共.界面.设置页 import 设置页  # noqa: E402
from 公共.界面.运行页 import 运行页  # noqa: E402
from 公共.模块参数 import 显示名  # noqa: E402
from 公共.wms import WMS首页, 专用配置目录, 专用窗口开着  # noqa: E402
from 公共.日志 import 日志根, 运行记录  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
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

        侧 = QFrame()
        侧.setObjectName("侧栏")
        侧.setFixedWidth(212)
        侧层 = QVBoxLayout(侧)
        侧层.setContentsMargins(14, 18, 14, 14)
        侧层.setSpacing(4)
        标 = QHBoxLayout()
        标.setSpacing(10)
        徽 = 图标字("包裹", "#FFFFFF", 16)
        徽.setFixedSize(34, 34)
        徽.setStyleSheet(f"color:white; background:{色['主']}; border-radius:9px;")
        标.addWidget(徽)
        名层 = QVBoxLayout()
        名层.setSpacing(0)
        名 = 标签("仓库助手")
        名.setStyleSheet("font-size:13pt; font-weight:bold;")
        名层.addWidget(名)
        名层.addWidget(标签("测试版 · 只查询不改数据", "说明"))
        标.addLayout(名层, 1)
        侧层.addLayout(标)
        侧层.addSpacing(18)
        侧层.addWidget(标签("  菜单", "组名"))
        self.导航组 = QButtonGroup(self)
        self.导航钮 = []
        图们 = ["首页", "运行", "记录", "设置"]
        for i, (页, 图) in enumerate(zip(self.页名, 图们)):
            b = 按钮(页, 图=图)
            b.setProperty("nav", "1")
            b.setCheckable(True)
            b.setIconSize(b.iconSize())
            self.导航组.addButton(b, i)
            self.导航钮.append(b)
            if 页 == "设置":
                侧层.addStretch(1)
                self.运行中标 = 标签("", "说明")
                self.运行中标.setWordWrap(True)
                侧层.addWidget(self.运行中标)
                侧层.addSpacing(6)
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
                          "刷新模块": self.刷新模块}, self.工作台.自动发, 测试不发送)
        for 页 in (self.工作台, self.运行页, self.记录页, self.设置页):
            self.页们.addWidget(页)
        总.addWidget(self.页们, 1)
        self.setCentralWidget(中心)
        self.自动发 = self.工作台.自动发
        self.statusBar().showMessage("测试模式：不发飞书" if 测试不发送 else "")
        self._本次 = None
        try:   # 打开时：运行结果页先显示上一次的结果（标明时间）
            from 公共 import 上次结果
            数据 = 上次结果.读取()
            if 数据:
                self.运行页.显示上次(数据)
        except Exception:
            _记下窗口错误("显示上一次的结果时出错：\n" + traceback.format_exc())
        self.去(0)

    def 去(self, 序号):
        self.导航钮[序号].setChecked(True)
        self.页们.setCurrentIndex(序号)
        if 序号 == 2:
            self.记录页.刷新()
        elif 序号 == 3:
            self.设置页.刷新()

    def 刷新模块(self):
        self.工作台.刷新模块()

    def _运行标(self, 文字, 种="运行"):
        self.运行中标.setText(文字)
        self.运行中标.setStyleSheet(f"color:{色[种]}; background:{色[种 + '底']}; border-radius:8px; padding:6px 8px;"
                                  if 文字 else "")
        self.导航钮[1].setIcon(图标("运行", 色[种] if 文字 else 色["次字"]))

    # ---------- 运行 ----------
    def 运行全部(self):
        self.开始运行([名 for 名, 开 in self.工作台.当前清单() if 开])

    def 运行选中(self):
        self.开始运行(self.工作台.选中的())

    def 开始运行(self, 名列表):
        if self.运行中:
            return
        if not 名列表:
            QMessageBox.information(self, "没有模块", "没有要运行的模块。\n（运行已启用：请先打开模块的开关；只运行选中的：请先点选模块。）")
            return
        if 专用窗口开着():
            QMessageBox.warning(self, "请先关闭专用 Chrome", "“自动化专用 Chrome”窗口还开着（登录 WMS 时打开的那个）。\n请先关掉它，再点运行。")
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
        好 = 结果["状态"] in ("成功", "无数据")
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
        有问题 = [r for r in 总结["结果们"] if r["状态"] not in ("成功", "无数据")]
        self.运行页.全部完成(总结["消息们"], self.本次日志, len(有问题))
        self._运行标(f"上次运行：{len(有问题)} 个模块有问题" if 有问题 else "上次运行：全部正常",
                    "注意" if 有问题 else "好")
        self.工作台.刷新模块()          # 卡片上的“上次结果”、需要注意
        if 坏的:
            QMessageBox.warning(self, "飞书没发成功", "\n".join(坏的))

    def _显示结果(self, 消息们):
        """测试用：直接把一组结果显示在运行结果页。"""
        self.运行页.开始([项["模块"] for 项 in 消息们], "")
        self.运行页.全部完成(消息们, 消息们[0].get("日志文件夹") if 消息们 else None,
                         sum(1 for 项 in 消息们 if 项["状态"] not in ("成功", "无数据")))
        self.去(1)

    def _手动发送(self, 项, 字, 钮):
        """把某个模块这次的结果发到飞书（运行时没发、或想再发一次时用）。发送情况记进这个模块的日志。"""
        if not 飞书.可以发送():
            QMessageBox.information(self, "飞书", "还没设置好飞书，请先到“设置”里点“设置飞书”。")
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
            QMessageBox.warning(self, "飞书没发成功", f"{状态}：{说明}")

    def _运行出错(self, 详情):
        运行记录.观察者 = None
        self.运行中 = False
        self.工作台.设可用(True)
        _记下窗口错误(详情)
        self._存上次(完成=False)
        self.运行页.出错()
        self._运行标("上次运行出现意外错误", "坏")
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
            QMessageBox.information(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            QMessageBox.information(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        subprocess.Popen([CHROME, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", WMS首页])
        QMessageBox.information(self, "登录 WMS", "已打开自动化专用 Chrome。\n请在里面登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。\n\n注意：这个 Chrome 开着时不能运行查询。")

    def 更新邮编(self):
        from 公共 import 邮编
        日期 = 邮编.数据日期()
        问 = (f"现在的邮编数据是 {日期:%Y-%m-%d} 下载的。\n" if 日期 else "电脑上还没有邮编数据。\n") + \
            "要从日本邮政官网下载最新的邮编数据吗？（约 2 MB，需要联网，官方每月更新一次）"
        if QMessageBox.question(self, "更新邮编数据", 问, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            好, 说明 = 邮编.更新数据()
        finally:
            QApplication.restoreOverrideCursor()
        (QMessageBox.information if 好 else QMessageBox.warning)(self, "更新邮编数据", 说明)
        self.设置页.刷新()

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
    主题.套用(应用)
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

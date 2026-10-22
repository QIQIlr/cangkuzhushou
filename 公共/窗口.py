# 职责：仓库助手 窗口版（测试版）。双击 仓库助手（测试版）.vbs 打开，不出现黑色命令行窗口。
# 内容：左边模块列表（勾选=启用，拖动或上移/下移=调顺序，改动立即保存到 模块设置.txt）；
#       右边运行按钮、进度、运行过程、结果（和发到飞书的一样）、打开日志；
#       下面设置：飞书、消息格式、登录 WMS。
# 说明：查询在后台线程里跑，窗口不会卡住；掉线时弹窗请你登录。
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
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFormLayout, QGroupBox,  # noqa: E402
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
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
        from 公共.设置飞书 import 格式
        网址 = self.网址.text().strip()
        if not 格式.match(网址):
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


class 主窗口(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("仓库助手（测试版）")
        self.resize(1100, 720)
        self.运行中 = False
        self.本次日志 = None
        self.登录回答 = None
        self.登录事件 = threading.Event()
        self.传话 = 传话()
        self.传话.步骤.connect(self._显示步骤)
        self.传话.开始模块.connect(self._开始模块)
        self.传话.模块完成.connect(self._模块完成)
        self.传话.全部完成.connect(self._全部完成)
        self.传话.出错.connect(self._运行出错)
        self.传话.需要登录.connect(self._请登录)
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
        右层.addWidget(self.过程, 2)
        右层.addWidget(QLabel("结果（和发到飞书的一样）："))
        self.结果 = QPlainTextEdit()
        self.结果.setReadOnly(True)
        右层.addWidget(self.结果, 3)
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
        for 文字, 函数 in (("设置飞书", self.设置飞书), ("设置消息格式", self.设置消息格式),
                         ("登录 WMS", self.登录WMS), ("打开日志文件夹", lambda: os.startfile(日志根)),
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
        self.结果.clear()
        self.飞书状态.setText("")
        self.开本次日志按钮.setEnabled(False)
        self.进度条.setMaximum(len(名列表))
        self.进度条.setValue(0)
        self.进度文字.setText("正在打开 WMS ……")
        self.过程.appendPlainText(f"{datetime.now():%H:%M:%S} 开始：{' → '.join(名列表)}")
        运行记录.观察者 = lambda 模块名, 文字: self.传话.步骤.emit(模块名, 文字)
        threading.Thread(target=self._后台运行, args=(名列表,), daemon=True).start()

    def _后台运行(self, 名列表):
        try:
            from 公共.运行 import 运行模块们
            总结 = 运行模块们(名列表, 发送=not 测试不发送, 显示=False, 等待登录=self._等登录,
                          回报=lambda 事件, 内容: self._回报(事件, 内容))
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
        self.结果.setPlainText(总结["消息"])
        状态, 说明 = 总结["飞书"]
        self.飞书状态.setText(f"飞书：{状态}（{说明}）")
        self.本次日志 = 总结["日志文件夹"]
        self.开本次日志按钮.setEnabled(True)
        有问题 = [r for r in 总结["结果们"] if r["状态"] not in ("成功", "无数据")]
        self.进度文字.setText("完成：全部正常 ✔" if not 有问题 else f"完成：{len(有问题)} 个模块有问题 ⚠（看下面的结果和建议）")
        if 状态 in ("失败", "未知"):
            QMessageBox.warning(self, "飞书没发成功", f"飞书：{状态}\n{说明}")

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

    # ---------- 设置 ----------
    def 设置飞书(self):
        飞书设置窗口(self).exec()

    def 设置消息格式(self):
        from 公共.消息格式 import 格式目录
        名们 = sorted(p.stem for p in 格式目录.glob("*.txt"))
        if not 名们:
            QMessageBox.information(self, "没有格式文件", "格式 文件夹里还没有格式文件。")
            return
        名 = 名们[0]
        if len(名们) > 1:
            名, ok = QInputDialog.getItem(self, "设置消息格式", "要改哪个模块的消息格式？", 名们, 0, False)
            if not ok:
                return
        self._格式模块 = 名
        self._记事本 = subprocess.Popen(["notepad.exe", str(格式目录 / f"{名}.txt")])
        self.statusBar().showMessage(f"已用记事本打开 格式\\{名}.txt：改好后保存（Ctrl+S）并关掉记事本，这里会自动预览。")
        self._格式计时 = QTimer(self)
        self._格式计时.timeout.connect(self._等记事本)
        self._格式计时.start(500)

    def _等记事本(self):
        if self._记事本.poll() is None:
            return
        self._格式计时.stop()
        self.statusBar().clearMessage()
        import importlib
        from 公共.消息格式 import 格式目录, 格式错误, 排版
        from 公共.设置消息格式 import 最近结果
        名 = self._格式模块
        模块 = importlib.import_module(f"模块.{名}")
        结果, 来源 = 最近结果(名)
        公共, 区域列表 = 模块.排版内容(结果, 用时=15)
        try:
            排版((格式目录 / f"{名}.txt").read_text(encoding="utf-8-sig"), 公共, 区域列表)
        except 格式错误 as e:
            答 = QMessageBox.warning(self, "格式写错了", f"✘ {e}\n\n不改的话，查询时会继续用上一次能用的格式，查询不会失败。\n\n现在再打开改一下吗？",
                                    QMessageBox.Yes | QMessageBox.No)
            if 答 == QMessageBox.Yes:
                self.设置消息格式()
            return
        消息, _ = 模块.组成消息(结果, "（预览）", 用时=15)
        框 = QMessageBox(self)
        框.setWindowTitle("消息格式预览")
        框.setText(f"✔ 格式没问题。下面是用{来源}排出来的样子：\n\n{消息}")
        发 = 框.addButton("发一条【测试】预览到飞书", QMessageBox.ActionRole) if 飞书.可以发送() else None
        框.addButton("好", QMessageBox.AcceptRole)
        框.exec()
        if 发 is not None and 框.clickedButton() is 发:
            状态, 说明 = 飞书.发送("【测试】格式预览\n" + 消息)
            QMessageBox.information(self, "飞书", f"飞书：{状态}（{说明}）")

    def 登录WMS(self):
        if self.运行中:
            QMessageBox.information(self, "正在运行", "正在运行中，请等运行完再登录。")
            return
        if 专用窗口开着():
            QMessageBox.information(self, "已经打开", "自动化专用 Chrome 已经开着了，请在里面登录，然后关掉它。")
            return
        subprocess.Popen([CHROME, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", WMS首页])
        QMessageBox.information(self, "登录 WMS", "已打开自动化专用 Chrome。\n请在里面登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。\n\n注意：这个 Chrome 开着时不能运行查询。")

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

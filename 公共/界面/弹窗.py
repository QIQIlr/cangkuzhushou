# 职责：弹出的小窗口和模块设置面板。内容、按钮、保存规则和改版前一样，只换了样子。
#   任务选择窗口：转寄退货任务运行中，按飞书顺序列出全部标题，点一行勾选（不分组、不排序、默认不勾，小柒 2026-10-24 确认）
#   飞书设置窗口：粘贴 Webhook，测试成功才保存
#   模块设置面板：工作台右边那块（就地改名、查询范围、跑完自动发飞书；改动即保存，小柒 2026-10-24）
import importlib

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QScrollArea, QVBoxLayout, QWidget)

from 公共 import 模块参数, 模块设置, 飞书
from 公共.界面.主题 import 色
from 公共.界面.组件 import 分隔线, 卡片, 开关, 按钮, 标签, 空白提示


class 任务选择窗口(QDialog):
    def __init__(self, 父, 清单):
        super().__init__(父)
        self.setWindowTitle("转寄退货任务：选择要读取的任务")
        self.resize(1000, 660)
        层 = QVBoxLayout(self)
        层.setContentsMargins(20, 18, 20, 16)
        层.setSpacing(10)
        行们, 应有 = 清单["行们"], 清单.get("应有")
        层.addWidget(标签("飞书 · 我负责的", "眉"))
        头 = 标签(f"共读到 {len(行们)} 条" + (f"，和页面显示的 {应有} 条一致" if 应有 == len(行们) else ""), "大标题")
        层.addWidget(头)
        for 句 in 清单.get("提醒", []):
            注 = 标签(句, 换行=True)
            注.setStyleSheet(f"color:{色['注意字']}; background:{色['注意底']}; border:1px solid {色['注意线']};"
                            "border-radius:8px; padding:6px 10px;")
            层.addWidget(注)
        层.addWidget(标签("按飞书里的顺序列出。点一行就勾选或取消（可以选多条），再点“开始读取”。每条大约 6～11 秒。", "说明"))
        self.列表 = QListWidget()
        self.列表.setWordWrap(True)                       # 长标题换行显示，不截断
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.setStyleSheet(f"QListWidget::item {{ padding: 8px 6px; border-bottom: 1px solid {色['线']}; }}")
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
        self.开始 = 按钮("开始读取（已选 0 条）", "主")
        self.开始.setEnabled(False)
        self.开始.clicked.connect(self.accept)
        取消 = 按钮("取消（这次不读）")
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
        self.setMinimumWidth(560)
        层 = QVBoxLayout(self)
        层.setContentsMargins(20, 18, 20, 16)
        层.setSpacing(10)
        层.addWidget(标签("设置", "眉"))
        层.addWidget(标签("飞书群机器人", "大标题"))
        层.addWidget(标签("在飞书群设置 → 群机器人 → 你的机器人 里复制 Webhook 地址，粘贴到下面。\n"
                         "点“测试并保存”会发一条测试消息，成功才保存。", "说明", 换行=True))
        表 = QFormLayout()
        表.setSpacing(10)
        self.网址 = QLineEdit()
        self.网址.setEchoMode(QLineEdit.Password)
        self.网址.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/……（输入时不显示）")
        self.关键词 = QLineEdit(飞书.读设置().get("飞书关键词", ""))
        self.关键词.setPlaceholderText("机器人“安全设置”里的自定义关键词；没有就空着")
        表.addRow("Webhook 地址", self.网址)
        表.addRow("自定义关键词", self.关键词)
        层.addLayout(表)
        if 飞书.可以发送():
            层.addWidget(标签("目前已经设置好。只有换群或换机器人时才需要重新填。", "说明"))
        行 = QHBoxLayout()
        行.addStretch(1)
        取消 = 按钮("取消")
        取消.clicked.connect(self.reject)
        钮 = 按钮("测试并保存", "主")
        钮.clicked.connect(self.测试)
        行.addWidget(取消)
        行.addWidget(钮)
        层.addLayout(行)

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


def 模块信息(模块名):
    """(默认参数, 可发飞书, 说明)。模块文件载入失败时给空的，界面照样能开。"""
    try:
        模块 = importlib.import_module(f"模块.{模块名}")
        return getattr(模块, "默认参数", {}), getattr(模块, "可发飞书", True), getattr(模块, "说明", "")
    except Exception:
        return {}, True, ""


class 模块设置面板(QWidget):
    """工作台右边：选中模块的设置（小柒 2026-10-24）。
    - 名字：点名字或铅笔就地修改，✓ / 回车 保存，✗ / Esc 取消；原名固定不变。
    - 查询范围：仓库 + 单独的区，规则见 公共\查询范围.py（勾了仓库，它包含的区收起）。
    - 跑完自动发到飞书群（这个模块）。
    范围和飞书开关一改就保存，没有“保存”按钮。保存后发 已保存(原名)。"""
    已保存 = Signal(str)

    def __init__(self):
        super().__init__()
        self.模块名 = None
        self.总开关开 = False          # 工作台右上角“跑完自动发飞书”，只用来写说明
        外 = QVBoxLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        self.卡 = 卡片(18, 12)
        外.addWidget(self.卡)
        self.空 = 空白提示("设置", "模块设置", "在左边点一个模块，这里就能改它的名字、查询范围和跑完要不要自动发飞书。")
        self.卡.层.addWidget(self.空)
        self.表 = None

    # ---------- 搭界面 ----------
    def 显示(self, 模块名, 说明=""):
        """换成某个模块的设置（模块名 = 原名；None = 空白提示）。"""
        if self.表 is not None:
            self.表.hide()
            self.卡.层.removeWidget(self.表)
            self.表.deleteLater()
            self.表 = None
        self.模块名 = 模块名
        self.空.setVisible(模块名 is None)
        if 模块名 is None:
            return
        from 公共 import 查询范围
        默认, self.可发, 模块说明 = 模块信息(模块名)
        self.参数 = 模块参数.读取(模块名, 默认)
        # 一闪而过的小窗口（小柒 2026-10-24 报）：以前新面板先不挂在卡片上就去设“显示”，
        # 那些勾选框、文字就被 Windows 当成独立的小窗口弹出来一下。现在一开始就挂在卡片上、先藏着，搭好再显示。
        self.表 = QWidget(self.卡)
        self.表.hide()
        层 = QVBoxLayout(self.表)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(8)
        层.addWidget(标签("模块设置", "眉"))
        # 名字：平时是文字 + 铅笔，点了变成输入框
        self.名字行 = QWidget()
        名层 = QHBoxLayout(self.名字行)
        名层.setContentsMargins(0, 0, 0, 0)
        名层.setSpacing(4)
        self.名字字 = 可点标签(模块参数.显示名(模块名))
        self.名字字.setStyleSheet("font-size:14pt; font-weight:bold;")
        self.名字字.setToolTip("点一下改名字")
        self.名字字.点了.connect(self.开始改名)
        名层.addWidget(self.名字字, 0)
        铅笔 = 按钮("", "图标", 图="编辑", 提示="改名字")
        铅笔.clicked.connect(self.开始改名)
        名层.addWidget(铅笔)
        名层.addStretch(1)
        层.addWidget(self.名字行)
        self.改名行 = QWidget()
        改层 = QHBoxLayout(self.改名行)
        改层.setContentsMargins(0, 0, 0, 0)
        改层.setSpacing(4)
        self.名字框 = 名字输入框()
        self.名字框.setMaxLength(模块参数.最长)
        self.名字框.回车.connect(self.保存名字)
        self.名字框.取消.connect(self.取消改名)
        改层.addWidget(self.名字框, 1)
        好 = 按钮("", "图标", 图="勾", 图色=色["好"], 提示="保存名字（回车）")
        好.clicked.connect(self.保存名字)
        不 = 按钮("", "图标", 图="错", 提示="不改了（Esc）")
        不.clicked.connect(self.取消改名)
        改层.addWidget(好)
        改层.addWidget(不)
        self.改名行.setVisible(False)
        层.addWidget(self.改名行)
        self.改名提示 = 标签("", "说明", 换行=True)
        self.改名提示.setVisible(False)
        层.addWidget(self.改名提示)
        原名字 = 标签(f"原名：{模块名}（固定不变；改名只改显示的名字）", "说明", 换行=True)
        self.原名字 = 原名字
        层.addWidget(原名字)
        原名字.setVisible(模块参数.显示名(模块名) != 模块名)
        if 说明 or 模块说明:
            层.addWidget(标签(说明 or 模块说明, "说明", 换行=True))
        层.addWidget(分隔线())

        滚 = QScrollArea()
        滚.setWidgetResizable(True)
        滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        内 = QWidget()
        内层 = QVBoxLayout(内)
        内层.setContentsMargins(0, 0, 4, 0)
        内层.setSpacing(6)
        # 飞书放在前面：一眼就能看到
        内层.addWidget(标签("飞书", "组名"))
        self.发送框 = 开关("跑完自动发到飞书群")
        if self.可发:
            self.发送框.setChecked(bool(self.参数.get("发到飞书", True)))
            self.发送框.toggled.connect(self._改飞书)
            内层.addWidget(self.发送框)
        self.飞书说明 = 标签("", "说明", 换行=True)
        内层.addWidget(self.飞书说明)
        # 查询范围
        self.仓库框, self.区框 = {}, {}
        if "查询范围" in self.参数:
            已选, _ = 查询范围.整理(self.参数.get("查询范围"))
            内层.addSpacing(8)
            内层.addWidget(标签("查询范围（每勾一项，单独出一张表）", "组名"))
            内层.addWidget(标签("仓库", "说明"))
            for 仓 in 查询范围.仓库:
                框 = QCheckBox(查询范围.说明(仓), 内)
                框.setChecked(仓 in 已选)
                框.toggled.connect(self._改范围)
                self.仓库框[仓] = 框
                内层.addWidget(框)
            内层.addSpacing(4)
            内层.addWidget(标签("单独的区", "说明"))
            self.区格 = QGridLayout()
            self.区格.setHorizontalSpacing(16)
            for 区 in 查询范围.区域们():
                框 = QCheckBox(查询范围.说明(区), 内)
                框.setChecked(区 in 已选)
                框.toggled.connect(self._改范围)
                self.区框[区] = 框
            内层.addLayout(self.区格)
            self.范围说明 = 标签("", "说明", 换行=True)
            内层.addWidget(self.范围说明)
            self._排范围()
        内层.addStretch(1)
        滚.setWidget(内)
        层.addWidget(滚, 1)
        层.addWidget(分隔线())
        self.保存字 = 标签("改动会自动保存。", "说明")
        层.addWidget(self.保存字)
        self.卡.层.addWidget(self.表, 1)
        self.表.show()
        self.更新飞书说明()

    # ---------- 名字 ----------
    def 开始改名(self):
        if self.表 is None:
            return
        self.名字框.setText(模块参数.显示名(self.模块名))
        self.名字行.setVisible(False)
        self.改名行.setVisible(True)
        self.改名提示.setText(f"回车保存，Esc 不改。最多 {模块参数.最长} 个字；想改回原来的名字，就填“{self.模块名}”。")
        self.改名提示.setStyleSheet("")
        self.改名提示.setVisible(True)
        self.名字框.setFocus()
        self.名字框.selectAll()

    def 取消改名(self):
        self.改名行.setVisible(False)
        self.改名提示.setVisible(False)
        self.名字行.setVisible(True)

    def 保存名字(self):
        问题 = self.应用新名字(self.模块名, self.名字框.text().strip())
        if 问题:
            self.改名提示.setText("没保存：" + 问题)
            self.改名提示.setStyleSheet(f"color:{色['坏']};")
            self.名字框.setFocus()
            return
        self.取消改名()

    def 应用新名字(self, 原名, 新名):
        """改名的唯一入口（右边铅笔、左边卡片上双击名字都走这里）。返回 "" = 好了，或者一句没改的原因。"""
        if 新名 == 模块参数.显示名(原名):
            return ""
        问题 = 模块参数.检查名字(原名, 新名, 模块设置.所有模块())
        if 问题:
            if 原名 == self.模块名 and self.表 is not None:
                self.保存字.setText("没改名：" + 问题)
                self.保存字.setStyleSheet(f"color:{色['坏']};")
            return 问题
        模块参数.保存显示名(原名, 新名)
        if 原名 == self.模块名 and self.表 is not None:
            self.名字字.setText(模块参数.显示名(原名))
            self.原名字.setVisible(模块参数.显示名(原名) != 原名)
            self._已保存(f"名字已改成“{模块参数.显示名(原名)}”")
        else:
            self.已保存.emit(原名)
        return ""

    # ---------- 范围 ----------
    def _排范围(self):
        """勾了仓库：它包含的区取消勾选并收起；没勾仓库的区照常显示。"""
        from 公共 import 查询范围
        收起 = []
        for 区, 框 in self.区框.items():
            仓 = 查询范围.包含它的仓库(区, [名 for 名, f in self.仓库框.items() if f.isChecked()])
            if 仓:
                框.blockSignals(True)
                框.setChecked(False)
                框.blockSignals(False)
                收起.append(f"{区}")
            框.setVisible(not 仓)
        for 框 in self.区框.values():          # 显示的区按顺序排，收起的不占位置
            self.区格.removeWidget(框)
        for i, 框 in enumerate(f for f in self.区框.values() if not f.isHidden()):
            self.区格.addWidget(框, i // 3, i % 3)
        空 = not any(f.isChecked() for f in self.仓库框.values()) and not any(
            f.isChecked() and not f.isHidden() for f in self.区框.values())
        字 = ("已经包含在勾选的仓库里，不用单独勾：" + "、".join(收起) + "。") if 收起 else ""
        if 空:
            字 = "一项都没勾：这个模块即使在左边开着，运行时也不会跑。"
        self.范围说明.setText(字)
        self.范围说明.setStyleSheet(f"color:{色['注意']};" if 空 else "")
        self.范围说明.setVisible(bool(字))

    def _改范围(self, _开=None):
        from 公共 import 查询范围
        框 = self.sender()
        self._排范围()
        选择 = [名 for 名, f in self.仓库框.items() if f.isChecked()] + \
             [名 for 名, f in self.区框.items() if f.isChecked() and not f.isHidden()]
        整理后, _ = 查询范围.整理(选择)
        self.参数["查询范围"] = 整理后          # 可以一项都不勾：这个模块就不跑（小柒 2026-10-24）
        模块参数.保存(self.模块名, self.参数)
        self._排范围()
        self._已保存("查询范围已保存：" + ("、".join(整理后) if 整理后 else "一项都没勾，这个模块不会跑"))

    # ---------- 飞书 ----------
    def _改飞书(self, 开):
        self.参数["发到飞书"] = bool(开)
        模块参数.保存(self.模块名, self.参数)
        self.更新飞书说明()
        self._已保存("已保存：" + ("跑完自动发到飞书群" if 开 else "跑完不自动发"))

    def 设总开关(self, 开):
        self.总开关开 = bool(开)
        self.更新飞书说明()

    def 更新飞书说明(self):
        if self.表 is None:
            return
        if not self.可发:
            字 = "这个模块的结果只在仓库助手里看，不能发到飞书。"
        elif not self.总开关开:
            字 = ("现在不会自动发：工作台右上角的“跑完自动发飞书”关着。"
                  if self.发送框.isChecked() else "跑完不会自动发。") + "想发的时候，在结果下面点“发到飞书”。"
        else:
            字 = "跑完会自动发到飞书群。" if self.发送框.isChecked() else "跑完不会自动发。想发的时候，在结果下面点“发到飞书”。"
        self.飞书说明.setText(字)

    def _已保存(self, 文字):
        from datetime import datetime
        self.保存字.setText(f"✔ {文字}（{datetime.now():%H:%M:%S}）")
        self.保存字.setStyleSheet(f"color:{色['好']};")
        self.已保存.emit(self.模块名)


class 可点标签(QLabel):
    点了 = Signal()

    def __init__(self, 文字=""):
        super().__init__(文字)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, 事件):
        if 事件.button() == Qt.LeftButton:
            self.点了.emit()
        super().mouseReleaseEvent(事件)


class 名字输入框(QLineEdit):
    回车 = Signal()
    取消 = Signal()

    def keyPressEvent(self, 事件):
        if 事件.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.回车.emit()
        elif 事件.key() == Qt.Key_Escape:
            self.取消.emit()
        else:
            super().keyPressEvent(事件)

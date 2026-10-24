# 职责：弹出的小窗口和模块设置面板。内容、按钮、保存规则和改版前一样，只换了样子。
#   任务选择窗口：转寄退货任务运行中，按飞书顺序列出全部标题，点一行勾选（不分组、不排序、默认不勾，小柒 2026-10-24 确认）
#   飞书设置窗口：粘贴 Webhook，测试成功才保存
#   模块设置面板：工作台右边那块（名字、查询范围/区域、发到飞书）
import importlib

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit,
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
    """工作台右边：选中模块的设置。保存规则和改版前的“模块设置”窗口一样。保存后发 已保存(原名)。"""
    已保存 = Signal(str)

    def __init__(self):
        super().__init__()
        self.模块名 = None
        外 = QVBoxLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        self.卡 = 卡片(18, 12)
        外.addWidget(self.卡)
        self.空 = 空白提示("设置", "模块设置", "在左边点一个模块，这里就能改它的名字、查询范围和发不发飞书。双击模块也能打开。")
        self.卡.层.addWidget(self.空)
        self.表 = None

    def 显示(self, 模块名, 说明=""):
        """换成某个模块的设置（模块名 = 原名；None = 空白提示）。"""
        if self.表 is not None:
            self.表.setParent(None)
            self.表.deleteLater()
            self.表 = None
        self.模块名 = 模块名
        self.空.setVisible(模块名 is None)
        if 模块名 is None:
            return
        默认, 可发, 模块说明 = 模块信息(模块名)
        self.参数 = 模块参数.读取(模块名, 默认)
        self.表 = QWidget()
        层 = QVBoxLayout(self.表)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(10)
        层.addWidget(标签("模块设置", "眉"))
        名 = 标签(模块参数.显示名(模块名), "小标题")
        名.setStyleSheet("font-size:14pt; font-weight:bold;")
        层.addWidget(名)
        if 说明 or 模块说明:
            层.addWidget(标签(说明 or 模块说明, "说明", 换行=True))
        层.addWidget(分隔线())

        滚 = QScrollArea()
        滚.setWidgetResizable(True)
        滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        内 = QWidget()
        内层 = QVBoxLayout(内)
        内层.setContentsMargins(0, 0, 4, 0)
        内层.setSpacing(8)
        内层.addWidget(标签("名字", "组名"))
        名行 = QHBoxLayout()
        self.名字框 = QLineEdit(模块参数.显示名(模块名))
        self.名字框.setMaxLength(模块参数.最长)
        名行.addWidget(self.名字框, 1)
        恢复 = 按钮("恢复原名", "淡")
        恢复.clicked.connect(lambda: self.名字框.setText(模块名))
        名行.addWidget(恢复)
        内层.addLayout(名行)
        内层.addWidget(标签(f"原名：{模块名}（固定不变）。改名后窗口、飞书卡片、Excel、日志都用新名字；勾选、顺序和下面的设置不变。"
                          f"最多 {模块参数.最长} 个字，不能有 {' '.join(模块参数.不能用的符号)}", "说明", 换行=True))
        self.区域框, self.范围框 = {}, {}
        if "查询范围" in self.参数:
            from 公共.待处理 import 仓库, 范围选项
            内层.addSpacing(6)
            内层.addWidget(标签("查询范围（每个勾选项单独一张表、一张飞书卡片）", "组名"))
            for 范 in 范围选项:
                文字 = f"{范}（{' + '.join(仓库[范])}）" if 范 in 仓库 else (f"{范}（测试区）" if 范 == "B区" else f"{范}（单独）")
                框 = QCheckBox(文字)
                框.setChecked(范 in self.参数["查询范围"])
                self.范围框[范] = 框
                内层.addWidget(框)
            内层.addWidget(标签("一般勾仓库就行；想单独看某个区时再勾那个区。", "说明", 换行=True))
        if "区域" in self.参数:
            内层.addSpacing(6)
            内层.addWidget(标签("查询区域（表格和结果按这里的顺序）", "组名"))
            格 = QGridLayout()
            格.setHorizontalSpacing(16)
            for i, 区 in enumerate(模块参数.区域选项()):
                框 = QCheckBox(区)
                框.setChecked(区 in self.参数["区域"])
                self.区域框[区] = 框
                格.addWidget(框, i // 3, i % 3)
            内层.addLayout(格)
            内层.addWidget(标签("区域选项来自 WMS 的“所属区域”下拉（运行待审核、待拣货、待增值时会自动更新）。", "说明", 换行=True))
        内层.addSpacing(6)
        内层.addWidget(标签("飞书", "组名"))
        self.发送框 = 开关("结果发到飞书")
        self.发送框.setChecked(self.参数.get("发到飞书", True) and 可发)
        if 可发:
            内层.addWidget(self.发送框)
        else:
            内层.addWidget(标签("这个模块的结果只在仓库助手窗口里看，不发飞书。", "说明", 换行=True))
        内层.addStretch(1)
        滚.setWidget(内)
        层.addWidget(滚, 1)
        层.addWidget(分隔线())
        行 = QHBoxLayout()
        行.addStretch(1)
        放弃 = 按钮("放弃修改")
        放弃.clicked.connect(lambda: self.显示(模块名, 说明))
        保存 = 按钮("保存", "主")
        保存.clicked.connect(self.保存)
        行.addWidget(放弃)
        行.addWidget(保存)
        层.addLayout(行)
        self.卡.层.addWidget(self.表, 1)

    def 聚焦(self):
        if self.表 is not None:
            self.名字框.setFocus()

    def 保存(self):
        新名 = self.名字框.text().strip()
        问题 = 模块参数.检查名字(self.模块名, 新名, 模块设置.所有模块())
        if 问题:
            QMessageBox.warning(self, "名字不能用", 问题)
            return
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
        self.参数["发到飞书"] = self.发送框.isChecked()          # 和改版前一样：不能发的模块存“否”
        模块参数.保存(self.模块名, self.参数)
        模块参数.保存显示名(self.模块名, 新名)
        self.已保存.emit(self.模块名)

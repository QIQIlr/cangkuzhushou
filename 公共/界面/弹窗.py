# 职责：弹出的小窗口和模块设置面板。内容、按钮、保存规则和改版前一样，只换了样子。
#   任务选择窗口：转寄退货任务运行中，按飞书顺序列出全部标题，点一行勾选（不分组、不排序、默认不勾，小柒 2026-10-24 确认）
#   飞书设置窗口：粘贴 Webhook，测试成功才保存
#   问题清单窗口：工作台标题行右侧 ⚠ 点开——上次没跑成的模块，可以去看记录或只重跑这几个（2026-10-31）
#   模块设置面板：工作台右边那块（就地改名、查询范围、跑完自动发飞书；改动即保存，小柒 2026-10-24）
import importlib

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QScrollArea, QStyle, QStyledItemDelegate,
                               QStyleOptionViewItem, QVBoxLayout, QWidget)

from 公共 import 模块参数, 模块设置, 飞书
from 公共.界面 import 提示
from 公共.界面.提示 import 窗内弹窗, 胶囊钮
from 公共.界面.主题 import 字号, 色
from 公共.界面.组件 import 分组块, 勾选行, 开关, 按钮, 标签, 状态标签, 空白提示, 行


class _勾在右边(QStyledItemDelegate):
    """规范“多选”：选中的行末尾显示蓝色 ✓，不用方框勾选框；长标题换行显示。"""

    def _窄(self, 选项, 索引):
        o = QStyleOptionViewItem(选项)
        self.initStyleOption(o, 索引)
        o.features &= ~QStyleOptionViewItem.HasCheckIndicator
        o.rect = o.rect.adjusted(16, 0, -48, 0)
        return o

    def sizeHint(self, 选项, 索引):
        o = self._窄(选项, 索引)
        宽 = max(100, o.rect.width())
        高 = o.fontMetrics.boundingRect(0, 0, 宽, 10000, Qt.TextWordWrap, o.text).height()
        return QSize(选项.rect.width(), max(44, 高 + 20))

    def paint(self, p, 选项, 索引):
        o = self._窄(选项, 索引)
        o.state &= ~QStyle.State_Selected
        o.state &= ~QStyle.State_HasFocus
        p.save()
        p.setPen(QColor(色["字"]))
        p.setFont(o.font)
        p.drawText(o.rect, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap, o.text)
        if 索引.row() < 索引.model().rowCount() - 1:
            p.setPen(QColor(色["线"]))
            p.drawLine(选项.rect.left() + 16, 选项.rect.bottom(), 选项.rect.right(), 选项.rect.bottom())
        if Qt.CheckState(索引.data(Qt.CheckStateRole)) == Qt.Checked:
            from 公共.界面.主题 import 图标字体对象, 图码
            p.setPen(QColor(色["主"]))
            p.setFont(图标字体对象(16))
            p.drawText(QRectF(选项.rect.right() - 44, 选项.rect.top(), 28, 选项.rect.height()), Qt.AlignCenter, 图码["勾"])
        p.restore()


class 任务选择窗口(窗内弹窗):
    """转寄退货任务运行中弹出：按飞书顺序列出全部标题，点一行勾选（不分组、不排序、默认不勾，小柒 2026-10-24 确认）。
    规范“弹窗”：标题加粗居中；里面用分组列表，选中的行末尾蓝色 ✓；底部 取消（蓝字）、开始读取（蓝色加粗）。"""

    def __init__(self, 父, 清单):
        super().__init__(父, 820)
        self.setWindowTitle("转寄退货任务：选择要读取的任务")
        self.卡.setMinimumHeight(560)
        层 = self.卡层
        行们, 应有 = 清单["行们"], 清单.get("应有")
        头 = 标签(f"选择要读取的任务")
        头.setAlignment(Qt.AlignCenter)
        头.setStyleSheet(f"font-size:{字号['弹窗标题']}px; font-weight:bold;")
        层.addWidget(头)
        副 = 标签(f"飞书“我负责的”共读到 {len(行们)} 条" + (f"，和页面显示的 {应有} 条一致" if 应有 == len(行们) else "")
                 + "。按飞书里的顺序列出，点一行就选中或取消（可以选多条）。每条大约 6～11 秒。", "说明", 换行=True)
        副.setAlignment(Qt.AlignCenter)
        层.addWidget(副)
        for 句 in 清单.get("提醒", []):
            注 = 标签(句, 换行=True)
            注.setStyleSheet(f"color:{色['注意字']}; background:{色['注意底']}; border-radius:12px; padding:8px 16px;")
            层.addWidget(注)
        层.addSpacing(4)
        self.列表 = QListWidget()
        self.列表.setWordWrap(True)                       # 长标题换行显示，不截断
        self.列表.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.列表.setItemDelegate(_勾在右边(self.列表))
        self.列表.setStyleSheet("QListWidget::item, QListWidget::item:selected, QListWidget::item:hover { background: transparent; }")
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
        行.setSpacing(10)
        self.开始 = 胶囊钮("开始读取（已选 0 条）", "主")
        self.开始.setEnabled(False)
        self.开始.clicked.connect(self.accept)
        取消 = 胶囊钮("取消（这次不读）", "次")
        取消.clicked.connect(self.reject)
        行.addWidget(取消, 1)
        行.addWidget(self.开始, 1)
        层.addSpacing(8)
        层.addLayout(行)

    def 默认动作(self):
        if self.开始.isEnabled():
            self.accept()

    def _切换(self, 项):
        项.setCheckState(Qt.Unchecked if 项.checkState() == Qt.Checked else Qt.Checked)
        数 = len(self.选中())
        self.开始.setText(f"开始读取（已选 {数} 条）")
        self.开始.setEnabled(数 > 0)

    def 选中(self):
        return [self.列表.item(i).data(Qt.UserRole) for i in range(self.列表.count())
                if self.列表.item(i).checkState() == Qt.Checked]


class 飞书设置窗口(窗内弹窗):
    """规范“弹窗”：标题加粗居中、说明居中；输入框放在分组列表的行里；底部 取消（蓝字）、测试并保存（蓝色加粗）。"""

    def __init__(self, 父):
        super().__init__(父, 560)
        self.setWindowTitle("设置飞书群机器人")
        层 = self.卡层
        头 = 标签("飞书群机器人")
        头.setAlignment(Qt.AlignCenter)
        头.setStyleSheet(f"font-size:{字号['弹窗标题']}px; font-weight:bold;")
        层.addWidget(头)
        说 = 标签("在飞书群设置 → 群机器人 → 你的机器人 里复制 Webhook 地址，粘贴到下面。"
                 "点“测试并保存”会发一条测试消息，成功才保存。", "说明", 换行=True)
        说.setAlignment(Qt.AlignCenter)
        层.addWidget(说)
        层.addSpacing(8)
        self.网址 = QLineEdit()
        self.网址.setEchoMode(QLineEdit.Password)
        self.网址.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/……（输入时不显示）")
        self.关键词 = QLineEdit(飞书.读设置().get("飞书关键词", ""))
        self.关键词.setPlaceholderText("机器人“安全设置”里的自定义关键词；没有就空着")
        for 框 in (self.网址, self.关键词):
            框.setStyleSheet("QLineEdit { border: none; padding: 4px 0; background: transparent; }")
            框.setMinimumWidth(320)
        组 = 分组块("", "目前已经设置好。只有换群或换机器人时才需要重新填。" if 飞书.可以发送() else "")
        组.加行(行("Webhook 地址", self.网址))
        组.加行(行("自定义关键词", self.关键词))
        层.addWidget(组)
        层.addSpacing(8)
        钮行 = QHBoxLayout()
        钮行.setSpacing(10)
        取消 = 胶囊钮("取消", "次")
        取消.clicked.connect(self.reject)
        钮 = 胶囊钮("测试并保存", "主")
        钮.clicked.connect(self.测试)
        钮行.addWidget(取消, 1)
        钮行.addWidget(钮, 1)
        层.addLayout(钮行)

    def 默认动作(self):
        self.测试()
    def 测试(self):
        网址 = self.网址.text().strip()
        if not 飞书.格式.match(网址):
            提示.警告(self, "地址不对", "这不像飞书 Webhook 地址，应该以\nhttps://open.feishu.cn/open-apis/bot/v2/hook/ 开头。")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            状态, 说明 = 飞书.发送("【测试】仓库助手 飞书连接测试", 网址=网址, 关键词=self.关键词.text().strip())
        finally:
            QApplication.restoreOverrideCursor()
        if 状态 == "成功":
            飞书.写设置({"飞书Webhook": 网址, "飞书关键词": self.关键词.text().strip(), "飞书已测通": "是"})
            提示.信息(self, "成功", "✔ 成功！飞书群里应该收到了一条测试消息。\n设置已保存。")
            self.accept()
        else:
            提示.警告(self, "没有成功", f"测试没有成功（{状态}）：{说明}\n\n设置没有保存。")


class 问题清单窗口(窗内弹窗):
    """上次运行没跑成的模块（2026-10-31，小柒确认效果图）：标题 + 一句说明 + 分组列表 + 三个按钮。
    列表每行：模块名 / 一句原因 / 状态标签。选吧() 返回 None（关闭）、("看记录",) 或 ("重跑", [原名…])。"""

    def __init__(self, 父, 时间, 条们):
        super().__init__(父, 460)
        self.选了 = None            # 基类的 self.结果 是“接受 / 拒绝”，这里要带回更细的选择，所以另用一个属性
        self.条们 = list(条们)
        层 = self.卡层
        题 = QLabel("上次没跑成的地方")
        题.setAlignment(Qt.AlignCenter)
        题.setStyleSheet(f"font-size:{字号['弹窗标题']}px; font-weight:bold; color:{色['字']}; background:transparent;")
        层.addWidget(题)
        说 = QLabel(f"{时间:%m/%d %H:%M} 那次运行，这 {len(self.条们)} 个模块没有拿到结果。")
        说.setAlignment(Qt.AlignCenter)
        说.setWordWrap(True)
        说.setStyleSheet(f"font-size:{字号['正文'] - 1}px; color:{色['次字']}; background:transparent;")
        层.addWidget(说)
        层.addSpacing(6)
        组 = 分组块("")
        for 原名, 状态, 原因 in self.条们:
            组.加行(行(模块参数.显示名(原名), 状态标签(状态), 原因))
        层.addWidget(组)
        层.addSpacing(10)
        底 = QHBoxLayout()
        底.setSpacing(10)
        关 = 胶囊钮("关闭", "取消")
        看 = 胶囊钮("看运行记录", "次")
        跑 = 胶囊钮(f"重新运行这 {len(self.条们)} 个", "主")
        关.clicked.connect(self.reject)
        看.clicked.connect(lambda: self._选(("看记录",)))
        跑.clicked.connect(lambda: self._选(("重跑", [x[0] for x in self.条们])))
        for b in (关, 看, 跑):
            底.addWidget(b, 1)              # 三个等宽并排
        层.addLayout(底)

    def _选(self, 值):
        self.选了 = 值
        self.accept()

    def 选吧(self):
        self.exec()
        return self.选了

    def 默认动作(self):
        """回车 = 主按钮（重跑这几个）。"""
        self._选(("重跑", [x[0] for x in self.条们]))


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
        self.卡 = QWidget()            # 规范：右侧面板不加框，内容直接放在灰底上，用分组块分开
        self.卡.层 = QVBoxLayout(self.卡)
        self.卡.层.setContentsMargins(0, 0, 0, 0)
        self.卡.层.setSpacing(0)
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
        # 一闪而过的小窗口（小柒 2026-10-24 报）：新面板一开始就挂在父控件上、先藏着，搭好再显示。
        self.表 = QWidget(self.卡)
        self.表.hide()
        层 = QVBoxLayout(self.表)
        层.setContentsMargins(0, 0, 0, 0)
        层.setSpacing(4)
        层.addWidget(标签("模块设置", "眉"))
        # 名字：平时是文字 + 铅笔，点了变成输入框
        self.名字行 = QWidget()
        名层 = QHBoxLayout(self.名字行)
        名层.setContentsMargins(0, 0, 0, 0)
        名层.setSpacing(4)
        self.名字字 = 可点标签(模块参数.显示名(模块名))
        self.名字字.setProperty("role", "paneltitle")
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
        好 = 按钮("", "图标", 图="勾", 提示="保存名字（回车）")
        好.clicked.connect(self.保存名字)
        不 = 按钮("", "图标", 图="错", 图色=色["弱字"], 提示="不改了（Esc）")
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
        层.addSpacing(12)

        滚 = QScrollArea()
        滚.setWidgetResizable(True)
        滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        内 = QWidget()
        内层 = QVBoxLayout(内)
        内层.setContentsMargins(0, 0, 4, 0)
        内层.setSpacing(16)
        # 飞书放在前面：一眼就能看到
        self.飞书组 = 分组块("飞书")
        self.发送框 = 开关()
        if self.可发:
            self.发送框.setChecked(bool(self.参数.get("发到飞书", True)))
            self.发送框.toggled.connect(self._改飞书)
            self.飞书组.加行(行("跑完自动发到飞书群", self.发送框))
        else:
            self.飞书组.块.setVisible(False)
        内层.addWidget(self.飞书组)
        # 查询范围：仓库、单独的区，各一个分组块；选中的行末尾蓝色 ✓
        self.仓库框, self.区框 = {}, {}
        if "查询范围" in self.参数:
            已选, _ = 查询范围.整理(self.参数.get("查询范围"))
            仓组 = 分组块("查询范围 · 仓库（每勾一项，单独出一张表）")
            for 仓 in 查询范围.仓库:
                框 = 勾选行(查询范围.说明(仓), 内)
                框.setChecked(仓 in 已选)
                框.toggled.connect(self._改范围)
                self.仓库框[仓] = 框
                仓组.加行(框)
            内层.addWidget(仓组)
            self.区组 = 分组块("单独的区")
            for 区 in 查询范围.区域们():
                框 = 勾选行(查询范围.说明(区), 内)
                框.setChecked(区 in 已选)
                框.toggled.connect(self._改范围)
                self.区框[区] = 框
                self.区组.加行(框)
            内层.addWidget(self.区组)
            self._排范围()
        内层.addStretch(1)
        滚.setWidget(内)
        层.addWidget(滚, 1)
        self.保存字 = 标签("改动会自动保存。", "脚注")
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
        self.区组.排线()
        self.区组.块.setVisible(any(not f.isHidden() for f in self.区框.values()))
        空 = not any(f.isChecked() for f in self.仓库框.values()) and not any(
            f.isChecked() and not f.isHidden() for f in self.区框.values())
        字 = ("已经包含在勾选的仓库里，不用单独勾：" + "、".join(收起) + "。") if 收起 else ""
        if 空:
            字 = "一项都没勾：这个模块即使在左边开着，运行时也不会跑。"
        self.区组.设脚注(字, 色["注意字"] if 空 else None)
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
        self.飞书组.设脚注(字)

    def _已保存(self, 文字):
        from datetime import datetime
        self.保存字.setText(f"✔ {文字}（{datetime.now():%H:%M:%S}）")
        self.保存字.setStyleSheet(f"color:{色['好字']};")
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

# 职责：界面样板页（规范 v1.3 第 5 条，小柒 2026-10-25）：把仓库助手用到的每个零件都摆一份，给小柒确认。
#   小柒说可以以后，所有页面只用这里的零件；新零件先加到这里和规范里，再用。
#   入口：设置页最下面“界面样板”。每个零件旁边写它参考的苹果官方设计（HIG）条目。
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QListWidget, QProgressBar, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView)

from 公共.界面 import 提示
from 公共.界面.主题 import 色, 字号
from 公共.界面.组件 import (分段, 分组块, 勾选行, 开关, 按钮, 标签, 状态标签, 空白提示, 行, 页眉)


def _区(总, 名, 出处, 内容):
    """一个零件一节：灰色小标题（零件名 · 参考的苹果 HIG 条目）+ 内容。"""
    总.addWidget(标签(f"{名}    ·    参考：{出处}", "组名"))
    if isinstance(内容, QWidget):
        总.addWidget(内容)
    else:
        总.addLayout(内容)
    总.addSpacing(12)


def _横(*零件):
    h = QHBoxLayout()
    h.setSpacing(12)
    for z in 零件:
        h.addWidget(z)
    h.addStretch(1)
    return h


class 样板页(QWidget):
    返回 = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("页面")
        外 = QVBoxLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        滚 = QScrollArea()
        滚.setWidgetResizable(True)
        滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        内 = QWidget()
        内.setObjectName("页面")
        总 = QVBoxLayout(内)
        总.setContentsMargins(24, 20, 24, 24)
        总.setSpacing(6)
        头 = 页眉("设置 · 只给你确认用", "界面样板", "仓库助手用到的每个零件都在这里。你说可以以后，所有页面只用这些零件。")
        回 = 按钮("‹ 返回设置", "文字")
        回.clicked.connect(self.返回)
        头.右.addWidget(回)
        总.addWidget(头)
        总.addSpacing(12)

        _区(总, "按钮（三级 + 危险 + 设置行小按钮）", "HIG Buttons",
            _横(按钮("主按钮", "主"), 按钮("次要按钮"), 按钮("文字按钮", "文字"), 按钮("危险操作", "危险胶囊"),
                按钮("小按钮", "小"), self._不可用(按钮("不能点", "主")), self._不可用(按钮("不能点"))))

        开 = 开关()
        开.setChecked(True)
        关 = 开关()
        灰 = 开关()
        灰.setEnabled(False)
        _区(总, "开关（开 / 关 / 不能点）", "HIG Toggles", _横(开, 关, 灰))

        _区(总, "分段控件（切换几种视图）", "HIG Segmented controls", _横(分段(["合计", "合箱拣货", "单箱拣货"])))

        正常 = QLineEdit()
        正常.setPlaceholderText("灰色提示字")
        正常.setFixedWidth(280)
        出错框 = QLineEdit("待审核/测试")
        出错框.setFixedWidth(280)
        出错框.setStyleSheet(f"QLineEdit {{ border: 1px solid {色['坏']}; }}")
        错字 = 标签("名字里不能有 \\ / : * ? \" < > |", "说明")
        错字.setStyleSheet(f"color:{色['坏字']};")
        框列 = QVBoxLayout()
        框列.setSpacing(4)
        框列.addLayout(_横(正常, 出错框))
        框列.addWidget(错字)
        _区(总, "输入框（正常 / 出错时下面一行红字）", "HIG Text fields", 框列)

        组 = 分组块("分组小标题", "块下面可以跟一行灰色说明。")
        s = 开关()
        s.setChecked(True)
        组.加行(行("开关行", s))
        a = 勾选行("多选行：选中的末尾蓝色 ✓")
        a.setChecked(True)
        组.加行(a)
        组.加行(勾选行("多选行：没选中"))
        组.加行(行("带说明的行", 按钮("小按钮", "小"), "第二行灰色说明文字，可以换行。"))
        组.setMaximumWidth(560)
        _区(总, "分组列表（最重要的零件）", "HIG Lists and tables（Inset grouped）", 组)

        徽 = QHBoxLayout()
        徽.setSpacing(10)
        for 状 in ("成功", "无数据", "不完整", "失败"):
            徽.addWidget(状态标签(状, 醒目=True))
        徽.addSpacing(24)
        for 状 in ("成功", "无数据", "不完整", "失败"):
            徽.addWidget(状态标签(状))
        徽.addStretch(1)
        _区(总, "角标（胶囊）和状态圆点", "HIG Color（系统色 green / gray / orange / red）", 徽)

        条们 = QVBoxLayout()
        条们.setSpacing(8)
        for 种, 字 in (("注意", "● 提醒条：A区往前查到 10/10，还有 1 条对不上，请到 WMS 里看一下"),
                       ("坏", "● 出错条：这次没查到待增值的数量（不是 0）")):
            l = 标签(字, 换行=True)
            l.setStyleSheet(f"background:{色[种 + '底']}; color:{色[种 + '字']}; border-radius:12px; padding:10px 16px;")
            条们.addWidget(l)
        _区(总, "提醒条", "HIG Color（状态色淡底）", 条们)

        from 公共.结果页 import 数量表格
        表 = 数量表格(None)
        表.填(["日期", "D区", "E区", "瑞江合计"], [["10/23 周五", 12, 0, 12], ["10/24 周六（今天）", 5, 2, 7],
                                               ["**合计**", "**17**", "**2**", "**19**"]])
        _区(总, "表格", "HIG Lists and tables", 表)

        进 = QProgressBar()
        进.setTextVisible(False)
        进.setValue(62)
        进.setFixedWidth(220)
        状条 = QHBoxLayout()
        点 = 标签("●")
        点.setStyleSheet(f"color:{色['主']}; font-size:{字号['说明']}px;")
        状条.addWidget(点)
        状条.addWidget(标签("正在运行：待拣货"))
        状条.addWidget(进)
        状条.addWidget(标签("第3步 合箱拣货 D区 ……", "说明"))
        状条.addStretch(1)
        状条.addWidget(按钮("运行过程 ›", "文字"))
        _区(总, "运行状态条（细进度条，平滑前进）", "HIG Progress indicators", 状条)

        滚示 = QListWidget()
        for i in range(1, 31):
            滚示.addItem(f"第 {i} 行：把鼠标移到这里或滚一下，右边才出现细滚动条，内容宽度不变")
        滚示.setFixedSize(560, 150)
        滚示.setStyleSheet("QListWidget::item { padding: 6px 12px; }")
        _区(总, "悬浮细滚动条（不占宽度，停下 1 秒后淡出）", "HIG Scroll views", 滚示)

        弹 = QHBoxLayout()
        for 字, 函数 in (("打开提示弹窗", lambda: 提示.询问(self, "更新邮编数据", "现在的邮编数据是 2026-10-24 下载的。\n要从日本邮政官网下载最新的吗？（约 2 MB）",
                                                             是="下载", 否="不用了")),
                        ("打开危险确认", lambda: 提示.询问(self, "正在运行", "查询还在运行。现在关闭会中止这次运行。\n确定要关闭吗？",
                                                             是="关闭", 否="不关", 危险=True))):
            b = 按钮(字)
            b.clicked.connect(函数)
            弹.addWidget(b)
        弹.addStretch(1)
        _区(总, "窗口内弹窗（压暗 + 白色圆角卡片，Esc 取消，回车确定）", "HIG Alerts", 弹)

        空 = 空白提示("运行", "这次打开后还没有运行", "空状态：区域中间一个浅灰图标 + 一行灰字说明。")
        空.setFixedHeight(200)
        _区(总, "空状态", "HIG Writing（Empty states）", 空)

        总.addWidget(标签("导航（展开 = 图标 + 文字；收起 = 只剩图标，鼠标停留显示名字）：就是最左边那一栏，点 ☰ 可以切换。", "说明", 换行=True))
        总.addStretch(1)
        滚.setWidget(内)
        外.addWidget(滚)

    @staticmethod
    def _不可用(b):
        b.setEnabled(False)
        return b

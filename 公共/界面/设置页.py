# 职责：设置页。一般设置一次就不用再管的东西，按用途分组：飞书 ｜ 登录（WMS、飞书）｜ 邮编数据 ｜ 文件和模块。
#   “跑完自动发飞书”总开关只在工作台右上角（小柒 2026-10-24：不要两处都有），这里只用一句话说明现在是什么情况。
#   文字要求：平常的话，第一次用的人也看得懂（小柒 2026-10-24）。
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from 公共 import 飞书
from 公共.界面.组件 import 分组块, 按钮, 页眉, 行


def _一行(图, 标题, 说明, 右边们):
    """iOS 设置的一行：左边标题 + 灰色说明，右边文字按钮。（图 参数留着不用：规范不在设置行前放彩色图标）"""
    w = 行(标题, list(右边们), 说明 or " ")
    w.主字.setStyleSheet("font-size:15px;")
    return w

class 设置页(QWidget):
    def __init__(self, 动作, 自动发开关, 测试不发送=False):
        """动作：{设置飞书, 登录WMS, 登录飞书, 更新邮编, 打开日志, 刷新模块} → 窗口里的函数。
        自动发开关：工作台右上角的总开关（这里只读它的状态来写说明）。"""
        super().__init__()
        self.setObjectName("页面")
        self.自动发开关 = 自动发开关
        外 = QVBoxLayout(self)
        外.setContentsMargins(0, 0, 0, 0)
        滚 = QScrollArea()
        滚.setWidgetResizable(True)
        滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        内 = QWidget()
        内.setObjectName("页面")
        总 = QVBoxLayout(内)
        总.setContentsMargins(24, 20, 24, 20)
        总.setSpacing(20)
        总.addWidget(页眉("", "设置", "一般设置一次就不用再管。"))

        def 组(名, 行们):
            g = 分组块(名)
            for x in 行们:
                g.加行(x)
            g.setMaximumWidth(880)
            总.addWidget(g)

        def 钮(文字, 键, 类型="文字"):
            b = 按钮(文字, 类型)
            b.clicked.connect(lambda: 动作[键]())
            return b

        self.飞书行 = _一行("发送", "飞书群机器人", "", [钮("设置飞书", "设置飞书")])
        self.自动行 = _一行("同步", "跑完自动发飞书", "", [])
        飞书行们 = [self.飞书行, self.自动行]
        if 测试不发送:
            飞书行们.append(_一行("信息", "测试模式", "现在是测试模式：怎么设置都不会发飞书。", []))
        组("飞书", 飞书行们)
        组("登录", [
            _一行("全局", "WMS", "仓库助手用一个单独的 Chrome（叫“自动化专用 Chrome”）去查 WMS，和你平时用的 Chrome 分开。"
                  "点“登录 WMS”会打开它：要求登录就登录，已经登录就不用管，然后把这个 Chrome 关掉。"
                  "它开着的时候不能点运行。", [钮("登录 WMS", "登录WMS")]),
            _一行("人", "飞书网页版", "转寄退货任务要读飞书里的任务。运行时如果提示“需要登录飞书”，点这里，"
                  "在打开的 Chrome 里扫码登录，看到任务列表后把它关掉。", [钮("登录飞书", "登录飞书")]),
        ])
        self.邮编行 = _一行("地图", "日本邮编数据", "", [钮("更新邮编数据", "更新邮编")])
        组("数据", [self.邮编行])
        组("文件和模块", [
            _一行("文件夹", "日志文件夹", "每次运行的详细记录、出错时的截图和 Excel 都在这里。出问题时 Claude 会自己来看，你一般不用打开。",
                  [钮("打开日志文件夹", "打开日志")]),
            _一行("刷新", "模块列表", "Claude 加了新模块、或者有人直接改过 模块设置.txt 以后，点一下让工作台重新读取。",
                  [钮("刷新模块列表", "刷新模块")]),
        ])
        总.addStretch(1)
        滚.setWidget(内)
        外.addWidget(滚)
        自动发开关.toggled.connect(lambda _: self.刷新())
        self.刷新()

    def 刷新(self):
        self.飞书行.说明字.setText("仓库助手往哪个飞书群发结果。已经设置好了；只有换群或换机器人时才需要重新设置。"
                                 if 飞书.可以发送() else "还没设置。设置好以后，结果才能发到飞书群。")
        现在 = "开着" if self.自动发开关.isChecked() else "关着"
        self.自动行.说明字.setText(
            f"现在{现在}。这个开关在工作台右上角，运行按钮旁边。\n"
            "怎么算：总开关开着，并且这个模块自己的“跑完自动发到飞书群”也开着，跑完才会自动发。"
            "两个里有一个关着就不自动发。不管开关怎样，都可以在结果下面点“发到飞书”手动发一次。")
        try:
            from 公共 import 邮编
            日期 = 邮编.数据日期()
        except Exception:
            日期 = None
        self.邮编行.说明字.setText("转寄退货任务靠它查日本邮编、核对地址。"
                                 + (f"现在的数据是 {日期:%Y-%m-%d} 下载的。" if 日期 else "电脑上还没有邮编数据。")
                                 + "日本邮政每月更新一次，隔几个月点一次更新就够了（要联网，约 2 MB）。")

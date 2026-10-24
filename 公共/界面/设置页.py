# 职责：设置页。把改版前窗口最下面那排按钮按用途分组放在这里，每个按钮做的事和以前一样。
#   飞书群机器人 ｜ 登录（WMS、飞书）｜ 邮编数据 ｜ 运行选项 ｜ 文件和模块
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from 公共 import 飞书
from 公共.界面.主题 import 色
from 公共.界面.组件 import 卡片, 图标字, 开关, 按钮, 标签, 页眉


def _一行(图, 标题, 说明, 右边们):
    w = QWidget()
    层 = QHBoxLayout(w)
    层.setContentsMargins(0, 4, 0, 4)
    层.setSpacing(14)
    圈 = 图标字(图, 色["主"], 15)
    圈.setFixedSize(36, 36)
    圈.setStyleSheet(f"color:{色['主']}; background:{色['主浅']}; border-radius:18px;")
    层.addWidget(圈, 0, Qt.AlignTop)
    字层 = QVBoxLayout()
    字层.setSpacing(2)
    t = 标签(标题)
    t.setStyleSheet("font-weight:bold; font-size:10.5pt;")
    字层.addWidget(t)
    s = 标签(说明, "说明", 换行=True)
    字层.addWidget(s)
    层.addLayout(字层, 1)
    for x in 右边们:
        层.addWidget(x, 0, Qt.AlignVCenter)
    w.说明字 = s
    return w


class 设置页(QWidget):
    def __init__(self, 动作, 自动发开关, 测试不发送=False):
        """动作：{设置飞书, 登录WMS, 登录飞书, 更新邮编, 打开日志, 刷新模块} → 窗口里的函数。
        自动发开关：工作台上那个开关（这里放一个同步的）。"""
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
        总.setContentsMargins(28, 22, 28, 22)
        总.setSpacing(14)
        总.addWidget(页眉("设置", "设置", "飞书、登录、邮编数据和运行选项。一般设置一次就不用再管。"))

        def 组(名, 行们):
            卡 = 卡片(16, 6)
            卡.层.addWidget(标签(名, "组名"))
            for 行 in 行们:
                卡.层.addWidget(行)
            卡.setMaximumWidth(880)
            总.addWidget(卡)

        def 钮(文字, 键, 类型=None):
            b = 按钮(文字, 类型)
            b.clicked.connect(lambda: 动作[键]())
            return b

        self.飞书行 = _一行("发送", "飞书群机器人", "", [钮("设置飞书", "设置飞书")])
        组("飞书", [self.飞书行])
        组("登录", [
            _一行("全局", "WMS", "打开自动化专用 Chrome 进入 WMS。已登录就不用管；登录完关掉那个 Chrome 窗口。"
                  "注意：这个 Chrome 开着时不能运行查询。", [钮("登录 WMS", "登录WMS")]),
            _一行("人", "飞书网页版", "转寄退货任务用。程序报“需要登录飞书”时点这里，扫码或输入账号登录，看到任务列表后关掉那个 Chrome。",
                  [钮("登录飞书", "登录飞书")]),
        ])
        self.邮编行 = _一行("地图", "日本邮编数据", "", [钮("更新邮编数据", "更新邮编")])
        组("数据", [self.邮编行])
        self.同步开关 = 开关()
        self.同步开关.setChecked(自动发开关.isChecked())
        self.同步开关.toggled.connect(lambda 开: 自动发开关.setChecked(开) if 自动发开关.isChecked() != 开 else None)
        自动发开关.toggled.connect(lambda 开: self.同步开关.setChecked(开) if self.同步开关.isChecked() != 开 else None)
        运行行们 = [_一行("同步", "运行完自动发到飞书", "打开 = 按各模块自己的“结果发到飞书”自动发；关闭 = 只在窗口里显示，"
                        "想发哪个就点那个结果下面的“发到飞书”。工作台上也有这个开关。", [self.同步开关])]
        if 测试不发送:
            运行行们.append(_一行("信息", "测试模式", "现在是测试模式：不发飞书。", []))
        组("运行", 运行行们)
        组("文件和模块", [
            _一行("文件夹", "日志文件夹", "每次运行的记录、出错时的截图和 Excel 都在这里。", [钮("打开日志文件夹", "打开日志")]),
            _一行("刷新", "模块列表", "模块文件夹里加了新模块、或手改了 模块设置.txt 之后，点一下重新读取。", [钮("刷新模块列表", "刷新模块")]),
        ])
        总.addStretch(1)
        滚.setWidget(内)
        外.addWidget(滚)
        self.刷新()

    def 刷新(self):
        self.飞书行.说明字.setText("已经设置好，结果会发到这个群。只有换群或换机器人时才需要重新设置。" if 飞书.可以发送()
                                 else "还没设置。设置好之后，各模块的结果才能发到飞书群。")
        try:
            from 公共 import 邮编
            日期 = 邮编.数据日期()
        except Exception:
            日期 = None
        self.邮编行.说明字.setText((f"现在的数据是 {日期:%Y-%m-%d} 下载的。" if 日期 else "电脑上还没有邮编数据。")
                                 + "转寄退货任务按它查邮编、核对地址。官方每月更新，隔几个月更新一次就行（要联网，约 2 MB）。")

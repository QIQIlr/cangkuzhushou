# 职责：结果页的对外入口（外面只认 `from 公共 import 结果页; 结果页.一页(...)`）。
#   2026-10-31 从单个 结果页.py（1054 行）拆成包，**纯搬家，函数体一个字没改**。
#   内部结构：
#     零件.py    通用小零件 + 结论条 + 错误框 + 提醒框 + 底部一行
#     数量页.py  数量表、表块、自动排版
#     单号页.py  单号格、区域单号页（含“找单号”）
#     面单页.py  面单明细、任务清单、面单页
#   这个文件只放：对外导出 + _内容()（按结果挑一种样子）+ 一页()（把一块块拼起来）

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from 公共.界面 import 主题
from 公共.结果页.零件 import (_底部, _标签, _结论条, _提醒框, _错误框, 提醒们, 要看数, 飞书说明, 标签字)  # noqa: F401
from 公共.结果页.数量页 import 数量表格, _数量内容
from 公共.结果页.单号页 import 区域单号页
from 公共.结果页.面单页 import 面单页

色 = 主题.色
状态样子 = 主题.结果状态字
样式表 = 主题.结果页样式表

__all__ = ["一页", "提醒们", "要看数", "飞书说明", "标签字", "数量表格", "区域单号页",
           "色", "状态样子", "样式表"]


# ---------------- 一页 ----------------
def _内容(项, 状态栏):
    if 项.get("面单") is not None:
        return 面单页(项) if 项["面单"] else None
    if 项.get("分组") and 项["状态"] != "失败":
        return 区域单号页(项["分组"], 状态栏)
    if 项.get("数量表们") or any(行 for _, _, 行 in 项.get("表们", [])):
        return _数量内容(项, 状态栏)
    if 项["状态"] != "失败" and 项.get("文字") and not 项.get("结论"):
        字 = _标签(项["文字"])          # 只给文字的老模块
        字.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        return 字
    return None


def 一页(项, 状态栏, 发送):
    """一个模块的结果页（分栏视图的右边，小柒 2026-10-25）：
    整个详情只有一个滚动条；里面 结论 → 出错 / 提醒 → 内容（分组列表、表格）；最下面一行 飞书说明 + 文字按钮。
    发送(项, 说明字, 按钮)：点“发到飞书”时窗口去发。"""
    外 = QWidget()
    外.setStyleSheet(样式表)
    外层 = QVBoxLayout(外)
    外层.setContentsMargins(0, 0, 0, 0)
    外层.setSpacing(0)
    滚 = QScrollArea()
    滚.setWidgetResizable(True)
    滚.setFrameShape(QFrame.NoFrame)
    滚.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    内 = QWidget()
    内.setObjectName("页面")
    层 = QVBoxLayout(内)
    层.setContentsMargins(24, 20, 24, 16)
    层.setSpacing(16)
    层.addWidget(_结论条(项))
    句们 = 提醒们(项)
    if 项.get("错误们"):
        错行 = QHBoxLayout()               # 错误块最宽 640、靠左；窄窗口时跟着变窄，字照样换行
        错行.addWidget(_错误框(项["错误们"], "坏" if 项["状态"] == "失败" else "注意", 项.get("日志文件夹"), 句们), 1000)
        错行.addStretch(1)
        层.addLayout(错行)
    elif 句们:                             # 只有提醒、没有出错（如“任务有变动”“对不上”）：照旧单独一块橙色
        层.addWidget(_提醒框(句们))
    内容 = _内容(项, 状态栏)
    if 内容 is not None:
        层.addWidget(内容)
    层.addStretch(1)
    滚.setWidget(内)
    外层.addWidget(滚, 1)
    底 = QWidget()
    底层 = QVBoxLayout(底)
    底层.setContentsMargins(24, 8, 24, 12)
    底层.addLayout(_底部(项, 发送))
    外层.addWidget(底)
    return 外

# 职责：仓库助手的统一样子——颜色、字号、圆角、图标，以及整个程序用的一张样式表。
# 方向（2026-10-24 重新设计，参考 Taskless / Norix / Moneta 等，见 architecture 里的设计说明）：
#   浅灰底 + 白色圆角卡片 + 一个蓝色主色；状态色只表示状态；不加动画、渐变、毛玻璃。
# 改颜色只改这里，窗口、结果页、弹窗都会跟着变。
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

图标目录 = Path(__file__).resolve().parent / "图标"

色 = {
    # 底和面
    "底": "#F3F4F6", "面": "#FFFFFF", "面2": "#F9FAFB", "线": "#E5E7EB", "线深": "#D1D5DB",
    # 文字
    "字": "#111827", "次字": "#4B5563", "弱字": "#6B7280", "灰": "#9CA3AF",
    # 主色（只有一个蓝）
    "主": "#2F5BEA", "主深": "#2449C7", "主浅": "#EEF2FF", "主中": "#C7D2FE",
    # 状态
    "好": "#15803D", "好底": "#DCFCE7",
    "注意": "#B45309", "注意底": "#FEF3C7", "注意线": "#FCD34D", "注意字": "#78350F",
    "坏": "#B91C1C", "坏底": "#FEE2E2", "坏线": "#FCA5A5", "坏字": "#7F1D1D",
    "次": "#4B5563", "次底": "#F3F4F6",
    "运行": "#2F5BEA", "运行底": "#EEF2FF",
    # 零碎（以前散在各页面里的，2026-10-25 收回到这里）
    "白": "#FFFFFF", "选中卡底": "#F7F9FF", "单号字": "#444444", "面单字": "#111111",
    # 结果页用惯的名字（值和上面一样，只是起了个说法）
    "说明": "#6B7280", "选中": "#EEF2FF", "今天": "#EEF2FF", "合计底": "#F9FAFB", "段": "#F3F4F6",
}
字体 = "Microsoft YaHei UI"
等宽 = "Consolas"
圆角 = 10

# 结果页的状态写法（文字前带符号；颜色种类对应上面的 色）
结果状态字 = {"未运行": ("○ 没运行", "次"), "成功": ("✔ 成功", "好"), "无数据": ("○ 无数据", "次"),
           "不完整": ("⚠ 不完整", "注意"), "失败": ("✖ 失败", "坏")}

# 状态 → (文字, 颜色种类, 图标)
状态样子 = {"成功": ("成功", "好", "勾"), "无数据": ("无数据", "次", "圆"), "不完整": ("不完整", "注意", "警告"),
          "失败": ("失败", "坏", "错"), "等待": ("等待", "次", "时钟"), "运行中": ("正在运行", "运行", "同步"),
          "未运行": ("没运行", "次", "圆")}

# Windows 自带图标字体（Segoe Fluent Icons；老系统退回 Segoe MDL2 Assets），不用另装东西
图标字体 = "Segoe Fluent Icons"
图码 = {
    "首页": "", "运行": "", "记录": "", "设置": "", "勾": "", "警告": "",
    "错": "", "圆": "", "时钟": "", "同步": "", "文件夹": "", "刷新": "",
    "发送": "", "上": "", "下": "", "拖": "", "包裹": "", "邮件": "",
    "人": "", "地图": "", "文档": "", "表格": "", "信息": "", "列表": "",
    "铃": "", "钥匙": "", "链接": "", "全局": "", "编辑": "", "筛选": "",
    "右": "", "展开": "", "收起": "", "复制": "", "Excel": "", "飞书": "",
}


def 图标字体对象(大小=12):
    f = QFont(图标字体)
    f.setFamilies([图标字体, "Segoe MDL2 Assets"])
    f.setPixelSize(大小)
    return f


def 图标(名, 颜色=None, 大小=16):
    """用图标字体画一个 QIcon（按钮、列表用）。"""
    比 = 2
    图 = QPixmap(大小 * 比, 大小 * 比)
    图.fill(Qt.transparent)
    p = QPainter(图)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(颜色 or 色["次字"]))
    p.setFont(图标字体对象(int(大小 * 比 * 0.82)))
    p.drawText(QRectF(0, 0, 大小 * 比, 大小 * 比), Qt.AlignCenter, 图码.get(名, 名))
    p.end()
    图.setDevicePixelRatio(比)
    return QIcon(图)


def 画图标(p, 名, 中心, 大小, 颜色):
    """在别人的 paintEvent 里画一个图标。"""
    p.save()
    p.setPen(QColor(颜色))
    p.setFont(图标字体对象(大小))
    p.drawText(QRectF(中心.x() - 大小, 中心.y() - 大小, 大小 * 2, 大小 * 2), Qt.AlignCenter, 图码.get(名, 名))
    p.restore()


def 字(大小=10, 粗=False, 族=None):
    f = QFont(族 or 字体)
    f.setPointSizeF(大小)
    f.setBold(粗)
    return f


def 颜色(名):
    return QColor(色.get(名, 名))


_勾 = (图标目录 / "勾.svg").as_posix()

样式表 = f"""
* {{ font-family: "{字体}"; }}
QMainWindow, QDialog {{ background: {色['底']}; }}
QWidget {{ color: {色['字']}; }}
QToolTip {{ background: {色['字']}; color: white; border: none; padding: 5px 8px; border-radius: 6px; }}

/* 外壳 */
QFrame#侧栏 {{ background: {色['面']}; border: none; border-right: 1px solid {色['线']}; }}
QPushButton[nav="1"] {{ text-align: left; padding: 9px 12px; border: none; border-radius: 8px; background: transparent;
    color: {色['次字']}; font-size: 10.5pt; }}
QPushButton[nav="1"]:hover {{ background: {色['面2']}; color: {色['字']}; }}
QPushButton[nav="1"]:checked {{ background: {色['主浅']}; color: {色['主']}; font-weight: bold; }}
QWidget#页面 {{ background: {色['底']}; }}
QLabel[role="eyebrow"] {{ color: {色['弱字']}; font-size: 9.5pt; }}
QLabel[role="title"] {{ font-size: 19pt; font-weight: bold; color: {色['字']}; }}
QLabel[role="subtitle"] {{ color: {色['弱字']}; font-size: 10pt; }}
QLabel[role="heading"] {{ font-size: 11pt; font-weight: bold; color: {色['字']}; }}
QLabel[role="group"] {{ color: {色['灰']}; font-size: 8.5pt; font-weight: bold; letter-spacing: 1px; }}
QLabel[role="hint"] {{ color: {色['弱字']}; font-size: 9pt; }}

/* 卡片 */
QFrame[card="1"] {{ background: {色['面']}; border: 1px solid {色['线']}; border-radius: {圆角}px; }}
QFrame[card="1"] QLabel {{ background: transparent; border: none; }}
QFrame#坏框 {{ background: {色['坏底']}; border: 1px solid {色['坏线']}; border-radius: 8px; }}
QFrame#坏框 QLabel {{ color: {色['坏字']}; background: transparent; border: none; }}
QFrame#注意框 {{ background: {色['注意底']}; border: 1px solid {色['注意线']}; border-radius: 8px; }}
QFrame#注意框 QLabel {{ color: {色['注意字']}; background: transparent; border: none; }}

/* 按钮 */
QPushButton {{ background: {色['面']}; border: 1px solid {色['线深']}; border-radius: 8px; padding: 6px 14px;
    color: {色['字']}; min-height: 20px; }}
QPushButton:hover {{ background: {色['面2']}; border-color: {色['灰']}; }}
QPushButton:pressed {{ background: {色['底']}; }}
QPushButton:disabled {{ color: {色['灰']}; background: {色['面2']}; border-color: {色['线']}; }}
QPushButton:focus {{ outline: none; }}
QPushButton[kind="primary"] {{ background: {色['主']}; border: 1px solid {色['主']}; color: white; font-weight: bold; padding: 8px 18px; }}
QPushButton[kind="primary"]:hover {{ background: {色['主深']}; border-color: {色['主深']}; }}
QPushButton[kind="primary"]:disabled {{ background: {色['主中']}; border-color: {色['主中']}; color: white; }}
QPushButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; color: {色['次字']}; padding: 5px 10px; }}
QPushButton[kind="ghost"]:hover {{ background: {色['底']}; color: {色['字']}; }}
QPushButton[kind="icon"] {{ background: transparent; border: 1px solid transparent; padding: 4px; min-width: 26px; }}
QPushButton[kind="icon"]:hover {{ background: {色['底']}; border-color: {色['线']}; }}
QPushButton[seg="1"] {{ background: transparent; border: none; border-radius: 6px; padding: 4px 14px; color: {色['次字']}; }}
QPushButton[seg="1"]:hover {{ color: {色['字']}; }}
QPushButton[seg="1"]:checked {{ background: {色['面']}; color: {色['字']}; font-weight: bold; border: 1px solid {色['线']}; }}
QFrame#分段 {{ background: {色['底']}; border-radius: 8px; border: none; }}

/* 输入 */
QLineEdit {{ background: {色['面']}; border: 1px solid {色['线深']}; border-radius: 6px; padding: 6px 8px;
    selection-background-color: {色['主中']}; selection-color: {色['字']}; }}
QLineEdit:focus {{ border: 1px solid {色['主']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {色['灰']}; border-radius: 4px; background: {色['面']}; }}
QCheckBox::indicator:hover {{ border-color: {色['主']}; }}
QCheckBox::indicator:checked {{ background: {色['主']}; border-color: {色['主']}; image: url({_勾}); }}
QCheckBox::indicator:disabled {{ background: {色['底']}; border-color: {色['线深']}; }}

/* 列表、表格、文本框 */
QListWidget, QTableWidget, QPlainTextEdit {{ background: {色['面']}; border: 1px solid {色['线']}; border-radius: 8px;
    outline: none; selection-background-color: {色['主浅']}; selection-color: {色['字']}; }}
QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: {色['主浅']}; color: {色['字']}; }}
QListWidget::item:hover {{ background: {色['面2']}; }}
QTableWidget {{ gridline-color: {色['线']}; }}
QHeaderView::section {{ background: {色['面2']}; color: {色['弱字']}; border: none; border-bottom: 1px solid {色['线']};
    padding: 6px 8px; font-weight: bold; }}
QTableCornerButton::section {{ background: {色['面2']}; border: none; }}
QPlainTextEdit {{ font-family: "{等宽}", "{字体}"; font-size: 9pt; color: {色['次字']}; padding: 4px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* 滚动条：细 */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {色['线深']}; border-radius: 3px; min-height: 30px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: {色['灰']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {色['线深']}; border-radius: 3px; min-width: 30px; margin: 2px 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* 进度条 */
QProgressBar {{ background: {色['底']}; border: none; border-radius: 3px; height: 6px; max-height: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {色['主']}; border-radius: 3px; }}

QSplitter::handle {{ background: transparent; }}
QStatusBar {{ background: {色['底']}; color: {色['弱字']}; }}
QStatusBar::item {{ border: none; }}
QGroupBox {{ background: {色['面']}; border: 1px solid {色['线']}; border-radius: 8px; margin-top: 18px; padding: 12px 10px 10px 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 4px; top: 0px; color: {色['次字']}; font-weight: bold; }}
QMessageBox QLabel {{ font-size: 10pt; }}
"""


# 结果页里几个表格、列表的样子（结果页.一页 用）
结果页样式表 = f"""
QTableWidget#数量表 {{ gridline-color:{色['线']}; border:1px solid {色['线']}; border-radius:8px;
    selection-background-color:{色['选中']}; selection-color:{色['字']}; }}
QListWidget#任务列表, QListWidget#区域列表, QListWidget#单号列表 {{ border:1px solid {色['线']}; border-radius:8px; }}
QListWidget#任务列表::item, QListWidget#区域列表::item {{ border-bottom:1px solid {色['线']}; }}
QListWidget#任务列表::item:selected, QListWidget#区域列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
QListWidget#单号列表::item {{ border-radius:6px; }}
QListWidget#单号列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
"""


def 套用(应用):
    """程序启动时调用一次：统一用 Fusion 底子 + 上面的样式表，每台电脑看起来一样，测试截图也和实际一样。"""
    应用.setStyle("Fusion")
    应用.setFont(字(10))
    应用.setStyleSheet(样式表)


def 圆点(p, x, y, r, 颜色值):
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(颜色值))
    p.drawEllipse(QPointF(x, y), r, r)
    p.restore()

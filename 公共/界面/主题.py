# 职责：仓库助手的统一样子——颜色、字号、圆角、图标，以及整个程序用的一张样式表。
# 方向（2026-10-24 重新设计，参考 Taskless / Norix / Moneta 等，见 architecture 里的设计说明）：
#   浅灰底 + 白色圆角卡片 + 一个蓝色主色；状态色只表示状态；不加动画、渐变、毛玻璃。
# 改颜色只改这里，窗口、结果页、弹窗都会跟着变。
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

图标目录 = Path(__file__).resolve().parent / "图标"

# 2026-10-25 起按《仓库助手设计规范》（iOS 风格，Apple HIG）取值；规范第 3 节的色值都在这里。
色 = {
    # 底和面（规范：页面底色、侧栏底色、内容块、分隔线）
    "底": "#F2F2F7", "侧栏": "#E9E9EE", "面": "#FFFFFF", "面2": "#F2F2F7", "线": "#E5E5EA", "线深": "#D1D1D6",
    # 文字（规范：正文字、次要字；“次字”= 比次要字深一点的正文辅助色、“灰”= 不能点的字，规范 v1.1 补）
    "字": "#000000", "次字": "#3C3C43", "弱字": "#8E8E93", "灰": "#C7C7CC",
    # 主色 · 蓝；选中行；次要按钮底
    "主": "#007AFF", "主深": "#0062CC", "主浅": "#E8F1FF", "主中": "#99C7FF", "次钮底": "#E5E5EA",
    # 开关
    "开关开": "#34C759", "开关关": "#E9E9EA",
    # 状态（规范：成功绿、无数据灰、不完整橙、失败红；“底”是同色很淡的底；“字”是放在淡底上读得清的同色深一点）
    "好": "#34C759", "好底": "#EAF9EE", "好字": "#248A3D",
    "注意": "#FF9500", "注意底": "#FFF4E5", "注意线": "#FFD8A8", "注意字": "#C93400",
    "坏": "#FF3B30", "坏底": "#FFECEB", "坏线": "#FFB3AE", "坏字": "#D70015",
    "次": "#8E8E93", "次底": "#F2F2F7",
    "运行": "#007AFF", "运行底": "#E8F1FF",
    # 零碎
    "白": "#FFFFFF", "选中卡底": "#E8F1FF", "单号字": "#3C3C43", "面单字": "#000000",
    # 结果页用惯的名字（值和上面一样，只是起了个说法）
    "说明": "#8E8E93", "选中": "#E8F1FF", "今天": "#E8F1FF", "合计底": "#FFFFFF", "段": "#F2F2F7",
}
字体 = "Microsoft YaHei UI"
等宽 = "Consolas"
圆角 = 12                     # 分组块、弹窗
# 字号（像素，规范第 4 节）
字号 = {"大标题": 26, "标题": 20, "行标题": 15, "正文": 14, "说明": 12, "大数字": 20, "弹窗标题": 17}
# 间距只用这几个值（规范第 5 节）：4 / 8 / 12 / 16 / 20 / 24
行高最小 = 44

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


def 像素字(级别或像素=14, 粗=False, 半粗=False, 族=None):
    """按规范的字号取字体：像素字("行标题") 或 像素字(15)。半粗 = 比常规粗一点（规范的“半粗”）。"""
    f = QFont(族 or 字体)
    f.setPixelSize(字号.get(级别或像素, 级别或像素) if isinstance(级别或像素, str) else 级别或像素)
    if 粗:
        f.setWeight(QFont.Bold)
    elif 半粗:
        f.setWeight(QFont.DemiBold)
    return f


def 颜色(名):
    return QColor(色.get(名, 名))


_勾 = (图标目录 / "勾.svg").as_posix()

样式表 = f"""
* {{ font-family: "{字体}"; }}
QMainWindow, QDialog {{ background: {色['底']}; }}
QWidget {{ color: {色['字']}; font-size: {字号['正文']}px; }}
QToolTip {{ background: {色['面']}; color: {色['字']}; border: 1px solid {色['线']}; padding: 6px 8px; border-radius: 8px; }}

/* 外壳：左侧导航（规范：选中整行蓝底白字、圆角 8px） */
QFrame#侧栏 {{ background: {色['侧栏']}; border: none; }}
QLabel#软件名 {{ font-size: {字号['标题']}px; font-weight: bold; }}
QPushButton[nav="1"] {{ text-align: left; padding: 8px 12px; border: none; border-radius: 8px; background: transparent;
    color: {色['字']}; font-size: {字号['行标题']}px; min-height: 22px; }}
QPushButton[nav="1"]:hover {{ background: {色['次钮底']}; }}
QPushButton[nav="1"]:checked {{ background: {色['主']}; color: {色['白']}; }}
QPushButton[nav="1"][narrow="1"] {{ text-align: center; padding: 8px 0; }}
QWidget#页面 {{ background: {色['底']}; }}
QLabel[role="eyebrow"] {{ color: {色['弱字']}; font-size: {字号['说明'] + 1}px; }}
QLabel[role="title"] {{ font-size: {字号['大标题']}px; font-weight: bold; color: {色['字']}; }}
QLabel[role="subtitle"] {{ color: {色['弱字']}; font-size: {字号['说明'] + 1}px; }}
QLabel[role="heading"] {{ font-size: {字号['行标题']}px; font-weight: bold; color: {色['字']}; }}
QLabel[role="paneltitle"] {{ font-size: {字号['标题']}px; font-weight: bold; color: {色['字']}; }}
QLabel[role="group"] {{ color: {色['弱字']}; font-size: {字号['说明'] + 1}px; padding-left: 16px; }}
QLabel[role="hint"] {{ color: {色['弱字']}; font-size: {字号['说明']}px; }}
QLabel[role="foot"] {{ color: {色['弱字']}; font-size: {字号['说明']}px; padding-left: 16px; }}

/* 分组块（规范最重要的零件）：白色圆角块，不用线框、不用阴影 */
QFrame[card="1"] {{ background: {色['面']}; border: none; border-radius: {圆角}px; }}
QFrame[card="1"] QLabel {{ background: transparent; border: none; }}
QFrame#坏框 {{ background: {色['坏底']}; border: none; border-radius: {圆角}px; }}
QFrame#坏框 QLabel {{ color: {色['坏字']}; background: transparent; border: none; }}
QFrame#注意框 {{ background: {色['注意底']}; border: none; border-radius: {圆角}px; }}
QFrame#注意框 QLabel {{ color: {色['注意字']}; background: transparent; border: none; }}
QFrame#行线 {{ background: {色['线']}; border: none; }}

/* 按钮（规范三级：主按钮蓝底白字、次要按钮灰底蓝字、文字按钮只有蓝字；都做成胶囊） */
QPushButton {{ background: {色['次钮底']}; border: none; border-radius: 16px; padding: 6px 16px; min-height: 20px;
    color: {色['主']}; font-size: {字号['正文']}px; }}
QPushButton:hover {{ background: {色['线深']}; }}
QPushButton:pressed {{ background: {色['灰']}; }}
QPushButton:disabled {{ color: {色['灰']}; background: {色['面2']}; }}
QPushButton:focus {{ outline: none; }}
QPushButton[kind="primary"] {{ background: {色['主']}; color: {色['白']}; border-radius: 18px; padding: 8px 20px; }}
QPushButton[kind="primary"]:hover {{ background: {色['主深']}; }}
QPushButton[kind="primary"]:disabled {{ background: {色['主中']}; color: {色['白']}; }}
QPushButton[kind="ghost"] {{ background: transparent; color: {色['主']}; padding: 4px 8px; }}
QPushButton[kind="ghost"]:hover {{ background: {色['主浅']}; }}
QPushButton[kind="ghost"]:disabled {{ color: {色['灰']}; background: transparent; }}
QPushButton[kind="danger"] {{ background: transparent; color: {色['坏']}; padding: 4px 8px; }}
QPushButton[kind="icon"] {{ background: transparent; border-radius: 14px; padding: 4px; min-width: 20px; color: {色['主']}; }}
QPushButton[kind="icon"]:hover {{ background: {色['次钮底']}; }}
QPushButton[kind="icon"]:disabled {{ background: transparent; }}
/* 分段控件：灰色轨道，选中那段白底 */
QFrame#分段 {{ background: {色['次钮底']}; border-radius: 9px; border: none; }}
QPushButton[seg="1"] {{ background: transparent; border: none; border-radius: 7px; padding: 4px 14px; color: {色['字']};
    min-height: 18px; }}
QPushButton[seg="1"]:hover {{ background: transparent; color: {色['次字']}; }}
QPushButton[seg="1"]:checked {{ background: {色['面']}; color: {色['字']}; font-weight: bold; }}

/* 输入：白底、圆角 8px、灰色提示字 */
QLineEdit {{ background: {色['面']}; border: 1px solid {色['线']}; border-radius: 8px; padding: 6px 10px;
    selection-background-color: {色['主中']}; selection-color: {色['字']}; }}
QLineEdit:focus {{ border: 1px solid {色['主']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1.5px solid {色['灰']}; border-radius: 9px; background: {色['面']}; }}
QCheckBox::indicator:checked {{ background: {色['主']}; border-color: {色['主']}; image: url({_勾}); }}
QCheckBox::indicator:disabled {{ background: {色['底']}; border-color: {色['线']}; }}

/* 列表、表格、文本框：放在白色圆角块里 */
QListWidget, QTableWidget, QPlainTextEdit {{ background: {色['面']}; border: none; border-radius: {圆角}px;
    outline: none; selection-background-color: {色['主浅']}; selection-color: {色['字']}; }}
QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: {色['主浅']}; color: {色['字']}; }}
QListWidget::item:hover {{ background: {色['面2']}; }}
QTableWidget {{ gridline-color: {色['线']}; }}
QHeaderView::section {{ background: {色['面']}; color: {色['弱字']}; border: none; border-bottom: 1px solid {色['线']};
    padding: 6px 8px; font-size: {字号['说明']}px; font-weight: normal; }}
QTableCornerButton::section {{ background: {色['面']}; border: none; }}
QPlainTextEdit {{ font-family: "{等宽}", "{字体}"; font-size: {字号['说明']}px; color: {色['次字']}; padding: 6px;
    background: {色['面2']}; border-radius: 8px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* 滚动条：细 */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {色['线深']}; border-radius: 3px; min-height: 30px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: {色['弱字']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {色['线深']}; border-radius: 3px; min-width: 30px; margin: 2px 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* 进度：细的蓝色进度条 */
QProgressBar {{ background: {色['次钮底']}; border: none; border-radius: 2px; height: 4px; max-height: 4px; text-align: center; }}
QProgressBar::chunk {{ background: {色['主']}; border-radius: 2px; }}

QSplitter::handle {{ background: transparent; }}
QStatusBar {{ background: {色['底']}; color: {色['弱字']}; }}
QStatusBar::item {{ border: none; }}
QGroupBox {{ background: {色['面']}; border: none; border-radius: {圆角}px; margin-top: 22px; padding: 12px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 16px; top: 2px; color: {色['弱字']}; }}
QMessageBox {{ background: {色['面']}; }}
QMessageBox QLabel {{ font-size: {字号['正文']}px; }}
"""


# 结果页里几个表格、列表的样子（结果页.一页 用）
结果页样式表 = f"""
QTableWidget#数量表 {{ background:{色['面']}; border:none; border-radius:0;
    selection-background-color:{色['选中']}; selection-color:{色['字']}; }}
QTableWidget#数量表::item {{ border-bottom:1px solid {色['线']}; padding:0 8px; }}
QListWidget#任务列表, QListWidget#区域列表, QListWidget#单号列表 {{ background:{色['面']}; border:1px solid {色['线']}; border-radius:12px; }}
QListWidget#任务列表::item, QListWidget#区域列表::item {{ border-bottom:1px solid {色['线']}; }}
QListWidget#任务列表::item:selected, QListWidget#区域列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
QListWidget#单号列表::item {{ border-radius:6px; }}
QListWidget#单号列表::item:selected {{ background:{色['选中']}; color:{色['字']}; }}
"""


def 套用(应用):
    """程序启动时调用一次：统一用 Fusion 底子 + 上面的样式表，每台电脑看起来一样，测试截图也和实际一样。"""
    应用.setStyle("Fusion")
    应用.setFont(像素字("正文"))
    应用.setStyleSheet(样式表)


def 圆点(p, x, y, r, 颜色值):
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(颜色值))
    p.drawEllipse(QPointF(x, y), r, r)
    p.restore()

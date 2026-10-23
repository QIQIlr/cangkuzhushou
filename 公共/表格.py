# 职责：把“行 × 列”的数字表做成三种样子，所有需要表格的模块共用：
#   1) 飞书卡片（真正的表格）  2) 对齐的文字表格（窗口和日志里看）  3) Excel 文件
# 输入：标题、列名列表（第一列是行名，例如“日期”）、行列表（每行是 [行名, 值1, 值2, …]）。
#   值可以是数字，也可以是“失败”等文字。行名以 ** 包起来表示加粗（例如 "**合计**"）。
import unicodedata


def _宽(文字):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(文字))


def _去粗(文字):
    return str(文字).replace("**", "")


def 文字表格(列名, 行们):
    全部 = [列名] + [[_去粗(x) for x in 行] for 行 in 行们]
    宽度 = [max(_宽(行[i]) for 行 in 全部) for i in range(len(列名))]
    输出 = []
    for n, 行 in enumerate(全部):
        格 = [str(行[0]) + " " * (宽度[0] - _宽(行[0]))]
        格 += [" " * (宽度[i] - _宽(行[i])) + str(行[i]) for i in range(1, len(行))]
        输出.append("  ".join(格))
        if n == 0:
            输出.append("-" * (sum(宽度) + 2 * (len(宽度) - 1)))
    return "\n".join(输出)


def 表格元素(列名, 行们, 对齐=None, 每页行数=10):
    """飞书卡片里的一个表格（官方表格组件，一页最多 10 行，超过会分页）。
    对齐：每列 "left"/"center"/"right"；不给就第一列靠左、其余靠右。
    文档：https://open.feishu.cn/document/feishu-cards/card-json-v2-components/content-components/table"""
    键 = [f"c{i}" for i in range(len(列名))]
    对齐 = 对齐 or (["left"] + ["right"] * (len(列名) - 1))
    列 = [{"name": 键[i], "display_name": 列名[i], "data_type": "lark_md",
          "horizontal_align": 对齐[i], "width": "auto"} for i in range(len(列名))]
    行数据 = [{键[i]: str(行[i]) for i in range(len(列名))} for 行 in 行们]
    return {"tag": "table", "page_size": min(每页行数, 10, max(1, len(行数据))), "row_height": "low",
            "header_style": {"text_align": "center", "bold": True, "background_style": "grey"},
            "columns": 列, "rows": 行数据}


def 文字元素(内容):
    return {"tag": "markdown", "content": 内容}


def 组卡片(标题, 元素们, 颜色="blue"):
    """飞书消息卡片 JSON 2.0。一张卡片最多 5 个表格，整条消息不超过 20KB。"""
    return {"schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": 标题}, "template": 颜色},
            "body": {"elements": list(元素们)}}


def 存Excel多表(路径, 标题, 表们, 备注=()):
    """表们：[(工作表名, 列名, 行们), …]，每个表一个工作表。"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    簿 = Workbook()
    for 序, (表名, 列名, 行们) in enumerate(表们):
        表 = 簿.active if 序 == 0 else 簿.create_sheet()
        表.title = 表名
        表.append([标题])
        表["A1"].font = Font(bold=True, size=13)
        表.append([])
        表.append(list(列名))
        for 格 in 表[3]:
            格.font = Font(bold=True)
            格.fill = PatternFill("solid", fgColor="DDDDDD")
            格.alignment = Alignment(horizontal="center")
        for 行 in 行们:
            表.append([_去粗(x) if isinstance(x, str) else x for x in 行])
            if str(行[0]).startswith("**"):
                for 格 in 表[表.max_row]:
                    格.font = Font(bold=True)
        if 序 == 0:
            for 句 in 备注:
                表.append([])
                表.append([_去粗(句)])
        for i, 名 in enumerate(列名, 1):
            宽 = max([_宽(名)] + [_宽(_去粗(行[i - 1])) for 行 in 行们] + [8])
            表.column_dimensions[get_column_letter(i)].width = min(40, 宽 + 2)
    簿.save(路径)


def _大小(卡):
    import json
    return len(json.dumps({"msg_type": "interactive", "card": 卡}, ensure_ascii=False).encode("utf-8"))


def 折叠面板(标题, 元素们, 展开=False):
    """飞书卡片的折叠面板：平时只显示标题，点一下展开里面的内容。
    文档：https://open.feishu.cn/document/feishu-cards/card-json-v2-components/containers/collapsible-panel"""
    return {"tag": "collapsible_panel", "expanded": 展开,
            "header": {"title": {"tag": "markdown", "content": 标题},
                       "icon": {"tag": "standard_icon", "token": "down-small-ccm_outlined", "size": "16px 16px"},
                       "icon_position": "right", "icon_expanded_angle": -180},
            "border": {"color": "grey", "corner_radius": "5px"},
            "vertical_spacing": "4px", "padding": "4px 8px 4px 8px",
            "elements": list(元素们)}


def 单号文字表(单号们, 标题="", 分隔="\t"):
    """把单号排成整齐的文字表：第一行标题，下面每行“序号<Tab>单号”，序号补零对齐（01、02…；超过 99 用 001）。
    用 Tab 分隔：粘到 Excel 会自动分成两列，粘到记事本、飞书也对齐。"""
    位数 = max(2, len(str(len(单号们))))
    行们 = ([标题] if 标题 else []) + [f"{str(i).zfill(位数)}{分隔}{号}" for i, 号 in enumerate(单号们, 1)]
    return "\n".join(行们)


def 代码块(文字):
    """卡片里的等宽文字块（对齐不会乱，方便选中复制）。"""
    return {"tag": "markdown", "content": "```\n" + 文字 + "\n```"}


def 按大小分卡(标题, 头元素, 分段元素们, 尾元素=(), 颜色="blue", 上限字节=18000):
    """头元素放第 1 张，尾元素放最后一张；分段元素（例如每个区一个折叠面板）按大小依次装进卡片，
    一张装不下就开下一张，标题加“（1/2）”。一个分段本身超过上限时，按行拆开（不丢内容）。"""
    卡们, 当前 = [], list(头元素)
    for 段 in 分段元素们:
        if 当前 and _大小(组卡片(标题, 当前 + [段] + list(尾元素), 颜色)) > 上限字节:
            卡们.append(当前)
            当前 = []
        当前.append(段)
    卡们.append(当前)
    卡们[-1] = 卡们[-1] + list(尾元素)
    共 = len(卡们)
    return [组卡片(标题 + (f"（{i}/{共}）" if 共 > 1 else ""), 元素们, 颜色) for i, 元素们 in enumerate(卡们, 1)]
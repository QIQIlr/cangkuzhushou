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


def 卡片(标题, 列名, 行们, 备注=(), 颜色="blue"):
    """只有一个表格的卡片。"""
    return 组卡片(标题, [表格元素(列名, 行们)] + [文字元素(句) for 句 in 备注], 颜色)


def 文字元素(内容):
    return {"tag": "markdown", "content": 内容}


def 组卡片(标题, 元素们, 颜色="blue"):
    """飞书消息卡片 JSON 2.0。一张卡片最多 5 个表格，整条消息不超过 20KB。"""
    return {"schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": 标题}, "template": 颜色},
            "body": {"elements": list(元素们)}}


def 存Excel(路径, 标题, 列名, 行们, 备注=()):
    存Excel多表(路径, 标题, [("结果", 列名, 行们)], 备注)


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


def 明细卡片们(标题, 头元素, 列名, 行们, 尾元素=(), 颜色="blue", 排法="分页", 对齐=None, 上限字节=18000):
    """一张汇总 + 很长的明细时用：自动拆成几张卡片，不丢任何一行。
    头元素只放在第 1 张，尾元素只放在最后一张；拆成多张时标题后面加“（1/3）”。
    排法 = "分页"：每张卡片一个表格，飞书里翻页看；
           "每10条"：每 10 行一个表格，往下翻就能全部看到（一张卡片最多 5 个表格）。
    飞书限制：整条消息不超过 20 KB、一张卡片最多 5 个表格（见 自定义机器人 文档）。上限字节留了余量。"""
    头元素, 尾元素 = list(头元素), list(尾元素)
    头表数 = sum(1 for e in 头元素 if e.get("tag") == "table")
    卡们 = []      # 每张：元素列表
    当前 = list(头元素)
    剩 = list(行们)

    def 表数(元素们):
        return sum(1 for e in 元素们 if e.get("tag") == "table")

    while 剩:
        if 排法 == "每10条":
            块 = 剩[:10]
            试 = 当前 + [表格元素(列名, 块, 对齐)]
            if 表数(试) <= 5 and _大小(组卡片(标题, 试 + 尾元素, 颜色)) <= 上限字节:
                当前, 剩 = 试, 剩[10:]
                continue
            if 当前 == 头元素 or not 当前:
                raise ValueError("一张卡片连 10 行都放不下")
            卡们.append(当前)
            当前 = []
        else:   # 分页：一张卡片一个表格，能放多少行放多少行
            n = len(剩)
            while n > 0 and _大小(组卡片(标题, 当前 + [表格元素(列名, 剩[:n], 对齐)] + 尾元素, 颜色)) > 上限字节:
                n = max(1, n * 3 // 4) if n > 1 else 0
            if n == 0:
                raise ValueError("一张卡片连 1 行都放不下")
            卡们.append(当前 + [表格元素(列名, 剩[:n], 对齐)])
            当前, 剩 = [], 剩[n:]
    if 当前 or not 卡们:
        卡们.append(当前)
    卡们[-1] = 卡们[-1] + 尾元素
    共 = len(卡们)
    return [组卡片(标题 + (f"（{i}/{共}）" if 共 > 1 else ""), 元素们, 颜色) for i, 元素们 in enumerate(卡们, 1)]
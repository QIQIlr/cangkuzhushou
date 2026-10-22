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


def 卡片(标题, 列名, 行们, 备注=(), 颜色="blue"):
    """飞书消息卡片 JSON 2.0（官方表格组件，一页最多 10 行，超过会分页）。
    文档：https://open.feishu.cn/document/feishu-cards/card-json-v2-components/content-components/table"""
    键 = [f"c{i}" for i in range(len(列名))]
    列 = [{"name": 键[0], "display_name": 列名[0], "data_type": "lark_md", "horizontal_align": "left", "width": "auto"}]
    列 += [{"name": 键[i], "display_name": 列名[i], "data_type": "lark_md", "horizontal_align": "right", "width": "auto"}
          for i in range(1, len(列名))]
    行数据 = [{键[i]: str(行[i]) for i in range(len(列名))} for 行 in 行们]
    元素 = [{"tag": "table", "page_size": min(10, max(1, len(行数据))), "row_height": "low",
             "header_style": {"text_align": "center", "bold": True, "background_style": "grey"},
             "columns": 列, "rows": 行数据}]
    for 句 in 备注:
        元素.append({"tag": "markdown", "content": 句})
    return {"schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": 标题}, "template": 颜色},
            "body": {"elements": 元素}}


def 存Excel(路径, 标题, 列名, 行们, 备注=()):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    簿 = Workbook()
    表 = 簿.active
    表.title = "结果"
    表.append([标题])
    表["A1"].font = Font(bold=True, size=13)
    表.append([])
    表.append(list(列名))
    for 格 in 表[3]:
        格.font = Font(bold=True)
        格.fill = PatternFill("solid", fgColor="DDDDDD")
        格.alignment = Alignment(horizontal="center")
    for 行 in 行们:
        值们 = [_去粗(行[0])] + [x for x in 行[1:]]
        表.append(值们)
        if str(行[0]).startswith("**"):
            for 格 in 表[表.max_row]:
                格.font = Font(bold=True)
    for 句 in 备注:
        表.append([])
        表.append([_去粗(句)])
    表.column_dimensions["A"].width = 18
    for i in range(2, len(列名) + 1):
        表.column_dimensions[chr(64 + i)].width = 10
    簿.save(路径)

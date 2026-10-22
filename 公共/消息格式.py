# 职责：按“格式”文件排版飞书消息。所有模块共用。
# 输入：模块名、公共内容（日期、时间、合计、状态、用时）、每个区域的内容列表。
# 输出：(消息文字, 问题说明)。
#   格式文件写错时，用“上一次能用的格式”排版；还没有就用模块自带的默认格式。
#   问题说明里写清楚第几行错了，不会因为格式错而让查询失败。
# 格式文件在 格式\模块名.txt；上一次能用的备份在 格式\上次可用\模块名.txt。
#
# 格式文件规则：
#   以 # 开头的行是说明，不会发出去。
#   [开头] [每个区域] [没有包裹时] [查询失败时] [结尾] [设置] 是分段标记，各占一行。
#   {名字} 会被换成对应内容。换完后变成空的行会自动去掉；格式里本来就有的空行会保留。
import re
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
格式目录 = 根目录 / "格式"
备份目录 = 格式目录 / "上次可用"

分段名 = ["开头", "每个区域", "没有包裹时", "查询失败时", "结尾", "设置"]
公共占位 = ["日期", "时间", "合计", "状态", "用时", "空行"]
区域占位 = ["区域", "数量", "单号列表", "状态"]
分隔词 = {"换行": "\n", "逗号": "，", "顿号": "、", "空格": " ", "斜杠": " / "}
_占位 = re.compile(r"\{([^{}]*)\}")


class 格式错误(Exception):
    pass


def 解析(文字):
    """把格式文件拆成各段。返回 (段字典, 单号分隔)。有错时抛出 格式错误，说明第几行。"""
    段 = {}
    当前 = None
    for 行号, 行 in enumerate(文字.splitlines(), 1):
        if 行.lstrip().startswith("#"):
            continue
        标记 = re.fullmatch(r"\s*\[(.*?)\]\s*", 行)
        if 标记:
            名 = 标记.group(1).strip()
            if 名 not in 分段名:
                raise 格式错误(f"第 {行号} 行：不认识的分段 [{名}]（可用的有：{'、'.join('[' + n + ']' for n in 分段名)}）")
            if 名 in 段:
                raise 格式错误(f"第 {行号} 行：[{名}] 出现了两次")
            当前 = 名
            段[名] = []
            continue
        if 当前 is None:
            if 行.strip():
                raise 格式错误(f"第 {行号} 行：这行写在了所有分段标记前面，请放到 [开头] 等分段下面")
            continue
        if 当前 != "设置":
            if 行.count("{") != 行.count("}"):
                raise 格式错误(f"第 {行号} 行：大括号 {{ }} 没有配对：{行.strip()}")
            可用 = 公共占位 if 当前 in ("开头", "结尾") else 公共占位 + 区域占位
            for m in _占位.finditer(行):
                if m.group(1).strip() not in 可用:
                    raise 格式错误(f"第 {行号} 行：不认识 {{{m.group(1)}}}，[{当前}] 里能用的有："
                                 + "、".join("{" + n + "}" for n in dict.fromkeys(可用)))
        段[当前].append((行号, 行))

    if "每个区域" not in 段:
        raise 格式错误("缺少 [每个区域] 分段，各区域的结果没地方放")
    分隔 = "\n"
    for 行号, 行 in 段.get("设置", []):
        if not 行.strip():
            continue
        if "=" not in 行:
            raise 格式错误(f"第 {行号} 行：[设置] 里要写成 名字=值，例如 单号分隔=换行")
        键, 值 = [x.strip() for x in 行.split("=", 1)]
        if 键 != "单号分隔":
            raise 格式错误(f"第 {行号} 行：[设置] 里目前只有“单号分隔”这一项")
        分隔 = 分隔词.get(值, 值)
    # 每段前后的空行只是为了文件好看，去掉；想要空行请写 {空行}
    return {k: "\n".join(l for _, l in v).strip("\n") for k, v in 段.items() if k != "设置"}, 分隔


def _填(文字, 内容):
    return _占位.sub(lambda m: str({**内容, "空行": ""}[m.group(1).strip()]), 文字)


def 排版(文字, 公共, 区域列表):
    段, 分隔 = 解析(文字)
    行 = []

    def 加(片段):
        for l in 片段.splitlines():
            if l.strip() == "{空行}":
                行.append("")
                continue
            空 = l.strip() == ""
            填好 = _填(l, 内容).rstrip()
            if 填好.strip() == "" and not 空:
                continue          # 换完后变空的行去掉
            行.extend(填好.split("\n"))

    内容 = dict(公共)
    加(段.get("开头", ""))
    for 区 in 区域列表:
        内容 = {**公共, **区, "单号列表": 分隔.join(区.get("单号", []))}
        if 区.get("状态") == "失败":
            加(段.get("查询失败时", "{区域}：查询失败"))
        elif 区.get("数量") == 0 and "没有包裹时" in 段:
            加(段["没有包裹时"])
        else:
            加(段["每个区域"])
    内容 = dict(公共)
    加(段.get("结尾", ""))
    return "\n".join(行).strip("\n")


def 套用(模块名, 公共, 区域列表, 默认格式):
    """返回 (消息, 问题说明)。格式文件可用时顺便更新“上次可用”备份。"""
    文件 = 格式目录 / f"{模块名}.txt"
    备份 = 备份目录 / f"{模块名}.txt"
    try:
        文字 = 文件.read_text(encoding="utf-8-sig")
        消息 = 排版(文字, 公共, 区域列表)
        备份目录.mkdir(parents=True, exist_ok=True)
        备份.write_text(文字, encoding="utf-8")
        return 消息, ""
    except FileNotFoundError:
        问题 = f"找不到格式文件 格式\\{模块名}.txt"
    except 格式错误 as e:
        问题 = f"格式文件 格式\\{模块名}.txt 有误：{e}"
    except Exception as e:
        问题 = f"格式文件 格式\\{模块名}.txt 读不了：{e}"
    try:
        return 排版(备份.read_text(encoding="utf-8"), 公共, 区域列表), 问题 + "（已改用上一次能用的格式）"
    except Exception:
        return 排版(默认格式, 公共, 区域列表), 问题 + "（已改用默认格式）"

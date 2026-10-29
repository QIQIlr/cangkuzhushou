# 职责：把窗口里最近一次运行的结果存一份，下次打开仓库助手时“运行结果”页直接显示（小柒 2026-10-24）。
# 存在 日志\上次结果.json，只留最近一次（下次运行开始时换掉）。每个模块整理好就写一次，中途关窗口也能看到已经跑完的。
# 转寄退货任务的面单内容（姓名、地址、电话）不存进来（2026-10-29），只存任务标题和读取情况；日志\ 不进 Git。
# 只有小柒在窗口里点运行才写；Claude 的测试不写。
import json
from datetime import date, datetime

from 公共.日志 import 日志根

文件名 = "上次结果.json"


def _编码(x):
    if isinstance(x, datetime):
        return {"__时间__": x.isoformat()}
    if isinstance(x, date):
        return {"__日期__": x.isoformat()}
    return str(x)


def _解码(d):
    if "__时间__" in d and len(d) == 1:
        return datetime.fromisoformat(d["__时间__"])
    if "__日期__" in d and len(d) == 1:
        return date.fromisoformat(d["__日期__"])
    return d


不存面单说明 = "这是上一次的结果。为了不在电脑上留客户信息，面单的姓名、地址、电话没有保存，这里只有任务标题。要看完整面单，请重新运行一次。"


def _去掉客户信息(项):
    """转寄退货任务的“项”：面单（姓名、地址、电话）、飞书文字、卡片、表格都不存，只留每条任务的标题和读取情况（2026-10-29）。
    窗口里正在看的结果不受影响，只是存到文件里的这一份变短了。"""
    if 项.get("面单") is None:
        return 项
    新 = {k: v for k, v in 项.items() if k not in ("文字", "卡片们", "表们", "备注")}
    新["面单"] = [{"序": 页.get("序"), "类型": 页.get("类型", ""), "单号": 页.get("单号", ""), "标题": 页.get("标题", ""),
                 "失败": 页.get("失败", ""), "要看数": 页.get("要看数", 0), "总结": [], "段们": [], "收起段": [],
                 "没存": True} for 页 in 项["面单"]]
    新["提醒们"] = [不存面单说明] + [s for s in (项.get("提醒们") or []) if s != 不存面单说明]
    新["不发飞书"] = True          # 文字和卡片没存，这一份不能再发
    return 新


def 保存(开始, 模块们, 结果们, 完成):
    """开始：这次运行开始的时间；模块们：原名列表（按顺序）；结果们：运行模块们 给窗口的“项”；完成：是否全部跑完。"""
    数据 = {"开始": 开始, "完成": 完成, "模块们": list(模块们), "结果们": [_去掉客户信息(项) for 项 in 结果们]}
    路径 = 日志根 / 文件名
    临时 = 路径.with_suffix(".json.tmp")
    日志根.mkdir(exist_ok=True)
    临时.write_text(json.dumps(数据, ensure_ascii=False, default=_编码), encoding="utf-8")
    临时.replace(路径)


def 读取():
    """返回 {开始, 完成, 模块们, 结果们}；没有或读不出来时返回 None。"""
    try:
        数据 = json.loads((日志根 / 文件名).read_text(encoding="utf-8"), object_hook=_解码)
        if not isinstance(数据.get("结果们"), list) or not isinstance(数据.get("开始"), datetime):
            return None
        for 项 in 数据["结果们"]:
            if isinstance(项.get("飞书"), list):
                项["飞书"] = tuple(项["飞书"])
        return 数据
    except Exception:
        return None

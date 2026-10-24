# 职责：把窗口里最近一次运行的结果存一份，下次打开仓库助手时“运行结果”页直接显示（小柒 2026-10-24）。
# 存在 日志\上次结果.json，只留最近一次（下次运行开始时换掉）。每个模块整理好就写一次，中途关窗口也能看到已经跑完的。
# 里面有转寄退货任务的面单内容（姓名、地址、电话），只在这台电脑上，不进版本记录（日志\ 不进 Git）。
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


def 保存(开始, 模块们, 结果们, 完成):
    """开始：这次运行开始的时间；模块们：原名列表（按顺序）；结果们：运行模块们 给窗口的“项”；完成：是否全部跑完。"""
    数据 = {"开始": 开始, "完成": 完成, "模块们": list(模块们), "结果们": list(结果们)}
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

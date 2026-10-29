# 职责：“任务管理”页面的计数查询（点“查询”→ 读“共 N 条记录”），带防连点和条件核对。新模块共用。
# 输入：页面、运行记录；每次查询时给出“期望的条件”（任务大类代码、区域字母、日期参数名和日期范围）。
# 输出：总条数（整数）。查不到时抛出 自动化错误，绝不返回 0 冒充。
# 防连点：两次查询至少隔 1 秒（每个区第一次按天查之前隔约 2 秒）；WMS 提示“点击次数过多”（code 100010）时
#   等 3、5、8、8 秒重查，最多 4 次，并且这次运行剩下的查询（各模块共用）都改成隔 2 秒。
# 核对：WMS 实际收到的条件（任务大类、待处理、区域、日期）必须和期望一致；页面显示的“共 N 条记录”必须等于读到的数。
# 说明：没有记录时 WMS 返回 list=null、total=null，这时核对页面确实显示“共 0 条记录”再记 0。
import re
import time
from urllib.parse import parse_qs, urlparse

from 公共.错误 import 自动化错误, 页面改版, 网络超时, 数据不完整, 归类, 浏览器被关, 网络断开, 等不到

查询接口 = "task/pageV1"
最小间隔秒 = 1.0
放慢后间隔秒 = 2.0
第一次按天前间隔秒 = 2.0          # 日志里“点击次数过多”几乎都出在查完总数、紧接着查第一天的时候（2026-10-29）
重试等待秒 = [3, 5, 8, 8]

# 整次运行共用（各模块一个）：放慢后的间隔一直保持到这次运行结束，下一个模块也不会又变回 1 秒（2026-10-29）。
# 每次运行开始时由 公共\运行.py 调 新的一次运行() 恢复成 1 秒。
本次 = {"上次": 0.0, "间隔": 最小间隔秒}


def 新的一次运行():
    本次.update(上次=0.0, 间隔=最小间隔秒)


class 计数查询器:
    def __init__(self, 页面, 记录):
        self.页面, self.记录 = 页面, 记录
        self.按天查过 = False        # 上一次查的是不是“按天”

    @property
    def 间隔(self):
        return 本次["间隔"]

    def 查(self, 期望):
        """期望 = {"taskCategories": "4", "taskStatus": "0", "shelvesRegionNum": "D",
                   "日期参数": "createTime", "日期范围": ("2026-10-23 00:00:00", "2026-10-23 23:59:59") 或 None}"""
        for 第几次 in range(len(重试等待秒) + 1):
            间隔 = 本次["间隔"]
            if 期望.get("日期范围") and not self.按天查过:
                间隔 = max(间隔, 第一次按天前间隔秒)
            等 = 间隔 - (time.time() - 本次["上次"])
            if 等 > 0:
                time.sleep(等)
            try:
                with self.页面.expect_response(lambda r: 查询接口 in r.url and "pageNo=1" in r.url, timeout=30000) as 等待:
                    self.页面.get_by_role("button", name="查询").first.click()
                回应 = 等待.value
                数据 = 回应.json()
            except Exception as e:
                e2 = 归类(e)
                if e2.类型 in (浏览器被关, 网络断开, 等不到):   # 如实报（体检 2026-10-28）
                    raise e2
                raise 自动化错误(网络超时, "点“查询”后 30 秒内没有拿到结果。")
            finally:
                本次["上次"] = time.time()
                self.按天查过 = bool(期望.get("日期范围"))   # 刚查完总数 → 下一次按天查前多等一会
            if isinstance(数据, dict) and 数据.get("code") == 100010:   # 点击次数过多
                if 第几次 < len(重试等待秒):
                    秒 = 重试等待秒[第几次]
                    self.记录.写(f"    WMS 提示“点击次数过多”，等 {秒} 秒后重查（第 {第几次 + 1} 次）")
                    本次["间隔"] = max(本次["间隔"], 放慢后间隔秒)   # 这次运行后面的查询（包括后面的模块）都放慢一点
                    time.sleep(秒)
                    continue
                raise 自动化错误(网络超时, "WMS 一直提示“点击次数过多”，重查 4 次仍不行。")
            if not isinstance(数据, dict) or 数据.get("code") != 0 or 数据.get("data") is None:
                raise 自动化错误(网络超时, "WMS 返回了错误：" + str(数据)[:200])
            return self._核对(回应.url, 数据["data"], 期望)

    def _核对(self, 网址, 数据, 期望):
        参数 = parse_qs(urlparse(网址).query)
        for 键 in ("taskCategories", "taskStatus", "shelvesRegionNum"):
            if 参数.get(键, [None])[0] != 期望[键]:
                raise 自动化错误(页面改版, f"查询条件没有生效（{键}={参数.get(键)}，应为 {期望[键]}），本次结果不可信。")
        名 = 期望["日期参数"]
        for 别的 in ("createTime", "addValueTimeStart", "receiveTime", "finishTime"):
            if 别的 != 名 and any(k.startswith(别的) for k in 参数):
                raise 自动化错误(页面改版, f"多了一个时间条件（{别的}），本次结果不可信。")
        实际 = (参数.get(f"{名}[0]", [None])[0], 参数.get(f"{名}[1]", [None])[0])
        if 实际 != (期望["日期范围"] or (None, None)):
            raise 自动化错误(页面改版, f"时间条件不对：应为 {期望['日期范围'] or '空'}，实际 {实际}。")
        总数 = 数据.get("total")
        if 总数 is None and not 数据.get("list"):
            总数 = 0
        if not isinstance(总数, int):
            raise 自动化错误(数据不完整, "读不到总条数。")
        try:
            self.页面.locator("span").filter(has_text=re.compile(f"^共 {总数} 条记录$")).first.wait_for(timeout=10000)
        except Exception:
            raise 自动化错误(数据不完整, f"页面显示的条数和读到的 {总数} 不一致。")
        return 总数

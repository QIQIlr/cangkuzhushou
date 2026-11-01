# 职责：“任务管理”页面的计数查询（点“查询”→ 读“共 N 条记录”），带防连点和条件核对。新模块共用。
# 输入：页面、运行记录；每次查询时给出“期望的条件”（任务大类代码、区域字母、日期参数名和日期范围）。
# 输出：总条数（整数）。查不到时抛出 自动化错误，绝不返回 0 冒充。
# 防连点：两次查询至少隔 1 秒（每个区第一次按天查之前隔约 2 秒）；WMS 提示“点击次数过多”（code 100010）时
#   等 3、5、8、8 秒重查，最多 4 次，并且这次运行剩下的查询（各模块共用）都改成隔 2 秒。
# 核对：WMS 实际收到的条件（任务大类、待处理、区域、日期）必须和期望一致；页面显示的“共 N 条记录”必须等于读到的数。
# 说明：没有记录时 WMS 返回 list=null、total=null，这时核对页面确实显示“共 0 条记录”再记 0。
#
# ⚠ 这里和 模块\无任务包裹.py 的 _等查询结果 长得像，但查的是两个不同页面（任务管理 / 包裹管理），
#   流程本来就不一样，所以**故意不共享代码**。要改下面这三件事时，记得两边都看一眼：
#   等多久（30 秒）、怎么核对“共 N 条记录”、出错怎么翻译成中文。
import re
import time
from urllib.parse import parse_qs, urlparse

from 公共.错误 import (自动化错误, 页面改版, 网络超时, 数据不完整, 归类, 浏览器被关, 网络断开, 等不到,
                    WMS掉线, 验证码, WMS提示错误, WMS提示)

查询接口 = "task/pageV1"
# 任务管理页“任务小类”的网址参数名（2026-11-01 只读探索：合箱增值=32、单箱增值=33，选“全部”时不带这个参数）
任务小类参数 = "taskType"
# 页面上出现这些字 = 被限制访问 / 要人验证：立刻停下，不重试、不绕过（方案 9.3）
危险词 = ("验证码", "安全验证", "人机验证", "访问频繁", "操作频繁", "请求过于频繁", "访问过于频繁",
       "异常访问", "请完成验证", "账号存在风险", "点击次数过多")
最小间隔秒 = 1.0
放慢后间隔秒 = 2.0
第一次按天前间隔秒 = 2.0          # 日志里“点击次数过多”几乎都出在查完总数、紧接着查第一天的时候（2026-10-29）
重试等待秒 = [3, 5, 8, 8]

# 只读判断：页面是不是弹了验证码 / 提示条（2026-11-01，方案 9.3）。'captcha' = 看见了验证码控件。
_危险JS = """() => {
  const 看得见 = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  for (const f of document.querySelectorAll('img[src*="captcha" i], iframe[src*="captcha" i], .verify-img, .captcha-box')) {
    if (看得见(f)) return 'captcha';
  }
  const 框们 = document.querySelectorAll('.el-message-box, .el-message, .el-notification');
  for (const 框 of 框们) {
    if (!看得见(框)) continue;
    const 字 = (框.innerText || '').trim();
    if (字) return 字;
  }
  return '';
}"""

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
                   "日期参数": "createTime", "日期范围": ("2026-10-23 00:00:00", "2026-10-23 23:59:59") 或 None,
                   "小类": {"参数": "taskType", "值": "32" 或 None}   # 可选；不写 = 不许带小类条件（2026-11-01）}"""
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
                self._危险("")                 # 2026-11-01：先看是不是掉线 / 验证码，是就立刻停（不要报成“等不到”再查下一个区）
                e2 = 归类(e)
                if e2.类型 in (浏览器被关, 网络断开, 等不到):   # 如实报（体检 2026-10-28）
                    raise e2
                raise 自动化错误(网络超时, "点“查询”后 30 秒内没有拿到结果。")
            finally:
                本次["上次"] = time.time()
                self.按天查过 = bool(期望.get("日期范围"))   # 刚查完总数 → 下一次按天查前多等一会
            self._危险(回应.url)                   # 2026-11-01：跳回登录页 / 页面上有验证码 → 立刻停下
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

    def _危险(self, 网址=""):
        """2026-11-01（方案 9.3）：运行中途被踢回登录页、或页面上跳出验证码 / “访问频繁” → 立刻停下。
        只读页面，不点、不等；读不到就当没事（不能因为读不到反而停下）。普通提示条不拦（照常查）。"""
        try:
            地 = str(网址 or "") + " " + str(getattr(self.页面, "url", "") or "")
        except Exception:
            地 = str(网址 or "")
        if "/login" in 地:
            raise 自动化错误(WMS掉线, "点“查询”后页面跳回了登录页，WMS 掉线了。")
        try:
            字 = self.页面.evaluate(_危险JS) or ""
        except Exception:
            return
        if not isinstance(字, str) or not 字:
            return
        一行 = " ".join(字.split())[:80]
        if 字 == "captcha" or "验证" in 字:
            raise 自动化错误(验证码, f"WMS 弹出验证：“{一行}”")
        if any(词 in 字 for 词 in 危险词):
            raise 自动化错误(WMS提示, f"WMS 弹出提示：“{一行}”")

    def _核对(self, 网址, 数据, 期望):
        参数 = parse_qs(urlparse(网址).query)
        for 键 in ("taskCategories", "taskStatus", "shelvesRegionNum"):
            if 参数.get(键, [None])[0] != 期望[键]:
                raise 自动化错误(页面改版, f"查询条件没有生效（{键}={参数.get(键)}，应为 {期望[键]}），本次结果不可信。")
        # 任务小类（2026-11-01，方案 6.1）：期望里写了的必须对得上；没写的绝不许带着小类条件查
        小类 = 期望.get("小类")
        实际 = 参数.get(任务小类参数, [None])[0]
        if 小类 is None:
            if 实际 not in (None, "", "全部"):
                raise 自动化错误(页面改版, f"多了一个任务小类条件（{任务小类参数}={实际}），本次结果不可信。")
        else:
            应为 = (小类 or {}).get("值")
            if 实际 != 应为 and not (应为 is None and 实际 in ("", "全部")):
                raise 自动化错误(页面改版, f"任务小类条件不对：应为 {应为 or '全部（不带这个条件）'}，实际 {实际 or '空'}。")
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

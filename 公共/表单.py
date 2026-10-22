# 职责：WMS 查询条件表单的通用操作（下拉选择、清空日期、直接填日期），新模块共用。
# 说明：WMS 的查询条件都是“标题 + 输入框”的格子，按标题文字找到格子再操作，不用屏幕坐标。
import re

from 公共.错误 import 自动化错误, 页面改版


def 表单项(页面, 名称):
    return 页面.locator(".vxe-form--item-inner").filter(
        has=页面.locator(".vxe-form--item-title-label").filter(has_text=re.compile("^" + 名称 + "$"))).first


def 下拉选项(页面, 名称):
    """读某个下拉框里的所有选项文字。"""
    框 = 表单项(页面, 名称)
    if 框.count() == 0:
        raise 自动化错误(页面改版, f"查询条件里找不到“{名称}”。")
    框.locator(".el-select").click()
    页面.wait_for_timeout(500)
    选项 = 页面.locator(".el-select-dropdown__item:visible").all_inner_texts()
    页面.keyboard.press("Escape")
    页面.wait_for_timeout(300)
    return [x.strip() for x in 选项]


def 下拉选择(页面, 名称, 选项):
    框 = 表单项(页面, 名称)
    if 框.count() == 0:
        raise 自动化错误(页面改版, f"查询条件里找不到“{名称}”。")
    框.locator(".el-select").click()
    页面.wait_for_timeout(500)
    项 = 页面.locator(".el-select-dropdown__item:visible").filter(has_text=re.compile("^" + 选项 + "$")).first
    if 项.count() == 0:
        页面.keyboard.press("Escape")
        raise 自动化错误(页面改版, f"“{名称}”下拉里找不到“{选项}”。")
    项.click()
    页面.wait_for_timeout(300)


def 日期值(页面, 名称):
    return [框.input_value() for 框 in 表单项(页面, 名称).locator("input").all()]


def 清空日期(页面, 名称):
    """点日期框右边的小叉清空。已经是空的就不动。"""
    if not any(日期值(页面, 名称)):
        return
    日期 = 表单项(页面, 名称)
    叉 = 日期.locator(".el-range__close-icon")
    for _ in range(5):   # 小叉只在鼠标停在上面时出现，所以多试几次
        页面.mouse.move(0, 0)
        日期.locator(".el-date-editor").hover()
        页面.wait_for_timeout(400)
        if "hidden" not in (叉.get_attribute("class") or ""):
            break
    叉.click(timeout=5000)
    页面.wait_for_timeout(300)
    if any(日期值(页面, 名称)):
        raise 自动化错误(页面改版, f"“{名称}”没有清空。")


def 填日期(页面, 名称, 开始, 结束, 空白处="任务编号"):
    """直接往日期框里填“YYYY-MM-DD HH:MM:SS”，填完核对框里的值；不对就再填一次。"""
    框们 = 表单项(页面, 名称).locator("input")
    for 第几次 in (1, 2):
        框们.nth(0).click()
        框们.nth(0).fill(开始)
        框们.nth(1).click()
        框们.nth(1).fill(结束)
        页面.keyboard.press("Enter")
        页面.wait_for_timeout(300)
        # 点一下别的地方，把日历面板关掉
        页面.locator(".vxe-form--item-title-label").filter(has_text=re.compile("^" + 空白处 + "$")).first.click()
        页面.wait_for_timeout(300)
        if 日期值(页面, 名称) == [开始, 结束]:
            return
    raise 自动化错误(页面改版, f"“{名称}”填不进去：想填 {开始} ~ {结束}，框里是 {日期值(页面, 名称)}。")

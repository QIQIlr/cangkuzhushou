# 职责：设置飞书群机器人（双击 设置飞书.bat 运行）。
# 输入：在黑色窗口里粘贴 Webhook 地址、输入自定义关键词。
# 输出：测试消息发送成功后，保存到 密钥.env，并打开“自动发送”。
# 安全：Webhook 地址输入时不显示，只保存在 密钥.env，不写日志。
import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from 公共 import 飞书  # noqa: E402

格式 = re.compile(r"^https://open\.(feishu\.cn|larksuite\.com)/open-apis/bot/v2/hook/[\w-]+$")


def 主程序():
    print("========== 设置飞书群机器人 ==========\n")
    print("第 1 步：请粘贴飞书群机器人的 Webhook 地址，然后按回车。")
    print("（为了安全，粘贴后屏幕上不会显示任何字，这是正常的。右键或 Ctrl+V 粘贴。）")
    网址 = getpass.getpass("Webhook 地址：").strip()
    if not 格式.match(网址):
        print("\n✘ 这不像飞书 Webhook 地址。应该以 https://open.feishu.cn/open-apis/bot/v2/hook/ 开头。")
        print("  请在飞书群设置 → 群机器人 → 你的机器人 里复制 Webhook 地址，然后重新双击 设置飞书.bat。")
        return 1
    print(f"已收到：……{网址[-4:]}（只显示最后 4 位）\n")

    print("第 2 步：请输入机器人的“自定义关键词”，然后按回车。")
    print("（在机器人的“安全设置”里能看到；没有设置关键词就直接按回车。）")
    关键词 = input("自定义关键词：").strip()

    print("\n第 3 步：正在发送测试消息 ……")
    状态, 说明 = 飞书.发送(f"【测试】仓库助手 飞书连接测试", 网址=网址, 关键词=关键词)
    if 状态 == "成功":
        飞书.写设置({"飞书Webhook": 网址, "飞书关键词": 关键词, "飞书已测通": "是"})
        print("\n✔ 成功！请到飞书群里看一下，应该收到了一条“【测试】仓库助手 飞书连接测试”。")
        print("  设置已保存，以后查询结果会自动发到这个群。")
        return 0
    print(f"\n✘ 测试没有成功（{状态}）：{说明}")
    if 状态 == "未知":
        print("  请到飞书群里看一下有没有收到测试消息。")
    print("  设置没有保存。处理后请重新双击 设置飞书.bat；处理不了就把这段文字发给 Claude（不要发 Webhook 地址）。")
    return 1


if __name__ == "__main__":
    try:
        结果码 = 主程序()
    except (KeyboardInterrupt, EOFError):
        print("\n已取消，没有保存任何设置。")
        结果码 = 1
    sys.exit(结果码)

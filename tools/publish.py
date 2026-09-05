#!/usr/bin/env python3
"""PTE 考试系统 · 一键发布工具（零依赖）。

两种模式：
  1) 生成草稿：把内容写成可直接复制粘贴的文本文件，放到 publish_drafts/<平台>/。
     python tools/publish.py --drafts
  2) 真实发布：对「有开放 API」的平台（Dev.to / Telegram / Mastodon / WordPress）
     自动发布；对「无开放 API」的平台（小红书 / 抖音 / 知乎 / B站 / 公众号）只生成草稿，
     因为你必须在这些平台用自己的账号登录后手动粘贴（它们没有公开发帖 API，且需短信验证）。

用法：
  python tools/publish.py --drafts            # 生成所有草稿文件
  python tools/publish.py --post              # 有 token 的平台自动发，其余给清单
  python tools/publish.py --post --platform telegram   # 只发某一个

环境变量（可选，填了才自动发）：
  DEVTO_API_KEY=xxx
  TG_BOT_TOKEN=xxx  TG_CHAT_ID=xxx
  MASTODON_URL=https://xxx  MASTODON_TOKEN=xxx
  WP_URL=https://xxx/wp-json  WP_USER=xxx  WP_PASS=xxx
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa
    pass

# ---------------------------------------------------------------------------
# 内容（与 docs/marketing/posts-batch1.md 保持一致）
# ---------------------------------------------------------------------------
POSTS = [
    {
        "platform": "xiaohongshu", "kind": "图文", "schedule": "第1周·周一",
        "title": "雅思考不过？换 PTE 两周上岸，平替神器¥6.6永久",
        "body": (
            "备考雅思口语写作卡 6.0 快一年，转 PTE 才发现真香。\n"
            "自用一款离线练习系统：¥6.6 一次激活永久用，不用联网也能练，口语写作 AI 实时批改，题库机经很全。\n"
            "二战党狂刷不心疼，机构几千块的工具这俩完全平替。\n"
            "需要的姐妹评论扣“资料”，发你下载+最新机经包～"
        ),
        "tags": ["PTE", "PTE备考", "雅思转PTE", "PTE机经", "留学澳洲"],
    },
    {
        "platform": "xiaohongshu", "kind": "图文", "schedule": "第1周·周五",
        "title": "机构 PTE 练习系统几千块？¥6.6 永久激活的平替我找到了",
        "body": (
            "不是广告，纯自用分享。\n"
            "- 机构同款：按年/按次收费，贵且要联网\n"
            "- 我的平替：¥6.6 永久、可离线、AI 批改、题库覆盖主流机经\n"
            "适合预算有限、需要大量刷题+批改的同学。\n"
            "下载和付款方式放评论区/主页了，自取。"
        ),
        "tags": ["PTE", "省钱", "PTE练习", "留学"],
    },
    {
        "platform": "douyin", "kind": "口播30s", "schedule": "第1周·周三",
        "title": "PTE 口语写作发愁？¥6.6 永久平替",
        "body": (
            "「还在为 PTE 口语写作发愁？机构几千块的练习系统，其实有个 ¥6.6 永久激活的平替，"
            "离线就能用、AI 帮你批改。评论打‘PTE’，我发你下载和最新机经。关注不迷路。」\n"
            "（拍摄：屏幕录一段软件界面/批改动画，口播配字幕）"
        ),
        "tags": [],
    },
    {
        "platform": "zhihu", "kind": "回答", "schedule": "第1周·周日",
        "title": "PTE 自学有什么好用的练习工具？",
        "body": (
            "答：自用一款离线练习系统，核心优势是便宜（¥6.6 永久）、可离线、带 AI 口语写作批改，"
            "题库覆盖主流机经。适合预算有限、需要大量刷题批改的同学。\n"
            "需要的我可以私信下载方式，也整理了机经包。"
        ),
        "tags": [],
    },
    {
        "platform": "bilibili", "kind": "视频脚本", "schedule": "第2周·周三",
        "title": "PTE 模考系统完整演示｜¥6.6 永久离线练+AI批改",
        "body": (
            "【开头】备考 PTE 被机构练习系统价格劝退？这期实测一款 ¥6.6 永久激活的离线模考系统。\n"
            "【演示】打开软件 → 24h 免费试用 → 选套题 → 口语/写作 AI 批改 → 出分报告。\n"
            "【结尾】付款后客服发激活码，链接放简介。评论‘PTE’发机经包。"
        ),
        "tags": ["PTE", "PTE备考", "软件测评"],
    },
    {
        "platform": "wechat_mp", "kind": "图文", "schedule": "第2周·周五",
        "title": "PTE 二战党必看：¥6.6 平替机构几千块练习系统",
        "body": (
            "很多同学二战 PTE，光练习系统就花掉几千。其实有一款离线模考工具，¥6.6 一次激活永久用，"
            "AI 口语写作批改、机经题库全覆盖。\n"
            "我们做了完整演示和对比，需要的话后台回复‘PTE’领取下载+机经包。"
        ),
        "tags": [],
    },
    {
        "platform": "zhihu", "kind": "回答", "schedule": "第3周·周一",
        "title": "PTE 和雅思到底怎么选？过来人给你算笔账",
        "body": (
            "从认可度、难度、出分速度、费用四方面对比：PTE 机考出分快（1-5 天）、交叉评分，"
            "写作口语弱项的同学更容易提分。\n"
            "练习工具方面，自用一款 ¥6.6 永久离线模考系统，AI 批改口语写作，评论区/私信自取。"
        ),
        "tags": ["PTE", "雅思", "留学"],
    },
    {
        "platform": "douyin", "kind": "口播30s", "schedule": "第3周·周三",
        "title": "PTE 备考最痛的三个坑，你踩了几个",
        "body": (
            "「PTE 备考三大坑：一，报了大班课没人管；二，练习系统按年收费几千块；"
            "三，口语写作没人批改，瞎练。其实 ¥6.6 就能拿到永久离线练习+AI 批改，评论‘PTE’自取。」"
        ),
        "tags": [],
    },
    {
        "platform": "xiaohongshu", "kind": "图文", "schedule": "第3周·周五",
        "title": "二战 PTE 才明白的事：工具选对，分数真的涨",
        "body": (
            "一战踩坑：机经乱刷、写作没批改，白花钱。\n"
            "二战换了离线模考系统，AI 实时批改口语写作，¥6.6 永久用，刷题不心疼。\n"
            "出分经验和工具评论区自取。"
        ),
        "tags": ["PTE", "二战", "PTE备考"],
    },
    {
        "platform": "xiaohongshu", "kind": "图文", "schedule": "第3周·周日",
        "title": "PTE 代理/机构合作：批量激活码，成本价拿",
        "body": (
            "面向机构/留学中介/学习博主：可批量拿激活码自行定价转售，学生党也能做分销，"
            "卖出一单有提成。\n详谈加微信（见主页）。"
        ),
        "tags": ["PTE", "代理", "留学中介"],
    },
    {
        "platform": "bilibili", "kind": "视频脚本", "schedule": "第4周·周一",
        "title": "PTE 模考系统保姆级教程：从下载到激活到刷题",
        "body": (
            "【下载】简介链接（网盘/GitHub 分卷合并教程）→【安装】管理员运行 →【试用】24h 免费 →"
            "【激活】付款找客服拿码 →【刷题】题库/AI 批改演示。全程录屏+字幕。"
        ),
        "tags": ["PTE", "PTE备考", "教程"],
    },
    {
        "platform": "xiaohongshu", "kind": "图文", "schedule": "第4周·周五",
        "title": "出分喜报墙｜他们用 ¥6.6 的工具考过了 PTE",
        "body": (
            "整理近期用户出分截图（授权发布）：口语 58→73、写作 79…\n"
            "同款工具 ¥6.6 永久，评论区自取。欢迎晒分返现（见主页活动）。"
        ),
        "tags": ["PTE", "出分", "喜报"],
    },
    {
        "platform": "douyin", "kind": "口播30s", "schedule": "第4周·周日",
        "title": "PTE 常见问题一次答清（离线/激活/退款）",
        "body": (
            "「问得最多的三个问题：离线能用吗？能。¥6.6 是永久的吗？是。先试后买吗？"
            "24 小时免费试用。还有问题评论区丢过来。」"
        ),
        "tags": [],
    },
    {
        "platform": "zhihu", "kind": "回答", "schedule": "第4周·周日",
        "title": "有没有便宜的 PTE 刷题网站/软件推荐？",
        "body": (
            "预算有限推荐这款离线模考系统：¥6.6 永久激活、AI 口语写作批改、覆盖主流机经，"
            "对比按年收费的大平台性价比极高。下载方式见个人主页。"
        ),
        "tags": [],
    },
]

LANDING = "https://sunav66.github.io/pte-exam-system/"
WX = "wxid_34mm5tyy8l5t12"

API_PLATFORMS = {"devto", "telegram", "mastodon", "wordpress"}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s)[:24]


def _post_json(url: str, payload: dict, headers: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def generate_drafts(out_root: str = "publish_drafts"):
    os.makedirs(out_root, exist_ok=True)
    for p in POSTS:
        d = os.path.join(out_root, p["platform"])
        os.makedirs(d, exist_ok=True)
        fn = os.path.join(d, f"{p['schedule'].replace('·', '_')}__{_slug(p['title'])}.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"平台: {p['platform']}  ({p['kind']})\n")
            f.write(f"计划: {p['schedule']}\n")
            f.write(f"标题: {p['title']}\n")
            if p["tags"]:
                f.write(f"标签: {' '.join('#'+t for t in p['tags'])}\n")
            f.write("-" * 40 + "\n")
            f.write(p["body"] + "\n")
            f.write("-" * 40 + "\n")
            f.write(f"落点: {LANDING}\n客服微信: {WX}\n")
            if p["platform"] not in API_PLATFORMS:
                f.write("【手动发布】登录该平台账号 → 新建笔记/视频/回答 → 粘贴以上内容 → 发布。\n")
        print("草稿:", fn)
    print(f"\n共生成 {len(POSTS)} 份草稿 → {out_root}/")


def publish(api_only: bool, platform: str | None):
    posted, manual = [], []
    for p in POSTS:
        if platform and p["platform"] != platform:
            continue
        if p["platform"] in API_PLATFORMS:
            ok = _publish_api(p)
            (posted if ok else manual).append(p["platform"] + "/" + p["title"])
        else:
            manual.append(p["platform"] + "/" + p["title"])

    print("\n=== 发布结果 ===")
    print("已自动发布:", posted or "（无，需配置 token 或该平台无 API）")
    print("需手动发布:", manual or "（无）")
    if manual:
        print("\n手动平台请在对应 App/网页登录后复制 publish_drafts/ 下文件内容发布。")


def _publish_api(p: dict) -> bool:
    plat = p["platform"]
    try:
        if plat == "devto":
            key = os.getenv("DEVTO_API_KEY")
            if not key:
                return False
            _post_json("https://dev.to/api/articles",
                       {"article": {"title": p["title"], "body_markdown": p["body"] + f"\n\n{LANDING}",
                                    "published": True, "tags": p["tags"][:4]}},
                       {"api-key": key, "Content-Type": "application/json", "Accept": "application/json"})
            return True
        if plat == "telegram":
            tok, chat = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
            if not (tok and chat):
                return False
            _post_json(f"https://api.telegram.org/bot{tok}/sendMessage",
                       {"chat_id": chat, "text": f"{p['title']}\n\n{p['body']}\n{LANDING}"},
                       {"Content-Type": "application/json"})
            return True
        if plat == "mastodon":
            url, tok = os.getenv("MASTODON_URL"), os.getenv("MASTODON_TOKEN")
            if not (url and tok):
                return False
            _post_json(f"{url.rstrip('/')}/api/v1/statuses",
                       {"status": f"{p['title']}\n\n{p['body']}\n{LANDING}"},
                       {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            return True
        if plat == "wordpress":
            wp, user, pw = os.getenv("WP_URL"), os.getenv("WP_USER"), os.getenv("WP_PASS")
            if not (wp and user and pw):
                return False
            import base64
            auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
            _post_json(f"{wp.rstrip('/')}/wp/v2/posts",
                       {"title": p["title"], "content": p["body"] + f"\n<p>{LANDING}</p>", "status": "publish"},
                       {"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
            return True
    except Exception as e:  # noqa
        print(f"  [{plat}] 发布失败: {e}")
        return False
    return False


def generate_checklist(out: str = "docs/marketing/publish-checklist.md"):
    lines = ["# PTE 发布清单（照勾）", "", "总进度：0 / %d 篇" % len(POSTS), ""]
    for p in POSTS:
        tag = " ".join("#" + t for t in p["tags"]) if p["tags"] else "—"
        lines.append("- [ ] **%s** `%s`/%s — %s  （标签: %s）" % (
            p["schedule"], p["platform"], p["kind"], p["title"], tag))
        lines.append("  - 草稿目录: `publish_drafts/%s/`" % p["platform"])
    lines += [
        "",
        "## 步骤",
        "1. 登录对应平台账号",
        "2. 打开 `publish_drafts/<平台>/` 下对应草稿文件，全选复制",
        "3. 新建笔记/视频/回答并粘贴，补图后发布",
        "4. 回来把上面 `[ ]` 改成 `[x]`",
        "",
        "落地页: %s    客服微信: %s" % (LANDING, WX),
        "注：小红书/抖音/知乎/B站/公众号 均无开放发帖 API，需手动发布；",
        "Dev.to / Telegram / Mastodon / WordPress 配置 token 后可用 `python tools/publish.py --post` 自动发。",
    ]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("发布清单已生成:", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true", help="生成可复制草稿文件")
    ap.add_argument("--post", action="store_true", help="自动发布（需要 token）")
    ap.add_argument("--checklist", action="store_true", help="生成发布清单 markdown")
    ap.add_argument("--platform", type=str, default=None, help="只处理某平台")
    args = ap.parse_args()

    if args.drafts:
        generate_drafts()
    if args.checklist:
        generate_checklist()
    if args.post:
        publish(api_only=not args.drafts, platform=args.platform)
    if not (args.drafts or args.post or args.checklist):
        print(__doc__)


if __name__ == "__main__":
    main()

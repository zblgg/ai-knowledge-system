#!/usr/bin/env python3
"""
管培生日报监控脚本
- 每天早上10点检查前一天的日报填报情况
- 每周一早上发送上周汇总
"""
import requests
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
BITABLE_TOKEN = "OHZ8bNe1GaZsTWstktkczbVSnQb"
TABLE_ID = "tblzrv75eruK07HY"
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/86407aaf-b12e-4cb7-ba88-23f7e7db57eb"

# 管培生名单（用户ID -> 真名）
NAME_MAPPING = {
    "用户569150": "陈佳俊",
}

# 应该填报的人员列表
EXPECTED_MEMBERS = ["单秋收", "陈佳俊"]


def get_access_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    return resp.json().get("tenant_access_token")


def parse_name(name_field):
    """解析姓名字段"""
    if isinstance(name_field, list) and name_field:
        n = name_field[0].get("name", "") if isinstance(name_field[0], dict) else str(name_field[0])
        return NAME_MAPPING.get(n, n)
    return str(name_field) if name_field else "未知"


def parse_date(date_val):
    """解析日期字段"""
    if isinstance(date_val, (int, float)) and date_val > 0:
        return datetime.fromtimestamp(date_val / 1000)
    return None


def get_all_records(token):
    """获取所有日报记录"""
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    page_token = None

    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_TOKEN}/tables/{TABLE_ID}/records"
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()

        if data.get("code") != 0:
            break

        items = data.get("data", {}).get("items", [])
        all_records.extend(items)

        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")

    return all_records


def check_daily_report(records, check_date):
    """检查指定日期的填报情况"""
    filled_members = set()

    for record in records:
        fields = record.get("fields", {})
        record_date = parse_date(fields.get("日期"))
        name = parse_name(fields.get("姓名"))

        if record_date and record_date.date() == check_date.date():
            filled_members.add(name)

    missing_members = [m for m in EXPECTED_MEMBERS if m not in filled_members]

    return {
        "date": check_date,
        "filled": list(filled_members),
        "missing": missing_members
    }


def send_daily_notification(result):
    """发送每日填报提醒"""
    date_str = result["date"].strftime("%m月%d日")

    if not result["missing"]:
        content = f"**{date_str} 日报填报情况**\n\n✅ 全员已填报！\n\n已填：{', '.join(result['filled'])}"
        template = "green"
    else:
        content = f"**{date_str} 日报填报情况**\n\n"
        content += f"✅ 已填：{', '.join(result['filled']) if result['filled'] else '无'}\n\n"
        content += f"❌ **未填**：{', '.join(result['missing'])}\n\n"
        content += "请相关同学尽快补填日报！"
        template = "red"

    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "📋 日报填报提醒"},
                "template": template
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"}]}
            ]
        }
    }

    resp = requests.post(WEBHOOK_URL, json=message)
    return resp.json()


def generate_weekly_summary(records, week_start, week_end):
    """生成周报汇总"""
    # 筛选本周数据
    week_data = []
    for record in records:
        fields = record.get("fields", {})
        record_date = parse_date(fields.get("日期"))
        if record_date and week_start <= record_date <= week_end:
            week_data.append({
                "date": record_date,
                "name": parse_name(fields.get("姓名")),
                "decision": fields.get("今日决策时刻(选1个你做过判断/选择的时刻)", "") or "",
                "choice": fields.get("我的选择：", "") or "",
                "result": fields.get("结果：", "") or "",
                "problem_action": fields.get("发现的问题 + 我的行动(不要只提问题,要说你做了什么)", "") or "",
                "need_support": fields.get("需要支持的地方(只写1个最需要的)", "") or "",
            })

    # 统计填报情况
    by_person = defaultdict(list)
    for d in week_data:
        by_person[d["name"]].append(d)

    # 统计每人填报天数
    fill_stats = []
    for name in EXPECTED_MEMBERS:
        reports = by_person.get(name, [])
        dates = set(r["date"].strftime("%m/%d") for r in reports)
        fill_stats.append(f"• {name}：{len(dates)}天/7天")

    # 提取主要工作内容（按人）
    work_summary = []
    for name in EXPECTED_MEMBERS:
        reports = by_person.get(name, [])
        if reports:
            work_items = []
            for r in sorted(reports, key=lambda x: x["date"], reverse=True)[:5]:
                content = r["decision"] or r["problem_action"]
                if content and content not in ["无", "暂无"]:
                    work_items.append(f"  - {r['date'].strftime('%m/%d')}: {content[:40]}...")
            if work_items:
                work_summary.append(f"**{name}**\n" + "\n".join(work_items[:3]))

    # 提取待解决事项
    issues = []
    for d in week_data:
        support = d.get("need_support", "")
        if support and support not in ["无", "暂无", "-", "/"]:
            issues.append(f"• [{d['date'].strftime('%m/%d')}] {d['name']}: {support[:50]}")

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_reports": len(week_data),
        "fill_stats": fill_stats,
        "work_summary": work_summary,
        "issues": issues[:5]
    }


def send_weekly_notification(summary):
    """发送周报汇总"""
    week_str = f"{summary['week_start'].strftime('%m/%d')} - {summary['week_end'].strftime('%m/%d')}"

    elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**📊 填报统计**\n本周共 {summary['total_reports']} 条日报\n\n" + "\n".join(summary['fill_stats'])}
        },
        {"tag": "hr"}
    ]

    # 添加工作汇总
    if summary["work_summary"]:
        work_content = "**📝 本周工作要点**\n\n" + "\n\n".join(summary["work_summary"])
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": work_content}})
        elements.append({"tag": "hr"})

    # 添加待解决事项
    if summary["issues"]:
        issues_content = "**🚨 待解决事项**\n" + "\n".join(summary["issues"])
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": issues_content}})

    elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"由 AI知识管理同步 自动生成 | {datetime.now().strftime('%Y-%m-%d')}"}]})

    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📋 管培生周报汇总 ({week_str})"},
                "template": "blue"
            },
            "elements": elements
        }
    }

    resp = requests.post(WEBHOOK_URL, json=message)
    return resp.json()


def run_daily_check():
    """执行每日检查"""
    print(f"[{datetime.now()}] 执行每日填报检查...")

    token = get_access_token()
    if not token:
        print("获取飞书令牌失败")
        return

    records = get_all_records(token)
    print(f"获取到 {len(records)} 条日报记录")

    # 检查昨天的日报
    yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"检查日期：{yesterday.strftime('%Y-%m-%d')}")

    result = check_daily_report(records, yesterday)
    print(f"已填：{result['filled']}")
    print(f"漏填：{result['missing']}")

    resp = send_daily_notification(result)
    print(f"通知发送结果：{resp}")


def run_weekly_summary():
    """执行周报汇总（每周一运行，汇总上周）"""
    print(f"[{datetime.now()}] 生成周报汇总...")

    token = get_access_token()
    if not token:
        print("获取飞书令牌失败")
        return

    records = get_all_records(token)
    print(f"获取到 {len(records)} 条日报记录")

    # 计算上周的时间范围（上周一到上周日）
    today = datetime.now()
    # 本周一
    this_monday = today - timedelta(days=today.weekday())
    this_monday = this_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # 上周一
    last_monday = this_monday - timedelta(days=7)
    # 上周日
    last_sunday = this_monday - timedelta(days=1)
    last_sunday = last_sunday.replace(hour=23, minute=59, second=59)

    print(f"汇总周期：{last_monday.strftime('%Y-%m-%d')} 至 {last_sunday.strftime('%Y-%m-%d')}")

    summary = generate_weekly_summary(records, last_monday, last_sunday)
    resp = send_weekly_notification(summary)
    print(f"通知发送结果：{resp}")


def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "daily":
            run_daily_check()
        elif sys.argv[1] == "weekly":
            run_weekly_summary()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python daily_report_monitor.py [daily|weekly]")
    else:
        # 默认执行每日检查
        run_daily_check()


if __name__ == "__main__":
    main()

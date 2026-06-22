#!/usr/bin/env python3
"""
从飞书拉取最新状态
用于对话开始时了解"之前做了什么"

用法：
    python fetch_feishu.py           # 输出摘要到终端
    python fetch_feishu.py --json    # 输出JSON格式
    python fetch_feishu.py --context # 输出Claude可读的上下文
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_FOLDER_TOKEN


def fetch_context():
    """从飞书获取上下文"""
    from sync_feishu import FeishuSync

    FEISHU_BITABLE_TOKEN = os.getenv("FEISHU_BITABLE_TOKEN", "")

    if not FEISHU_APP_ID or not FEISHU_APP_SECRET or not FEISHU_BITABLE_TOKEN:
        return {"error": "飞书配置不完整"}

    syncer = FeishuSync()
    syncer.bitable_token = FEISHU_BITABLE_TOKEN

    try:
        syncer.get_tenant_access_token()
        syncer.get_all_table_ids()
        return syncer.get_context_summary()
    except Exception as e:
        return {"error": str(e)}


def format_for_human(context: dict) -> str:
    """格式化为人类可读的摘要"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"📋 飞书状态同步 ({context.get('fetch_time', '')[:16]})")
    lines.append("=" * 50)

    # 待处理线头
    threads = context.get("pending_threads", [])
    lines.append(f"\n🧵 待处理线头 ({len(threads)} 条)")
    if threads:
        for t in threads:
            priority = t.get("优先级", "中")
            icon = "🔴" if priority == "高" else "🟡" if priority == "中" else "🟢"
            lines.append(f"   {icon} {t.get('标题', '')}")
    else:
        lines.append("   无待处理事项")

    # 最近归档
    archives = context.get("recent_archives", [])
    lines.append(f"\n📁 最近对话 ({len(archives)} 条)")
    if archives:
        for a in archives:
            lines.append(f"   [{a.get('日期', '')}] {a.get('主题', '')}")
            summary = a.get('一句话总结', '')
            if summary:
                lines.append(f"      → {summary[:50]}...")
    else:
        lines.append("   无归档记录")

    if context.get("error"):
        lines.append(f"\n⚠️ 错误: {context.get('error')}")

    lines.append("")
    return "\n".join(lines)


def format_for_claude(context: dict) -> str:
    """格式化为Claude可读的上下文提示"""
    lines = []
    lines.append("<feishu_context>")
    lines.append(f"同步时间: {context.get('fetch_time', '')[:16]}")

    # 待处理线头
    threads = context.get("pending_threads", [])
    if threads:
        lines.append("\n待处理事项:")
        for t in threads:
            priority = t.get("优先级", "中")
            lines.append(f"- [{priority}] {t.get('标题', '')} (来源: {t.get('来源', '未知')})")

    # 最近归档
    archives = context.get("recent_archives", [])
    if archives:
        lines.append("\n最近对话记录:")
        for a in archives:
            lines.append(f"- {a.get('日期', '')}: {a.get('主题', '')}")
            summary = a.get('一句话总结', '')
            if summary:
                lines.append(f"  摘要: {summary}")

    if not threads and not archives:
        lines.append("\n暂无历史记录")

    lines.append("</feishu_context>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从飞书拉取最新状态")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--context", action="store_true", help="输出Claude可读的上下文")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式，只在有内容时输出")
    args = parser.parse_args()

    context = fetch_context()

    if args.json:
        print(json.dumps(context, ensure_ascii=False, indent=2))
    elif args.context:
        output = format_for_claude(context)
        # 静默模式下，只有有待办或最近记录时才输出
        if args.quiet:
            if context.get("pending_threads") or context.get("recent_archives"):
                print(output)
        else:
            print(output)
    else:
        print(format_for_human(context))


if __name__ == "__main__":
    main()

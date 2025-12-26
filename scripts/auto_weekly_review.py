#!/usr/bin/env python3
"""
自动周复盘脚本
每周一自动执行，生成上周的复盘报告并同步到云端
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "对话归档"
THREADS_FILE = PROJECT_ROOT / "线头追踪" / "THREADS.md"
REVIEW_DIR = PROJECT_ROOT / "复盘报告"

def get_week_range():
    """获取上周的日期范围"""
    today = datetime.now()
    # 找到上周一
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday

def scan_archives(start_date, end_date):
    """扫描指定日期范围内的归档文件"""
    archives = []

    # 遍历可能的月份目录
    current = start_date
    while current <= end_date:
        month_dir = ARCHIVE_DIR / current.strftime("%Y-%m")
        if month_dir.exists():
            for f in month_dir.glob("*.md"):
                # 从文件名提取日期 (MMDD_xxx.md)
                try:
                    file_date_str = f.stem[:4]  # 取前4位 MMDD
                    file_month = int(file_date_str[:2])
                    file_day = int(file_date_str[2:4])
                    file_date = datetime(current.year, file_month, file_day)

                    if start_date <= file_date <= end_date:
                        archives.append({
                            'path': f,
                            'date': file_date,
                            'content': f.read_text(encoding='utf-8')
                        })
                except:
                    continue
        current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)

    return sorted(archives, key=lambda x: x['date'])

def extract_insights(content):
    """从归档内容中提取洞见"""
    insights = []
    in_insights_section = False

    for line in content.split('\n'):
        if '核心洞见' in line or '洞见' in line:
            in_insights_section = True
            continue
        if in_insights_section:
            if line.startswith('#'):
                break
            if line.strip().startswith(('-', '*', '1', '2', '3', '4', '5')):
                insight = line.strip().lstrip('-*0123456789. ')
                if insight and len(insight) > 5:
                    insights.append(insight)

    return insights[:5]  # 最多5条

def extract_tags(content):
    """提取标签"""
    import re
    tags = re.findall(r'#(\w+)', content)
    return list(set(tags))

def count_threads():
    """统计线头数量"""
    if not THREADS_FILE.exists():
        return {'pending': 0, 'completed': 0}

    content = THREADS_FILE.read_text(encoding='utf-8')
    pending = content.count('- [ ]')
    completed = content.count('- [x]')

    return {'pending': pending, 'completed': completed}

def generate_review(start_date, end_date, archives):
    """生成复盘报告"""
    week_num = start_date.isocalendar()[1]

    # 统计数据
    all_insights = []
    all_tags = []
    for a in archives:
        all_insights.extend(extract_insights(a['content']))
        all_tags.extend(extract_tags(a['content']))

    # 标签统计
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    threads = count_threads()

    # 生成报告
    report = f"""# {start_date.year}年{start_date.month}月 第{week_num}周 AI对话复盘

**周期**：{start_date.strftime('%m.%d')} - {end_date.strftime('%m.%d')}
**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 数据概览

| 指标 | 数量 |
|------|------|
| 归档对话 | {len(archives)} 次 |
| 核心洞见 | {len(all_insights)} 条 |
| 待办线头 | {threads['pending']} 个 |

---

## 主题分布

"""

    if tag_counts:
        report += "| 主题 | 对话数 |\n|------|--------|\n"
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
            report += f"| #{tag} | {count} |\n"
    else:
        report += "*本周无标签数据*\n"

    report += "\n---\n\n## 核心洞见汇总\n\n"

    if all_insights:
        for i, insight in enumerate(all_insights[:10], 1):
            report += f"{i}. {insight}\n"
    else:
        report += "*本周无归档洞见*\n"

    report += """
---

## 下周关注

基于当前线头，下周应重点关注：
1. 清理积压线头
2. 继续保持对话归档习惯

---

## 反思

*[可手动补充本周AI使用效率的反思]*

---

> 此报告由系统自动生成
"""

    return report

def main():
    print(f"[{datetime.now()}] 开始生成周复盘报告...")

    # 获取上周日期范围
    start_date, end_date = get_week_range()
    print(f"复盘周期: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

    # 扫描归档
    archives = scan_archives(start_date, end_date)
    print(f"找到 {len(archives)} 个归档文件")

    # 生成报告
    report = generate_review(start_date, end_date, archives)

    # 保存报告
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    week_num = start_date.isocalendar()[1]
    report_file = REVIEW_DIR / f"{start_date.year}-{start_date.month:02d}_第{week_num}周复盘.md"
    report_file.write_text(report, encoding='utf-8')
    print(f"报告已保存: {report_file}")

    # 同步到云端
    print("正在同步到云端...")
    sync_script = Path(__file__).parent / "sync.py"
    if sync_script.exists():
        os.system(f'python3 "{sync_script}" --file "{report_file}"')

    print(f"[{datetime.now()}] 周复盘完成!")

if __name__ == "__main__":
    main()

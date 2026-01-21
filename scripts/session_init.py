#!/usr/bin/env python3
"""
会话初始化脚本
在 Claude Code 会话开始时自动加载上下文
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path("/Users/zhubailin/Downloads/ Claude Code Projects")
KNOWLEDGE_DIR = PROJECT_ROOT / "AI知识管理系统"

def get_recent_progress():
    """获取最近的项目进度"""
    result = []

    # 优先读取根目录的 项目状态.md（汇总文件）
    status_file = PROJECT_ROOT / "项目状态.md"
    if status_file.exists():
        try:
            content = status_file.read_text(encoding='utf-8')
            # 取前800字符，保留关键信息
            preview = content[:800] + "..." if len(content) > 800 else content
            result.append(f"【项目状态汇总】\n{preview}")
        except:
            pass

    # 再查找各项目的 PROGRESS.md（如果有的话）
    progress_files = []
    for project_dir in PROJECT_ROOT.iterdir():
        if project_dir.is_dir():
            progress_file = project_dir / "PROGRESS.md"
            if progress_file.exists():
                mtime = progress_file.stat().st_mtime
                progress_files.append((progress_file, mtime))

    # 按修改时间排序，取最近的
    progress_files.sort(key=lambda x: x[1], reverse=True)

    for pf, _ in progress_files[:2]:  # 最近2个项目
        try:
            content = pf.read_text(encoding='utf-8')
            preview = content[:400] + "..." if len(content) > 400 else content
            project_name = pf.parent.name
            result.append(f"【{project_name}】\n{preview}")
        except:
            pass

    return result


def get_threads():
    """获取待处理线头"""
    threads_file = KNOWLEDGE_DIR / "线头追踪" / "THREADS.md"
    if not threads_file.exists():
        return None

    try:
        content = threads_file.read_text(encoding='utf-8')
        # 提取待跟进事项部分
        if "## 待跟进事项" in content:
            start = content.find("## 待跟进事项")
            end = content.find("---", start + 1)
            if end == -1:
                end = len(content)
            section = content[start:end].strip()
            return section
    except:
        pass

    return None


def main():
    output = []
    output.append(f"<session_context>")
    output.append(f"会话开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 获取线头
    threads = get_threads()
    if threads:
        # 只输出表格部分的前几行
        lines = threads.split('\n')
        table_lines = [l for l in lines if l.startswith('|')][:8]  # 表头+前5条
        if table_lines:
            output.append("\n待处理事项（高优先级）:")
            output.append('\n'.join(table_lines))

    # 获取最近项目进度
    progress = get_recent_progress()
    if progress:
        output.append("\n最近项目状态:")
        for p in progress[:2]:  # 只显示2个
            # 再精简一下
            short = p[:300] + "..." if len(p) > 300 else p
            output.append(short)

    output.append("</session_context>")

    print('\n'.join(output))


if __name__ == "__main__":
    main()

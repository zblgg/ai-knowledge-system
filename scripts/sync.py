#!/usr/bin/env python3
"""
知识管理系统 - 统一同步入口（多维表格版）

用法：
    python sync.py                     # 同步所有新增文件
    python sync.py --file <文件路径>    # 同步单个文件
    python sync.py --all               # 强制同步所有文件
    python sync.py --status            # 查看同步状态
    python sync.py --init              # 初始化多维表格
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BASE_DIR, ARCHIVE_DIR, THREADS_FILE, KNOWLEDGE_DIR, REVIEW_DIR,
    FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_FOLDER_TOKEN
)

# 同步状态文件
SYNC_STATE_FILE = Path(__file__).parent / ".sync_state.json"
FEISHU_BITABLE_TOKEN = os.getenv("FEISHU_BITABLE_TOKEN", "")


def load_sync_state() -> dict:
    """加载同步状态"""
    if SYNC_STATE_FILE.exists():
        with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"synced_files": {}, "last_sync": None}


def save_sync_state(state: dict):
    """保存同步状态"""
    state["last_sync"] = datetime.now().isoformat()
    with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_all_md_files() -> list:
    """获取所有待同步的Markdown文件"""
    files = []

    # 对话归档
    if ARCHIVE_DIR.exists():
        files.extend(ARCHIVE_DIR.rglob("*.md"))

    # 线头追踪
    if THREADS_FILE.exists():
        files.append(THREADS_FILE)

    # 知识沉淀
    if KNOWLEDGE_DIR.exists():
        files.extend(KNOWLEDGE_DIR.rglob("*.md"))

    # 复盘报告
    if REVIEW_DIR.exists():
        files.extend(REVIEW_DIR.rglob("*.md"))

    # 排除模板文件
    files = [f for f in files if not f.name.startswith("_")]

    return files


def get_new_files(state: dict) -> list:
    """获取新增或修改的文件"""
    all_files = get_all_md_files()
    synced = state.get("synced_files", {})

    new_files = []
    for f in all_files:
        f_str = str(f)
        mtime = f.stat().st_mtime

        if f_str not in synced or synced[f_str]["mtime"] < mtime:
            new_files.append(f)

    return new_files


def classify_file(file_path: Path) -> str:
    """根据文件路径分类"""
    path_str = str(file_path)

    if "线头追踪" in path_str or file_path.name == "THREADS.md":
        return "threads"
    elif "对话归档" in path_str:
        return "archive"
    elif "知识沉淀" in path_str:
        return "knowledge"
    elif "复盘报告" in path_str:
        return "archive"  # 复盘报告也作为归档处理
    else:
        return "knowledge"


def sync_file(file_path: Path, syncer, state: dict) -> bool:
    """同步单个文件到飞书多维表格"""
    from sync_feishu import (
        parse_threads_file, parse_archive_file, sync_to_feishu
    )

    file_type = classify_file(file_path)
    success = False

    try:
        if file_type == "threads":
            # 线头文件：解析每个线头，同步到表格
            threads = parse_threads_file(file_path)
            print(f"      解析到 {len(threads)} 个线头")
            synced_count = 0
            for thread in threads:
                if sync_to_feishu(syncer, "thread", thread):
                    synced_count += 1
            print(f"      同步 {synced_count}/{len(threads)} 个线头")
            success = synced_count > 0

        elif file_type == "archive":
            # 归档文件：提取元信息 + 创建详情文档
            meta = parse_archive_file(file_path)

            # 创建详情文档
            content = file_path.read_text(encoding="utf-8")
            doc_url = syncer.create_document(file_path.stem, content)

            # 同步元信息到表格
            success = sync_to_feishu(syncer, "archive", meta, doc_url)
            if success:
                print(f"      ✓ 归档索引已更新")

        elif file_type == "knowledge":
            # 知识沉淀：创建文档 + 索引
            content = file_path.read_text(encoding="utf-8")

            # 判断类型
            knowledge_type = "其他"
            path_str = str(file_path)
            if "方法论" in path_str:
                knowledge_type = "方法论"
            elif "SOP" in path_str:
                knowledge_type = "SOP"
            elif "洞见" in path_str:
                knowledge_type = "洞见"

            # 提取摘要（第一段非标题内容）
            lines = content.split('\n')
            summary = ""
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('---'):
                    summary = line[:200]
                    break

            # 创建详情文档
            doc_url = syncer.create_document(file_path.stem, content)

            # 同步到表格
            data = {
                "标题": file_path.stem,
                "类型": knowledge_type,
                "摘要": summary
            }
            success = sync_to_feishu(syncer, "knowledge", data, doc_url)
            if success:
                print(f"      ✓ 知识索引已更新")

    except Exception as e:
        print(f"      ✗ 同步失败: {e}")
        return False

    # 更新状态
    if success:
        state["synced_files"][str(file_path)] = {
            "mtime": file_path.stat().st_mtime,
            "synced_at": datetime.now().isoformat(),
            "type": file_type
        }

    return success


def main():
    parser = argparse.ArgumentParser(description="知识管理系统同步工具")
    parser.add_argument("--file", "-f", help="同步单个文件")
    parser.add_argument("--all", "-a", action="store_true", help="强制同步所有文件")
    parser.add_argument("--status", "-s", action="store_true", help="查看同步状态")
    parser.add_argument("--init", "-i", action="store_true", help="初始化多维表格")
    parser.add_argument("--check", "-c", action="store_true", help="检查配置")
    args = parser.parse_args()

    # 检查配置
    if args.check:
        print("📋 配置检查：")
        print(f"   FEISHU_APP_ID: {'✓' if FEISHU_APP_ID else '✗ 未配置'}")
        print(f"   FEISHU_APP_SECRET: {'✓' if FEISHU_APP_SECRET else '✗ 未配置'}")
        print(f"   FEISHU_FOLDER_TOKEN: {'✓' if FEISHU_FOLDER_TOKEN else '✗ 未配置'}")
        print(f"   FEISHU_BITABLE_TOKEN: {'✓' if FEISHU_BITABLE_TOKEN else '✗ 未配置'}")
        return

    # 查看状态
    if args.status:
        state = load_sync_state()
        synced = state.get("synced_files", {})
        print(f"📊 同步状态")
        print(f"   最后同步: {state.get('last_sync', '从未')}")
        print(f"   已同步文件: {len(synced)} 个")
        print()

        if synced:
            print("最近同步的文件：")
            sorted_files = sorted(
                synced.items(),
                key=lambda x: x[1].get("synced_at", ""),
                reverse=True
            )[:5]
            for f, info in sorted_files:
                print(f"   {Path(f).name} [{info.get('type', 'unknown')}]")
                print(f"      时间: {info.get('synced_at', 'N/A')}")
        return

    # 检查必要配置
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET or not FEISHU_FOLDER_TOKEN:
        print("❌ 飞书配置不完整")
        print("   请设置环境变量：")
        print("     export FEISHU_APP_ID='your_app_id'")
        print("     export FEISHU_APP_SECRET='your_app_secret'")
        print("     export FEISHU_FOLDER_TOKEN='your_folder_token'")
        return

    # 初始化同步器
    from sync_feishu import FeishuSync
    syncer = FeishuSync()
    syncer.get_tenant_access_token()

    # 初始化多维表格
    if args.init:
        print("📊 初始化多维表格...")
        if syncer.init_bitable():
            print("\n✅ 初始化成功！")
            print(f"   请添加环境变量: export FEISHU_BITABLE_TOKEN=\"{syncer.bitable_token}\"")
        else:
            print("❌ 初始化失败")
        return

    # 检查多维表格配置
    if not FEISHU_BITABLE_TOKEN:
        print("❌ 未配置 FEISHU_BITABLE_TOKEN")
        print("   请先运行: python sync.py --init")
        return

    syncer.bitable_token = FEISHU_BITABLE_TOKEN
    syncer.get_all_table_ids()

    state = load_sync_state()

    # 同步单个文件
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return

        print(f"📤 同步文件: {file_path.name}")
        if sync_file(file_path, syncer, state):
            save_sync_state(state)
            print("✅ 同步完成")
        else:
            print("❌ 同步失败")
        return

    # 同步所有文件
    if args.all:
        files = get_all_md_files()
        print(f"📤 强制同步所有文件 ({len(files)} 个)")
    else:
        files = get_new_files(state)
        if not files:
            print("✅ 没有新文件需要同步")
            return
        print(f"📤 同步新增/修改的文件 ({len(files)} 个)")

    success = 0
    for f in files:
        print(f"\n   📄 {f.name}")
        if sync_file(f, syncer, state):
            success += 1

    save_sync_state(state)
    print(f"\n✅ 同步完成: {success}/{len(files)} 成功")


if __name__ == "__main__":
    main()

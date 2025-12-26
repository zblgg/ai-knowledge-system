#!/usr/bin/env python3
"""
同步项目状态到飞书多维表格
"""
from pathlib import Path
from sync_feishu import FeishuSync, parse_projects_file, sync_to_feishu

# 项目状态文件路径
PROJECTS_FILE = Path(__file__).parent.parent.parent / "项目状态.md"


def main():
    print("📊 同步项目状态到飞书...")

    # 检查文件是否存在
    if not PROJECTS_FILE.exists():
        print(f"❌ 找不到项目状态文件: {PROJECTS_FILE}")
        return

    # 初始化飞书同步器
    syncer = FeishuSync()
    try:
        syncer.get_tenant_access_token()
        print("   ✓ 飞书连接成功")
    except Exception as e:
        print(f"❌ 飞书连接失败: {e}")
        return

    # 初始化多维表格（会自动创建项目状态表）
    if not syncer.init_bitable():
        print("❌ 初始化多维表格失败")
        return

    # 解析项目状态文件
    projects = parse_projects_file(PROJECTS_FILE)
    print(f"   📁 发现 {len(projects)} 个项目")

    # 同步每个项目
    success_count = 0
    for project in projects:
        if sync_to_feishu(syncer, "project", project):
            print(f"   ✓ {project['项目名']}")
            success_count += 1
        else:
            print(f"   ✗ {project['项目名']}")

    print(f"\n✅ 同步完成: {success_count}/{len(projects)} 个项目")
    print("   打开飞书多维表格即可查看")


if __name__ == "__main__":
    main()

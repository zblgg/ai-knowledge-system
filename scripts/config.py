"""
知识管理系统配置
"""
import os
from pathlib import Path

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).parent.parent
ARCHIVE_DIR = BASE_DIR / "对话归档"
THREADS_FILE = BASE_DIR / "线头追踪" / "THREADS.md"
KNOWLEDGE_DIR = BASE_DIR / "知识沉淀"
REVIEW_DIR = BASE_DIR / "复盘报告"

# ==================== 飞书配置 ====================
# 需要在飞书开放平台创建应用：https://open.feishu.cn/app
# 获取 App ID 和 App Secret
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 飞书云文档文件夹配置
# 在飞书云文档文件夹URL中找到 folder_token，例如：
# https://xxx.feishu.cn/drive/folder/XJuVfeEtDlHRAYdTKy7cqUdbncm
FEISHU_FOLDER_TOKEN = os.getenv("FEISHU_FOLDER_TOKEN", "")

# ==================== Notion配置 ====================
# 需要创建 Integration：https://www.notion.so/my-integrations
# 获取 Internal Integration Token
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")

# Notion 数据库ID
# 在数据库页面URL中找到，例如：
# https://www.notion.so/xxxxx?v=yyyyy 中的 xxxxx 部分
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# ==================== 同步配置 ====================
SYNC_TARGETS = {
    "feishu": bool(FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_FOLDER_TOKEN),
    "notion": bool(NOTION_API_KEY and NOTION_DATABASE_ID),
}

def check_config():
    """检查配置是否完整"""
    issues = []

    if not FEISHU_APP_ID:
        issues.append("未配置 FEISHU_APP_ID")
    if not FEISHU_APP_SECRET:
        issues.append("未配置 FEISHU_APP_SECRET")
    if not NOTION_API_KEY:
        issues.append("未配置 NOTION_API_KEY")
    if not NOTION_DATABASE_ID:
        issues.append("未配置 NOTION_DATABASE_ID")

    return issues

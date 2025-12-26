"""
Notion同步模块
将知识管理系统的内容同步到Notion数据库
"""
import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from config import NOTION_API_KEY, NOTION_DATABASE_ID

class NotionSync:
    """Notion同步器"""

    BASE_URL = "https://api.notion.com/v1"
    VERSION = "2022-06-28"

    def __init__(self):
        self.api_key = NOTION_API_KEY
        self.database_id = NOTION_DATABASE_ID

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.VERSION
        }

    def create_page(self, title: str, content: str, tags: List[str] = None,
                    date: str = None, summary: str = None) -> Optional[str]:
        """
        在Notion数据库中创建页面

        Args:
            title: 页面标题
            content: Markdown内容
            tags: 标签列表
            date: 日期 (YYYY-MM-DD)
            summary: 一句话总结

        Returns:
            页面URL或None
        """
        url = f"{self.BASE_URL}/pages"

        # 构建属性
        properties = {
            "标题": {
                "title": [{"text": {"content": title}}]
            }
        }

        # 可选属性
        if date:
            properties["日期"] = {"date": {"start": date}}
        if tags:
            properties["标签"] = {"multi_select": [{"name": tag} for tag in tags]}
        if summary:
            properties["摘要"] = {"rich_text": [{"text": {"content": summary[:2000]}}]}

        # 转换内容为Notion块
        children = self._markdown_to_blocks(content)

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": children[:100]  # Notion限制100个块
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if "id" in data:
            page_url = data.get("url", f"https://notion.so/{data['id'].replace('-', '')}")
            print(f"✅ Notion页面已创建: {title}")
            return page_url
        else:
            print(f"❌ 创建Notion页面失败: {data}")
            return None

    def query_database(self, filter_dict: dict = None) -> List[dict]:
        """查询数据库"""
        url = f"{self.BASE_URL}/databases/{self.database_id}/query"
        payload = {}
        if filter_dict:
            payload["filter"] = filter_dict

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()
        return data.get("results", [])

    def find_page_by_title(self, title: str) -> Optional[str]:
        """按标题查找页面"""
        results = self.query_database({
            "property": "标题",
            "title": {"equals": title}
        })
        if results:
            return results[0]["id"]
        return None

    def update_page(self, page_id: str, content: str) -> bool:
        """更新页面内容"""
        # 先删除现有块
        blocks_url = f"{self.BASE_URL}/blocks/{page_id}/children"
        resp = requests.get(blocks_url, headers=self._headers())
        existing_blocks = resp.json().get("results", [])

        for block in existing_blocks:
            delete_url = f"{self.BASE_URL}/blocks/{block['id']}"
            requests.delete(delete_url, headers=self._headers())

        # 添加新内容
        new_blocks = self._markdown_to_blocks(content)
        requests.patch(blocks_url, headers=self._headers(), json={
            "children": new_blocks[:100]
        })
        return True

    def _markdown_to_blocks(self, markdown: str) -> List[dict]:
        """
        将Markdown转换为Notion块

        支持：标题、列表、代码块、引用、分割线、普通文本
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 代码块
            if line.startswith('```'):
                lang = line[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                        "language": lang
                    }
                })
                i += 1
                continue

            # 标题
            if line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
                })
            elif line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
                })

            # 无序列表
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })

            # 有序列表
            elif re.match(r'^\d+\. ', line):
                content = re.sub(r'^\d+\. ', '', line)
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}
                })

            # 待办事项
            elif line.startswith('- [ ] ') or line.startswith('- [x] '):
                checked = line.startswith('- [x] ')
                content = line[6:]
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": content}}],
                        "checked": checked
                    }
                })

            # 引用
            elif line.startswith('> '):
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })

            # 分割线
            elif line.strip() in ['---', '***', '___']:
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })

            # 表格（简化处理，转为代码块）
            elif '|' in line and line.strip().startswith('|'):
                table_lines = [line]
                i += 1
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(table_lines)}}],
                        "language": "plain text"
                    }
                })
                continue

            # 普通段落
            elif line.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                })

            i += 1

        return blocks


def sync_file_to_notion(file_path: Path, tags: List[str] = None) -> Optional[str]:
    """
    同步单个Markdown文件到Notion

    Args:
        file_path: Markdown文件路径
        tags: 标签列表

    Returns:
        Notion页面URL或None
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("❌ 未配置Notion API凭据，跳过Notion同步")
        return None

    syncer = NotionSync()

    title = file_path.stem
    content = file_path.read_text(encoding="utf-8")

    # 尝试从内容中提取元信息
    date_match = re.search(r'\*\*日期\*\*[：:]\s*(\d{4}-\d{2}-\d{2})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

    summary_match = re.search(r'## 一句话总结\n+(.+)', content)
    summary = summary_match.group(1).strip() if summary_match else None

    tag_match = re.search(r'\*\*主题标签\*\*[：:]\s*(.+)', content)
    if tag_match and not tags:
        tags = [t.strip().lstrip('#') for t in tag_match.group(1).split()]

    # 检查是否已存在
    existing_page = syncer.find_page_by_title(title)
    if existing_page:
        print(f"📝 更新已存在的页面: {title}")
        syncer.update_page(existing_page, content)
        return f"https://notion.so/{existing_page.replace('-', '')}"

    return syncer.create_page(title, content, tags, date, summary)


if __name__ == "__main__":
    from config import check_config
    issues = check_config()
    if "NOTION_API_KEY" in str(issues):
        print("请先配置Notion API凭据")
        print("1. 访问 https://www.notion.so/my-integrations 创建Integration")
        print("2. 复制 Internal Integration Token")
        print("3. 在Notion中创建数据库，添加以下属性：")
        print("   - 标题 (title)")
        print("   - 日期 (date)")
        print("   - 标签 (multi_select)")
        print("   - 摘要 (rich_text)")
        print("4. 将Integration连接到该数据库")
        print("5. 设置环境变量 NOTION_API_KEY 和 NOTION_DATABASE_ID")
    else:
        print("Notion配置正常")

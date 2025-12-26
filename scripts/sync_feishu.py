"""
飞书同步模块
将知识管理系统的内容同步到飞书多维表格
"""
import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import os

from config import FEISHU_APP_ID, FEISHU_APP_SECRET

# 飞书云文档文件夹 Token
FEISHU_FOLDER_TOKEN = os.getenv("FEISHU_FOLDER_TOKEN", "")
# 飞书多维表格 Token（首次运行后会自动创建并保存）
FEISHU_BITABLE_TOKEN = os.getenv("FEISHU_BITABLE_TOKEN", "")


class FeishuSync:
    """飞书同步器（多维表格版）"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    # 表格配置
    TABLES_CONFIG = {
        "threads": {
            "name": "线头追踪",
            "fields": [
                {"field_name": "标题", "type": 1},  # 文本
                {"field_name": "分类", "type": 3, "property": {"options": [
                    {"name": "待跟进事项"},
                    {"name": "未成型想法"},
                    {"name": "待验证假设"},
                    {"name": "技术债务"},
                    {"name": "其他"}
                ]}},
                {"field_name": "状态", "type": 3, "property": {"options": [
                    {"name": "待处理"},
                    {"name": "进行中"},
                    {"name": "已完成"},
                    {"name": "搁置"}
                ]}},
                {"field_name": "优先级", "type": 3, "property": {"options": [
                    {"name": "高"},
                    {"name": "中"},
                    {"name": "低"}
                ]}},
                {"field_name": "内容", "type": 1},  # 文本
                {"field_name": "来源", "type": 1},  # 文本
                {"field_name": "创建时间", "type": 5},  # 日期
            ]
        },
        "archives": {
            "name": "对话归档",
            "fields": [
                {"field_name": "日期", "type": 5},  # 日期
                {"field_name": "主题", "type": 1},  # 文本
                {"field_name": "一句话总结", "type": 1},  # 文本
                {"field_name": "标签", "type": 4, "property": {"options": []}},  # 多选
                {"field_name": "核心洞见", "type": 1},  # 文本
                {"field_name": "待跟进数", "type": 2},  # 数字
                {"field_name": "详情链接", "type": 15},  # 链接
            ]
        },
        "knowledge": {
            "name": "知识沉淀",
            "fields": [
                {"field_name": "标题", "type": 1},  # 文本
                {"field_name": "类型", "type": 3, "property": {"options": [
                    {"name": "方法论"},
                    {"name": "SOP"},
                    {"name": "洞见"},
                    {"name": "其他"}
                ]}},
                {"field_name": "摘要", "type": 1},  # 文本
                {"field_name": "创建时间", "type": 5},  # 日期
                {"field_name": "详情链接", "type": 15},  # 链接
            ]
        },
        "projects": {
            "name": "项目状态",
            "fields": [
                {"field_name": "项目名", "type": 1},  # 文本
                {"field_name": "状态", "type": 3, "property": {"options": [
                    {"name": "运行中"},
                    {"name": "可用"},
                    {"name": "开发中"},
                    {"name": "待验证"},
                    {"name": "暂停"}
                ]}},
                {"field_name": "最近修改", "type": 1},  # 文本
                {"field_name": "Git提交数", "type": 1},  # 文本
                {"field_name": "待办", "type": 1},  # 文本
                {"field_name": "更新时间", "type": 5},  # 日期
            ]
        }
    }

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.folder_token = FEISHU_FOLDER_TOKEN
        self.bitable_token = FEISHU_BITABLE_TOKEN
        self.access_token = None
        self.table_ids = {}  # 缓存表格ID

    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret
        })
        data = resp.json()
        if data.get("code") == 0:
            self.access_token = data["tenant_access_token"]
            return self.access_token
        else:
            raise Exception(f"获取飞书token失败: {data}")

    def _headers(self) -> dict:
        """请求头"""
        if not self.access_token:
            self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    # ==================== 多维表格操作 ====================

    def create_bitable(self, name: str = "AI知识管理") -> Optional[str]:
        """创建多维表格"""
        url = f"{self.BASE_URL}/bitable/v1/apps"
        payload = {
            "name": name,
            "folder_token": self.folder_token
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if data.get("code") == 0:
            app_token = data["data"]["app"]["app_token"]
            self.bitable_token = app_token
            print(f"   ✓ 创建多维表格成功: {name}")
            print(f"   📋 表格Token: {app_token}")
            return app_token
        else:
            print(f"   ✗ 创建多维表格失败: {data.get('msg', data)}")
            return None

    def create_table(self, table_key: str) -> Optional[str]:
        """在多维表格中创建数据表"""
        if not self.bitable_token:
            print("   ✗ 未设置多维表格Token")
            return None

        config = self.TABLES_CONFIG.get(table_key)
        if not config:
            print(f"   ✗ 未知的表格类型: {table_key}")
            return None

        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables"
        payload = {
            "table": {
                "name": config["name"],
                "default_view_name": "表格视图",
                "fields": config["fields"]
            }
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if data.get("code") == 0:
            table_id = data["data"]["table_id"]
            self.table_ids[table_key] = table_id
            print(f"   ✓ 创建数据表成功: {config['name']}")
            return table_id
        elif data.get("code") == 1254043:  # 表名已存在
            # 获取已存在的表
            return self.get_table_id_by_name(config["name"])
        else:
            print(f"   ✗ 创建数据表失败: {data.get('msg', data)}")
            return None

    def get_table_id_by_name(self, name: str) -> Optional[str]:
        """根据表名获取表ID"""
        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables"
        resp = requests.get(url, headers=self._headers())
        data = resp.json()

        if data.get("code") == 0:
            for table in data.get("data", {}).get("items", []):
                if table.get("name") == name:
                    return table.get("table_id")
        return None

    def get_all_table_ids(self) -> Dict[str, str]:
        """获取所有数据表的ID"""
        if not self.bitable_token:
            return {}

        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables"
        resp = requests.get(url, headers=self._headers())
        data = resp.json()

        result = {}
        if data.get("code") == 0:
            for table in data.get("data", {}).get("items", []):
                name = table.get("name")
                table_id = table.get("table_id")
                # 映射表名到key
                for key, config in self.TABLES_CONFIG.items():
                    if config["name"] == name:
                        result[key] = table_id
                        break

        self.table_ids = result
        return result

    def add_record(self, table_key: str, fields: dict) -> Optional[str]:
        """添加记录到数据表"""
        table_id = self.table_ids.get(table_key)
        if not table_id:
            self.get_all_table_ids()
            table_id = self.table_ids.get(table_key)

        if not table_id:
            print(f"   ✗ 找不到数据表: {table_key}")
            return None

        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables/{table_id}/records"
        payload = {"fields": fields}

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if data.get("code") == 0:
            return data["data"]["record"]["record_id"]
        else:
            print(f"   ⚠ 添加记录失败: {data.get('msg', data)}")
            return None

    def search_record(self, table_key: str, field_name: str, value: str) -> Optional[dict]:
        """搜索记录"""
        table_id = self.table_ids.get(table_key)
        if not table_id:
            self.get_all_table_ids()
            table_id = self.table_ids.get(table_key)

        if not table_id:
            return None

        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables/{table_id}/records/search"
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [{
                    "field_name": field_name,
                    "operator": "is",
                    "value": [value]
                }]
            }
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            if items:
                return items[0]
        return None

    def update_record(self, table_key: str, record_id: str, fields: dict) -> bool:
        """更新记录"""
        table_id = self.table_ids.get(table_key)
        if not table_id:
            return False

        url = f"{self.BASE_URL}/bitable/v1/apps/{self.bitable_token}/tables/{table_id}/records/{record_id}"
        payload = {"fields": fields}

        resp = requests.put(url, headers=self._headers(), json=payload)
        data = resp.json()

        return data.get("code") == 0

    # ==================== 初始化 ====================

    def init_bitable(self) -> bool:
        """初始化多维表格（创建表格和数据表）"""
        print("📊 初始化飞书多维表格...")

        # 1. 检查是否已有多维表格
        if self.bitable_token:
            print(f"   使用已有表格: {self.bitable_token}")
            self.get_all_table_ids()
        else:
            # 创建新的多维表格
            if not self.create_bitable():
                return False

        # 2. 创建数据表
        for table_key in self.TABLES_CONFIG:
            if table_key not in self.table_ids:
                self.create_table(table_key)

        # 3. 获取所有表ID
        self.get_all_table_ids()

        print(f"   ✓ 初始化完成，共 {len(self.table_ids)} 个数据表")
        return True

    # ==================== 云文档操作（用于长内容）====================

    def create_document(self, title: str, content: str) -> Optional[str]:
        """创建云文档"""
        if not self.folder_token:
            return None

        url = f"{self.BASE_URL}/docx/v1/documents"
        payload = {
            "folder_token": self.folder_token,
            "title": title
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if data.get("code") == 0:
            document_id = data["data"]["document"]["document_id"]
            # 写入内容
            self._write_docx_content(document_id, content)
            return f"https://sn17sqmzhd.feishu.cn/docx/{document_id}"
        return None

    def _write_docx_content(self, document_id: str, content: str):
        """写入文档内容"""
        blocks = self._markdown_to_blocks(content)
        if not blocks:
            return

        batch_url = f"{self.BASE_URL}/docx/v1/documents/{document_id}/blocks/{document_id}/children"

        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            requests.post(batch_url, headers=self._headers(), json={
                "children": batch,
                "index": -1
            })

    def _markdown_to_blocks(self, markdown: str) -> list:
        """将Markdown转换为飞书文档块

        正确的 block_type 值：
        - 2: text (文本)
        - 3: heading1
        - 4: heading2
        - 5: heading3
        - 12: bullet (无序列表)
        - 13: ordered (有序列表)
        - 14: code (代码块)
        - 19: quote (引用)
        - 22: divider (分割线)
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            if not line.strip():
                i += 1
                continue

            # 代码块
            if line.strip().startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                code_content = '\n'.join(code_lines)
                if code_content.strip():
                    blocks.append({
                        "block_type": 14,
                        "code": {
                            "elements": [{"text_run": {"content": code_content}}],
                            "language": 1
                        }
                    })
                i += 1
                continue

            # 标题
            if line.startswith('# '):
                text = line[2:].strip()
                if text:
                    blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": text}}]}})
            elif line.startswith('## '):
                text = line[3:].strip()
                if text:
                    blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": text}}]}})
            elif line.startswith('### '):
                text = line[4:].strip()
                if text:
                    blocks.append({"block_type": 5, "heading3": {"elements": [{"text_run": {"content": text}}]}})
            # 无序列表
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                content = line.strip()[2:].strip()
                # 处理 checkbox
                if content.startswith('[ ]') or content.startswith('[x]'):
                    content = content[3:].strip()
                if content:
                    blocks.append({"block_type": 12, "bullet": {"elements": [{"text_run": {"content": content}}]}})
            # 有序列表
            elif line.strip() and line.strip()[0].isdigit() and '. ' in line:
                content = line.split('. ', 1)[1].strip() if '. ' in line else line.strip()
                if content:
                    blocks.append({"block_type": 13, "ordered": {"elements": [{"text_run": {"content": content}}]}})
            # 引用
            elif line.strip().startswith('> '):
                content = line.strip()[2:].strip()
                if content:
                    blocks.append({"block_type": 19, "quote": {"elements": [{"text_run": {"content": content}}]}})
            # 分割线
            elif line.strip() in ['---', '***', '___']:
                blocks.append({"block_type": 22, "divider": {}})
            # 表格行 - 转为普通文本
            elif '|' in line.strip():
                # 跳过表格分隔行
                if line.strip().replace('|', '').replace('-', '').replace(' ', '') == '':
                    pass
                else:
                    # 表格内容转为文本
                    cells = [c.strip() for c in line.strip().split('|') if c.strip()]
                    if cells:
                        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": ' | '.join(cells)}}]}})
            # 普通文本
            elif line.strip():
                blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line.strip()}}]}})

            i += 1

        return blocks


# ==================== 解析函数 ====================

def parse_threads_file(file_path: Path) -> List[dict]:
    """解析线头追踪文件，提取线头列表（支持表格和列表格式）"""
    content = file_path.read_text(encoding="utf-8")
    threads = []

    current_category = "其他"
    in_table = False
    table_headers = []

    for line in content.split('\n'):
        line_stripped = line.strip()

        # 识别分类标题
        if line_stripped.startswith('## '):
            category = line_stripped[3:].strip()
            if '待跟进' in category:
                current_category = "待跟进事项"
            elif '想法' in category or '未成型' in category:
                current_category = "未成型想法"
            elif '假设' in category or '验证' in category:
                current_category = "待验证假设"
            elif '深挖' in category or '问题' in category:
                current_category = "待跟进事项"
            elif '完成' in category or '放弃' in category:
                current_category = "已完成"
            else:
                current_category = "其他"
            in_table = False
            table_headers = []

        # 识别表格头
        elif '|' in line_stripped and ('日期' in line_stripped or '事项' in line_stripped or '想法' in line_stripped or '假设' in line_stripped or '问题' in line_stripped):
            in_table = True
            # 解析表头
            table_headers = [h.strip() for h in line_stripped.split('|') if h.strip()]

        # 跳过表格分隔行
        elif line_stripped.startswith('|') and '---' in line_stripped:
            continue

        # 解析表格数据行
        elif in_table and line_stripped.startswith('|') and '|' in line_stripped:
            cells = [c.strip() for c in line_stripped.split('|') if c.strip()]
            if len(cells) >= 2 and cells[0] and cells[1]:  # 至少有日期和内容
                # 跳过空行
                if all(c == '' or c == '|' for c in cells):
                    continue

                date_str = cells[0] if cells[0] else datetime.now().strftime("%Y-%m-%d")
                title = cells[1] if len(cells) > 1 else ""
                source = cells[2] if len(cells) > 2 else ""
                next_action = cells[3] if len(cells) > 3 else ""
                priority = cells[4] if len(cells) > 4 else "中"

                if not title:
                    continue

                # 标准化优先级
                if '高' in str(priority):
                    priority = "高"
                elif '低' in str(priority):
                    priority = "低"
                else:
                    priority = "中"

                threads.append({
                    "标题": title,
                    "分类": current_category,
                    "状态": "待处理" if current_category != "已完成" else "已完成",
                    "优先级": priority,
                    "内容": f"{title}\n下一步: {next_action}" if next_action else title,
                    "来源": source,
                    "创建时间": date_str
                })

        # 识别 checkbox 格式的线头条目
        elif line_stripped.startswith('- [ ]') or line_stripped.startswith('- [x]'):
            is_done = line_stripped.startswith('- [x]')
            item_content = line_stripped[5:].strip()

            title = item_content
            source = ""

            if '（来自' in item_content or '(来自' in item_content:
                match = re.search(r'[（(]来自[：:]?\s*(.+?)[）)]', item_content)
                if match:
                    source = match.group(1)
                    title = re.sub(r'[（(]来自.+?[）)]', '', item_content).strip()

            threads.append({
                "标题": title,
                "分类": current_category,
                "状态": "已完成" if is_done else "待处理",
                "优先级": "中",
                "内容": item_content,
                "来源": source,
                "创建时间": datetime.now().strftime("%Y-%m-%d")
            })

    return threads


def parse_archive_file(file_path: Path) -> dict:
    """解析对话归档文件，提取元信息"""
    content = file_path.read_text(encoding="utf-8")

    result = {
        "日期": None,
        "主题": file_path.stem,
        "一句话总结": "",
        "标签": [],
        "核心洞见": "",
        "待跟进数": 0
    }

    lines = content.split('\n')
    in_summary = False
    in_insights = False
    insights = []

    for line in lines:
        line_stripped = line.strip()

        # 提取日期
        if line_stripped.startswith('**日期**') or line_stripped.startswith('日期：'):
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
            if date_match:
                result["日期"] = date_match.group(1)

        # 提取标签 - 只匹配包含"标签"的行，避免匹配普通标题
        if '标签' in line and '#' in line:
            tags = re.findall(r'#([^\s#]+)', line)  # 匹配 # 后的非空白非#字符
            if tags:
                result["标签"] = tags

        # 提取一句话总结
        if '一句话总结' in line:
            in_summary = True
            continue
        if in_summary and line_stripped and not line_stripped.startswith('#') and not line_stripped.startswith('---'):
            result["一句话总结"] = line_stripped
            in_summary = False

        # 提取核心洞见
        if '核心洞见' in line:
            in_insights = True
            continue
        if in_insights:
            # 只有 ## 开头但不是 ### 开头才结束洞见区域
            if line_stripped.startswith('---'):
                in_insights = False
            elif line_stripped.startswith('## ') and not line_stripped.startswith('###'):
                in_insights = False
            elif line_stripped.startswith('###'):
                # 提取洞见标题，去掉序号
                insight_text = line_stripped[3:].strip()
                # 移除开头的数字和点
                insight_text = re.sub(r'^\d+\.\s*', '', insight_text)
                if insight_text:
                    insights.append(insight_text)

        # 统计待跟进数
        if line_stripped.startswith('- [ ]'):
            result["待跟进数"] += 1

    result["核心洞见"] = '\n'.join(insights[:3])  # 最多3条

    # 如果没有日期，从文件名提取
    if not result["日期"]:
        date_match = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', file_path.stem)
        if date_match:
            result["日期"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        else:
            result["日期"] = datetime.now().strftime("%Y-%m-%d")

    return result


def parse_projects_file(file_path: Path) -> List[dict]:
    """解析项目状态文件"""
    content = file_path.read_text(encoding="utf-8")
    projects = []

    current_project = None

    for line in content.split('\n'):
        line_stripped = line.strip()

        # 识别项目标题
        if line_stripped.startswith('## ') and not line_stripped.startswith('## 自动') and not line_stripped.startswith('## 主动'):
            if current_project:
                projects.append(current_project)
            current_project = {
                "项目名": line_stripped[3:].strip(),
                "状态": "-",
                "最近修改": "-",
                "Git提交数": "-",
                "待办": "无"
            }

        # 解析项目属性
        elif current_project and line_stripped.startswith('- **'):
            if '状态' in line_stripped:
                match = re.search(r'状态.*?：(.+)$', line_stripped)
                if match:
                    current_project["状态"] = match.group(1).strip()
            elif '最近修改' in line_stripped:
                match = re.search(r'最近修改.*?：(.+)$', line_stripped)
                if match:
                    current_project["最近修改"] = match.group(1).strip()
            elif 'Git' in line_stripped:
                match = re.search(r'Git.*?：(.+)$', line_stripped)
                if match:
                    current_project["Git提交数"] = match.group(1).strip()
            elif '待办' in line_stripped:
                match = re.search(r'待办.*?：(.+)$', line_stripped)
                if match:
                    current_project["待办"] = match.group(1).strip()

    # 添加最后一个项目
    if current_project:
        projects.append(current_project)

    return projects


# ==================== 同步函数 ====================

def date_to_timestamp(date_str: str) -> int:
    """将日期字符串转换为毫秒时间戳"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except:
        return int(datetime.now().timestamp() * 1000)


def sync_to_feishu(syncer: FeishuSync, content_type: str, data: dict, doc_url: str = None) -> bool:
    """同步数据到飞书多维表格"""

    if content_type == "thread":
        # 转换日期格式
        fields = {
            "标题": data["标题"],
            "分类": data["分类"],
            "状态": data["状态"],
            "优先级": data["优先级"],
            "内容": data["内容"],
            "来源": data["来源"],
            "创建时间": date_to_timestamp(data.get("创建时间", datetime.now().strftime("%Y-%m-%d")))
        }

        # 检查是否已存在
        existing = syncer.search_record("threads", "标题", data["标题"])
        if existing:
            syncer.update_record("threads", existing["record_id"], fields)
            return True
        else:
            return syncer.add_record("threads", fields) is not None

    elif content_type == "archive":
        fields = {
            "日期": date_to_timestamp(data["日期"]),
            "主题": data["主题"],
            "一句话总结": data["一句话总结"],
            "核心洞见": data["核心洞见"],
            "待跟进数": data["待跟进数"],
        }
        if data["标签"]:
            fields["标签"] = data["标签"]
        if doc_url:
            fields["详情链接"] = {"link": doc_url, "text": "查看详情"}

        # 检查是否已存在
        existing = syncer.search_record("archives", "主题", data["主题"])
        if existing:
            syncer.update_record("archives", existing["record_id"], fields)
            return True
        else:
            return syncer.add_record("archives", fields) is not None

    elif content_type == "knowledge":
        fields = {
            "标题": data["标题"],
            "类型": data.get("类型", "其他"),
            "摘要": data.get("摘要", ""),
            "创建时间": int(datetime.now().timestamp() * 1000),
        }
        if doc_url:
            fields["详情链接"] = {"link": doc_url, "text": "查看详情"}

        existing = syncer.search_record("knowledge", "标题", data["标题"])
        if existing:
            syncer.update_record("knowledge", existing["record_id"], fields)
            return True
        else:
            return syncer.add_record("knowledge", fields) is not None

    elif content_type == "project":
        fields = {
            "项目名": data["项目名"],
            "状态": data["状态"],
            "最近修改": data["最近修改"],
            "Git提交数": data.get("Git提交数", "-"),
            "待办": data.get("待办", "无"),
            "更新时间": int(datetime.now().timestamp() * 1000),
        }

        existing = syncer.search_record("projects", "项目名", data["项目名"])
        if existing:
            syncer.update_record("projects", existing["record_id"], fields)
            return True
        else:
            return syncer.add_record("projects", fields) is not None

    return False


# ==================== 测试入口 ====================

if __name__ == "__main__":
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("请先配置飞书API凭据")
    elif not FEISHU_FOLDER_TOKEN:
        print("请先配置 FEISHU_FOLDER_TOKEN")
    else:
        print("✅ 配置正常，初始化多维表格...")
        syncer = FeishuSync()
        try:
            syncer.get_tenant_access_token()
            print("   ✓ Token获取成功")

            if syncer.init_bitable():
                print("\n✅ 多维表格初始化成功！")
                print(f"   表格Token: {syncer.bitable_token}")
                print(f"   数据表: {list(syncer.table_ids.keys())}")
                print("\n请将以下环境变量添加到 ~/.zshrc:")
                print(f'   export FEISHU_BITABLE_TOKEN="{syncer.bitable_token}"')
        except Exception as e:
            print(f"❌ 失败: {e}")

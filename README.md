# AI对话知识管理系统

解决AI对话散乱、线头丢失、跨AI不互通的问题。

## 核心功能

- **本地存储**：Markdown文件，任何AI都能读取
- **云端同步**：自动同步到飞书文档和Notion数据库
- **自动化**：通过Claude Code Skill自动归档和同步

## 系统结构

```
AI知识管理系统/
├── 对话归档/           # 每次重要对话的要点归档
│   └── 2025-12/
│       └── 1225_合伙人裂变计划.md
├── 线头追踪/           # 未完成的想法、待跟进的事项
│   └── THREADS.md      # 所有活跃线头
├── 知识沉淀/           # 沉淀下来的方法论、SOP、洞见
│   ├── 方法论/
│   ├── SOP/
│   └── INDEX.md
├── 复盘报告/           # 周报、月报
│   └── 2025-12_第4周复盘.md
└── scripts/            # 自动化脚本
    ├── sync.py         # 统一同步入口
    ├── sync_feishu.py  # 飞书同步
    ├── sync_notion.py  # Notion同步
    └── SETUP.md        # 配置指南
```

## 使用方式

### 1. 对话结束时归档

对话结束前，对AI说：
> "帮我归档这次对话的要点"

或使用快捷命令：
> "/archive"

### 2. 记录线头

发现未完成的想法时，说：
> "把这个加到线头追踪：[内容]"

或直接编辑 `线头追踪/THREADS.md`

### 3. 沉淀知识

当对话产出了有价值的方法论/SOP/洞见时，说：
> "把这个沉淀到知识库"

### 4. 定期复盘

每周/每月，说：
> "帮我生成本周/本月的对话复盘"

## 跨AI使用

这套系统的核心是**用Markdown文件作为通用格式**：
- Claude Code 可以直接读写
- ChatGPT 可以通过上传文件读取
- 其他AI可以通过复制粘贴使用
- 你自己用任何编辑器都能查看

## 云同步配置

### 飞书同步

```bash
# 设置环境变量
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
export FEISHU_FOLDER_TOKEN="your_folder_token"
```

详细配置见 [scripts/SETUP.md](scripts/SETUP.md)

### Notion同步

```bash
# 设置环境变量
export NOTION_API_KEY="your_api_key"
export NOTION_DATABASE_ID="your_database_id"
```

详细配置见 [scripts/SETUP.md](scripts/SETUP.md)

### 同步命令

```bash
cd scripts

# 同步新增文件
python3 sync.py

# 同步单个文件
python3 sync.py --file "../对话归档/2025-12/xxx.md"

# 查看同步状态
python3 sync.py --status
```

或者直接对Claude说：
> "帮我同步知识库到云端"

## 手机端与电脑端协同

本系统支持手机端和电脑端 Claude Code 协同工作：

### 原理

```
手机 Claude Code ──归档对话──▶ 飞书多维表格 ◀──归档对话── 电脑 Claude Code
                                    │
                                    ▼
                              统一查看/管理
```

### 手机端设置

1. **克隆仓库**：
   ```bash
   git clone https://github.com/zblgg/ai-knowledge-system.git
   cd ai-knowledge-system
   ```

2. **配置环境变量**（在 ~/.env 中添加）：
   ```bash
   export FEISHU_APP_ID="your_app_id"
   export FEISHU_APP_SECRET="your_app_secret"
   export FEISHU_BITABLE_TOKEN="your_bitable_token"
   ```

3. **使用方式**：
   - 对话结束时说：`/archive-conversation` 归档对话
   - 想知道之前做了什么：`/sync-context` 拉取飞书

### 拉取上下文

开始对话时，可以先拉取飞书状态了解之前做了什么：

```bash
cd scripts
python3 fetch_feishu.py --context
```

输出示例：
```
<feishu_context>
同步时间: 2025-12-26 21:00

待处理事项:
- [高] 完成 partner-evaluation-v2 开发 (来源: 项目规划)

最近对话记录:
- 2025-12-26: 飞书监控配置
  摘要: 配置了知识库监控，自动推送到新群
</feishu_context>
```

## 快速开始

1. 把这个目录加到你的常用工作区
2. 配置飞书/Notion的API凭据（见 scripts/SETUP.md）
3. 养成对话结束时说"归档对话"的习惯
4. 每周说"生成周报"做复盘

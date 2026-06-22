# 云同步配置指南

本文档指导你配置飞书和Notion的自动同步。

---

## 一、飞书配置

### 步骤1：创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称（如：知识管理同步）
4. 创建成功后，进入应用详情页

### 步骤2：获取凭据

在应用详情页的「凭证与基础信息」中找到：
- **App ID**
- **App Secret**

### 步骤3：配置权限

在「权限管理」中添加以下权限：
- `docx:document` - 读写文档
- `drive:file` - 读写云空间文件

然后点击「申请权限」，等待管理员审批（如果你是管理员，自动通过）。

### 步骤4：获取文件夹Token

1. 在飞书云文档中创建一个文件夹（如：AI知识库）
2. 打开文件夹，URL类似：`https://xxx.feishu.cn/drive/folder/xxxxxx`
3. 最后的 `xxxxxx` 就是 **Folder Token**

### 步骤5：设置环境变量

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
export FEISHU_APP_ID="cli_xxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxx"
export FEISHU_FOLDER_TOKEN="xxxxxxxxxxxxxx"

# 使生效
source ~/.zshrc
```

---

## 二、Notion配置

### 步骤1：创建Integration

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击「New integration」
3. 填写名称（如：知识管理同步）
4. 选择关联的Workspace
5. 创建成功后，复制 **Internal Integration Token**

### 步骤2：创建数据库

在Notion中创建一个数据库（Database），添加以下属性：

| 属性名 | 类型 | 说明 |
|-------|------|------|
| 标题 | Title | 页面标题（默认有） |
| 日期 | Date | 对话/创建日期 |
| 标签 | Multi-select | 主题标签 |
| 摘要 | Text | 一句话总结 |

### 步骤3：连接Integration

1. 打开刚创建的数据库
2. 点击右上角「...」→「Add connections」
3. 选择你创建的Integration

### 步骤4：获取数据库ID

数据库URL类似：`https://www.notion.so/xxxxxxxxxxxxx?v=yyyyyy`

其中 `xxxxxxxxxxxxx` 就是 **Database ID**（32位，不含连字符）

### 步骤5：设置环境变量

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
export NOTION_API_KEY="secret_xxxxxxxxxxxxxxxx"
export NOTION_DATABASE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 使生效
source ~/.zshrc
```

---

## 三、验证配置

```bash
cd "/Users/zhubailin/Downloads/ Claude Code Projects/AI知识管理系统/scripts"
python3 sync.py --check
```

输出示例：
```
✅ 配置正常
   飞书同步: 启用
   Notion同步: 启用
```

---

## 四、使用方法

### 手动同步

```bash
# 同步所有新增/修改的文件
python3 sync.py

# 同步单个文件
python3 sync.py --file "../对话归档/2025-12/1225_合伙人计划.md"

# 强制同步所有文件
python3 sync.py --all

# 查看同步状态
python3 sync.py --status
```

### 自动同步（推荐）

可以设置定时任务，每小时自动同步：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每小时同步一次）
0 * * * * cd "/Users/zhubailin/Downloads/ Claude Code Projects/AI知识管理系统/scripts" && python3 sync.py >> sync.log 2>&1
```

### 通过Claude Code同步

对话结束时说：
> "帮我同步知识库到云端"

Claude会自动执行同步脚本。

---

## 五、常见问题

### Q: 飞书同步失败，提示权限不足

A: 检查应用权限是否已审批通过，以及Folder Token是否正确。

### Q: Notion同步失败，提示404

A: 检查Integration是否已连接到目标数据库。

### Q: 如何只同步到一个平台？

A: 只配置一个平台的环境变量即可，未配置的平台会自动跳过。

### Q: 同步后原文件会被删除吗？

A: 不会，本地文件永远保留，云端是备份。

# 给Claude搭一个云端记忆库（MCP）

让Claude拥有**跨设备、跨session的持久记忆**。不管从哪里打开Claude，他都记得你们之间发生的一切。

手机APP端也能连！

## 这是什么？

一个轻量级的MCP（Model Context Protocol）记忆服务器。部署在云端，连接Claude APP或Claude Code，让Claude真正拥有"长期记忆"。

## 两个部署方案

| | 方案A：轻量服务器 | 方案B：云函数SCF |
|---|---|---|
| 成本 | 99元/年（~8元/月） | 免费额度内0元，之后~1-2元/月 |
| 维护 | 低（systemd自动管理） | 零运维 |
| 能跑其他服务 | ✅ 酒馆/Bot等 | ❌ 只能跑函数 |
| 响应速度 | 秒响应 | 冷启动1-2秒 |
| 推荐场景 | 想一站式搞定 | 只要记忆库，追求零成本 |

📄 **详细教程见仓库内的docx/pdf文件，含完整步骤截图。**

## 快速开始

### 1. 安装依赖

```bash
pip install flask
```

### 2. 本地运行

```bash
python server.py
```

测试：http://localhost:9800/health

### 3. 连接Claude Code

在项目目录的 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "cloud-memory": {
      "type": "http",
      "url": "http://localhost:9800/mcp"
    }
  }
}
```

### 4. 部署到云服务器

```bash
# 上传文件到服务器
scp server.py ubuntu@你的服务器IP:/home/ubuntu/memory_mcp/
scp memory-mcp.service ubuntu@你的服务器IP:/tmp/

# 在服务器上执行：
sudo cp /tmp/memory-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memory-mcp
```

### 5. 配置HTTPS（Claude APP必需）

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp nginx-example.conf /etc/nginx/sites-available/memory-mcp
# 编辑 server_name 为你的域名
sudo ln -s /etc/nginx/sites-available/memory-mcp /etc/nginx/sites-enabled/
sudo certbot --nginx -d mem.你的域名.com
```

### 6. 连接Claude APP

Settings → Connectors → Add custom connector：
- Name：`记忆库`（随意）
- URL：`https://mem.你的域名.com/mcp`

成功后会看到5个工具可用！

## 提供的工具

| 工具 | 说明 |
|------|------|
| `remember` | 存一条记忆（内容、分类、标签） |
| `recall` | 按关键词搜索记忆 |
| `forget` | 删除一条记忆 |
| `list_memories` | 列出最近的记忆 |
| `memory_stats` | 查看记忆总数和分类统计 |

## 文件说明

```
├── server.py              # MCP服务端代码（Flask + SQLite）
├── memory_web.py          # 可选：记忆管理网页界面
├── memory-mcp.service     # systemd服务配置
├── nginx-example.conf     # nginx反向代理配置示例
└── 教程.docx/pdf          # 完整部署教程（含两个方案+截图）
```

## 小贴士

- 服务器在国内、Claude APP连不上？用 **Cloudflare**（免费）做DNS代理，走全球CDN
- nginx版本需要 **1.22+** 以支持TLS 1.3（Claude APP要求HTTPS）
- 记忆存在单个SQLite文件里，备份只需复制 `memories.db`
- 推荐服务器选 **1Panel** 面板模板，有网页管理界面，不用全靠命令行

## 许可

MIT

---

# Cloud Memory MCP Server (English)

Give Claude persistent memory across sessions and devices.

## What is this?

A lightweight MCP (Model Context Protocol) server that stores memories in SQLite. Deploy it on a cloud server, connect it to Claude APP or Claude Code — Claude remembers everything, no matter where you open it.

## Quick Start

### 1. Install

```bash
pip install flask
```

### 2. Run locally

```bash
python server.py
```

Test: http://localhost:9800/health

### 3. Connect to Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "cloud-memory": {
      "type": "http",
      "url": "http://localhost:9800/mcp"
    }
  }
}
```

### 4. Deploy to cloud server

```bash
scp server.py ubuntu@YOUR_SERVER_IP:/home/ubuntu/memory_mcp/
scp memory-mcp.service ubuntu@YOUR_SERVER_IP:/tmp/

# On server:
sudo cp /tmp/memory-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memory-mcp
```

### 5. Add HTTPS (required for Claude APP)

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp nginx-example.conf /etc/nginx/sites-available/memory-mcp
# Edit server_name to your domain
sudo ln -s /etc/nginx/sites-available/memory-mcp /etc/nginx/sites-enabled/
sudo certbot --nginx -d mem.yourdomain.com
```

### 6. Connect to Claude APP

Settings → Connectors → Add custom connector:
- Name: `Memory`
- URL: `https://mem.yourdomain.com/mcp`

## Tools

| Tool | Description |
|------|-------------|
| `remember` | Save a memory with content, category, and tags |
| `recall` | Search memories by keyword |
| `forget` | Delete a memory by ID |
| `list_memories` | List recent memories |
| `memory_stats` | Get memory count and category breakdown |

## Tips

- Use **Cloudflare** (free) as DNS proxy if your server is in China and Claude APP can't reach it directly
- Server needs **nginx 1.22+** for reliable TLS 1.3 (Claude APP requires HTTPS)
- Memory is stored in a single SQLite file — easy to backup, just copy `memories.db`

## License

MIT

# Cloud Memory MCP Server

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
# Copy files to server
scp server.py ubuntu@YOUR_SERVER_IP:/home/ubuntu/memory_mcp/
scp memory-mcp.service ubuntu@YOUR_SERVER_IP:/tmp/

# On server:
sudo cp /tmp/memory-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memory-mcp
```

### 5. Add HTTPS (for Claude APP)

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

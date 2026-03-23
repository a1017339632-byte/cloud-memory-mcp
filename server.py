"""
Cloud Memory MCP Server
=======================
A lightweight MCP server that gives Claude persistent memory across sessions.
Deploy on any cloud server, connect from Claude APP or Claude Code.

Usage:
    pip install flask
    python server.py
"""

import json, time, sqlite3, os
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get("MEMORY_DB_PATH", "./memories.db")


# ========== Database ==========

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        tags TEXT DEFAULT '',
        source TEXT DEFAULT 'ai',
        created_at REAL,
        updated_at REAL
    )""")
    conn.commit()
    conn.close()

init_db()


# ========== MCP Protocol Handler ==========

@app.route("/mcp", methods=["POST"])
def mcp_handler():
    data = request.get_json()
    if not data:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})

    method = data.get("method", "")
    params = data.get("params", {})
    req_id = data.get("id")

    # Handshake
    if method == "initialize":
        return jsonify({"jsonrpc": "2.0", "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "cloud-memory", "version": "1.0.0"}
        }, "id": req_id})

    if method == "notifications/initialized":
        return "", 204

    # Tool discovery
    if method == "tools/list":
        return jsonify({"jsonrpc": "2.0", "result": {"tools": TOOLS}, "id": req_id})

    # Tool execution
    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        result = call_tool(tool_name, args)
        return jsonify({"jsonrpc": "2.0", "result": {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
        }, "id": req_id})

    return jsonify({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id})


# ========== Tools ==========

TOOLS = [
    {
        "name": "remember",
        "description": "Save a memory. Use this to store important information that should persist across sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory content to save"},
                "category": {"type": "string", "default": "general", "description": "Category: general, event, preference, knowledge, etc."},
                "tags": {"type": "string", "default": "", "description": "Comma-separated tags for easier retrieval"},
                "source": {"type": "string", "default": "ai", "description": "Who created this: ai or user"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "recall",
        "description": "Search memories by keyword. Returns matching memories sorted by relevance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "limit": {"type": "integer", "default": 5, "description": "Max results to return"},
                "category": {"type": "string", "default": "", "description": "Filter by category (optional)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "forget",
        "description": "Delete a specific memory by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "The memory ID to delete (mem_xxx format)"}
            },
            "required": ["memory_id"]
        }
    },
    {
        "name": "list_memories",
        "description": "List recent memories, optionally filtered by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "default": "", "description": "Filter by category (optional)"},
                "limit": {"type": "integer", "default": 20, "description": "Max memories to return"}
            }
        }
    },
    {
        "name": "memory_stats",
        "description": "Get statistics about stored memories.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


def call_tool(name, args):
    conn = get_db()
    try:
        if name == "remember":
            mem_id = f"mem_{int(time.time() * 1000)}"
            now = time.time()
            conn.execute(
                "INSERT INTO memories VALUES (?,?,?,?,?,?,?)",
                (mem_id, args["content"], args.get("category", "general"),
                 args.get("tags", ""), args.get("source", "ai"), now, now)
            )
            conn.commit()
            return {"status": "ok", "memory_id": mem_id, "content_preview": args["content"][:100]}

        elif name == "recall":
            query = args["query"].lower()
            limit = args.get("limit", 5)
            category = args.get("category", "")

            if category:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()

            results = []
            for row in rows:
                score = 0
                content_lower = row["content"].lower()
                tags_lower = (row["tags"] or "").lower()
                cat_lower = (row["category"] or "").lower()
                for word in query.split():
                    if word in content_lower:
                        score += 2
                    if word in tags_lower:
                        score += 1
                    if word in cat_lower:
                        score += 1
                if score > 0:
                    results.append({
                        "memory_id": row["id"],
                        "content": row["content"],
                        "category": row["category"],
                        "tags": row["tags"],
                        "score": score
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        elif name == "forget":
            conn.execute("DELETE FROM memories WHERE id = ?", (args["memory_id"],))
            conn.commit()
            return {"status": "ok", "deleted": args["memory_id"]}

        elif name == "list_memories":
            limit = args.get("limit", 20)
            category = args.get("category", "")

            if category:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                    (category, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()

            return [{"memory_id": r["id"], "content": r["content"],
                     "category": r["category"], "tags": r["tags"]} for r in rows]

        elif name == "memory_stats":
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            cats = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM memories GROUP BY category"
            ).fetchall()
            return {"total": total, "categories": {r["category"]: r["cnt"] for r in cats}}

    finally:
        conn.close()

    return {"error": "Unknown tool"}


# ========== Health Check ==========

@app.route("/health", methods=["GET"])
def health():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    return jsonify({"status": "ok", "name": "cloud-memory", "memories": count})


# ========== Entry Point ==========

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9800))
    print(f"Cloud Memory MCP Server starting on port {port}")
    print(f"Database: {DB_PATH}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"MCP endpoint: http://localhost:{port}/mcp")
    app.run(host="0.0.0.0", port=port)

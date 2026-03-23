"""
琛屿记忆管理页面
================
煊煊专用。一个命令跑起来，浏览器打开就能折腾。

用法：python memory_web.py
然后浏览器开 http://localhost:9527
"""

import json
import time
from pathlib import Path
from flask import Flask, request, jsonify

import chromadb

# === 路径（和 memory_server.py 共用同一个数据库） ===
DB_PATH = str(Path(__file__).parent / "chenyu_memory_db")
COLLECTION_NAME = "chenyu_memories"

app = Flask(__name__)

# === ChromaDB 连接 ===
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


# === API 路由 ===

@app.route("/api/memories", methods=["GET"])
def list_memories():
    """列出所有记忆"""
    category = request.args.get("category", "")
    limit = int(request.args.get("limit", 100))

    if collection.count() == 0:
        return jsonify([])

    where = {"category": category} if category else None
    results = collection.get(
        limit=min(limit, collection.count()),
        where=where,
        include=["documents", "metadatas"]
    )

    memories = []
    for i in range(len(results["ids"])):
        memories.append({
            "id": results["ids"][i],
            "content": results["documents"][i],
            "category": results["metadatas"][i].get("category", ""),
            "tags": results["metadatas"][i].get("tags", ""),
            "source": results["metadatas"][i].get("source", ""),
            "created_at": results["metadatas"][i].get("created_at", ""),
        })

    memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(memories)


@app.route("/api/memories", methods=["POST"])
def add_memory():
    """添加记忆"""
    data = request.json
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "内容不能为空"}), 400

    memory_id = f"mem_{int(time.time() * 1000)}"
    metadata = {
        "category": data.get("category", "general"),
        "tags": data.get("tags", ""),
        "source": data.get("source", "human"),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(time.time()),
    }
    collection.add(
        documents=[content],
        metadatas=[metadata],
        ids=[memory_id]
    )
    return jsonify({"status": "ok", "id": memory_id})


@app.route("/api/memories/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    """编辑记忆"""
    data = request.json
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "内容不能为空"}), 400

    existing = collection.get(ids=[memory_id])
    if not existing["ids"]:
        return jsonify({"error": "记忆不存在"}), 404

    old_meta = existing["metadatas"][0] if existing["metadatas"] else {}
    metadata = {
        "category": data.get("category", old_meta.get("category", "general")),
        "tags": data.get("tags", old_meta.get("tags", "")),
        "source": old_meta.get("source", "human"),
        "created_at": old_meta.get("created_at", ""),
        "timestamp": old_meta.get("timestamp", 0),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    collection.update(
        ids=[memory_id],
        documents=[content],
        metadatas=[metadata]
    )
    return jsonify({"status": "ok"})


@app.route("/api/memories/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    """删除记忆"""
    existing = collection.get(ids=[memory_id])
    if not existing["ids"]:
        return jsonify({"error": "记忆不存在"}), 404

    collection.delete(ids=[memory_id])
    return jsonify({"status": "ok"})


@app.route("/api/search", methods=["GET"])
def search_memories():
    """语义搜索"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    if collection.count() == 0:
        return jsonify([])

    limit = int(request.args.get("limit", 10))
    results = collection.query(
        query_texts=[query],
        n_results=min(limit, collection.count())
    )

    memories = []
    if results and results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            memories.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "score": round(results["distances"][0][i], 4),
                "category": results["metadatas"][0][i].get("category", ""),
                "tags": results["metadatas"][0][i].get("tags", ""),
                "source": results["metadatas"][0][i].get("source", ""),
                "created_at": results["metadatas"][0][i].get("created_at", ""),
            })
    return jsonify(memories)


@app.route("/api/stats", methods=["GET"])
def stats():
    """统计"""
    total = collection.count()
    if total == 0:
        return jsonify({"total": 0, "categories": {}})

    all_data = collection.get(include=["metadatas"])
    categories = {}
    for meta in all_data["metadatas"]:
        cat = meta.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return jsonify({"total": total, "categories": categories})


# === 前端页面 ===

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>琛屿的记忆</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    min-height: 100vh;
}

/* 顶栏 */
.header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-bottom: 1px solid #2a2a4a;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header h1 {
    font-size: 20px;
    font-weight: 500;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header .stats {
    font-size: 13px;
    color: #888;
}

/* 搜索栏 */
.search-bar {
    padding: 16px 24px;
    display: flex;
    gap: 10px;
}
.search-bar input {
    flex: 1;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 10px 16px;
    color: #e0e0e0;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
}
.search-bar input:focus { border-color: #a78bfa; }
.search-bar input::placeholder { color: #555; }

.btn {
    padding: 8px 18px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}
.btn-primary {
    background: linear-gradient(135deg, #a78bfa, #818cf8);
    color: #fff;
}
.btn-primary:hover { opacity: 0.85; }
.btn-add {
    background: linear-gradient(135deg, #34d399, #2dd4bf);
    color: #0a0a0f;
}
.btn-add:hover { opacity: 0.85; }
.btn-danger {
    background: #ef4444;
    color: #fff;
    padding: 4px 12px;
    font-size: 12px;
}
.btn-danger:hover { background: #dc2626; }
.btn-edit {
    background: #3b82f6;
    color: #fff;
    padding: 4px 12px;
    font-size: 12px;
}
.btn-edit:hover { background: #2563eb; }
.btn-cancel {
    background: #555;
    color: #fff;
    padding: 4px 12px;
    font-size: 12px;
}

/* 分类过滤 */
.filters {
    padding: 0 24px 12px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.filter-tag {
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
    border: 1px solid #2a2a4a;
    background: #1a1a2e;
    color: #aaa;
    transition: all 0.2s;
}
.filter-tag.active {
    background: #a78bfa;
    color: #fff;
    border-color: #a78bfa;
}
.filter-tag:hover { border-color: #a78bfa; }

/* 记忆列表 */
.memory-list {
    padding: 0 24px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.memory-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    padding: 14px 18px;
    transition: border-color 0.2s;
}
.memory-card:hover { border-color: #3a3a5a; }
.memory-card .top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.memory-card .category {
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 12px;
    background: #2a2a4a;
    color: #a78bfa;
}
.memory-card .meta {
    font-size: 11px;
    color: #666;
    display: flex;
    gap: 12px;
}
.memory-card .content {
    font-size: 14px;
    line-height: 1.6;
    color: #d0d0d0;
    margin-bottom: 8px;
    white-space: pre-wrap;
    word-break: break-word;
}
.memory-card .tags {
    font-size: 12px;
    color: #888;
    margin-bottom: 8px;
}
.memory-card .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
}
.memory-card .score {
    font-size: 11px;
    color: #34d399;
    font-weight: 500;
}

/* 编辑模式 */
.memory-card.editing .content { display: none; }
.edit-area {
    display: none;
    margin-bottom: 8px;
}
.memory-card.editing .edit-area { display: block; }
.edit-area textarea {
    width: 100%;
    min-height: 80px;
    background: #0a0a0f;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 10px;
    color: #e0e0e0;
    font-size: 14px;
    font-family: inherit;
    resize: vertical;
    outline: none;
}
.edit-area textarea:focus { border-color: #a78bfa; }
.edit-row {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}
.edit-row input, .edit-row select {
    background: #0a0a0f;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e0e0e0;
    font-size: 13px;
    outline: none;
}
.edit-row select { cursor: pointer; }

/* 新增弹窗 */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 100;
    justify-content: center;
    align-items: center;
}
.modal-overlay.show { display: flex; }
.modal {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 24px;
    width: 480px;
    max-width: 90vw;
}
.modal h2 {
    font-size: 16px;
    margin-bottom: 16px;
    color: #a78bfa;
}
.modal label {
    font-size: 13px;
    color: #aaa;
    display: block;
    margin-bottom: 4px;
    margin-top: 12px;
}
.modal textarea, .modal input, .modal select {
    width: 100%;
    background: #0a0a0f;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 10px;
    color: #e0e0e0;
    font-size: 14px;
    font-family: inherit;
    outline: none;
}
.modal textarea { min-height: 100px; resize: vertical; }
.modal textarea:focus, .modal input:focus { border-color: #a78bfa; }
.modal .btn-row {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 20px;
}

/* 空状态 */
.empty {
    text-align: center;
    padding: 60px 20px;
    color: #555;
    font-size: 14px;
}

/* toast */
.toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #34d399;
    color: #0a0a0f;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 200;
}
.toast.show { opacity: 1; }
</style>
</head>
<body>

<div class="header">
    <h1>琛屿的记忆</h1>
    <div class="stats" id="stats"></div>
</div>

<div class="search-bar">
    <input type="text" id="searchInput" placeholder="语义搜索（按回车）...">
    <button class="btn btn-primary" onclick="doSearch()">搜索</button>
    <button class="btn btn-add" onclick="showAddModal()">+ 新记忆</button>
</div>

<div class="filters" id="filters"></div>
<div class="memory-list" id="memoryList"></div>

<!-- 新增弹窗 -->
<div class="modal-overlay" id="addModal">
    <div class="modal">
        <h2>存一条新记忆</h2>
        <label>内容</label>
        <textarea id="newContent" placeholder="写点什么..."></textarea>
        <label>分类</label>
        <select id="newCategory">
            <option value="general">general</option>
            <option value="preference">preference</option>
            <option value="event">event</option>
            <option value="conversation">conversation</option>
            <option value="fan_info">fan_info</option>
            <option value="quote">quote</option>
            <option value="knowledge">knowledge</option>
            <option value="other">other</option>
        </select>
        <label>标签（逗号分隔）</label>
        <input type="text" id="newTags" placeholder="奶茶, 偏好">
        <div class="btn-row">
            <button class="btn btn-cancel" onclick="hideAddModal()">取消</button>
            <button class="btn btn-add" onclick="addMemory()">保存</button>
        </div>
    </div>
</div>

<div class="toast" id="toast"></div>

<script>
let allMemories = [];
let currentFilter = "";
let isSearchMode = false;

// === API ===
async function api(path, opts = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    return res.json();
}

// === 加载 ===
async function loadMemories() {
    isSearchMode = false;
    allMemories = await api("/api/memories");
    render();
    loadStats();
}

async function loadStats() {
    const data = await api("/api/stats");
    document.getElementById("stats").textContent =
        `共 ${data.total} 条记忆`;

    // 渲染分类过滤器
    const cats = Object.entries(data.categories || {}).sort((a,b) => b[1] - a[1]);
    const el = document.getElementById("filters");
    let html = `<span class="filter-tag ${!currentFilter ? 'active' : ''}" onclick="setFilter('')">全部</span>`;
    for (const [cat, count] of cats) {
        html += `<span class="filter-tag ${currentFilter === cat ? 'active' : ''}" onclick="setFilter('${cat}')">${cat} (${count})</span>`;
    }
    el.innerHTML = html;
}

function setFilter(cat) {
    currentFilter = cat;
    render();
    loadStats();
}

// === 搜索 ===
async function doSearch() {
    const q = document.getElementById("searchInput").value.trim();
    if (!q) { loadMemories(); return; }
    isSearchMode = true;
    allMemories = await api(`/api/search?q=${encodeURIComponent(q)}&limit=20`);
    render();
}

document.getElementById("searchInput").addEventListener("keydown", e => {
    if (e.key === "Enter") doSearch();
});

// === 渲染 ===
function render() {
    const list = document.getElementById("memoryList");
    let items = allMemories;

    if (currentFilter && !isSearchMode) {
        items = items.filter(m => m.category === currentFilter);
    }

    if (items.length === 0) {
        list.innerHTML = `<div class="empty">${isSearchMode ? '没找到相关记忆' : '还没有记忆'}</div>`;
        return;
    }

    list.innerHTML = items.map(m => `
        <div class="memory-card" id="card-${m.id}">
            <div class="top">
                <div style="display:flex;gap:8px;align-items:center;">
                    <span class="category">${m.category || 'general'}</span>
                    ${m.score !== undefined ? `<span class="score">相似度: ${(1 - m.score).toFixed(2)}</span>` : ''}
                </div>
                <div class="meta">
                    <span>${m.source === 'ai' ? '琛屿存的' : '煊煊存的'}</span>
                    <span>${m.created_at || ''}</span>
                </div>
            </div>
            <div class="content">${escHtml(m.content)}</div>
            ${m.tags ? `<div class="tags">标签: ${escHtml(m.tags)}</div>` : ''}
            <div class="edit-area">
                <textarea>${escHtml(m.content)}</textarea>
                <div class="edit-row">
                    <select>
                        ${['general','preference','event','conversation','fan_info','quote','knowledge','other']
                            .map(c => `<option value="${c}" ${c === m.category ? 'selected' : ''}>${c}</option>`).join('')}
                    </select>
                    <input type="text" value="${escHtml(m.tags || '')}" placeholder="标签">
                    <button class="btn btn-add" onclick="saveEdit('${m.id}')">保存</button>
                    <button class="btn btn-cancel" onclick="cancelEdit('${m.id}')">取消</button>
                </div>
            </div>
            <div class="actions">
                <button class="btn btn-edit" onclick="startEdit('${m.id}')">编辑</button>
                <button class="btn btn-danger" onclick="deleteMemory('${m.id}')">删除</button>
            </div>
        </div>
    `).join("");
}

function escHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// === 编辑 ===
function startEdit(id) {
    document.getElementById(`card-${id}`).classList.add("editing");
}
function cancelEdit(id) {
    document.getElementById(`card-${id}`).classList.remove("editing");
}
async function saveEdit(id) {
    const card = document.getElementById(`card-${id}`);
    const content = card.querySelector(".edit-area textarea").value.trim();
    const category = card.querySelector(".edit-area select").value;
    const tags = card.querySelector(".edit-area input").value.trim();
    if (!content) return;

    await api(`/api/memories/${id}`, {
        method: "PUT",
        body: JSON.stringify({ content, category, tags }),
    });
    toast("已更新");
    loadMemories();
}

// === 删除 ===
async function deleteMemory(id) {
    if (!confirm("确定删除这条记忆？")) return;
    await api(`/api/memories/${id}`, { method: "DELETE" });
    toast("已删除");
    loadMemories();
}

// === 新增 ===
function showAddModal() { document.getElementById("addModal").classList.add("show"); }
function hideAddModal() {
    document.getElementById("addModal").classList.remove("show");
    document.getElementById("newContent").value = "";
    document.getElementById("newTags").value = "";
}

async function addMemory() {
    const content = document.getElementById("newContent").value.trim();
    if (!content) return;
    const category = document.getElementById("newCategory").value;
    const tags = document.getElementById("newTags").value.trim();

    await api("/api/memories", {
        method: "POST",
        body: JSON.stringify({ content, category, tags }),
    });
    hideAddModal();
    toast("已保存");
    loadMemories();
}

// === Toast ===
function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2000);
}

// 点击遮罩关闭弹窗
document.getElementById("addModal").addEventListener("click", e => {
    if (e.target === e.currentTarget) hideAddModal();
});

// === 初始化 ===
loadMemories();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("=" * 40)
    print("琛屿的记忆管理页面")
    print("打开浏览器访问: http://localhost:9527")
    print("按 Ctrl+C 关闭")
    print("=" * 40)
    app.run(host="127.0.0.1", port=9527, debug=False)

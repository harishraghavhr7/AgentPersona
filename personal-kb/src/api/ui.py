HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Personal Knowledge Base with Temporal Memory</title>
  <!-- Marked.js for fast, robust GitHub-flavored Markdown rendering -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {
      --bg: #0b0f19;
      --card: #151d2f;
      --card-hover: #1e293b;
      --border: #243147;
      --border-accent: rgba(56, 189, 248, 0.4);
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --active: #22c55e;
      --superseded: #f59e0b;
      --tag: #334155;
      --purple: #c084fc;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
    #sidebar { width: 340px; background: var(--card); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
    #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
    .panel-header { padding: 16px 20px; border-bottom: 1px solid var(--border); font-size: 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
    
    /* Badges */
    .badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; display: inline-flex; align-items: center; gap: 4px; }
    .badge-active { background: rgba(34, 197, 94, 0.15); color: var(--active); border: 1px solid var(--active); }
    .badge-superseded { background: rgba(245, 158, 11, 0.15); color: var(--superseded); border: 1px solid var(--superseded); }
    .badge-type { background: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid var(--accent); }
    .badge-provider { background: rgba(192, 132, 252, 0.15); color: var(--purple); border: 1px solid var(--purple); }
    .badge-sources { background: rgba(148, 163, 184, 0.15); color: var(--muted); border: 1px solid var(--border); }
    
    /* Document List & Timeline */
    #doc-list { flex: 1; overflow-y: auto; padding: 12px; }
    .doc-item { padding: 12px; background: rgba(11, 15, 25, 0.6); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; cursor: pointer; transition: 0.2s; }
    .doc-item:hover, .doc-item.selected { border-color: var(--accent); background: rgba(56, 189, 248, 0.05); }
    .doc-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #f1f5f9; }
    .doc-meta { font-size: 12px; color: var(--muted); }

    /* Ingestion box */
    .ingest-box { padding: 14px; border-top: 1px solid var(--border); background: var(--card); }
    .btn { background: var(--accent); color: #000; border: none; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s; }
    .btn:hover { background: var(--accent-hover); color: #fff; }
    .btn-secondary { background: var(--tag); color: var(--text); }
    .btn-secondary:hover { background: #475569; }

    /* Chat Area */
    #chat-container { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 24px; }
    .message { display: flex; flex-direction: column; gap: 6px; max-width: 90%; }
    .message.user { align-self: flex-end; }
    .message.user .bubble { background: #2563eb; color: #fff; border-radius: 14px 14px 2px 14px; }
    .message.assistant { align-self: flex-start; width: 100%; max-width: 900px; }
    .message.assistant .bubble { background: var(--card); border: 1px solid var(--border); border-radius: 14px 14px 14px 2px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.25); }
    .bubble { font-size: 14px; line-height: 1.6; }

    /* Response Header Badges */
    .response-header-badges { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); }

    /* Markdown Styling in Responses */
    .markdown-content h1, .markdown-content h2, .markdown-content h3 { color: #f8fafc; font-weight: 700; margin-top: 14px; margin-bottom: 8px; }
    .markdown-content h1 { font-size: 18px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
    .markdown-content h2 { font-size: 16px; }
    .markdown-content h3 { font-size: 14px; }
    .markdown-content p { margin-bottom: 12px; }
    .markdown-content ul, .markdown-content ol { padding-left: 20px; margin-bottom: 12px; }
    .markdown-content li { margin-bottom: 4px; }
    .markdown-content code { background: rgba(0, 0, 0, 0.35); padding: 2px 6px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: #38bdf8; }
    .markdown-content pre { background: #070a13; border: 1px solid var(--border); padding: 12px; border-radius: 6px; overflow-x: auto; margin-bottom: 12px; }
    .markdown-content pre code { background: none; padding: 0; color: #e2e8f0; }
    .markdown-content blockquote { border-left: 3px solid var(--accent); background: rgba(56, 189, 248, 0.05); padding: 10px 14px; margin: 14px 0; border-radius: 0 6px 6px 0; color: #cbd5e1; }
    
    /* Markdown Tables */
    .markdown-content table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }
    .markdown-content th, .markdown-content td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
    .markdown-content th { background: rgba(56, 189, 248, 0.08); color: var(--accent); font-weight: 600; }
    .markdown-content tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }

    /* Clickable Inline Citation Chips */
    .citation-ref {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 10px;
      padding: 1px 7px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      margin: 0 3px;
      line-height: 1.3;
      vertical-align: baseline;
      transition: all 0.2s ease;
    }
    .citation-ref:hover {
      background: var(--accent);
      color: #0b0f19;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.35);
    }

    /* Structured Source Cards Section */
    .sources-container { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }
    .sources-heading { font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
    .sources-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
    .source-card {
      background: rgba(11, 15, 25, 0.7);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .source-card:hover {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.05);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .source-card-main { display: flex; align-items: center; gap: 10px; overflow: hidden; }
    .source-card-id {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border-radius: 6px;
      padding: 2px 6px;
      font-size: 11px;
      font-weight: 700;
    }
    .source-card-info { overflow: hidden; }
    .source-card-filename { font-weight: 600; font-size: 13px; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .source-card-title { font-size: 11px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .source-card-arrow { color: var(--muted); font-size: 14px; margin-left: 8px; transition: transform 0.2s; }
    .source-card:hover .source-card-arrow { color: var(--accent); transform: translateX(3px); }

    /* Quick Queries & Input Bar */
    #input-bar { padding: 16px 24px; background: var(--card); border-top: 1px solid var(--border); }
    #presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .preset-btn { font-size: 11px; padding: 5px 12px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border); color: #cbd5e1; border-radius: 14px; cursor: pointer; transition: 0.2s; }
    .preset-btn:hover { background: var(--accent); color: #000; border-color: var(--accent); }
    .input-row { display: flex; gap: 10px; align-items: center; }
    #query-input { flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 12px 16px; border-radius: 8px; font-size: 14px; outline: none; }
    #query-input:focus { border-color: var(--accent); }
    .toggle-label { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; cursor: pointer; }

    /* Side Drawer: Source Details & History */
    #details-panel { position: absolute; right: 0; top: 0; width: 460px; height: 100%; background: var(--card); border-left: 1px solid var(--border); transform: translateX(100%); transition: 0.3s ease; display: flex; flex-direction: column; z-index: 10; box-shadow: -6px 0 24px rgba(0,0,0,0.6); }
    #details-panel.open { transform: translateX(0); }
    .details-content { flex: 1; overflow-y: auto; padding: 22px; }
    .meta-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; }
    .meta-label { color: var(--muted); }
    .meta-value { font-weight: 600; color: #f1f5f9; }
    .snippet-box { background: rgba(0,0,0,0.35); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-size: 13px; line-height: 1.5; color: #e2e8f0; margin-top: 14px; }
  </style>
</head>
<body>

  <!-- Left Sidebar: Tracked Knowledge Documents & Ingestion -->
  <div id="sidebar">
    <div class="panel-header">
      <span>Tracked Knowledge</span>
      <span id="health-indicator" class="badge badge-active">Online</span>
    </div>
    <div id="doc-list">
      <div style="color:var(--muted); font-size:13px; text-align:center; padding:20px;">Loading documents...</div>
    </div>
    <div class="ingest-box">
      <input type="file" id="sidebar-file-input" style="display:none;" accept=".doc,.docx,.pdf,.md,.markdown,.txt" onchange="handleFileSelected(event)">
      <button class="btn" style="width: 100%; margin-bottom: 8px;" onclick="runIngestion()">Scan & Sync Knowledge</button>
      <button class="btn btn-secondary" style="width: 100%; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 6px;" onclick="document.getElementById('sidebar-file-input').click()">
        📎 <span>Upload Document</span>
      </button>
      <button class="btn btn-secondary" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 6px;" onclick="openNoteModal()">
        📝 <span>Add Note / Task</span>
      </button>
      <div id="ingest-status" style="font-size:11px; color:var(--muted); margin-top:8px; text-align:center;"></div>
    </div>
  </div>

  <!-- Main Chat Area -->
  <div id="main">
    <div class="panel-header">
      <div>
        <span>Temporal Grounded RAG Assistant</span>
        <span style="font-size:12px; color:var(--muted); margin-left:10px;" id="llm-chain-badge">Groq &rarr; Gemini &rarr; OpenRouter</span>
      </div>
      <button class="btn btn-secondary" onclick="closeDetailsPanel()">✕ Close Panel</button>
    </div>

    <div id="chat-container">
      <div class="message assistant">
        <div class="bubble">
          <div class="markdown-content">
            <h1>Personal Knowledge Base with Temporal Memory</h1>
            <p>Welcome! I am your <strong>Grounded RAG Assistant</strong>. I answer questions strictly based on your personal knowledge base, with full temporal awareness, verified inline citations, and provenance tracking.</p>
            <ul>
              <li><strong>Chat Ingestion:</strong> Type <code>add today lists - complete ml -complete db</code>, <code>/todo ...</code>, <code>my current accomplishments: ...</code>, <code>store rule: ...</code>, or <code>note: ...</code> to record knowledge into your base directly from chat.</li>
              <li><strong>Upload & Chat:</strong> Click <strong>📎 Upload</strong> to ingest <code>.doc</code>, <code>.docx</code>, <code>.pdf</code>, <code>.md</code>, or <code>.txt</code> files and start questioning them immediately.</li>
              <li><strong>Quick Note:</strong> Click <strong>📝 Add Note</strong> to write and index notes or task lists instantly via form.</li>
              <li><strong>Clickable Citations:</strong> Click any citation like <code>[1]</code> or source card below to inspect provenance details.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Query Presets & Input Bar -->
    <div id="input-bar">
      <div id="presets">
        <button class="preset-btn" style="border-color: rgba(56, 189, 248, 0.4); color: #7dd3fc;" onclick="setQuery('add today lists - complete ml -complete db -practice leetcode')">📋 Add Today's Tasks</button>
        <button class="preset-btn" style="border-color: rgba(34, 197, 94, 0.4); color: #86efac;" onclick="setQuery('my current accomplishments: Completed LLM fallback chain (Groq->Gemini->OpenRouter) and Qdrant local fallback')">📝 Ingest Accomplishment</button>
        <button class="preset-btn" style="border-color: rgba(192, 132, 252, 0.4); color: #d8b4fe;" onclick="setQuery('store this rule: Production databases must use PostgreSQL; SQLite is reserved for temporary local testing')">📜 Store Project Rule</button>
        <button class="preset-btn" onclick="setQuery('What are my tasks for today?')">Today's Tasks</button>
        <button class="preset-btn" onclick="setQuery('What are my current accomplishments?')">My Accomplishments</button>
        <button class="preset-btn" onclick="setQuery('What is my current production database decision?')">Current Database</button>
        <button class="preset-btn" onclick="setQuery('What database did I use for the prototype?')">Prototype Database</button>
        <button class="preset-btn" onclick="setQuery('What vector database does the project use?')">Vector Database</button>
      </div>
      <div class="input-row">
        <input type="file" id="chat-file-input" style="display:none;" accept=".doc,.docx,.pdf,.md,.markdown,.txt" onchange="handleFileSelected(event)">
        <button class="btn btn-secondary" onclick="document.getElementById('chat-file-input').click()" title="Upload and vectorize document (.doc, .docx, .pdf, .md, .txt)" style="display:flex; align-items:center; gap:6px;">
          📎 <span>Upload</span>
        </button>
        <button class="btn btn-secondary" onclick="openNoteModal()" title="Add and index a note or task list" style="display:flex; align-items:center; gap:6px;">
          📝 <span>Add Note</span>
        </button>
        <input type="text" id="query-input" placeholder="Ask questions or type 'add today lists - ...', '/todo ...', 'note: ...' to ingest..." onkeydown="if(event.key==='Enter') sendQuery()">
        <label class="toggle-label">
          <input type="checkbox" id="debug-toggle"> Debug Info
        </label>
        <button class="btn" onclick="sendQuery()">Ask Assistant</button>
      </div>
    </div>

    <!-- Right Slide-out Drawer: Source Details & Provenance -->
    <div id="details-panel">
      <div class="panel-header">
        <span id="details-title">📄 Source Provenance</span>
        <button class="btn btn-secondary" onclick="closeDetailsPanel()">✕</button>
      </div>
      <div class="details-content" id="details-body">
        <div style="color:var(--muted); font-size:13px; text-align:center; padding:30px;">Select a citation [1] or source card to view grounded provenance.</div>
      </div>
    </div>
  </div>

  <script>
    const API_BASE = "";
    // Store message citations in memory for interactive drawer access
    const messageCitations = {};

    // Configure marked options
    if (window.marked) {
      marked.setOptions({
        gfm: true,
        breaks: true,
      });
    }

    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const badge = document.getElementById("health-indicator");
        if (data.status === "healthy") {
          badge.textContent = "Online";
          badge.className = "badge badge-active";
        } else {
          badge.textContent = "Degraded";
          badge.className = "badge badge-superseded";
        }
        if (data.llm_fallback_chain && data.llm_fallback_chain.length > 0) {
          const chainText = data.llm_fallback_chain.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(" → ");
          document.getElementById("llm-chain-badge").textContent = `LLM Fallback: ${chainText}`;
        }
      } catch (e) {
        document.getElementById("health-indicator").textContent = "Offline";
      }
    }

    async function loadDocuments() {
      try {
        const res = await fetch(`${API_BASE}/documents`);
        const docs = await res.json();
        const list = document.getElementById("doc-list");
        list.innerHTML = "";
        docs.forEach(d => {
          const item = document.createElement("div");
          item.className = "doc-item";
          const filename = d.source.split(/[\\\\/]/).pop();
          item.innerHTML = `
            <div class="doc-title">${filename}</div>
            <div class="doc-meta">v${d.version} | ${d.status.toUpperCase()} | ${d.chunk_ids.length} chunks</div>
          `;
          item.onclick = () => viewDocumentHistory(d.document_id, filename);
          list.appendChild(item);
        });
      } catch (e) {
        console.error(e);
      }
    }

    function setQuery(text) {
      document.getElementById("query-input").value = text;
      sendQuery();
    }

    async function sendQuery() {
      const input = document.getElementById("query-input");
      const query = input.value.trim();
      if (!query) return;

      const debug = document.getElementById("debug-toggle").checked;
      const container = document.getElementById("chat-container");
      const msgId = "msg_" + Date.now();

      // Append User Message
      const userMsg = document.createElement("div");
      userMsg.className = "message user";
      userMsg.innerHTML = `<div class="bubble">${query}</div>`;
      container.appendChild(userMsg);
      input.value = "";
      container.scrollTop = container.scrollHeight;

      // Append Assistant Typing Placeholder
      const asstMsg = document.createElement("div");
      asstMsg.className = "message assistant";
      asstMsg.id = msgId;
      asstMsg.innerHTML = `<div class="bubble" style="color:var(--muted);">Synthesizing answer with grounded provenance...</div>`;
      container.appendChild(asstMsg);
      container.scrollTop = container.scrollHeight;

      try {
        const res = await fetch(`${API_BASE}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query, debug: debug })
        });
        const data = await res.json();

        // Save citations in store
        const citationsList = data.citations || data.sources || [];
        messageCitations[msgId] = citationsList;

        // Render Markdown answer using marked.js
        let rawAnswer = data.answer || "";
        let parsedHtml = window.marked ? marked.parse(rawAnswer) : rawAnswer;

        // Transform citation markers like [1], [2] into clickable interactive pills
        parsedHtml = parsedHtml.replace(/\\[(\\d+)\\]/g, (match, idStr) => {
          return `<button class="citation-ref" onclick="openCitationDrawer(${idStr}, '${msgId}')">[${idStr}]</button>`;
        });

        // Top Metadata Badges: [ SEMANTIC ] [ OPENROUTER ] [ N SOURCES ]
        const queryType = data.query_type || "SEMANTIC";
        const providerName = (data.metadata && data.metadata.provider) ||
                             (data.debug_info && data.debug_info.llm_provider) ||
                             "LLM";
        const sourcesCount = citationsList.length;

        const headerBadges = `
          <div class="response-header-badges">
            <span class="badge badge-type">${queryType}</span>
            <span class="badge badge-provider">${providerName.toUpperCase()}</span>
            <span class="badge badge-sources">${sourcesCount} ${sourcesCount === 1 ? 'SOURCE' : 'SOURCES'}</span>
          </div>
        `;

        // Bottom Structured Source Cards
        let sourcesHtml = "";
        if (citationsList.length > 0) {
          let cardsHtml = citationsList.map(c => `
            <div class="source-card" onclick="openCitationDrawer(${c.id}, '${msgId}')">
              <div class="source-card-main">
                <span class="source-card-id">[${c.id}]</span>
                <span style="font-size:16px;">📄</span>
                <div class="source-card-info">
                  <div class="source-card-filename">${c.source}</div>
                  <div class="source-card-title">${c.title || c.snippet.slice(0, 50) + '...'}</div>
                </div>
              </div>
              <span class="source-card-arrow">→</span>
            </div>
          `).join("");

          sourcesHtml = `
            <div class="sources-container">
              <div class="sources-heading">Sources & Verified Provenance</div>
              <div class="sources-grid">${cardsHtml}</div>
            </div>
          `;
        }

        // Optional Debug Payload
        let debugHtml = "";
        if (debug && data.debug_info) {
          debugHtml = `<pre style="margin-top:12px; padding:10px; background:#070a13; color:#38bdf8; font-size:11px; border-radius:6px; overflow-x:auto;">${JSON.stringify(data.debug_info, null, 2)}</pre>`;
        }

        if (data.metadata && data.metadata.ingested) {
          loadDocuments();
        }

        asstMsg.innerHTML = `
          <div class="bubble">
            ${headerBadges}
            <div class="markdown-content">${parsedHtml}</div>
            ${sourcesHtml}
            ${debugHtml}
          </div>
        `;
        container.scrollTop = container.scrollHeight;
      } catch (e) {
        asstMsg.innerHTML = `<div class="bubble" style="color:#ef4444;">Error generating answer: ${e.message}</div>`;
      }
    }

    // Upload & Ingest Document Handler
    async function handleFileSelected(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      const container = document.getElementById("chat-container");
      const msgId = "msg_upload_" + Date.now();

      // Show user message
      const userMsg = document.createElement("div");
      userMsg.className = "message user";
      userMsg.innerHTML = `<div class="bubble">📎 Upload file: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)</div>`;
      container.appendChild(userMsg);

      // Show assistant processing indicator
      const asstMsg = document.createElement("div");
      asstMsg.className = "message assistant";
      asstMsg.id = msgId;
      asstMsg.innerHTML = `<div class="bubble" style="color:var(--muted);">Parsing text from <code>${file.name}</code>, generating embeddings, and storing in Qdrant...</div>`;
      container.appendChild(asstMsg);
      container.scrollTop = container.scrollHeight;

      try {
        let res;
        // Attempt multipart upload
        try {
          const formData = new FormData();
          formData.append("file", file);
          formData.append("category", "notes");
          res = await fetch(`${API_BASE}/ingest/upload`, {
            method: "POST",
            body: formData,
          });
        } catch (e) {
          res = null;
        }

        // If multipart upload failed, fallback to base64 JSON endpoint
        if (!res || !res.ok) {
          const b64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
          res = await fetch(`${API_BASE}/ingest/file`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: file.name,
              content_base64: b64,
              category: "notes",
            }),
          });
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to index document");

        asstMsg.innerHTML = `
          <div class="bubble">
            <div class="response-header-badges">
              <span class="badge badge-active">${data.status}</span>
              <span class="badge badge-provider">${file.name.split('.').pop().toUpperCase()}</span>
              <span class="badge badge-sources">${data.chunks_count} CHUNKS</span>
            </div>
            <div class="markdown-content">
              <h1>📄 Document Uploaded & Indexed</h1>
              <p>Successfully processed <strong><code>${data.filename}</code></strong> into your personal knowledge base.</p>
              <ul>
                <li><strong>Source:</strong> <code>${data.source}</code></li>
                <li><strong>Status:</strong> <span class="badge badge-active">${data.status}</span> (Version ${data.version})</li>
                <li><strong>Chunks Indexed:</strong> ${data.chunks_count}</li>
              </ul>
              <blockquote>You can now query anything from <strong>${data.filename}</strong> directly in the chat, and answers will include verified citations.</blockquote>
            </div>
          </div>
        `;
        loadDocuments();
      } catch (err) {
        asstMsg.innerHTML = `<div class="bubble" style="color:#ef4444;">❌ Failed to upload and index document: ${err.message}</div>`;
      } finally {
        event.target.value = "";
        container.scrollTop = container.scrollHeight;
      }
    }

    // Open Source Drawer for a specific citation ID
    function openCitationDrawer(citationId, msgId) {
      const citations = messageCitations[msgId] || [];
      const citation = citations.find(c => c.id === citationId) || citations[citationId - 1];
      if (!citation) return;

      const panel = document.getElementById("details-panel");
      const titleEl = document.getElementById("details-title");
      const body = document.getElementById("details-body");

      titleEl.innerHTML = `📄 [${citation.id}] ${citation.source}`;
      panel.classList.add("open");

      const statusBadge = citation.status ?
        `<span class="badge badge-${citation.status}">${citation.status.toUpperCase()}</span>` : "";

      body.innerHTML = `
        <div style="margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
          <h3 style="font-size:16px; color:#f8fafc;">${citation.title || citation.source}</h3>
          ${statusBadge}
        </div>

        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:8px; padding:14px; margin-bottom:16px;">
          <div class="meta-row">
            <span class="meta-label">Source Document</span>
            <span class="meta-value">${citation.source}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Chunk ID</span>
            <span class="meta-value">${citation.chunk_id || 'N/A'}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Relevance Score</span>
            <span class="meta-value">${citation.score != null ? citation.score : 'Dense Match'}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Document Type</span>
            <span class="meta-value">${citation.document_type || 'Note'}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Event Date</span>
            <span class="meta-value">${citation.event_at ? citation.event_at.split('T')[0] : 'N/A'}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Validity Window</span>
            <span class="meta-value">${citation.valid_from ? citation.valid_from.split('T')[0] : 'Start'} &rarr; ${citation.valid_until ? citation.valid_until.split('T')[0] : 'Present'}</span>
          </div>
        </div>

        <div style="font-size:12px; font-weight:700; color:var(--accent); text-transform:uppercase; margin-bottom:6px;">
          Verified Grounded Excerpt
        </div>
        <div class="snippet-box">
          "${citation.snippet || 'No excerpt available.'}"
        </div>
      `;
    }

    // View Document Version History Timeline
    async function viewDocumentHistory(docId, filename) {
      const panel = document.getElementById("details-panel");
      const titleEl = document.getElementById("details-title");
      const body = document.getElementById("details-body");

      titleEl.innerHTML = `🕒 History: ${filename}`;
      panel.classList.add("open");
      body.innerHTML = "<div style='color:var(--muted); padding:20px; text-align:center;'>Loading timeline...</div>";

      try {
        const res = await fetch(`${API_BASE}/documents/${docId}/history`);
        const data = await res.json();
        body.innerHTML = "";
        data.timeline.forEach(item => {
          const node = document.createElement("div");
          node.style.cssText = "position:relative; padding-left:20px; margin-bottom:20px; border-left:2px solid var(--border);";
          node.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span class="badge badge-${item.status}">${item.status.toUpperCase()}</span>
              <span style="font-size:11px; color:var(--muted);">${item.event_at ? item.event_at.split('T')[0] : 'No date'}</span>
            </div>
            <div style="font-size:12px; color:var(--muted); margin-bottom:6px;">
              Valid: ${item.valid_from ? item.valid_from.split('T')[0] : 'Start'} &rarr; ${item.valid_until ? item.valid_until.split('T')[0] : 'Present'}
            </div>
            <div style="font-size:13px; line-height:1.4; color:#e2e8f0;">${item.text_snippet}</div>
          `;
          body.appendChild(node);
        });
      } catch (e) {
        body.innerHTML = `<div style='color:#ef4444;'>Failed to load history: ${e.message}</div>`;
      }
    }

    function closeDetailsPanel() {
      document.getElementById("details-panel").classList.remove("open");
    }

    async function runIngestion() {
      const statusEl = document.getElementById("ingest-status");
      statusEl.textContent = "Scanning and embedding documents...";
      try {
        const res = await fetch(`${API_BASE}/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        const data = await res.json();
        statusEl.textContent = `Processed: ${data.processed} | Added: ${data.added} | Skipped: ${data.skipped}`;
        loadDocuments();
      } catch (e) {
        statusEl.textContent = `Error: ${e.message}`;
      }
    }

    // Modal Add Note / Task Handlers
    function openNoteModal() {
      document.getElementById("note-modal").style.display = "flex";
      document.getElementById("modal-note-content").focus();
    }

    function closeNoteModal() {
      document.getElementById("note-modal").style.display = "none";
    }

    function updateNoteTypePrompt() {
      const type = document.getElementById("modal-note-type").value;
      const content = document.getElementById("modal-note-content");
      if (type === "daily_tasks.md") {
        content.placeholder = "- complete ml\\n- complete db\\n- practice leetcode";
      } else if (type === "project_rules.md") {
        content.placeholder = "All internal service communication must use gRPC protocol.";
      } else if (type === "accomplishments.md") {
        content.placeholder = "Completed implementation of conversational task ingestion and LLM fallback chain.";
      } else {
        content.placeholder = "Write your note here...";
      }
    }

    async function submitModalNote() {
      const filename = document.getElementById("modal-note-type").value;
      let title = document.getElementById("modal-note-title").value.trim();
      let content = document.getElementById("modal-note-content").value.trim();
      if (!content) return;

      if (filename === "daily_tasks.md" && !title) {
        title = "Today's Tasks";
      }

      closeNoteModal();
      document.getElementById("modal-note-content").value = "";
      document.getElementById("modal-note-title").value = "";

      const container = document.getElementById("chat-container");
      const msgId = "msg_note_" + Date.now();

      const userMsg = document.createElement("div");
      userMsg.className = "message user";
      userMsg.innerHTML = `<div class="bubble">📝 Save Note: <strong>${title || filename}</strong><br><pre style="margin-top:6px; font-size:12px; background:transparent; white-space:pre-wrap;">${content}</pre></div>`;
      container.appendChild(userMsg);

      const asstMsg = document.createElement("div");
      asstMsg.className = "message assistant";
      asstMsg.id = msgId;
      asstMsg.innerHTML = `<div class="bubble" style="color:var(--muted);">Indexing note into <code>${filename}</code> and Qdrant...</div>`;
      container.appendChild(asstMsg);
      container.scrollTop = container.scrollHeight;

      try {
        const res = await fetch(`${API_BASE}/ingest/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: content,
            title: title || undefined,
            filename: filename,
            category: "notes"
          })
        });
        const data = await res.json();
        loadDocuments();

        asstMsg.innerHTML = `
          <div class="bubble">
            <div class="response-header-badges">
              <span class="badge badge-type">INGESTED</span>
              <span class="badge badge-active">${data.status || 'ACTIVE'}</span>
              <span class="badge badge-sources">1 SOURCE</span>
            </div>
            <div class="markdown-content">
              <h1>Knowledge Recorded & Indexed</h1>
              <p>Your note has been saved to <code>${data.source}</code> and is now indexed for immediate semantic and temporal retrieval.</p>
              <ul>
                <li><strong>Document:</strong> <code>${data.source}</code></li>
                <li><strong>Status:</strong> <code>${data.status}</code> (Version ${data.version})</li>
                <li><strong>Indexed Chunks:</strong> ${data.chunks_count}</li>
              </ul>
            </div>
          </div>
        `;
        container.scrollTop = container.scrollHeight;
      } catch (err) {
        asstMsg.innerHTML = `<div class="bubble" style="color:#ef4444;">Error saving note: ${err.message}</div>`;
      }
    }

    checkHealth();
    loadDocuments();
  </script>

  <!-- Add Note / Task Modal -->
  <div id="note-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:100; align-items:center; justify-content:center;">
    <div style="background:var(--card); border:1px solid var(--border); border-radius:12px; width:480px; max-width:90%; padding:24px; box-shadow:0 8px 32px rgba(0,0,0,0.5);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h3 style="font-size:16px; font-weight:700; color:#f8fafc;">📝 Ingest Note or Task List</h3>
        <button class="btn btn-secondary" onclick="closeNoteModal()" style="padding:4px 8px;">✕</button>
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:12px; color:var(--muted); display:block; margin-bottom:4px;">Document Type</label>
        <select id="modal-note-type" style="width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text); padding:8px 10px; border-radius:6px; font-size:13px;" onchange="updateNoteTypePrompt()">
          <option value="daily_tasks.md">Today's Tasks / Todo List (daily_tasks.md)</option>
          <option value="chat_notes.md">Chat Note / Memorization (chat_notes.md)</option>
          <option value="accomplishments.md">Engineering Accomplishment (accomplishments.md)</option>
          <option value="project_rules.md">Project Rule / Decision (project_rules.md)</option>
        </select>
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:12px; color:var(--muted); display:block; margin-bottom:4px;">Section Title (Optional)</label>
        <input type="text" id="modal-note-title" placeholder="e.g. Today's Tasks, Sprint Review, etc." style="width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text); padding:8px 10px; border-radius:6px; font-size:13px;">
      </div>
      <div style="margin-bottom:16px;">
        <label style="font-size:12px; color:var(--muted); display:block; margin-bottom:4px;">Content (Markdown or Bullet List)</label>
        <textarea id="modal-note-content" rows="6" placeholder="- complete ml&#10;- complete db&#10;- practice leetcode" style="width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text); padding:10px; border-radius:6px; font-size:13px; resize:vertical; font-family:inherit;"></textarea>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn btn-secondary" onclick="closeNoteModal()">Cancel</button>
        <button class="btn" onclick="submitModalNote()">Save & Index Knowledge</button>
      </div>
    </div>
  </div>
</body>
</html>
"""

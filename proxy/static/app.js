// Built-in provider -> model mapping
const BUILTIN_PROVIDERS = {
    deepseek: "deepseek-chat",
    openai: "gpt-4o-mini",
    claude: "claude-sonnet-4-6",
    groq: "llama-3.3-70b",
};

// Load custom providers from localStorage and merge
function loadCustomProviders() {
    const custom = JSON.parse(localStorage.getItem("custom_providers") || "[]");
    return custom;  // array of {name, endpoint, model, api_key}
}

const customProviders = loadCustomProviders();

// Populate provider dropdown
const providerSelect = document.getElementById("provider-select");
providerSelect.innerHTML = "";

// Add built-in options
const builtinKeys = Object.keys(BUILTIN_PROVIDERS);
builtinKeys.forEach(key => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = key.charAt(0).toUpperCase() + key.slice(1);
    providerSelect.appendChild(opt);
});

// Add custom options
customProviders.forEach(p => {
    const opt = document.createElement("option");
    opt.value = `custom:${p.name}`;
    opt.textContent = p.name + " (自定义)";
    providerSelect.appendChild(opt);
});

const state = {
    provider: builtinKeys[0] || "custom:" + (customProviders[0]?.name || ""),
    messages: [],
    isLoading: false,
    customProviders: customProviders,
};

// DOM refs
const providerSelect = document.getElementById("provider-select");
const modelDisplay = document.getElementById("model-display");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const messagesContainer = document.getElementById("messages");
const welcomeEl = document.getElementById("welcome");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const errorToast = document.getElementById("error-toast");

// Init
providerSelect.addEventListener("change", onProviderChange);
sendBtn.addEventListener("click", onSend);
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
    }
});

// History panel
const historyToggle = document.getElementById("history-toggle");
const historyPanel = document.getElementById("history-panel");
const historyClose = document.getElementById("history-close");
const historySearchInput = document.getElementById("history-search-input");
const historyList = document.getElementById("history-list");

historyToggle.addEventListener("click", () => {
    historyPanel.classList.remove("hidden");
    loadRecentHistory();
});

// Data export button
const exportBtn = document.createElement("button");
exportBtn.textContent = "📥 导出所有数据";
exportBtn.style.cssText = "width:calc(100%-32px);margin:8px 16px;padding:8px;border:1px solid #ccc;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;";
exportBtn.addEventListener("click", () => {
    window.open("/v1/export", "_blank");
});
historyPanel.insertBefore(exportBtn, historyList);

historyClose.addEventListener("click", () => {
    historyPanel.classList.add("hidden");
});

historySearchInput.addEventListener("input", debounce(() => {
    const q = historySearchInput.value.trim();
    if (q) searchHistory(q);
    else loadRecentHistory();
}, 400));

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

async function loadRecentHistory() {
    try {
        const resp = await fetch("/v1/history/recent?limit=30");
        const data = await resp.json();
        renderHistoryList(data.results || []);
    } catch {
        historyList.innerHTML = '<div class="history-empty">无法加载历史记录</div>';
    }
}

async function searchHistory(query) {
    try {
        const resp = await fetch(`/v1/history?query=${encodeURIComponent(query)}&limit=20`);
        const data = await resp.json();
        renderHistoryList(data.results || []);
    } catch {
        historyList.innerHTML = '<div class="history-empty">搜索失败</div>';
    }
}

function renderHistoryList(records) {
    if (!records.length) {
        historyList.innerHTML = '<div class="history-empty">没有历史记录</div>';
        return;
    }
    let html = "";
    for (const r of records) {
        const ts = (r.timestamp || "").slice(0, 19).replace("T", " ");
        const provider = r.provider || "?";
        const model = r.model || "?";
        let preview = "";
        try {
            const msgs = JSON.parse(r.messages_json || "[]");
            for (const m of msgs) {
                if (m.role === "user" && m.content) {
                    preview = typeof m.content === "string" ? m.content.slice(0, 60) : "";
                    break;
                }
            }
        } catch {}
        const requestId = r.request_id || "";
        html += `
            <div class="history-item" data-id="${requestId}">
                <div class="h-provider">${provider}/${model}</div>
                <div class="h-preview">${escapeHtml(preview)}</div>
                <div class="h-time">${ts}</div>
                <button class="h-inject" data-id="${requestId}">注入当前会话</button>
            </div>`;
    }
    historyList.innerHTML = html;

    // Inject buttons
    historyList.querySelectorAll(".h-inject").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            await injectConversation(id);
        });
    });

    // Click item to see details
    historyList.querySelectorAll(".history-item").forEach(item => {
        item.addEventListener("click", (e) => {
            if (e.target.closest(".h-inject")) return;
            const id = item.dataset.id;
            loadConversationDetail(id);
        });
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

async function injectConversation(requestId) {
    try {
        const resp = await fetch(`/v1/history?query=${requestId}&limit=1`);
        const data = await resp.json();
        const record = (data.results || [])[0];
        if (!record) { showError("未找到对话记录"); return; }

        const msgs = JSON.parse(record.messages_json || "[]");
        // Append to current state
        for (const m of msgs) {
            if (m.role === "user" || m.role === "assistant") {
                state.messages.push({ role: m.role, content: m.content });
                addMessage(m.role, m.content);
            }
        }
        showError(`✅ 已注入 ${msgs.length} 条历史消息`);
        historyPanel.classList.add("hidden");
    } catch (err) {
        showError("注入失败: " + err.message);
    }
}

async function loadConversationDetail(requestId) {
    try {
        const resp = await fetch(`/v1/history?query=${requestId}&limit=1`);
        const data = await resp.json();
        const record = (data.results || [])[0];
        if (!record) return;
        const msgs = JSON.parse(record.messages_json || "[]");
        historyList.innerHTML = '<button id="history-back" style="border:none;background:none;padding:8px 16px;cursor:pointer;font-size:13px;color:#4f46e5;">← 返回列表</button>';
        for (const m of msgs) {
            const role = m.role || "?";
            const content = typeof m.content === "string" ? m.content : JSON.stringify(m.content);
            historyList.innerHTML += `<div class="history-item" style="border:none;">
                <div class="h-provider">${role}</div>
                <div class="h-preview" style="white-space:normal;overflow:visible;text-overflow:clip;">${escapeHtml(content.slice(0, 200))}</div>
            </div>`;
        }
        document.getElementById("history-back").addEventListener("click", loadRecentHistory);
    } catch {}
}

checkConfig();

// --- Functions ---

async function checkConfig() {
    try {
        const resp = await fetch("/health");
        if (resp.ok) {
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.placeholder = "输入消息...";
        } else {
            showConfigPrompt();
        }
    } catch {
        showConfigPrompt();
    }
}

function showConfigPrompt() {
    messageInput.placeholder = "❌ 服务未就绪，请检查设置";
    errorToast.textContent = "⚠️ 无法连接后端，请确保服务已启动";
    errorToast.classList.remove("hidden");
    setTimeout(() => errorToast.classList.add("hidden"), 5000);
}

function onProviderChange() {
    state.provider = providerSelect.value;
    if (state.provider.startsWith("custom:")) {
        const name = state.provider.replace("custom:", "");
        const p = state.customProviders.find(c => c.name === name);
        modelDisplay.textContent = p ? p.model + " (自定义)" : "unknown";
    } else {
        modelDisplay.textContent = BUILTIN_PROVIDERS[state.provider] || "unknown";
    }
}

function onSend() {
    const text = messageInput.value.trim();
    if (!text || state.isLoading) return;

    // Clear input
    messageInput.value = "";
    messageInput.style.height = "auto";

    // Hide welcome
    welcomeEl.classList.add("hidden");

    // Add user message
    addMessage("user", text);
    state.messages.push({ role: "user", content: text });

    // Send
    sendToAI();
}

async function sendToAI() {
    state.isLoading = true;
    setLoading(true, "等待 AI 回复...");

    let body = { messages: state.messages };

    if (state.provider.startsWith("custom:")) {
        const name = state.provider.replace("custom:", "");
        const p = state.customProviders.find(c => c.name === name);
        if (p) {
            body["model"] = p.model;
            body["x-custom"] = {
                name: p.name,
                endpoint: p.endpoint,
                model: p.model,
                api_key: p.api_key,
            };
        }
    } else {
        body["model"] = BUILTIN_PROVIDERS[state.provider] || state.provider;
    }

    try {
        const resp = await fetch("/v1/chat/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            const err = await resp.text();
            throw new Error(`API error: ${resp.status} ${err}`);
        }

        const data = await resp.json();
        const content = data.choices?.[0]?.message?.content || "(空回复)";

        addMessage("assistant", content);
        state.messages.push({ role: "assistant", content });

        // If a degraded provider was used, show a small tag
        if (data["x-degraded"]) {
            const lastMsg = messagesContainer.lastElementChild;
            const tag = document.createElement("div");
            tag.className = "meta";
            tag.textContent = `⚠️ 已切换到备用供应商: ${data["x-provider-used"] || "unknown"}`;
            lastMsg.appendChild(tag);
        }
    } catch (err) {
        showError(err.message);
    } finally {
        state.isLoading = false;
        setLoading(false);
    }
}

function addMessage(role, content) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.textContent = content;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setLoading(show, text) {
    if (show) {
        loadingText.textContent = text || "连接中...";
        loadingOverlay.classList.remove("hidden");
    } else {
        loadingOverlay.classList.add("hidden");
    }
}

function showError(msg) {
    errorToast.textContent = `❌ ${msg}`;
    errorToast.classList.remove("hidden");
    setTimeout(() => errorToast.classList.add("hidden"), 6000);
}

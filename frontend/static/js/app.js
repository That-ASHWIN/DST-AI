/* ============================================================
 * CIMS SAGE · app.js
 * AI RAG Assistant frontend · Vanilla ES6
 * Backend: FastAPI (POST /chat, /upload/pdf, /upload/url,
 *          GET /admin/info, /admin/files, /admin/stats, /health/live)
 * ============================================================ */
"use strict";

/* ----------------------------- Config ----------------------------- */
const CONFIG = {
  STORAGE: {
    chats: "cims_sage_chats",
    active: "cims_sage_active",
    apiBase: "cims_sage_api_base",
    theme: "cims_sage_theme",
    typing: "cims_sage_typing",
    autoscroll: "cims_sage_autoscroll",
  },
  ENDPOINTS: {
    chat: "/chat",
    uploadPdf: "/upload/pdf",
    uploadUrl: "/upload/url",
    adminInfo: "/admin/info",
    adminFiles: "/admin/files",
    adminStats: "/admin/stats",
    health: "/health/live",
  },
  HEALTH_INTERVAL: 30000,
  TYPING_SPEED: 9, // ms per char
};

/* ----------------------------- State ------------------------------ */
const State = {
  chats: [],          // [{ id, title, messages:[{role,content,sources,ts}], createdAt }]
  activeId: null,
  isSending: false,
  abort: null,
  settings: {
    apiBase: "",
    typing: true,
    autoScroll: true,
  },
};

/* ----------------------------- Utils ------------------------------ */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const uid = () => "id-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const nowTs = () => Date.now();

function fmtTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}
function fmtDate(ts) {
  try {
    return new Date(ts).toLocaleDateString([], { month: "short", day: "numeric" });
  } catch { return ""; }
}
function escapeHtml(str = "") {
  return String(str)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

function lsGet(key, fallback = null) {
  try { const v = localStorage.getItem(key); return v === null ? fallback : v; }
  catch { return fallback; }
}
function lsSet(key, val) { try { localStorage.setItem(key, val); } catch {} }

/* ----------------------------- DOM refs --------------------------- */
const dom = {};
function cacheDom() {
  Object.assign(dom, {
    // shell
    sidebar: $("#sidebar"),
    sidebarBackdrop: $("#sidebarBackdrop"),
    sidebarToggle: $("#sidebarToggle"),
    sidebarCloseBtn: $("#sidebarCloseBtn"),
    // sidebar actions
    newChatBtn: $("#newChatBtn"),
    sidebarUploadPdf: $("#sidebarUploadPdf"),
    sidebarUploadUrl: $("#sidebarUploadUrl"),
    sidebarKnowledgeBase: $("#sidebarKnowledgeBase"),
    sidebarSettings: $("#sidebarSettings"),
    themeToggle: $("#themeToggle"),
    themeIcon: $("#themeIcon"),
    themeLabel: $("#themeLabel"),
    chatHistory: $("#chatHistory"),
    historyEmpty: $("#historyEmpty"),
    clearHistoryBtn: $("#clearHistoryBtn"),
    // topbar
    connectionStatus: $("#connectionStatus"),
    connectionDot: $("#connectionDot"),
    modelName: $("#modelName"),
    kbStatus: $("#kbStatus"),
    topbarRefresh: $("#topbarRefresh"),
    // chat
    chatScroll: $("#chatScroll"),
    chatMessages: $("#chatMessages"),
    welcomeScreen: $("#welcomeScreen"),
    // composer
    messageInput: $("#messageInput"),
    sendBtn: $("#sendBtn"),
    stopBtn: $("#stopBtn"),
    inputUploadPdf: $("#inputUploadPdf"),
    inputUploadUrl: $("#inputUploadUrl"),
    // modals
    pdfModal: $("#pdfModal"),
    pdfForm: $("#pdfForm"),
    pdfFileInput: $("#pdfFileInput"),
    pdfFileName: $("#pdfFileName"),
    pdfDropZone: $("#pdfDropZone"),
    pdfSubmitBtn: $("#pdfSubmitBtn"),
    urlModal: $("#urlModal"),
    urlForm: $("#urlForm"),
    urlInput: $("#urlInput"),
    urlSubmitBtn: $("#urlSubmitBtn"),
    settingsModal: $("#settingsModal"),
    apiBaseUrlInput: $("#apiBaseUrlInput"),
    typingToggle: $("#typingToggle"),
    autoScrollToggle: $("#autoScrollToggle"),
    saveSettingsBtn: $("#saveSettingsBtn"),
    kbModal: $("#kbModal"),
    kbStatDocs: $("#kbStatDocs"),
    kbStatChunks: $("#kbStatChunks"),
    kbStatModel: $("#kbStatModel"),
    kbStatStatus: $("#kbStatStatus"),
    kbFilesList: $("#kbFilesList"),
    kbRefreshBtn: $("#kbRefreshBtn"),
    kbAddBtn: $("#kbAddBtn"),
    // toast
    toastContainer: $("#toastContainer"),
  });
}

/* ----------------------------- Toasts ----------------------------- */
const Toast = {
  show(message, type = "info", title = null) {
    const icons = { success: "fa-circle-check", error: "fa-circle-xmark", info: "fa-circle-info", warning: "fa-triangle-exclamation" };
    const titles = { success: "Success", error: "Error", info: "Info", warning: "Warning" };
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `
      <i class="fa-solid ${icons[type] || icons.info} t-icon"></i>
      <div class="t-body">
        <p class="t-title">${escapeHtml(title || titles[type] || "Notice")}</p>
        <p class="t-msg">${escapeHtml(message)}</p>
      </div>
      <button class="t-close" aria-label="Dismiss"><i class="fa-solid fa-xmark"></i></button>`;
    const close = () => {
      el.classList.add("removing");
      setTimeout(() => el.remove(), 250);
    };
    el.querySelector(".t-close").addEventListener("click", close);
    dom.toastContainer.appendChild(el);
    setTimeout(close, type === "error" ? 6000 : 4000);
  },
  success(m, t) { this.show(m, "success", t); },
  error(m, t) { this.show(m, "error", t); },
  info(m, t) { this.show(m, "info", t); },
  warning(m, t) { this.show(m, "warning", t); },
};

/* ----------------------------- API wrapper ------------------------ */
const Api = {
  base() {
    return (State.settings.apiBase || "").replace(/\/+$/, "");
  },
  url(path) { return this.base() + path; },

  async request(path, { method = "GET", body, headers = {}, signal, isForm = false } = {}) {
    const opts = { method, headers: { ...headers }, signal };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body; // FormData; browser sets content-type
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    let res;
    try {
      res = await fetch(this.url(path), opts);
    } catch (err) {
      if (err && err.name === "AbortError") throw err;
      throw new Error("Network error — could not reach the backend.");
    }
    const ct = res.headers.get("content-type") || "";
    let data = null;
    if (ct.includes("application/json")) {
      data = await res.json().catch(() => null);
    } else {
      const txt = await res.text().catch(() => "");
      data = txt;
    }
    if (!res.ok) {
      const detail = (data && (data.detail || data.message || data.error)) || (typeof data === "string" && data) || `Request failed (${res.status})`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  },

  // POST /chat
  async chat(message, history, signal) {
    const payload = {
      query: message,
      message: message,
      question: message,
      history: (history || []).map((m) => ({ role: m.role, content: m.content })),
    };
    const data = await this.request(CONFIG.ENDPOINTS.chat, { method: "POST", body: payload, signal });
    return normalizeChatResponse(data);
  },

  // POST /upload/pdf (multipart)
  async uploadPdf(file) {
    const fd = new FormData();
    fd.append("file", file, file.name);
    return this.request(CONFIG.ENDPOINTS.uploadPdf, { method: "POST", body: fd, isForm: true });
  },

  // POST /upload/url
  async uploadUrl(link) {
    return this.request(CONFIG.ENDPOINTS.uploadUrl, { method: "POST", body: { url: link } });
  },

  health() { return this.request(CONFIG.ENDPOINTS.health); },
  adminInfo() { return this.request(CONFIG.ENDPOINTS.adminInfo); },
  adminFiles() { return this.request(CONFIG.ENDPOINTS.adminFiles); },
  adminStats() { return this.request(CONFIG.ENDPOINTS.adminStats); },
};

/* Normalize various RAG response shapes into { answer, sources[] } */
function normalizeChatResponse(data) {
  if (data == null) return { answer: "", sources: [] };
  if (typeof data === "string") return { answer: data, sources: [] };

  const answer =
    data.answer ?? data.response ?? data.message ?? data.result ??
    data.text ?? data.output ?? data.reply ?? data.content ??
    (data.data && (data.data.answer || data.data.response)) ?? "";

  let rawSources =
    data.sources ?? data.source_documents ?? data.documents ??
    data.citations ?? data.context ?? (data.data && data.data.sources) ?? [];

  if (!Array.isArray(rawSources)) rawSources = rawSources ? [rawSources] : [];

  const sources = rawSources.map((s) => {
    if (typeof s === "string") return { label: s, url: isUrl(s) ? s : null };
    const meta = s.metadata || s.meta || {};
    const label =
      s.title || s.name || s.source || s.file || s.filename ||
      meta.source || meta.title || meta.file_name || meta.filename || meta.url ||
      (s.page_content ? s.page_content.slice(0, 60) + "…" : "Source");
    const url = s.url || meta.url || meta.source_url || (isUrl(label) ? label : null);
    return { label: String(label), url: url || null };
  });

  return { answer: typeof answer === "string" ? answer : JSON.stringify(answer, null, 2), sources };
}
function isUrl(s) { return typeof s === "string" && /^https?:\/\//i.test(s); }

/* ----------------------------- Markdown --------------------------- */
function configureMarked() {
  if (typeof marked === "undefined") return;
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight(code, lang) {
      try {
        if (typeof hljs === "undefined") return escapeHtml(code);
        if (lang && hljs.getLanguage(lang)) return hljs.highlight(code, { language: lang }).value;
        return hljs.highlightAuto(code).value;
      } catch { return escapeHtml(code); }
    },
  });
}
function renderMarkdown(text) {
  const raw = (typeof marked !== "undefined") ? marked.parse(text || "") : escapeHtml(text || "").replace(/\n/g, "<br>");
  if (typeof DOMPurify !== "undefined") {
    return DOMPurify.sanitize(raw, { ADD_ATTR: ["target", "rel"] });
  }
  return raw;
}
/* Add language label + copy button to code blocks */
function decorateCodeBlocks(scope) {
  $$("pre", scope).forEach((pre) => {
    if (pre.dataset.decorated) return;
    pre.dataset.decorated = "1";
    const code = pre.querySelector("code");
    let lang = "code";
    if (code) {
      const m = (code.className || "").match(/language-([\w-]+)/);
      if (m) lang = m[1];
    }
    const bar = document.createElement("div");
    bar.className = "code-toolbar";
    bar.innerHTML = `<span class="code-lang">${escapeHtml(lang)}</span>
      <button class="code-copy" type="button"><i class="fa-regular fa-copy"></i> Copy</button>`;
    bar.querySelector(".code-copy").addEventListener("click", () => {
      copyText(code ? code.innerText : pre.innerText, bar.querySelector(".code-copy"));
    });
    pre.prepend(bar);
  });
  // ensure links open safely
  $$("a", scope).forEach((a) => { a.target = "_blank"; a.rel = "noopener noreferrer"; });
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
      setTimeout(() => { btn.innerHTML = orig; }, 1500);
    }
    Toast.success("Copied to clipboard");
  } catch {
    Toast.error("Could not copy");
  }
}

/* ----------------------------- Chat store ------------------------- */
function loadChats() {
  try {
    State.chats = JSON.parse(lsGet(CONFIG.STORAGE.chats, "[]")) || [];
  } catch { State.chats = []; }
  State.activeId = lsGet(CONFIG.STORAGE.active, null);
  if (!State.chats.find((c) => c.id === State.activeId)) {
    State.activeId = State.chats[0] ? State.chats[0].id : null;
  }
}
function persistChats() {
  lsSet(CONFIG.STORAGE.chats, JSON.stringify(State.chats));
  lsSet(CONFIG.STORAGE.active, State.activeId || "");
}
function activeChat() { return State.chats.find((c) => c.id === State.activeId) || null; }

function newChat(activate = true) {
  const chat = { id: uid(), title: "New Chat", messages: [], createdAt: nowTs() };
  State.chats.unshift(chat);
  if (activate) State.activeId = chat.id;
  persistChats();
  return chat;
}
function ensureActiveChat() {
  let chat = activeChat();
  if (!chat) chat = newChat(true);
  return chat;
}
function deleteChat(id) {
  State.chats = State.chats.filter((c) => c.id !== id);
  if (State.activeId === id) State.activeId = State.chats[0] ? State.chats[0].id : null;
  persistChats();
  renderHistory();
  renderActiveChat();
}
function clearAllChats() {
  State.chats = [];
  State.activeId = null;
  persistChats();
  renderHistory();
  renderActiveChat();
  Toast.info("All conversations cleared");
}

/* ----------------------------- Rendering -------------------------- */
function renderHistory() {
  const list = dom.chatHistory;
  list.innerHTML = "";
  if (!State.chats.length) {
    dom.historyEmpty.style.display = "block";
    return;
  }
  dom.historyEmpty.style.display = "none";
  State.chats.forEach((chat) => {
    const li = document.createElement("li");
    li.className = "history-item" + (chat.id === State.activeId ? " active" : "");
    li.dataset.id = chat.id;
    li.innerHTML = `
      <i class="fa-regular fa-message h-icon"></i>
      <span class="h-title">${escapeHtml(chat.title || "Untitled")}</span>
      <i class="fa-solid fa-trash-can h-del" title="Delete"></i>`;
    li.addEventListener("click", (e) => {
      if (e.target.classList.contains("h-del")) {
        e.stopPropagation();
        deleteChat(chat.id);
        return;
      }
      State.activeId = chat.id;
      persistChats();
      renderHistory();
      renderActiveChat();
      closeSidebarMobile();
    });
    list.appendChild(li);
  });
}

function setWelcomeVisible(visible) {
  dom.welcomeScreen.style.display = visible ? "flex" : "none";
}

function renderActiveChat() {
  const chat = activeChat();
  dom.chatMessages.innerHTML = "";
  if (!chat || !chat.messages.length) {
    setWelcomeVisible(true);
    return;
  }
  setWelcomeVisible(false);
  chat.messages.forEach((m) => appendMessageEl(m));
  scrollToBottom(true);
}

function buildMessageEl(msg) {
  const row = document.createElement("div");
  row.className = `msg-row ${msg.role}`;
  row.dataset.id = msg.id || (msg.id = uid());

  const avatar = document.createElement("div");
  avatar.className = `msg-avatar ${msg.role}`;
  avatar.innerHTML = msg.role === "user"
    ? '<i class="fa-solid fa-user"></i>'
    : '<i class="fa-solid fa-robot"></i>';

  const body = document.createElement("div");
  body.className = "msg-body";

  const bubble = document.createElement("div");
  bubble.className = `bubble ${msg.role}`;

  if (msg.role === "user") {
    bubble.innerHTML = `<p>${escapeHtml(msg.content).replace(/\n/g, "<br>")}</p>`;
  } else {
    bubble.innerHTML = renderMarkdown(msg.content);
    decorateCodeBlocks(bubble);
  }
  body.appendChild(bubble);

  // sources
  if (msg.role === "ai" && Array.isArray(msg.sources) && msg.sources.length) {
    body.appendChild(buildSourcesEl(msg.sources));
  }

  // meta
  const meta = document.createElement("div");
  meta.className = "msg-meta";
  const timeSpan = document.createElement("span");
  timeSpan.innerHTML = `<i class="fa-regular fa-clock"></i> ${fmtTime(msg.ts || nowTs())}`;
  meta.appendChild(timeSpan);

  if (msg.role === "ai") {
    const actions = document.createElement("div");
    actions.className = "msg-actions";
    const copyBtn = document.createElement("button");
    copyBtn.className = "msg-action-btn";
    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
    copyBtn.addEventListener("click", () => copyText(msg.content, copyBtn));
    actions.appendChild(copyBtn);
    meta.appendChild(actions);
  }
  body.appendChild(meta);

  row.appendChild(avatar);
  row.appendChild(body);
  return { row, bubble, body };
}

function buildSourcesEl(sources) {
  const wrap = document.createElement("div");
  wrap.className = "sources";
  sources.forEach((s, i) => {
    const chip = document.createElement(s.url ? "a" : "span");
    chip.className = "source-chip";
    if (s.url) { chip.href = s.url; chip.target = "_blank"; chip.rel = "noopener noreferrer"; }
    chip.innerHTML = `<i class="fa-solid fa-file-lines"></i><span>${escapeHtml(s.label || ("Source " + (i + 1)))}</span>`;
    wrap.appendChild(chip);
  });
  return wrap;
}

function appendMessageEl(msg) {
  const { row } = buildMessageEl(msg);
  dom.chatMessages.appendChild(row);
  return row;
}

/* Typing indicator (dots) for "AI is thinking" */
function appendThinkingEl() {
  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.dataset.thinking = "1";
  row.innerHTML = `
    <div class="msg-avatar ai"><i class="fa-solid fa-robot"></i></div>
    <div class="msg-body">
      <div class="bubble ai"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    </div>`;
  dom.chatMessages.appendChild(row);
  scrollToBottom(true);
  return row;
}

/* Stream text into a bubble with typing cursor animation */
async function typeInto(bubble, fullText, signal) {
  const useTyping = State.settings.typing;
  if (!useTyping) {
    bubble.innerHTML = renderMarkdown(fullText);
    decorateCodeBlocks(bubble);
    return;
  }
  let i = 0;
  const cursor = '<span class="type-cursor"></span>';
  const step = Math.max(1, Math.round(fullText.length / 600)); // speed up very long answers
  while (i < fullText.length) {
    if (signal && signal.aborted) break;
    i = Math.min(fullText.length, i + step);
    const partial = fullText.slice(0, i);
    bubble.innerHTML = renderMarkdown(partial) + cursor;
    scrollToBottom(false);
    await sleep(CONFIG.TYPING_SPEED);
  }
  bubble.innerHTML = renderMarkdown(fullText);
  decorateCodeBlocks(bubble);
}

/* ----------------------------- Scroll ----------------------------- */
function scrollToBottom(force = false) {
  if (!State.settings.autoScroll && !force) return;
  const el = dom.chatScroll;
  el.scrollTop = el.scrollHeight;
}

/* ----------------------------- Send flow -------------------------- */
async function sendMessage(text) {
  const message = (text != null ? text : dom.messageInput.value).trim();
  if (!message || State.isSending) return;

  const chat = ensureActiveChat();
  setWelcomeVisible(false);

  // user message
  const userMsg = { id: uid(), role: "user", content: message, ts: nowTs() };
  chat.messages.push(userMsg);
  appendMessageEl(userMsg);

  // title from first user message
  if (chat.title === "New Chat") {
    chat.title = message.slice(0, 40) + (message.length > 40 ? "…" : "");
    renderHistory();
  }

  // reset input
  dom.messageInput.value = "";
  autoResize();
  persistChats();
  scrollToBottom(true);

  // loading state
  setSending(true);
  const thinking = appendThinkingEl();
  State.abort = new AbortController();

  try {
    const history = chat.messages.slice(0, -1).slice(-10); // last 10 prior turns
    const { answer, sources } = await Api.chat(message, history, State.abort.signal);

    thinking.remove();
    const aiMsg = { id: uid(), role: "ai", content: answer || "*(No response returned by the backend.)*", sources: sources || [], ts: nowTs() };
    const { row, bubble } = buildMessageEl({ ...aiMsg, content: "" });
    dom.chatMessages.appendChild(row);
    // (re)attach sources/meta after typing: rebuild fully once typed
    await typeInto(bubble, aiMsg.content, State.abort.signal);
    // rebuild full element with sources + actions now that typing done
    const finalEls = buildMessageEl(aiMsg);
    row.replaceWith(finalEls.row);

    chat.messages.push(aiMsg);
    persistChats();
    scrollToBottom(false);
  } catch (err) {
    thinking.remove();
    if (err && err.name === "AbortError") {
      Toast.warning("Generation stopped");
    } else {
      const errMsg = { id: uid(), role: "ai", content: `⚠️ **Error:** ${err.message || "Something went wrong while contacting the backend."}`, sources: [], ts: nowTs() };
      chat.messages.push(errMsg);
      appendMessageEl(errMsg);
      persistChats();
      Toast.error(err.message || "Request failed");
    }
    scrollToBottom(true);
  } finally {
    setSending(false);
    State.abort = null;
    dom.messageInput.focus();
  }
}

function setSending(loading) {
  State.isSending = loading;
  dom.sendBtn.classList.toggle("is-loading", loading);
  dom.sendBtn.disabled = loading;
  dom.stopBtn.classList.toggle("hidden", !loading);
}

/* ----------------------------- Composer --------------------------- */
function autoResize() {
  const ta = dom.messageInput;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
}

/* ----------------------------- Modals ----------------------------- */
function openModal(modal) {
  modal.classList.remove("hidden");
  const focusable = modal.querySelector("input, textarea, button");
  if (focusable) setTimeout(() => focusable.focus(), 50);
}
function closeModal(modal) { modal.classList.add("hidden"); }
function closeAllModals() { $$(".modal-overlay").forEach((m) => m.classList.add("hidden")); }

/* PDF upload */
function bindPdfModal() {
  dom.pdfFileInput.addEventListener("change", () => {
    const f = dom.pdfFileInput.files[0];
    dom.pdfFileName.textContent = f ? f.name : "No file selected";
  });
  // drag & drop
  ["dragover", "dragenter"].forEach((ev) =>
    dom.pdfDropZone.addEventListener(ev, (e) => { e.preventDefault(); dom.pdfDropZone.classList.add("dragover"); }));
  ["dragleave", "dragend", "drop"].forEach((ev) =>
    dom.pdfDropZone.addEventListener(ev, () => dom.pdfDropZone.classList.remove("dragover")));
  dom.pdfDropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) {
      if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
        Toast.error("Please drop a PDF file"); return;
      }
      dom.pdfFileInput.files = e.dataTransfer.files;
      dom.pdfFileName.textContent = f.name;
    }
  });

  dom.pdfForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = dom.pdfFileInput.files[0];
    if (!file) { Toast.warning("Select a PDF first"); return; }
    setBtnLoading(dom.pdfSubmitBtn, true);
    try {
      const res = await Api.uploadPdf(file);
      Toast.success(extractMsg(res, `"${file.name}" indexed successfully`));
      dom.pdfForm.reset();
      dom.pdfFileName.textContent = "No file selected";
      closeModal(dom.pdfModal);
      await refreshStatus();
    } catch (err) {
      Toast.error(err.message || "Upload failed");
    } finally {
      setBtnLoading(dom.pdfSubmitBtn, false);
    }
  });
}

/* URL upload */
function bindUrlModal() {
  dom.urlForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const link = dom.urlInput.value.trim();
    if (!link) { Toast.warning("Enter a URL"); return; }
    setBtnLoading(dom.urlSubmitBtn, true);
    try {
      const res = await Api.uploadUrl(link);
      Toast.success(extractMsg(res, "URL content indexed successfully"));
      dom.urlForm.reset();
      closeModal(dom.urlModal);
      await refreshStatus();
    } catch (err) {
      Toast.error(err.message || "URL upload failed");
    } finally {
      setBtnLoading(dom.urlSubmitBtn, false);
    }
  });
}

function setBtnLoading(btn, loading) {
  if (!btn) return;
  const label = btn.querySelector(".btn-label");
  const spin = btn.querySelector(".spinner-sm");
  btn.disabled = loading;
  if (label) label.style.opacity = loading ? "0.6" : "1";
  if (spin) spin.classList.toggle("hidden", !loading);
}

function extractMsg(res, fallback) {
  if (res && typeof res === "object") {
    return res.message || res.detail || res.status || fallback;
  }
  if (typeof res === "string" && res.length < 160) return res;
  return fallback;
}

/* Settings */
function bindSettingsModal() {
  dom.saveSettingsBtn.addEventListener("click", () => {
    State.settings.apiBase = dom.apiBaseUrlInput.value.trim();
    State.settings.typing = dom.typingToggle.checked;
    State.settings.autoScroll = dom.autoScrollToggle.checked;
    lsSet(CONFIG.STORAGE.apiBase, State.settings.apiBase);
    lsSet(CONFIG.STORAGE.typing, State.settings.typing ? "1" : "0");
    lsSet(CONFIG.STORAGE.autoscroll, State.settings.autoScroll ? "1" : "0");
    Toast.success("Settings saved");
    closeModal(dom.settingsModal);
    refreshStatus();
  });
}
function fillSettings() {
  dom.apiBaseUrlInput.value = State.settings.apiBase || "";
  dom.typingToggle.checked = State.settings.typing;
  dom.autoScrollToggle.checked = State.settings.autoScroll;
}

/* Knowledge Base modal */
async function openKbModal() {
  openModal(dom.kbModal);
  await loadKbData();
}
async function loadKbData() {
  dom.kbFilesList.innerHTML = `<p class="kb-empty"><span class="spinner-sm" style="display:inline-block"></span> Loading…</p>`;
  dom.kbStatDocs.textContent = "…";
  dom.kbStatChunks.textContent = "…";
  dom.kbStatModel.textContent = "…";
  dom.kbStatStatus.textContent = "…";

  // stats + info in parallel, tolerate failures individually
  const [statsRes, infoRes, filesRes] = await Promise.allSettled([
    Api.adminStats(), Api.adminInfo(), Api.adminFiles(),
  ]);

  const stats = statsRes.status === "fulfilled" ? statsRes.value : {};
  const info = infoRes.status === "fulfilled" ? infoRes.value : {};
  const merged = { ...(info || {}), ...(stats || {}) };

  dom.kbStatDocs.textContent = pick(merged, ["documents", "num_documents", "doc_count", "files", "total_documents", "pdf_count"], "—");
  dom.kbStatChunks.textContent = pick(merged, ["chunks", "num_chunks", "chunk_count", "vectors", "total_chunks", "embeddings", "knowledge_base_chunks"], "—");
  dom.kbStatModel.textContent = pick(merged, ["model", "llm", "model_name", "ollama_model", "embedding_model"], "—");
  dom.kbStatStatus.textContent = pick(merged, ["status", "state", "health"], "Active");

  renderKbFiles(filesRes.status === "fulfilled" ? filesRes.value : null,
                filesRes.status === "rejected" ? filesRes.reason : null);
}
function renderKbFiles(filesData, err) {
  const list = dom.kbFilesList;
  if (err) { list.innerHTML = `<p class="kb-empty">Could not load files: ${escapeHtml(err.message || "error")}</p>`; return; }
  let files = [];
  if (Array.isArray(filesData)) files = filesData;
  else if (filesData && Array.isArray(filesData.files)) files = filesData.files;
  else if (filesData && Array.isArray(filesData.documents)) files = filesData.documents;
  else if (filesData && Array.isArray(filesData.data)) files = filesData.data;

  if (!files.length) { list.innerHTML = `<p class="kb-empty">No documents indexed yet. Upload a PDF or URL to get started.</p>`; return; }

  list.innerHTML = "";
  files.forEach((f) => {
    const name = typeof f === "string" ? f : (f.name || f.filename || f.file || f.title || f.source || f.url || f.id || "Document");
    const meta = typeof f === "object" ? (f.size || f.type || f.chunks || f.pages || f.date || f.created_at || "") : "";
    const isUrlFile = isUrl(name);
    const el = document.createElement("div");
    el.className = "kb-file";
    el.innerHTML = `
      <i class="fa-solid ${isUrlFile ? "fa-globe" : "fa-file-pdf"}"></i>
      <span class="f-name" title="${escapeHtml(String(name))}">${escapeHtml(String(name))}</span>
      ${meta ? `<span class="f-meta">${escapeHtml(String(meta))}</span>` : ""}`;
    list.appendChild(el);
  });
}
function pick(obj, keys, fallback) {
  if (!obj || typeof obj !== "object") return fallback;
  for (const k of keys) {
    if (obj[k] !== undefined && obj[k] !== null && obj[k] !== "") {
      const v = obj[k];
      if (Array.isArray(v)) return v.length;
      if (typeof v === "object") continue;
      return v;
    }
  }
  return fallback;
}

/* ----------------------------- Status / health ------------------- */
function setConnection(state, label) {
  dom.connectionDot.classList.remove("online", "offline");
  if (state === "online") dom.connectionDot.classList.add("online");
  else if (state === "offline") dom.connectionDot.classList.add("offline");
  dom.connectionStatus.textContent = label;
}

async function refreshStatus() {
  setConnection("connecting", "Connecting…");
  try {
    const health = await Api.health();
    const ok = !health || health.alive === true || health.status === undefined ||
      ["ok", "healthy", "up", "running", true, "online"].includes(health.status);
    setConnection(ok ? "online" : "offline", ok ? "Online" : "Degraded");
  } catch {
    setConnection("offline", "Offline");
  }

  // model + KB status (best effort)
  try {
    const [info, stats] = await Promise.allSettled([Api.adminInfo(), Api.adminStats()]);
    const i = info.status === "fulfilled" ? info.value : {};
    const s = stats.status === "fulfilled" ? stats.value : {};
    const merged = { ...(i || {}), ...(s || {}) };
    const model = pick(merged, ["model", "llm", "model_name", "ollama_model", "embedding_model"], null);
    if (model) dom.modelName.textContent = String(model);
    const docs = pick(merged, ["documents", "num_documents", "doc_count", "files", "total_documents", "pdf_count"], null);
    const chunks = pick(merged, ["chunks", "num_chunks", "vectors", "total_chunks", "knowledge_base_chunks"], null);
    if (docs !== null) dom.kbStatus.textContent = `KB: ${docs} docs${chunks !== null ? " · " + chunks + " chunks" : ""}`;
    else if (chunks !== null) dom.kbStatus.textContent = `KB: ${chunks} chunks`;
    else dom.kbStatus.textContent = "KB: ready";
  } catch { /* keep defaults */ }
}

/* ----------------------------- Theme ------------------------------ */
function applyTheme(theme) {
  const isDark = theme !== "light";
  document.documentElement.classList.toggle("dark", isDark);
  dom.themeIcon.className = isDark ? "fa-solid fa-moon" : "fa-solid fa-sun";
  dom.themeLabel.textContent = isDark ? "Dark Theme" : "Light Theme";
  lsSet(CONFIG.STORAGE.theme, isDark ? "dark" : "light");
}
function toggleTheme() {
  const isDark = document.documentElement.classList.contains("dark");
  applyTheme(isDark ? "light" : "dark");
}

/* ----------------------------- Sidebar (mobile) ------------------- */
function openSidebarMobile() {
  dom.sidebar.classList.add("open");
  dom.sidebarBackdrop.classList.remove("hidden");
}
function closeSidebarMobile() {
  dom.sidebar.classList.remove("open");
  dom.sidebarBackdrop.classList.add("hidden");
}

/* ----------------------------- Bindings --------------------------- */
function bindEvents() {
  // composer
  dom.messageInput.addEventListener("input", autoResize);
  dom.messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  dom.sendBtn.addEventListener("click", () => sendMessage());
  dom.stopBtn.addEventListener("click", () => { if (State.abort) State.abort.abort(); });

  // new chat
  dom.newChatBtn.addEventListener("click", () => {
    newChat(true);
    renderHistory();
    renderActiveChat();
    dom.messageInput.focus();
    closeSidebarMobile();
  });
  dom.clearHistoryBtn.addEventListener("click", () => {
    if (State.chats.length && confirm("Delete all conversations? This cannot be undone.")) clearAllChats();
  });

  // sidebar actions
  dom.sidebarUploadPdf.addEventListener("click", () => openModal(dom.pdfModal));
  dom.sidebarUploadUrl.addEventListener("click", () => openModal(dom.urlModal));
  dom.sidebarKnowledgeBase.addEventListener("click", openKbModal);
  dom.sidebarSettings.addEventListener("click", () => { fillSettings(); openModal(dom.settingsModal); });
  dom.themeToggle.addEventListener("click", toggleTheme);

  // composer upload buttons
  dom.inputUploadPdf.addEventListener("click", () => openModal(dom.pdfModal));
  dom.inputUploadUrl.addEventListener("click", () => openModal(dom.urlModal));

  // topbar
  dom.topbarRefresh.addEventListener("click", () => { refreshStatus(); Toast.info("Status refreshed"); });

  // mobile sidebar
  dom.sidebarToggle.addEventListener("click", openSidebarMobile);
  dom.sidebarCloseBtn.addEventListener("click", closeSidebarMobile);
  dom.sidebarBackdrop.addEventListener("click", closeSidebarMobile);

  // KB modal buttons
  dom.kbRefreshBtn.addEventListener("click", loadKbData);
  dom.kbAddBtn.addEventListener("click", () => { closeModal(dom.kbModal); openModal(dom.pdfModal); });

  // modal close (data-close + overlay click + ESC)
  $$("[data-close]").forEach((btn) => btn.addEventListener("click", (e) => {
    const overlay = e.target.closest(".modal-overlay");
    if (overlay) closeModal(overlay);
  }));
  $$(".modal-overlay").forEach((overlay) => overlay.addEventListener("mousedown", (e) => {
    if (e.target === overlay) closeModal(overlay);
  }));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAllModals(); });

  // suggestion cards
  $$(".suggestion-card").forEach((card) =>
    card.addEventListener("click", () => sendMessage(card.dataset.prompt)));

  // modal forms
  bindPdfModal();
  bindUrlModal();
  bindSettingsModal();
}

/* ----------------------------- Init ------------------------------- */
function loadSettings() {
  State.settings.apiBase = lsGet(CONFIG.STORAGE.apiBase, "") || "";
  State.settings.typing = lsGet(CONFIG.STORAGE.typing, "1") !== "0";
  State.settings.autoScroll = lsGet(CONFIG.STORAGE.autoscroll, "1") !== "0";
}

function init() {
  cacheDom();
  configureMarked();
  loadSettings();
  applyTheme(lsGet(CONFIG.STORAGE.theme, "dark"));
  loadChats();
  bindEvents();
  renderHistory();
  renderActiveChat();
  fillSettings();
  autoResize();
  refreshStatus();
  setInterval(refreshStatus, CONFIG.HEALTH_INTERVAL);
  dom.messageInput.focus();
  // eslint-disable-next-line no-console
  console.log("%cCIMS SAGE%c frontend ready.", "color:#3b82f6;font-weight:bold", "color:inherit");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

/* ====================================================
   Travel Presenter — App 主控制器
   ==================================================== */

const App = {
  sessionId: null,
  data: null,
  themes: [],

  /* ── 初始化 ──────────────────────────────────── */
  init() {
    Upload.init();
    this.loadThemes();
  },

  /* ── API 工具 ────────────────────────────────── */
  async api(url, opts = {}) {
    const res = await fetch(url, opts);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res;
  },

  async apiJSON(url, opts = {}) {
    const res = await this.api(url, opts);
    return res.json();
  },

  /* ── 主題載入 ────────────────────────────────── */
  async loadThemes() {
    try {
      const { themes } = await this.apiJSON("/api/themes");
      this.themes = themes;
    } catch (e) {
      console.warn("無法載入主題:", e);
    }
  },

  /* ── 切換畫面 ────────────────────────────────── */
  showEditor(sessionId, data) {
    this.sessionId = sessionId;
    this.data = data;

    document.getElementById("upload-screen").style.display = "none";
    document.getElementById("editor-screen").style.display = "";
    document.getElementById("session-info").style.display = "";
    document.getElementById("session-info").textContent = `Session: ${sessionId}`;
    document.getElementById("btn-new").style.display = "";

    Editor.populate(data);
    Editor.renderThemeSelector(this.themes, data.theme || "soft-cream");
  },

  /* ── 重設 ────────────────────────────────────── */
  reset() {
    this.sessionId = null;
    this.data = null;
    document.getElementById("upload-screen").style.display = "";
    document.getElementById("editor-screen").style.display = "none";
    document.getElementById("session-info").style.display = "none";
    document.getElementById("btn-new").style.display = "none";
    document.getElementById("preview-iframe").style.display = "none";
    document.getElementById("preview-placeholder").style.display = "";
  },

  /* ── 載入範例 ────────────────────────────────── */
  async loadSample() {
    const statusEl = document.getElementById("upload-status");
    const errorEl = document.getElementById("upload-error");
    statusEl.style.display = "flex";
    errorEl.style.display = "none";

    try {
      const { session_id, data } = await this.apiJSON("/api/sample", { method: "POST" });
      this.showEditor(session_id, data);
    } catch (e) {
      errorEl.textContent = e.message;
      errorEl.style.display = "";
    } finally {
      statusEl.style.display = "none";
    }
  },

  /* ── 儲存到後端 ──────────────────────────────── */
  async save() {
    if (!this.sessionId) return;
    const data = Editor.collectFormData();
    this.data = data;

    await this.apiJSON(`/api/session/${this.sessionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  /* ── 重新整理預覽 ────────────────────────────── */
  async refreshPreview() {
    try {
      await this.save();
      Preview.load(this.sessionId);
    } catch (e) {
      alert("預覽失敗：" + e.message);
    }
  },

  /* ── 下載 HTML ───────────────────────────────── */
  async downloadHTML() {
    try {
      await this.save();
      window.open(`/api/session/${this.sessionId}/download/html`, "_blank");
    } catch (e) {
      alert("下載失敗：" + e.message);
    }
  },

  /* ── 下載 PDF ────────────────────────────────── */
  async downloadPDF() {
    const statusEl = document.getElementById("download-status");
    try {
      await this.save();
      statusEl.style.display = "flex";

      const res = await this.api(`/api/session/${this.sessionId}/download/pdf`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = (this.data.title || "presentation") + ".pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("PDF 生成失敗：" + e.message);
    } finally {
      statusEl.style.display = "none";
    }
  },

  /* ── 圖片上傳 ────────────────────────────────── */
  async uploadImage(inputEl, target, pathInputId, thumbId) {
    const file = inputEl.files[0];
    if (!file || !this.sessionId) return;

    const fd = new FormData();
    fd.append("image", file);
    fd.append("target", target);

    try {
      const { path } = await this.apiJSON(
        `/api/session/${this.sessionId}/image`,
        { method: "POST", body: fd }
      );

      // 更新路徑欄位
      document.getElementById(pathInputId).value = path;

      // 更新縮圖
      if (thumbId) {
        const thumb = document.getElementById(thumbId);
        if (thumb) {
          thumb.src = `/uploads/${this.sessionId}/${path}`;
          thumb.style.display = "";
        }
      }
    } catch (e) {
      alert("圖片上傳失敗：" + e.message);
    }
  },
};


/* ── Accordion 切換 ──────────────────────────────── */
function toggleAccordion(headerEl) {
  const acc = headerEl.parentElement;
  const body = acc.querySelector(".accordion-body");
  const arrow = acc.querySelector(".accordion-arrow");
  const isOpen = acc.classList.contains("open");

  if (isOpen) {
    acc.classList.remove("open");
    body.style.display = "none";
    arrow.innerHTML = "&#x25B6;";
  } else {
    acc.classList.add("open");
    body.style.display = "";
    arrow.innerHTML = "&#x25BC;";
  }
}


/* ── 頁面載入 ────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => App.init());

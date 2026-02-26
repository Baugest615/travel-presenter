/* ====================================================
   Travel Presenter — 預覽控制
   ==================================================== */

const Preview = {
  /* ── 載入預覽 ────────────────────────────────── */
  load(sessionId) {
    const iframe = document.getElementById("preview-iframe");
    const placeholder = document.getElementById("preview-placeholder");

    iframe.style.display = "";
    placeholder.style.display = "none";

    // 用 src 載入（避免 CORS 問題）
    iframe.src = `/api/session/${sessionId}/preview?t=${Date.now()}`;

    // iframe 載入後調整縮放
    iframe.onload = () => this.scaleToFit();
  },

  /* ── 自動縮放 iframe ─────────────────────────── */
  scaleToFit() {
    const iframe = document.getElementById("preview-iframe");
    const container = document.getElementById("preview-container");
    if (!iframe || !container) return;

    const containerWidth = container.clientWidth - 32; // padding
    const originalWidth = 1440;

    const scale = Math.min(1, containerWidth / originalWidth);
    iframe.style.transform = `scale(${scale})`;
    iframe.style.transformOrigin = "top left";

    // 設定容器高度以匹配縮放後的 iframe
    try {
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      const bodyHeight = doc.body ? doc.body.scrollHeight : 810;
      iframe.style.height = bodyHeight + "px";
      container.style.minHeight = (bodyHeight * scale + 32) + "px";
    } catch (e) {
      // 跨域時無法取得 contentDocument，用預設高度
      iframe.style.height = "2400px";
    }
  },
};

/* ── 視窗大小改變時重新縮放 ────────────────────── */
window.addEventListener("resize", () => {
  const iframe = document.getElementById("preview-iframe");
  if (iframe && iframe.style.display !== "none") {
    Preview.scaleToFit();
  }
});

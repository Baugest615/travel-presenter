/* ====================================================
   Travel Presenter — 上傳處理
   ==================================================== */

const Upload = {
  init() {
    const box = document.getElementById("upload-box");
    const input = document.getElementById("file-input");
    if (!box || !input) return;

    // 拖放
    box.addEventListener("dragover", (e) => {
      e.preventDefault();
      box.classList.add("drag-over");
    });
    box.addEventListener("dragleave", () => {
      box.classList.remove("drag-over");
    });
    box.addEventListener("drop", (e) => {
      e.preventDefault();
      box.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      if (file) this.upload(file);
    });

    // 檔案選擇
    input.addEventListener("change", () => {
      if (input.files[0]) this.upload(input.files[0]);
      input.value = "";
    });
  },

  async upload(file) {
    const statusEl = document.getElementById("upload-status");
    const errorEl = document.getElementById("upload-error");
    statusEl.style.display = "flex";
    errorEl.style.display = "none";

    const fd = new FormData();
    fd.append("file", file);

    try {
      const { session_id, data } = await App.apiJSON("/api/upload", {
        method: "POST",
        body: fd,
      });
      App.showEditor(session_id, data);
    } catch (e) {
      errorEl.textContent = e.message;
      errorEl.style.display = "";
    } finally {
      statusEl.style.display = "none";
    }
  },
};

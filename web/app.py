"""Travel Presenter Web — Flask 主應用"""
import logging
import sys
import re
import json
import uuid
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# 確保能 import travel_presenter 套件
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from werkzeug.utils import secure_filename
from travel_presenter.models import TripData
from travel_presenter.parser import load_from_json, parse_docx
from travel_presenter.renderer.html_renderer import HtmlRenderer
from travel_presenter.themes.registry import list_themes, get_theme_css

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

# 上傳與暫存目錄
UPLOAD_DIR = PROJECT_ROOT / "web" / "_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Session 儲存（個人使用，記憶體即可）
sessions: dict[str, dict] = {}


# ── 頁面 ────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── 上傳 ────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_file():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="未提供檔案"), 400

    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)

    # 儲存原始檔案
    safe_name = secure_filename(f.filename) or "upload"
    save_path = session_dir / safe_name
    f.save(str(save_path))

    # 解析
    suffix = save_path.suffix.lower()
    try:
        if suffix == ".json":
            trip = load_from_json(save_path)
        elif suffix in (".docx", ".doc"):
            trip = parse_docx(save_path)
        else:
            return jsonify(error=f"不支援的格式: {suffix}，僅支援 .json 和 .docx"), 400
    except (ValueError, Exception) as e:
        return jsonify(error=f"解析失敗：{e}"), 400

    data = trip.model_dump(exclude_none=True)
    sessions[session_id] = data

    return jsonify(session_id=session_id, data=data)


# ── 範例資料 ────────────────────────────────────

@app.route("/api/sample", methods=["POST"])
def load_sample():
    sample_path = PROJECT_ROOT / "examples" / "hokkaido_sample.json"
    if not sample_path.exists():
        return jsonify(error="找不到範例資料"), 404

    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    (session_dir / "images").mkdir(exist_ok=True)

    trip = load_from_json(sample_path)
    data = trip.model_dump(exclude_none=True)
    sessions[session_id] = data

    return jsonify(session_id=session_id, data=data)


# ── Session CRUD ────────────────────────────────

@app.route("/api/session/<session_id>")
def get_session(session_id):
    data = sessions.get(session_id)
    if not data:
        return jsonify(error="Session 不存在"), 404
    return jsonify(data=data)


@app.route("/api/session/<session_id>", methods=["PUT"])
def update_session(session_id):
    if session_id not in sessions:
        return jsonify(error="Session 不存在"), 404

    data = request.get_json()
    if not data:
        return jsonify(error="未提供資料"), 400

    # 驗證 TripData 結構
    try:
        trip = TripData(**data)
        sessions[session_id] = trip.model_dump(exclude_none=True)
    except Exception as e:
        return jsonify(error=f"資料格式錯誤：{e}"), 422

    return jsonify(ok=True)


# ── 預覽 ────────────────────────────────────────

@app.route("/api/session/<session_id>/preview")
def preview(session_id):
    data = sessions.get(session_id)
    if not data:
        return "Session 不存在", 404

    trip = TripData(**data)
    renderer = HtmlRenderer()
    images_base = f"/uploads/{session_id}"
    html = renderer.render(trip, images_base=images_base)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


# ── 下載 HTML ───────────────────────────────────

@app.route("/api/session/<session_id>/download/html")
def download_html(session_id):
    data = sessions.get(session_id)
    if not data:
        return "Session 不存在", 404

    trip = TripData(**data)
    renderer = HtmlRenderer()

    # HTML 下載用絕對路徑讓圖片可離線顯示
    session_dir = UPLOAD_DIR / session_id
    images_base = str(session_dir.resolve().as_posix())
    html = renderer.render(trip, images_base=images_base)

    session_dir.mkdir(exist_ok=True)
    html_path = session_dir / "presentation.html"
    html_path.write_text(html, encoding="utf-8")

    filename = f"{trip.title or 'presentation'}.html"
    return send_file(str(html_path), as_attachment=True, download_name=filename)


# ── 下載 PDF ────────────────────────────────────

@app.route("/api/session/<session_id>/download/pdf")
def download_pdf(session_id):
    data = sessions.get(session_id)
    if not data:
        return jsonify(error="Session 不存在"), 404

    try:
        from travel_presenter.renderer.pdf_renderer import PdfRenderer
    except Exception:
        return jsonify(error="PDF 渲染需要 playwright 套件，請先安裝"), 500

    trip = TripData(**data)
    renderer = HtmlRenderer()

    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    images_base = str(session_dir.resolve().as_posix())
    html = renderer.render(trip, images_base=images_base)

    output_path = str(session_dir / "output.pdf")
    try:
        pdf_renderer = PdfRenderer()
        pdf_renderer.render(html, output_path, base_dir=str(session_dir))
    except Exception as e:
        return jsonify(error=f"PDF 渲染失敗：{e}"), 500

    filename = f"{trip.title or 'presentation'}.pdf"
    return send_file(output_path, as_attachment=True, download_name=filename)


# ── 圖片上傳 ────────────────────────────────────

@app.route("/api/session/<session_id>/image", methods=["POST"])
def upload_image(session_id):
    if session_id not in sessions:
        return jsonify(error="Session 不存在"), 404

    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify(error="未提供圖片"), 400

    target = request.form.get("target", "misc")

    session_dir = UPLOAD_DIR / session_id / "images"
    session_dir.mkdir(exist_ok=True)

    # 安全的檔案名
    ext = Path(f.filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return jsonify(error=f"不支援的圖片格式: {ext}"), 400

    filename = f"{target}{ext}"
    save_path = session_dir / filename
    f.save(str(save_path))

    relative_path = f"images/{filename}"
    return jsonify(path=relative_path)


# ── 提供上傳的圖片 ──────────────────────────────

@app.route("/uploads/<path:filepath>")
def serve_upload(filepath):
    return send_from_directory(str(UPLOAD_DIR), filepath)


# ── 主題 API ────────────────────────────────────

@app.route("/api/themes")
def get_themes():
    themes = list_themes()
    result = []
    for t in themes:
        colors = {}
        if t["available"]:
            try:
                css = get_theme_css(t["id"])
                for var in ("bg-primary", "charcoal", "accent", "accent-light"):
                    match = re.search(rf'--{var}:\s*([^;]+);', css)
                    if match:
                        colors[var] = match.group(1).strip()
            except Exception:
                pass
        result.append({
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "available": t["available"],
            "colors": colors,
        })
    return jsonify(themes=result)


# ── 啟動 ────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    port = 5500
    logger.info("Travel Presenter Web 已啟動: http://localhost:%d", port)
    app.run(host="127.0.0.1", port=port, debug=False)

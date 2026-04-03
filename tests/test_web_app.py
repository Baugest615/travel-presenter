"""Flask Web App 整合測試 — 覆蓋所有 11 個 API 路由"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 確保 project root 在 sys.path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app, sessions, UPLOAD_DIR


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client():
    """Flask test client — 每個測試隔離 session 狀態"""
    app.config["TESTING"] = True
    sessions.clear()
    with app.test_client() as c:
        yield c
    sessions.clear()


@pytest.fixture
def sample_json_bytes() -> bytes:
    """讀取範例 JSON 為 bytes，供上傳測試用"""
    path = EXAMPLES_DIR / "hokkaido_sample.json"
    return path.read_bytes()


@pytest.fixture
def minimal_json_bytes() -> bytes:
    """最小合法 TripData JSON"""
    data = {
        "title": "測試行程",
        "date_range": "2026/04/01 — 04/03",
        "destination": "東京",
    }
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


@pytest.fixture
def session_with_data(client, sample_json_bytes):
    """建立一個已有資料的 session，回傳 (session_id, data)"""
    resp = client.post("/api/upload", data={
        "file": (io.BytesIO(sample_json_bytes), "sample.json"),
    }, content_type="multipart/form-data")
    body = resp.get_json()
    return body["session_id"], body["data"]


# ── 1. GET / — 首頁 ──────────────────────────────────────

class TestIndex:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"html" in resp.data.lower()


# ── 2. POST /api/upload — 檔案上傳 ───────────────────────

class TestUpload:
    def test_upload_json_success(self, client, sample_json_bytes):
        resp = client.post("/api/upload", data={
            "file": (io.BytesIO(sample_json_bytes), "hokkaido.json"),
        }, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "session_id" in body
        assert "data" in body
        assert body["data"]["title"]  # 有標題

    def test_upload_no_file(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 400
        assert "未提供檔案" in resp.get_json()["error"]

    def test_upload_unsupported_format(self, client):
        resp = client.post("/api/upload", data={
            "file": (io.BytesIO(b"hello"), "readme.txt"),
        }, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "不支援" in resp.get_json()["error"]

    def test_upload_invalid_json_raises_system_exit(self, client):
        """json_loader 對無效 JSON 呼叫 sys.exit(1) — 已知設計問題，
        Web 層未捕獲 SystemExit 導致請求崩潰而非回傳 400。
        此測試記錄現狀，建議未來將 json_loader 改為 raise ValueError。"""
        with pytest.raises(SystemExit):
            client.post("/api/upload", data={
                "file": (io.BytesIO(b"not json {{{"), "bad.json"),
            }, content_type="multipart/form-data")

    def test_upload_docx_success(self, client, make_docx):
        """上傳合法 DOCX（最小可解析的結構）"""
        docx_path = make_docx(
            tables=[{"rows": [["D1★ 台北→東京", ""], ["台北出發前往東京", "（早）敬請自理（午）機上餐食（晚）飯店晚餐\n【宿】東京王子飯店"]]}],
        )
        with open(docx_path, "rb") as f:
            resp = client.post("/api/upload", data={
                "file": (f, "trip.docx"),
            }, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "session_id" in body


# ── 3. POST /api/sample — 範例載入 ───────────────────────

class TestSample:
    def test_load_sample_success(self, client):
        resp = client.post("/api/sample")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "session_id" in body
        assert body["data"]["destination"]


# ── 4. GET /api/session/<id> — 讀取 session ──────────────

class TestGetSession:
    def test_get_existing_session(self, client, session_with_data):
        sid, data = session_with_data
        resp = client.get(f"/api/session/{sid}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == data["title"]

    def test_get_nonexistent_session(self, client):
        resp = client.get("/api/session/no-such-id")
        assert resp.status_code == 404


# ── 5. PUT /api/session/<id> — 更新 session ──────────────

class TestUpdateSession:
    def test_update_session_success(self, client, session_with_data):
        sid, data = session_with_data
        data["title"] = "更新後的標題"
        resp = client.put(
            f"/api/session/{sid}",
            data=json.dumps(data),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        # 確認真的更新了
        check = client.get(f"/api/session/{sid}")
        assert check.get_json()["data"]["title"] == "更新後的標題"

    def test_update_nonexistent_session(self, client):
        resp = client.put(
            "/api/session/no-such-id",
            data=json.dumps({"title": "x", "date_range": "x", "destination": "x"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_update_invalid_data(self, client, session_with_data):
        sid, _ = session_with_data
        # 缺少必填欄位
        resp = client.put(
            f"/api/session/{sid}",
            data=json.dumps({"bad_field": "only"}),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_update_no_body(self, client, session_with_data):
        sid, _ = session_with_data
        resp = client.put(f"/api/session/{sid}")
        # 無 Content-Type: application/json → Flask 回 415 Unsupported Media Type
        assert resp.status_code in (400, 415)


# ── 6. GET /api/session/<id>/preview — HTML 預覽 ─────────

class TestPreview:
    def test_preview_renders_html(self, client, session_with_data):
        sid, _ = session_with_data
        resp = client.get(f"/api/session/{sid}/preview")
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
        assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()

    def test_preview_nonexistent_session(self, client):
        resp = client.get("/api/session/no-such-id/preview")
        assert resp.status_code == 404


# ── 7. GET /api/session/<id>/download/html — 下載 HTML ───

class TestDownloadHtml:
    def test_download_html_success(self, client, session_with_data):
        sid, data = session_with_data
        resp = client.get(f"/api/session/{sid}/download/html")
        assert resp.status_code == 200
        # 應是檔案下載
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert len(resp.data) > 100  # 確實有內容

    def test_download_html_nonexistent(self, client):
        resp = client.get("/api/session/no-such-id/download/html")
        assert resp.status_code == 404


# ── 8. GET /api/session/<id>/download/pdf — 下載 PDF ─────

class TestDownloadPdf:
    def test_download_pdf_nonexistent_session(self, client):
        resp = client.get("/api/session/no-such-id/download/pdf")
        assert resp.status_code == 404

    def test_download_pdf_import_failure(self, client, session_with_data):
        """模擬 PdfRenderer import 失敗（例如 playwright 未安裝）"""
        sid, _ = session_with_data

        # app.py download_pdf() 做 lazy import：
        #   try:
        #       from travel_presenter.renderer.pdf_renderer import PdfRenderer
        #   except Exception:
        #       return jsonify(error="PDF 渲染需要 playwright 套件..."), 500
        #
        # 注入一個 raise ImportError 的假模組
        original = sys.modules.get("travel_presenter.renderer.pdf_renderer")
        # 移除快取讓 import 重新執行
        sys.modules.pop("travel_presenter.renderer.pdf_renderer", None)

        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        def fake_import(name, *args, **kwargs):
            if name == "travel_presenter.renderer.pdf_renderer":
                raise ImportError("No module named 'playwright'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            resp = client.get(f"/api/session/{sid}/download/pdf")

        assert resp.status_code == 500
        body = resp.get_json()
        assert body is not None
        assert "PDF" in body.get("error", "") or "playwright" in body.get("error", "").lower()

        # 清理
        if original is not None:
            sys.modules["travel_presenter.renderer.pdf_renderer"] = original


# ── 9. POST /api/session/<id>/image — 圖片上傳 ───────────

class TestImageUpload:
    def test_upload_image_success(self, client, session_with_data):
        sid, _ = session_with_data
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal PNG header
        resp = client.post(f"/api/session/{sid}/image", data={
            "image": (io.BytesIO(fake_png), "cover.png"),
            "target": "cover",
        }, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "path" in body
        assert "cover.png" in body["path"]

    def test_upload_image_no_file(self, client, session_with_data):
        sid, _ = session_with_data
        resp = client.post(f"/api/session/{sid}/image")
        assert resp.status_code == 400

    def test_upload_image_unsupported_format(self, client, session_with_data):
        sid, _ = session_with_data
        resp = client.post(f"/api/session/{sid}/image", data={
            "image": (io.BytesIO(b"data"), "doc.pdf"),
            "target": "cover",
        }, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "不支援" in resp.get_json()["error"]

    def test_upload_image_nonexistent_session(self, client):
        resp = client.post("/api/session/no-such-id/image", data={
            "image": (io.BytesIO(b"\x89PNG"), "img.png"),
        }, content_type="multipart/form-data")
        assert resp.status_code == 404


# ── 10. GET /uploads/<path> — 圖片提供 ───────────────────

class TestServeUpload:
    def test_serve_uploaded_image(self, client, session_with_data):
        """上傳圖片後能透過 /uploads/ 取回"""
        sid, _ = session_with_data
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        client.post(f"/api/session/{sid}/image", data={
            "image": (io.BytesIO(fake_png), "day1.png"),
            "target": "day1",
        }, content_type="multipart/form-data")

        resp = client.get(f"/uploads/{sid}/images/day1.png")
        assert resp.status_code == 200
        assert resp.data[:4] == b"\x89PNG"

    def test_serve_nonexistent_file(self, client):
        resp = client.get("/uploads/fake/no-file.png")
        assert resp.status_code == 404


# ── 11. GET /api/themes — 主題列表 ────────────────────────

class TestThemes:
    def test_list_themes(self, client):
        resp = client.get("/api/themes")
        assert resp.status_code == 200
        themes = resp.get_json()["themes"]
        assert len(themes) >= 3
        # 每個主題應有基本欄位
        for t in themes:
            assert "id" in t
            assert "name" in t
            assert "available" in t

    def test_themes_have_colors(self, client):
        resp = client.get("/api/themes")
        themes = resp.get_json()["themes"]
        available = [t for t in themes if t["available"]]
        assert len(available) >= 1
        # 可用主題應有顏色資訊
        for t in available:
            assert len(t.get("colors", {})) > 0

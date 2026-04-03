"""Playwright PDF 渲染器 — 將 HTML 轉為 PDF"""
import logging
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class PdfRenderer:
    SLIDE_WIDTH = 1440
    SLIDE_HEIGHT = 810

    def render(self, html_content: str, output_path: str,
               base_dir: str | None = None) -> str:
        """HTML string → PDF file"""
        if sync_playwright is None:
            logger.error("PDF 渲染需要 playwright 套件")
            logger.error("  安裝方式：")
            logger.error("    pip install playwright")
            logger.error("    playwright install chromium")
            sys.exit(1)

        temp_html = None
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as e:
                    logger.error("無法啟動瀏覽器 — %s", e)
                    logger.error("  請確認已安裝 Chromium：playwright install chromium")
                    sys.exit(1)

                page = browser.new_page(
                    viewport={"width": self.SLIDE_WIDTH, "height": self.SLIDE_HEIGHT}
                )

                if base_dir:
                    temp_html = Path(base_dir) / "_temp_render.html"
                    temp_html.write_text(html_content, encoding="utf-8")
                    url = f"file:///{temp_html.resolve().as_posix()}"
                    page.goto(url, timeout=60000)
                else:
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".html", delete=False, encoding="utf-8"
                    ) as f:
                        f.write(html_content)
                        temp_path = f.name
                    temp_html = Path(temp_path)
                    page.goto(f"file:///{temp_html.resolve().as_posix()}", timeout=60000)

                # 等待頁面就緒（domcontentloaded 比 networkidle 更快且可靠）
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)  # 等待字體載入

                # 生成 PDF
                page.pdf(
                    path=output_path,
                    width=f"{self.SLIDE_WIDTH}px",
                    height=f"{self.SLIDE_HEIGHT}px",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )

                browser.close()
        finally:
            # 確保臨時檔清理
            if temp_html and temp_html.exists():
                try:
                    temp_html.unlink()
                except OSError:
                    pass

        return output_path

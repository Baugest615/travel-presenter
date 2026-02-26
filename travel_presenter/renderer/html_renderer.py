"""Jinja2 HTML 渲染引擎 — 將 TripData 轉為完整的 HTML 簡報"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..models import TripData
from ..themes.registry import get_theme_css


# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"


class HtmlRenderer:
    def __init__(self, templates_dir: Path | str | None = None):
        tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(tdir)),
            autoescape=False,  # HTML 模板不需要自動轉義
        )

    def render(self, trip: TripData, images_base: str = "") -> str:
        """將整份行程渲染為單一 HTML 文件（多頁 slide）"""
        theme_name = trip.theme or "soft-cream"
        theme_css = get_theme_css(theme_name)

        # 準備圖片路徑前綴
        prefix = (images_base.rstrip("/") + "/") if images_base else ""

        # 收集總覽頁的 4 張圖片
        overview_images = []
        for day in trip.days:
            if day.image:
                overview_images.append(prefix + day.image)
            if day.image_alt:
                overview_images.append(prefix + day.image_alt)
        overview_images = overview_images[:4]

        # 找出航班頁使用的圖片（取第一個有圖的 day 或 cover）
        flight_image = ""
        for day in trip.days:
            if day.image and day.layout != "hero":
                flight_image = prefix + day.image
                break

        # 組裝所有頁面
        pages_html = []
        page_num = 1

        # 1. 封面
        trip_ctx = self._trip_with_prefix(trip, prefix)
        pages_html.append(self._render_page("pages/cover.html", trip=trip_ctx, theme_css=theme_css))
        page_num += 1

        # 2. 引言（可選）
        if trip.quote:
            pages_html.append(self._render_page(
                "pages/quote.html", trip=trip_ctx, page_num=page_num, theme_css=theme_css))
            page_num += 1

        # 3. 航班資訊
        if trip.flights:
            pages_html.append(self._render_page(
                "pages/flight_info.html",
                trip=trip_ctx,
                page_num=page_num,
                flight_image=flight_image,
                badge_title=f"{trip.days[-1].day}日{trip.destination}",
                badge_sub="FLIGHT INFORMATION",
                badge_style="", badge_title_style="", badge_sub_style="",
                theme_css=theme_css,
            ))
            page_num += 1

        # 4. 行程總覽
        pages_html.append(self._render_page(
            "pages/overview.html",
            trip=trip_ctx,
            page_num=page_num,
            overview_images=overview_images,
            badge_title="行程總覽",
            badge_sub="ITINERARY OVERVIEW",
            badge_style="", badge_title_style="", badge_sub_style="",
            theme_css=theme_css,
        ))
        page_num += 1

        # 5. 每日行程
        for day in trip.days:
            layout = day.layout or "split"
            template = f"pages/day_{layout}.html"

            # 加上圖片前綴
            day_ctx = day.model_copy()
            if day_ctx.image:
                day_ctx.image = prefix + day_ctx.image
            if day_ctx.image_alt:
                day_ctx.image_alt = prefix + day_ctx.image_alt

            badge_sub = (day.title_en or day.route or "").upper()
            if layout == "hero":
                # hero 佈局會多產生一頁
                pages_html.append(self._render_page(
                    template,
                    day=day_ctx,
                    trip=trip_ctx,
                    page_num=page_num,
                    badge_title=f"Day {day.day} — {day.date}",
                    badge_sub=badge_sub,
                    badge_style="", badge_title_style="", badge_sub_style="",
                    theme_css=theme_css,
                ))
                page_num += 2  # hero 佔兩頁
            else:
                pages_html.append(self._render_page(
                    template,
                    day=day_ctx,
                    trip=trip_ctx,
                    page_num=page_num,
                    badge_title=f"Day {day.day} — {day.date}",
                    badge_sub=badge_sub,
                    badge_style="", badge_title_style="", badge_sub_style="",
                    theme_css=theme_css,
                ))
                page_num += 1

        # 6. 住宿一覽
        if trip.hotels:
            pages_html.append(self._render_page(
                "pages/hotel_overview.html",
                trip=trip_ctx,
                page_num=page_num,
                badge_title="住宿一覽",
                badge_sub="ACCOMMODATION",
                badge_style="", badge_title_style="", badge_sub_style="",
                theme_css=theme_css,
            ))
            page_num += 1

        # 7. 結尾
        pages_html.append(self._render_page(
            "pages/ending.html", trip=trip_ctx, theme_css=theme_css))

        # 組合成完整 HTML
        return self._wrap_full_html(trip, theme_css, pages_html)

    def _render_page(self, template_name: str, **kwargs) -> str:
        """渲染單個頁面模板"""
        tmpl = self.env.get_template(template_name)
        return tmpl.render(**kwargs)

    def _wrap_full_html(self, trip: TripData, theme_css: str, pages: list[str]) -> str:
        """用 base.html 包裝所有頁面"""
        base = self.env.get_template("base.html")
        content_html = "\n".join(pages)
        return base.render(
            trip=trip,
            theme_css=theme_css,
            content=content_html,
        )

    def _trip_with_prefix(self, trip: TripData, prefix: str) -> TripData:
        """為 trip 的圖片路徑加上前綴"""
        trip_copy = trip.model_copy()
        if trip_copy.cover_image:
            trip_copy.cover_image = prefix + trip_copy.cover_image
        if trip_copy.ending_image:
            trip_copy.ending_image = prefix + trip_copy.ending_image
        return trip_copy

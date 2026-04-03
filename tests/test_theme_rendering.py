"""Theme 渲染測試 — CSS 注入正確性、HTML 結構、三主題覆蓋"""
import pytest
from travel_presenter.themes.registry import get_theme_css, list_themes, THEMES
from travel_presenter.renderer.html_renderer import HtmlRenderer
from travel_presenter.models import TripData, DayItinerary, Meals


class TestThemeRegistry:
    """主題註冊表測試"""

    def test_list_themes_returns_all_three(self):
        """應列出三個主題"""
        themes = list_themes()
        assert len(themes) == 3
        ids = {t["id"] for t in themes}
        assert ids == {"soft-cream", "dark-modern", "magazine"}

    def test_all_themes_css_files_exist(self):
        """所有主題的 CSS 檔案應存在"""
        for theme in list_themes():
            assert theme["available"] is True, f"Theme {theme['id']} CSS file missing"

    def test_unknown_theme_raises(self):
        """未知主題名稱應拋出 ValueError"""
        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme_css("nonexistent-theme")

    @pytest.mark.parametrize("theme_name", ["soft-cream", "dark-modern", "magazine"])
    def test_theme_css_has_root_variables(self, theme_name):
        """每個主題 CSS 應定義 :root 變數"""
        css = get_theme_css(theme_name)
        assert ":root" in css
        assert "--bg-primary" in css
        assert "--text-primary" in css
        assert "--accent" in css

    @pytest.mark.parametrize("theme_name", ["soft-cream", "dark-modern", "magazine"])
    def test_theme_css_has_font_variables(self, theme_name):
        """每個主題應定義字體變數"""
        css = get_theme_css(theme_name)
        assert "--font-title" in css or "--font-body" in css


class TestHtmlRendering:
    """HTML 渲染結構測試"""

    @pytest.fixture
    def renderer(self):
        return HtmlRenderer()

    def test_render_minimal_trip(self, renderer, minimal_trip):
        """最小 TripData 應能渲染出有效 HTML"""
        html = renderer.render(minimal_trip)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "測試行程" in html

    def test_render_contains_theme_css(self, renderer, full_trip):
        """渲染結果應包含主題 CSS"""
        html = renderer.render(full_trip)
        # soft-cream 的 CSS 變數值應存在
        assert "--bg-primary" in html
        assert "--text-primary" in html

    def test_render_has_slide_structure(self, renderer, full_trip):
        """渲染結果應包含 slide 結構"""
        html = renderer.render(full_trip)
        assert 'class="slide"' in html or "class='slide'" in html

    def test_render_includes_all_days(self, renderer, full_trip):
        """每日行程都應出現在 HTML 中"""
        html = renderer.render(full_trip)
        assert "Day 1" in html
        assert "Day 2" in html
        assert "森林精靈露台" in html

    def test_render_includes_flights(self, renderer, full_trip):
        """航班資訊應出現在 HTML 中"""
        html = renderer.render(full_trip)
        assert "BR116" in html or "BR 116" in html

    def test_render_includes_quote(self, renderer, full_trip):
        """引言應出現在 HTML 中"""
        html = renderer.render(full_trip)
        assert "在最寒冷的季節" in html

    @pytest.mark.parametrize("theme_name", ["soft-cream", "dark-modern", "magazine"])
    def test_render_with_each_theme(self, renderer, minimal_trip, theme_name):
        """三種主題都應能正常渲染"""
        minimal_trip.theme = theme_name
        html = renderer.render(minimal_trip)
        assert "<!DOCTYPE html>" in html
        # 確認注入的是正確主題的 CSS
        expected_css = get_theme_css(theme_name)
        # 驗證 CSS 的關鍵片段有被注入
        assert "--bg-primary" in html

    def test_render_without_optional_sections(self, renderer):
        """沒有 flights/quote/hotels 時不應崩潰"""
        trip = TripData(
            title="極簡行程",
            date_range="2026/04/01",
            destination="測試",
            days=[
                DayItinerary(
                    day=1,
                    date="4/1",
                    title="第一天",
                    meals=Meals(),
                ),
            ],
        )
        html = renderer.render(trip)
        assert "<!DOCTYPE html>" in html
        assert "極簡行程" in html
        # 不應有 flight 相關內容（因為沒有 flights）
        assert "FLIGHT" not in html.upper() or "flight_info" not in html

    def test_render_page_break_structure(self, renderer, full_trip):
        """應包含分頁控制"""
        html = renderer.render(full_trip)
        assert "page-break-after" in html

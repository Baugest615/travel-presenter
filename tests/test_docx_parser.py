"""DOCX Parser 韌性測試 — 畸形檔案、缺欄位、邊界條件"""
import pytest
from pathlib import Path

from travel_presenter.parser.docx_parser import (
    parse_docx,
    _classify_table,
    _parse_day_table,
    _extract_title_from_route,
    _infer_airline_name,
    _infer_destination,
)
from travel_presenter.models import TripData


class TestParseDocxErrorHandling:
    """畸形 DOCX 輸入的錯誤處理"""

    def test_nonexistent_file_raises(self):
        """不存在的檔案應拋出 ValueError"""
        with pytest.raises(ValueError, match="無法開啟"):
            parse_docx("/tmp/definitely_not_a_real_file_12345.docx")

    def test_corrupted_file_raises(self, tmp_path):
        """損毀的檔案（非 DOCX 格式）應拋出 ValueError"""
        bad_file = tmp_path / "corrupted.docx"
        bad_file.write_text("this is not a docx file")
        with pytest.raises(ValueError, match="無法開啟"):
            parse_docx(bad_file)

    def test_empty_docx_returns_fallback(self, make_docx):
        """空白 DOCX（無表格無段落）應回傳 fallback TripData"""
        path = make_docx(tables=[], paragraphs=[])
        result = parse_docx(path)
        assert isinstance(result, TripData)
        assert result.destination == "旅遊"  # fallback destination
        assert len(result.days) == 0
        assert len(result.flights) == 0

    def test_binary_garbage_file_raises(self, tmp_path):
        """純二進位垃圾應拋出 ValueError"""
        garbage = tmp_path / "garbage.docx"
        garbage.write_bytes(b"\x00\x01\x02\xff" * 100)
        with pytest.raises(ValueError, match="無法開啟"):
            parse_docx(garbage)


class TestParseDocxDayTable:
    """每日行程表格解析"""

    def test_standard_day_table(self, make_docx):
        """標準 2×1 日行程表格應正確解析"""
        path = make_docx(tables=[{
            "rows": [
                ["D1★ 桃園機場 → 新千歲機場 → 富良野"],
                ["（早）機上餐食（午）拉麵定食（晚）飯店自助餐\n【宿】富良野王子大飯店"],
            ]
        }])
        result = parse_docx(path)
        assert len(result.days) == 1
        day = result.days[0]
        assert day.day == 1
        assert "富良野" in day.route
        assert day.meals.breakfast == "機上餐食"
        assert day.meals.lunch == "拉麵定食"
        assert day.hotel is not None
        assert "富良野王子" in day.hotel.name

    def test_day_without_meals(self, make_docx):
        """缺少餐食資訊的日行程不應崩潰"""
        path = make_docx(tables=[{
            "rows": [
                ["D1 東京市區觀光"],
                ["自由活動\n【宿】東京灣希爾頓"],
            ]
        }])
        result = parse_docx(path)
        assert len(result.days) == 1
        # 沒有匹配 RE_MEALS，應保持預設值
        assert result.days[0].meals.breakfast == "敬請自理"

    def test_day_without_hotel(self, make_docx):
        """缺少住宿資訊的日行程不應崩潰"""
        path = make_docx(tables=[{
            "rows": [
                ["D7 新千歲機場 → 桃園機場"],
                ["（早）飯店早餐（午）機上餐食（晚）溫暖的家"],
            ]
        }])
        result = parse_docx(path)
        assert len(result.days) == 1
        # 沒有【宿】標記，hotel 應為 None
        assert result.days[0].hotel is None

    def test_skip_warm_home_hotel(self, make_docx):
        """「溫暖的家」應被過濾掉"""
        path = make_docx(tables=[{
            "rows": [
                ["D5 返程"],
                ["（早）飯店早餐（午）機上（晚）自理\n【宿】溫暖的家"],
            ]
        }])
        result = parse_docx(path)
        assert len(result.days) == 1
        # 「溫暖的家」在 _SKIP_HOTELS 中，應被清除
        assert result.days[0].hotel is None


class TestDocxHelperFunctions:
    """輔助函式單元測試"""

    def test_extract_title_filters_airports(self):
        """路線標題應過濾掉機場"""
        result = _extract_title_from_route("桃園機場 → 新千歲機場 → 富良野")
        assert "桃園" not in result
        assert "富良野" in result

    def test_extract_title_single_destination(self):
        """單一目的地路線"""
        result = _extract_title_from_route("富良野 → 美瑛 → 旭川")
        assert "富良野" in result

    def test_infer_airline_known_codes(self):
        """已知航空公司代碼應回傳中文名"""
        assert _infer_airline_name("BR") == "長榮航空"
        assert _infer_airline_name("CI") == "中華航空"
        assert _infer_airline_name("JL") == "日本航空"
        assert _infer_airline_name("NH") == "全日空"

    def test_infer_airline_unknown_code(self):
        """未知代碼應原樣回傳"""
        assert _infer_airline_name("ZZ") == "ZZ"

    def test_infer_destination_hokkaido(self):
        """北海道關鍵字應推斷為北海道"""
        days = [{"route": "桃園 → 北海道新千歲"}, {"route": "北海道富良野 → 旭川"}]
        result = _infer_destination(days, [])
        assert result == "北海道"

    def test_infer_destination_fallback(self):
        """無法推斷時 fallback 為「旅遊」"""
        days = [{"route": "A → B"}]
        result = _infer_destination(days, [])
        assert result == "旅遊"


class TestDocxCJKEdgeCases:
    """CJK 字元邊界條件"""

    def test_fullwidth_parentheses_meals(self, make_docx):
        """全形括號的餐食仍應正確解析"""
        path = make_docx(tables=[{
            "rows": [
                ["D1 東京"],
                ["（早）飯店早餐（午）壽司（晚）居酒屋\n【宿】東京飯店"],
            ]
        }])
        result = parse_docx(path)
        assert result.days[0].meals.breakfast == "飯店早餐"

    def test_halfwidth_parentheses_meals(self, make_docx):
        """半形括號的餐食也應正確解析（RE_MEALS 支援兩種）"""
        path = make_docx(tables=[{
            "rows": [
                ["D1 東京"],
                ["(早)飯店早餐(午)壽司(晚)居酒屋\n【宿】東京飯店"],
            ]
        }])
        result = parse_docx(path)
        assert result.days[0].meals.breakfast == "飯店早餐"

    def test_star_variants_in_day_title(self, make_docx):
        """★ 和 ☆ 都應被清理"""
        path = make_docx(tables=[{
            "rows": [
                ["D2☆ 大阪城 → 心齋橋"],
                ["（早）飯店（午）大阪燒（晚）螃蟹道樂"],
            ]
        }])
        result = parse_docx(path)
        assert result.days[0].day == 2
        assert "☆" not in result.days[0].route

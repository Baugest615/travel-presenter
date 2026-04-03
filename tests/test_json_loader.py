"""JSON Parser 韌性測試 — 缺欄位、CJK 編碼、schema 驗證"""
import json
import pytest
from pathlib import Path

from travel_presenter.parser.json_loader import load_from_json
from travel_presenter.models import TripData


class TestJsonLoaderHappyPath:
    """正常載入"""

    def test_load_sample_json(self, sample_json_path):
        """範例 hokkaido_sample.json 應成功載入"""
        result = load_from_json(sample_json_path)
        assert isinstance(result, TripData)
        assert result.destination == "北海道"
        assert len(result.days) == 7
        assert len(result.flights) == 2

    def test_load_minimal_valid_json(self, make_json):
        """只有必填欄位的 JSON 應成功載入"""
        data = {
            "title": "測試",
            "date_range": "2026/04/01",
            "destination": "東京",
        }
        path = make_json(data)
        result = load_from_json(path)
        assert result.title == "測試"
        assert result.destination == "東京"
        assert len(result.days) == 0  # default_factory=list


class TestJsonLoaderErrorHandling:
    """錯誤處理 — json_loader 用 sys.exit(1) 處理錯誤"""

    def test_nonexistent_file_exits(self):
        """不存在的檔案應 sys.exit(1)"""
        with pytest.raises(SystemExit) as exc_info:
            load_from_json("/tmp/no_such_file_12345.json")
        assert exc_info.value.code == 1

    def test_malformed_json_exits(self, tmp_path):
        """語法錯誤的 JSON 應 sys.exit(1)"""
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json content!!!", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            load_from_json(bad)
        assert exc_info.value.code == 1

    def test_missing_required_field_exits(self, make_json):
        """缺少必填欄位（title）應 sys.exit(1)"""
        data = {
            "date_range": "2026/04/01",
            "destination": "東京",
            # 缺 title
        }
        path = make_json(data)
        with pytest.raises(SystemExit) as exc_info:
            load_from_json(path)
        assert exc_info.value.code == 1

    def test_missing_destination_exits(self, make_json):
        """缺少 destination 應 sys.exit(1)"""
        data = {
            "title": "測試",
            "date_range": "2026/04/01",
            # 缺 destination
        }
        path = make_json(data)
        with pytest.raises(SystemExit) as exc_info:
            load_from_json(path)
        assert exc_info.value.code == 1

    def test_wrong_type_for_days_exits(self, make_json):
        """days 欄位型別錯誤應 sys.exit(1)"""
        data = {
            "title": "測試",
            "date_range": "2026/04/01",
            "destination": "東京",
            "days": "not a list",
        }
        path = make_json(data)
        with pytest.raises(SystemExit) as exc_info:
            load_from_json(path)
        assert exc_info.value.code == 1


class TestJsonCJKEncoding:
    """CJK 編碼邊界"""

    def test_cjk_title_preserved(self, make_json):
        """中文標題應完整保留"""
        data = {
            "title": "2026 北海道七日遊：破冰船★雪上樂園",
            "date_range": "2026/03/15",
            "destination": "北海道",
        }
        path = make_json(data)
        result = load_from_json(path)
        assert result.title == "2026 北海道七日遊：破冰船★雪上樂園"

    def test_japanese_characters(self, make_json):
        """日文片假名/平假名應正確載入"""
        data = {
            "title": "ほっかいどう旅行",
            "date_range": "2026/03/15",
            "destination": "北海道",
            "notes": ["ホテルチェックイン 15:00"],
        }
        path = make_json(data)
        result = load_from_json(path)
        assert result.title == "ほっかいどう旅行"
        assert "ホテルチェックイン" in result.notes[0]

    def test_emoji_in_fields(self, make_json):
        """Emoji 不應導致載入失敗"""
        data = {
            "title": "🏔️ 北海道之旅 ❄️",
            "date_range": "2026/03/15",
            "destination": "北海道",
            "quote": "雪の世界 ⛄",
        }
        path = make_json(data)
        result = load_from_json(path)
        assert "🏔️" in result.title
        assert "⛄" in result.quote

    def test_mixed_encoding_special_chars(self, make_json):
        """混合特殊字元（全形標點、破折號、引號）"""
        data = {
            "title": "「北海道」——冬季限定",
            "date_range": "2026/03/15 — 03/21",
            "destination": "北海道",
            "quote": "『在最寒冷的季節，遇見最溫暖的風景。』",
        }
        path = make_json(data)
        result = load_from_json(path)
        assert "「北海道」" in result.title
        assert "『" in result.quote

"""主題註冊與查詢"""
from pathlib import Path

THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "themes"

THEMES = {
    "soft-cream": {
        "name": "Soft Cream 極簡風",
        "css_file": "soft-cream.css",
        "description": "溫暖奶油色底，深色標籤，襯線標題，極簡排版",
    },
    "dark-modern": {
        "name": "深色現代風",
        "css_file": "dark-modern.css",
        "description": "深藍黑底，金色強調，冰藍輔色",
    },
    "magazine": {
        "name": "雜誌風",
        "css_file": "magazine.css",
        "description": "大圖為主，文字覆蓋在圖上，時尚感",
    },
}


def get_theme_css(theme_name: str) -> str:
    """載入主題 CSS 內容"""
    theme = THEMES.get(theme_name)
    if not theme:
        raise ValueError(f"Unknown theme: {theme_name}. Available: {list(THEMES.keys())}")

    css_path = THEMES_DIR / theme["css_file"]
    if not css_path.exists():
        raise FileNotFoundError(f"Theme CSS not found: {css_path}")

    return css_path.read_text(encoding="utf-8")


def list_themes() -> list[dict]:
    """列出所有可用主題"""
    result = []
    for key, info in THEMES.items():
        css_path = THEMES_DIR / info["css_file"]
        result.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "available": css_path.exists(),
        })
    return result

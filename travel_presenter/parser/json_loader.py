"""從 JSON 檔案載入行程資料"""
import json
import sys
from pathlib import Path
from ..models import TripData


def load_from_json(json_path: str | Path) -> TripData:
    """讀取 JSON 檔案並轉為 TripData"""
    path = Path(json_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"錯誤：JSON 格式不正確 — {e}")
        print(f"  檔案：{path}")
        print("  提示：可用線上 JSON 驗證工具檢查語法")
        sys.exit(1)
    except OSError as e:
        print(f"錯誤：無法讀取檔案 — {e}")
        sys.exit(1)

    try:
        return TripData(**data)
    except Exception as e:
        print(f"錯誤：JSON 資料結構不符合預期 — {e}")
        print("  提示：請參考 README.md 中的 JSON 格式說明")
        sys.exit(1)

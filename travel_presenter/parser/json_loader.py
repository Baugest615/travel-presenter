"""從 JSON 檔案載入行程資料"""
import json
import logging
import sys
from pathlib import Path
from ..models import TripData

logger = logging.getLogger(__name__)


def load_from_json(json_path: str | Path) -> TripData:
    """讀取 JSON 檔案並轉為 TripData"""
    path = Path(json_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("JSON 格式不正確 — %s", e)
        logger.error("  檔案：%s", path)
        logger.error("  提示：可用線上 JSON 驗證工具檢查語法")
        sys.exit(1)
    except OSError as e:
        logger.error("無法讀取檔案 — %s", e)
        sys.exit(1)

    try:
        return TripData(**data)
    except Exception as e:
        logger.error("JSON 資料結構不符合預期 — %s", e)
        logger.error("  提示：請參考 README.md 中的 JSON 格式說明")
        sys.exit(1)

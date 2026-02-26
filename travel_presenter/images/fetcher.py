"""自動圖片抓取 — 從 Unsplash 取得免費高品質旅遊照片"""
from __future__ import annotations

import os
import re
import hashlib
import json
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import quote_plus
from urllib.error import URLError

from ..models import TripData


# Unsplash API
UNSPLASH_API = "https://api.unsplash.com"
UNSPLASH_SEARCH = f"{UNSPLASH_API}/search/photos"

# 常見目的地的英文關鍵字映射（提升搜尋精度）
DESTINATION_KEYWORDS = {
    "北海道": "Hokkaido Japan winter",
    "東京": "Tokyo Japan",
    "大阪": "Osaka Japan",
    "京都": "Kyoto Japan temple",
    "沖繩": "Okinawa Japan beach",
    "富良野": "Furano Hokkaido lavender snow",
    "札幌": "Sapporo Japan",
    "小樽": "Otaru canal Japan",
    "阿寒": "Lake Akan Hokkaido",
    "美瑛": "Biei Hokkaido",
    "峇厘島": "Bali Indonesia temple",
    "峇里島": "Bali Indonesia temple",
    "烏布": "Ubud Bali rice terrace",
    "海神廟": "Tanah Lot Bali",
    "首爾": "Seoul Korea",
    "曼谷": "Bangkok Thailand",
    "普吉島": "Phuket Thailand beach",
    "巴黎": "Paris France",
    "倫敦": "London England",
    "紐約": "New York City",
    "破冰船": "icebreaker ship drift ice",
    "流冰": "drift ice Hokkaido",
    "溫泉": "Japanese hot spring onsen",
    "精靈露台": "Ningle Terrace Furano",
    "雪上摩托車": "snowmobile winter",
    "OUTLET": "shopping mall outlet",
    "運河": "canal winter snow",
    "螃蟹": "Japanese crab cuisine",
}


class ImageFetcher:
    """從 Unsplash 自動抓取旅遊照片並快取到本地。"""

    def __init__(
        self,
        cache_dir: str | Path = "output/images",
        api_key: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("UNSPLASH_ACCESS_KEY", "")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_index_path = self.cache_dir / "_index.json"
        self._cache_index = self._load_cache_index()

    # ── 公開 API ────────────────────────────────────

    def available(self) -> bool:
        """檢查 API key 是否可用。"""
        return bool(self.api_key)

    def fetch_for_trip(self, trip: TripData, force: bool = False) -> TripData:
        """
        為整份行程自動抓取圖片。
        會修改 trip 物件的 cover_image、days[].image 等欄位。
        """
        if not self.available():
            print("  ⚠ 未設定 UNSPLASH_ACCESS_KEY，跳過自動抓圖")
            print("    設定方式：set UNSPLASH_ACCESS_KEY=你的金鑰")
            return trip

        print(f"  正在從 Unsplash 抓取圖片（快取目錄: {self.cache_dir}）...")

        # 1. 封面圖
        if not trip.cover_image or force:
            cover_query = self._build_query(trip.destination, context="landscape scenic")
            cover_path = self._fetch_image(cover_query, tag="cover")
            if cover_path:
                trip.cover_image = cover_path
                print(f"    ✓ 封面: {cover_query}")

        # 2. 每日行程圖
        for day in trip.days:
            if day.image and not force:
                continue  # 已有圖片，跳過

            query = self._build_day_query(day, trip.destination)
            tag = f"day{day.day}"
            img_path = self._fetch_image(query, tag=tag)
            if img_path:
                day.image = img_path
                print(f"    ✓ Day {day.day}: {query}")
            else:
                print(f"    ✗ Day {day.day}: 找不到「{query}」的圖片")

            # 避免觸及 API 速率限制
            time.sleep(0.5)

        # 3. 航班頁圖（用目的地搜尋）
        # 不需要額外處理，renderer 會自動從 day images 取

        print(f"  抓圖完成，共 {self._count_images(trip)} 張")
        return trip

    # ── 搜尋與下載 ────────────────────────────────

    def _fetch_image(
        self,
        query: str,
        tag: str = "",
        orientation: str = "landscape",
        size: str = "regular",
    ) -> Optional[str]:
        """搜尋 Unsplash 並下載第一張結果，回傳本地檔案路徑。"""
        cache_key = f"{query}_{orientation}"
        cached = self._cache_index.get(cache_key)
        if cached and Path(cached).exists():
            return cached

        try:
            url = (
                f"{UNSPLASH_SEARCH}"
                f"?query={quote_plus(query)}"
                f"&orientation={orientation}"
                f"&per_page=1"
            )
            req = Request(url, headers={
                "Authorization": f"Client-ID {self.api_key}",
                "Accept-Version": "v1",
            })
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = data.get("results", [])
            if not results:
                return None

            photo = results[0]
            img_url = photo["urls"].get(size, photo["urls"]["regular"])
            photographer = photo["user"]["name"]

            # 下載圖片
            file_name = f"{tag}_{hashlib.md5(query.encode()).hexdigest()[:8]}.jpg"
            file_path = self.cache_dir / file_name

            img_req = Request(img_url, headers={"User-Agent": "TravelPresenter/1.0"})
            with urlopen(img_req, timeout=30) as img_resp:
                file_path.write_bytes(img_resp.read())

            # 更新快取索引
            abs_path = str(file_path.resolve().as_posix())
            self._cache_index[cache_key] = abs_path
            self._save_cache_index()

            return abs_path

        except (URLError, json.JSONDecodeError, KeyError, OSError) as e:
            return None

    # ── 關鍵字建構 ────────────────────────────────

    def _build_query(self, text: str, context: str = "") -> str:
        """從中文文字建構英文搜尋關鍵字。"""
        # 先嘗試已知的對照表
        for zh, en in DESTINATION_KEYWORDS.items():
            if zh in text:
                return f"{en} {context}".strip()
        # 直接用原文（Unsplash 支援部分中文）
        return f"{text} travel {context}".strip()

    def _build_day_query(self, day, destination: str) -> str:
        """為某天行程建構搜尋關鍵字。"""
        # 優先用標題中的景點名
        title = day.title or ""
        route = day.route or ""
        combined = f"{title} {route}"

        # 嘗試從已知景點對照表找最佳匹配
        best_match = ""
        best_len = 0
        for zh, en in DESTINATION_KEYWORDS.items():
            if zh in combined and len(zh) > best_len:
                best_match = en
                best_len = len(zh)

        if best_match:
            return best_match

        # 從標題提取有意義的地名（去掉常見動詞和連接詞）
        clean = re.sub(r'[退房|出發|前往|抵達|入住|搭乘|安排|預計]', '', title)
        clean = re.sub(r'[\n\r→>＞【】()（）~～]', ' ', clean)
        parts = [p.strip() for p in clean.split() if len(p.strip()) >= 2]

        if parts:
            # 取最有意義的前兩個詞
            query_parts = parts[:2]
            return f"{' '.join(query_parts)} {destination} travel"

        return f"{destination} travel scenery"

    # ── 快取管理 ────────────────────────────────

    def _load_cache_index(self) -> dict:
        if self._cache_index_path.exists():
            try:
                return json.loads(self._cache_index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache_index(self):
        self._cache_index_path.write_text(
            json.dumps(self._cache_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _count_images(self, trip: TripData) -> int:
        count = 1 if trip.cover_image else 0
        count += sum(1 for d in trip.days if d.image)
        return count

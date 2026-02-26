"""AI 內容美化 — 用 LLM 自動生成英文標題、引言、精煉描述"""
from __future__ import annotations

import os
import json
from typing import Optional

from ..models import TripData


SYSTEM_PROMPT = """你是一位專業的旅遊文案撰寫師，擅長將旅行社的制式行程文字轉化為優美、吸引人的簡報文案。

你的任務是美化旅遊行程簡報的內容，包括：
1. 為每天行程生成簡潔優雅的英文副標題（title_en）
2. 為整趟旅程生成一句引言（quote）和英文引言（quote_en）
3. 精簡過長的標題，保留核心景點名稱
4. 為每天的亮點活動生成 highlights 列表

風格要求：
- 英文標題用斜體感的優雅風格，如 "Ningle Terrace, Furano" 或 "Ice Cruise Experience"
- 引言要有意境，中日/中英混搭皆可，如「帶你看見北方的光」
- highlights 用 2-4 個短語，如 ["雪上摩托車", "四輪越野車", "香蕉船"]
- 標題精簡到 15 字以內（可分兩行）

回覆格式必須是合法 JSON：
{
  "quote": "中文引言",
  "quote_en": "English quote",
  "days": [
    {
      "day": 1,
      "title": "精簡後的中文標題",
      "title_en": "English Subtitle",
      "highlights": ["亮點1", "亮點2"]
    }
  ]
}"""


class AiEnhancer:
    """用 LLM API 美化行程內容。支援 Anthropic Claude 和 OpenAI 格式。"""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        # 優先用 Anthropic Claude
        self.anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = model or "claude-sonnet-4-20250514"
        self._provider = self._detect_provider()

    def available(self) -> bool:
        return self._provider is not None

    def enhance(self, trip: TripData) -> TripData:
        """用 AI 美化行程內容，回傳修改後的 TripData。"""
        if not self.available():
            print("  ⚠ 未設定 AI API Key，跳過內容美化")
            print("    支援：ANTHROPIC_API_KEY 或 OPENAI_API_KEY")
            return trip

        print(f"  正在用 AI 美化內容（{self._provider}）...")

        # 建構 prompt
        trip_summary = self._build_summary(trip)
        user_prompt = (
            f"以下是一份 {trip.destination} {len(trip.days)} 日旅遊行程，"
            f"請按照指示美化內容：\n\n{trip_summary}"
        )

        try:
            if self._provider == "anthropic":
                result = self._call_anthropic(user_prompt)
            else:
                result = self._call_openai(user_prompt)

            if result:
                trip = self._apply_enhancements(trip, result)
                print("  ✓ AI 美化完成")
            else:
                print("  ⚠ AI 回覆解析失敗，使用原始內容")

        except Exception as e:
            print(f"  ⚠ AI 美化失敗: {e}")

        return trip

    # ── 摘要建構 ────────────────────────────────

    def _build_summary(self, trip: TripData) -> str:
        lines = [
            f"目的地：{trip.destination}",
            f"天數：{len(trip.days)} 天",
            f"日期：{trip.date_range}",
            "",
        ]
        for d in trip.days:
            lines.append(f"Day {d.day} ({d.date}):")
            lines.append(f"  標題：{d.title}")
            if d.route:
                lines.append(f"  路線：{d.route}")
            if d.description:
                desc_short = d.description[:200]
                lines.append(f"  描述：{desc_short}")
            lines.append("")
        return "\n".join(lines)

    # ── API 呼叫 ────────────────────────────────

    def _call_anthropic(self, user_prompt: str) -> Optional[dict]:
        """呼叫 Anthropic Claude API。"""
        from urllib.request import urlopen, Request
        import json as _json

        body = _json.dumps({
            "model": self.model,
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")

        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        text = data["content"][0]["text"]
        return self._parse_json_response(text)

    def _call_openai(self, user_prompt: str) -> Optional[dict]:
        """呼叫 OpenAI 相容 API。"""
        from urllib.request import urlopen, Request
        import json as _json

        body = _json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }).encode("utf-8")

        req = Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_key}",
            },
            method="POST",
        )

        with urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        text = data["choices"][0]["message"]["content"]
        return self._parse_json_response(text)

    # ── 結果處理 ────────────────────────────────

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """從 LLM 回覆中提取 JSON。"""
        # 嘗試直接解析
        text = text.strip()
        # 移除 markdown code block
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 嘗試找 { ... } 的部分
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return None

    def _apply_enhancements(self, trip: TripData, data: dict) -> TripData:
        """將 AI 生成的內容套用到 TripData。"""
        # 引言
        if data.get("quote"):
            trip.quote = data["quote"]
        if data.get("quote_en"):
            trip.quote_en = data["quote_en"]

        # 每日行程
        day_map = {d["day"]: d for d in data.get("days", []) if "day" in d}
        for trip_day in trip.days:
            enhanced = day_map.get(trip_day.day, {})

            if enhanced.get("title_en") and not trip_day.title_en:
                trip_day.title_en = enhanced["title_en"]

            if enhanced.get("title"):
                # 只在 AI 建議的標題更短時才替換
                if len(enhanced["title"]) < len(trip_day.title or ""):
                    trip_day.title = enhanced["title"]

            if enhanced.get("highlights") and not trip_day.highlights:
                trip_day.highlights = enhanced["highlights"]

        return trip

    # ── 偵測可用的 Provider ─────────────────────

    def _detect_provider(self) -> Optional[str]:
        if self.anthropic_key:
            return "anthropic"
        if self.openai_key:
            return "openai"
        return None

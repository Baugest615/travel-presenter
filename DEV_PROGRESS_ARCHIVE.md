# DEV_PROGRESS Archive

> 歷史歸檔段落。當前進度請看 [DEV_PROGRESS.md](DEV_PROGRESS.md)。
> 此檔由 `dev-progress-archive.sh` 自動維護。


---

## Phase 1：MVP 核心（已完成）
- [x] 資料模型 `TripData`（Pydantic v2）
- [x] JSON 載入器 `json_loader.py`
- [x] Jinja2 模板系統（base + pages + components）
- [x] HTML 渲染器 `HtmlRenderer`
- [x] PDF 渲染器 `PdfRenderer`（Playwright + Chromium）
- [x] CLI 入口 `cli.py`
- [x] 範例資料 `hokkaido_sample.json`

_archived: 2026-04-24 (last modified 56d ago)_

## Phase 2：DOCX 解析（已完成）
- [x] DOCX 解析器 `docx_parser.py`
- [x] 自動偵測航班、餐食、住宿、行程標題
- [x] 支援多種格式的 DOCX 文件

_archived: 2026-04-24 (last modified 56d ago)_

## Phase 2.5：AI 增強 + 圖片擷取（已完成）
- [x] AI 增強器 `ai_enhancer.py`（OpenAI GPT-4o）
- [x] 圖片擷取器 `fetcher.py`（Unsplash API）
- [x] CLI `--ai` / `--fetch-images` 參數

_archived: 2026-04-24 (last modified 56d ago)_

## Phase 3：多主題系統（已完成）
- [x] Soft Cream 極簡風（預設）
- [x] Dark Modern 深色現代風
- [x] Magazine 雜誌風
- [x] 主題註冊表 `registry.py`
- [x] CSS 變數系統，主題只改變數不改 HTML

_archived: 2026-04-24 (last modified 56d ago)_

## Phase 4：錯誤處理 & 收尾（已完成）
- [x] 完整錯誤處理（JSON/DOCX 解析、PDF 渲染）
- [x] 圖片佔位符（無圖時顯示山景 emoji + 標題）
- [x] 內容溢出保護
- [x] README 使用說明

_archived: 2026-04-24 (last modified 56d ago)_

## Phase 5：Web 介面（已完成）
- [x] Flask 後端 `web/app.py`（12 個 API 路由）
- [x] 上傳畫面（拖放 DOCX/JSON + 載入範例）
- [x] 編輯器：基本資訊、航班、集合、每日行程 Tab、住宿、注意事項
- [x] 主題選擇器（3 主題色票卡片）
- [x] 圖片上傳（封面、每日行程）
- [x] iframe 預覽（1440x810，自動縮放）
- [x] HTML / PDF 下載
- [x] `start.bat` 一鍵啟動腳本
- [x] 端到端 Playwright 測試驗證

_archived: 2026-04-24 (last modified 56d ago)_



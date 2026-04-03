# Travel Presenter — 開發進度

## Phase 1：MVP 核心（已完成）
- [x] 資料模型 `TripData`（Pydantic v2）
- [x] JSON 載入器 `json_loader.py`
- [x] Jinja2 模板系統（base + pages + components）
- [x] HTML 渲染器 `HtmlRenderer`
- [x] PDF 渲染器 `PdfRenderer`（Playwright + Chromium）
- [x] CLI 入口 `cli.py`
- [x] 範例資料 `hokkaido_sample.json`

## Phase 2：DOCX 解析（已完成）
- [x] DOCX 解析器 `docx_parser.py`
- [x] 自動偵測航班、餐食、住宿、行程標題
- [x] 支援多種格式的 DOCX 文件

## Phase 2.5：AI 增強 + 圖片擷取（已完成）
- [x] AI 增強器 `ai_enhancer.py`（OpenAI GPT-4o）
- [x] 圖片擷取器 `fetcher.py`（Unsplash API）
- [x] CLI `--ai` / `--fetch-images` 參數

## Phase 3：多主題系統（已完成）
- [x] Soft Cream 極簡風（預設）
- [x] Dark Modern 深色現代風
- [x] Magazine 雜誌風
- [x] 主題註冊表 `registry.py`
- [x] CSS 變數系統，主題只改變數不改 HTML

## Phase 4：錯誤處理 & 收尾（已完成）
- [x] 完整錯誤處理（JSON/DOCX 解析、PDF 渲染）
- [x] 圖片佔位符（無圖時顯示山景 emoji + 標題）
- [x] 內容溢出保護
- [x] README 使用說明

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

## Phase 6：維護與安全（已完成）
- [x] Pin dependency versions（requirements.txt 鎖版本）
- [x] Filename sanitization 安全修復（secure_filename）
- [x] print() → logging 替換

## Night Shift 2026-04-03（最終彙整）
- **Develop (已 merge)**：Pin dependency versions + secure_filename 安全修復 + print→logging 替換
- **Develop (待 review)**：
  - `night-shift/2026-04-03/DOCX-JSON-Parser-韌性測試-Theme-渲染測試` — 48 tests + Python 3.9 相容 bug fix

## Phase 7：測試基礎建設（已完成）
- [x] pytest 框架建立（conftest.py + fixtures）
- [x] DOCX Parser 韌性測試（畸形檔案、缺欄位、邊界條件）— 17 tests
- [x] JSON Parser 韌性測試（缺欄位、CJK 編碼、schema 驗證）— 9 tests
- [x] Theme 渲染測試（CSS 注入正確性、HTML 結構、三主題覆蓋）— 22 tests
- [x] 附帶修復：json_loader.py / html_renderer.py 補 `from __future__ import annotations`（Python 3.9 相容）
- 測試結果：48 passed / 0 failed（0.38s）

## Phase 8：Web App 整合測試（進行中）
- [x] Flask test_client fixture 建���
- [x] 11 個 API 路由全覆蓋（27 個測試案例）
- [x] 測試結果：75 passed / 0 failed（含原有 48 + 新增 27）
- [ ] 待 review：`night-shift/2026-04-04/Flask-Web-App-整合測試-—-12-個-API-路由覆蓋`

### 發現的問題
- `json_loader.py` 對無效 JSON 呼叫 `sys.exit(1)` 而非 raise exception，
  導致 Web 層無法捕獲並回傳 400 — 建議未來改為 `raise ValueError`

## 技術架構

```
travel_presenter/
├── travel_presenter/    # 核心套件（模型、解析、渲染、AI、主題）
├── templates/           # Jinja2 簡報模板
├── themes/              # CSS 主題檔
├── examples/            # 範例資料
├── web/                 # Flask Web 介面
│   ├── app.py           # 後端 API
│   ├── templates/       # index.html
│   └── static/          # CSS + JS
├── start.bat            # 一鍵啟動
└── requirements.txt     # 依賴清單
```

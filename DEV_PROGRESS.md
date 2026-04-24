# Travel Presenter — 開發進度

## 目前狀態

### Night Shift 2026-04-06
- develop（已 merge）：DEV_PROGRESS 同步至真實狀態，75 tests ✅

## Phase 6：維護與安全（已完成）
- [x] Pin dependency versions（requirements.txt 鎖版本）
- [x] Filename sanitization 安全修復（secure_filename）
- [x] print() → logging 替換

## Phase 7：測試基礎建設（已完成）
- [x] pytest 框架建立（conftest.py + fixtures）
- [x] DOCX Parser 韌性測試（畸形檔案、缺欄位、邊界條件）— 17 tests
- [x] JSON Parser 韌性測試（缺欄位、CJK 編碼、schema 驗證）— 9 tests
- [x] Theme 渲染測試（CSS 注入正確性、HTML 結構、三主題覆蓋）— 22 tests
- [x] 附帶修復：json_loader.py / html_renderer.py 補 `from __future__ import annotations`（Python 3.9 相容）
- 測試結果：48 passed / 0 failed（0.38s）

## Phase 8：Web App 整合測試（已完成）
- [x] Flask test_client fixture 建立
- [x] 11 個 API 路由全覆蓋（27 個測試案例）
- [x] 測試結果：75 passed / 0 failed（含原有 48 + 新增 27，0.56s）

### 已知問題（待未來處理）
- `json_loader.py` 對無效 JSON 呼叫 `sys.exit(1)` 而非 raise exception，
  導致 Web 層無法捕獲並回傳 400 — 建議未來改為 `raise ValueError`

## Night Shift 紀錄
- **2026-04-03**：Pin deps + secure_filename + logging（已 merge）；DOCX/JSON/Theme 48 tests（已 merge）
- **2026-04-04**：Flask 整合測試 27 tests（已 merge）
- **2026-04-06**：Phase 7/8 收尾 — DEV_PROGRESS 同步、已 merge branch 清理建議

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

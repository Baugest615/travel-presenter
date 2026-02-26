# Travel Presenter — 旅遊行程簡報生成器

將旅行社提供的 DOCX 行程書或 JSON 資料，自動轉換成高品質 PDF 簡報。

## 功能特色

- **DOCX 直接生成** — 丟入旅行社 Word 檔，自動解析行程、航班、住宿、餐食
- **三種視覺主題** — Soft Cream 極簡風 / Dark Modern 深色現代 / Magazine 雜誌風
- **模板化系統** — Jinja2 元件化模板，主題只改 CSS 變數不改 HTML 結構
- **AI 內容美化**（可選）— 自動生成英文副標題、引言、亮點摘要
- **自動抓圖**（可選）— 從 Unsplash 免費圖庫自動下載旅遊照片

## 安裝

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 安裝 Playwright 瀏覽器（PDF 渲染需要）
playwright install chromium
```

### requirements.txt

```
pydantic>=2.0
python-docx>=1.0
jinja2>=3.1
playwright>=1.40
Pillow>=10.0
```

## 快速開始

### 從 DOCX 生成 PDF（最常用）

```bash
python -m travel_presenter generate "行程.docx" -o output/簡報.pdf
```

### 指定主題

```bash
python -m travel_presenter generate "行程.docx" -t dark-modern -o output/簡報.pdf
```

可用主題：`soft-cream`（預設）、`dark-modern`、`magazine`

### 先解析再生成（可手動編輯 JSON）

```bash
# 步驟 1：DOCX → JSON
python -m travel_presenter parse "行程.docx" -o trip.json

# 步驟 2：手動編輯 trip.json（調整標題、補圖片路徑等）

# 步驟 3：JSON → PDF
python -m travel_presenter generate trip.json -t magazine -o output/簡報.pdf
```

### 只輸出 HTML（快速預覽）

```bash
python -m travel_presenter generate trip.json --html-only -o preview.html
```

直接用瀏覽器開啟即可預覽，不需要 Playwright。

### 查看可用主題

```bash
python -m travel_presenter themes
```

## CLI 完整參數

### `generate` — 生成簡報

```
python -m travel_presenter generate <input> [選項]

位置參數：
  input                 輸入檔案路徑（.json 或 .docx）

選項：
  -o, --output PATH     輸出路徑（預設：output/presentation.pdf）
  -t, --theme THEME     視覺主題：soft-cream / dark-modern / magazine
  --images-dir PATH     圖片目錄路徑
  --html-only           只輸出 HTML，不轉 PDF
  --title TEXT          覆寫標題
  --company TEXT        公司名稱
  --auto-images         自動從 Unsplash 抓取圖片（需 UNSPLASH_ACCESS_KEY）
  --enhance             用 AI 美化內容（需 ANTHROPIC_API_KEY 或 OPENAI_API_KEY）
```

### `parse` — DOCX 轉 JSON

```
python -m travel_presenter parse <input> [選項]

位置參數：
  input                 DOCX 檔案路徑

選項：
  -o, --output PATH     輸出 JSON 路徑（預設：output/parsed.json）
```

### `themes` — 列出主題

```
python -m travel_presenter themes
```

## 主題一覽

| 主題 | 風格 | 適合場景 |
|------|------|---------|
| `soft-cream` | 暖奶油色底、襯線標題、極簡排版 | 高端旅遊、文青風行程 |
| `dark-modern` | 深藍黑底、金色強調、玻璃態卡片 | 商務旅遊、冬季行程 |
| `magazine` | 白底、珊瑚紅強調、粗體編輯排版 | 活潑行程、年輕族群 |

## 可選功能

### AI 內容美化

設定環境變數後加上 `--enhance` 即可：

```bash
# 支援 Anthropic Claude（推薦）
set ANTHROPIC_API_KEY=sk-ant-...

# 或 OpenAI
set OPENAI_API_KEY=sk-...

python -m travel_presenter generate "行程.docx" --enhance -o output/簡報.pdf
```

AI 會自動生成：英文副標題、行程引言、亮點摘要、精簡標題。

### 自動抓取圖片

設定 Unsplash API Key 後加上 `--auto-images`：

```bash
set UNSPLASH_ACCESS_KEY=你的金鑰

python -m travel_presenter generate "行程.docx" --auto-images -o output/簡報.pdf
```

圖片會快取到 `output/images/`，重複生成不會重新下載。

取得 Unsplash API Key：https://unsplash.com/developers

## JSON 資料格式

手動建立或編輯 JSON 時的欄位說明：

```jsonc
{
  "title": "2026 北海道",
  "subtitle": "破冰船・雪上樂園・七日之旅",
  "company": "開麗娛樂",
  "date_range": "2026.03.15 — 03.21",
  "destination": "北海道",
  "theme": "soft-cream",
  "cover_image": "images/cover.jpg",
  "quote": "帶你看見北方的光",
  "quote_en": "Discover the Northern Light",

  "flights": [
    {
      "direction": "departure",
      "airline": "長榮航空",
      "flight_number": "BR116",
      "date": "3/15",
      "departure_airport": "TPE",
      "departure_time": "09:30",
      "arrival_airport": "CTS",
      "arrival_time": "14:00"
    }
  ],

  "days": [
    {
      "day": 1,
      "date": "3/15（六）",
      "title": "森林精靈露台",
      "title_en": "Ningle Terrace, Furano",
      "route": "桃園 → 新千歲 → 富良野",
      "description": "抵達北海道後...",
      "highlights": ["精靈露台", "森林散步"],
      "image": "images/day1.jpg",
      "meals": {
        "breakfast": "機上餐食",
        "lunch": "機上餐食",
        "dinner": "飯店晚餐"
      },
      "hotel": {
        "name": "新富良野王子大飯店",
        "phone": "+81 167-22-1111"
      }
    }
  ],

  "hotels": [
    {
      "name": "新富良野王子大飯店",
      "area": "FURANO",
      "phone": "+81 167-22-1111",
      "nights": [1]
    }
  ]
}
```

## 專案結構

```
travel_presenter/
├── travel_presenter/           # Python 套件
│   ├── cli.py                  # CLI 進入點
│   ├── models.py               # Pydantic 資料模型
│   ├── parser/                 # 輸入解析
│   │   ├── docx_parser.py      # DOCX → TripData
│   │   └── json_loader.py      # JSON → TripData
│   ├── renderer/               # 輸出渲染
│   │   ├── html_renderer.py    # Jinja2 → HTML
│   │   └── pdf_renderer.py     # Playwright → PDF
│   ├── themes/                 # 主題管理
│   │   └── registry.py
│   ├── enhancer/               # AI 美化（可選）
│   │   └── ai_enhancer.py
│   └── images/                 # 自動抓圖（可選）
│       └── fetcher.py
├── templates/                  # Jinja2 模板
│   ├── base.html
│   ├── components/             # 可重用元件
│   └── pages/                  # 頁面類型
├── themes/                     # 主題 CSS
│   ├── soft-cream.css
│   ├── dark-modern.css
│   └── magazine.css
├── examples/                   # 範例資料
├── output/                     # 預設輸出目錄
└── requirements.txt
```

## 簡報頁面結構

自動生成的簡報包含以下頁面（依序）：

1. **封面** — 全幅背景圖 + 標題
2. **引言**（可選）— 一句引言文字
3. **航班資訊** — 去程/回程航班代碼與時間
4. **行程總覽** — 7 日行程路線一覽
5. **每日行程** × N — 左文右圖分割佈局，含餐食、住宿、活動
6. **住宿一覽** — 所有飯店卡片
7. **結尾頁** — Thank You

## 常見問題

### PDF 輸出全白 / 缺少字型

確保已安裝 Playwright Chromium：

```bash
playwright install chromium
```

### 中文亂碼

Windows 環境建議設定：

```bash
set PYTHONUTF8=1
```

### DOCX 解析不完整

可先 parse 為 JSON 檢查，再手動補全：

```bash
python -m travel_presenter parse "行程.docx" -o check.json
```

### 圖片不顯示

- HTML 預覽：確保圖片路徑正確，可用 `--images-dir` 指定圖片目錄
- PDF 輸出：PDF 渲染器會以輸入檔案所在目錄為基準解析相對路徑

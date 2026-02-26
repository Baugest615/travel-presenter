@echo off
chcp 65001 >nul 2>&1
title Travel Presenter Web

echo ============================================
echo   Travel Presenter — 旅遊簡報生成器
echo ============================================
echo.

cd /d "%~dp0"

:: ── 檢查 Python ────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.10+
    echo 下載: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ── 建立虛擬環境（首次執行）───────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] 建立虛擬環境...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [錯誤] 無法建立虛擬環境
        pause
        exit /b 1
    )
)

:: ── 啟動虛擬環境 ──────────────────────────────
call .venv\Scripts\activate.bat

:: ── 安裝依賴（首次或更新時）──────────────────
echo [2/4] 檢查依賴套件...
pip install -q -r requirements.txt 2>nul
if %ERRORLEVEL% neq 0 (
    echo [提示] 正在安裝依賴套件，請稍候...
    pip install -r requirements.txt
)

:: ── 安裝 Playwright Chromium（首次執行）──────
python -c "from playwright.sync_api import sync_playwright" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    if not exist ".venv\Lib\site-packages\playwright\driver\package\.local-browsers" (
        echo [3/4] 安裝 Chromium 瀏覽器（供 PDF 渲染使用）...
        python -m playwright install chromium
    ) else (
        echo [3/4] Chromium 已安裝
    )
) else (
    echo [3/4] 跳過 Chromium（playwright 未安裝，PDF 功能將不可用）
)

:: ── 啟動 Flask 伺服器 ────────────────────────
echo [4/4] 啟動 Web 伺服器...
echo.
echo ============================================
echo   已啟動！請在瀏覽器開啟：
echo   http://localhost:5500
echo.
echo   按 Ctrl+C 停止伺服器
echo ============================================
echo.

:: 延遲 2 秒後自動開啟瀏覽器
start "" "http://localhost:5500"

python web/app.py

:: 結束
echo.
echo 伺服器已停止。
pause

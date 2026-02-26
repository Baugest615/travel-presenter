"""Travel Presenter CLI — 旅遊行程簡報生成器"""
import argparse
import sys
import io
from pathlib import Path

# Windows UTF-8 修正
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def cmd_generate(args):
    """從 JSON 或 DOCX 生成簡報"""
    from .parser import load_from_json, parse_docx
    from .renderer.html_renderer import HtmlRenderer
    from .renderer.pdf_renderer import PdfRenderer

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"錯誤：找不到輸入檔案 {input_path}")
        sys.exit(1)

    # 載入資料
    suffix = input_path.suffix.lower()
    try:
        if suffix == ".json":
            trip = load_from_json(input_path)
        elif suffix in (".docx", ".doc"):
            print(f"正在解析 DOCX: {input_path.name} ...")
            trip = parse_docx(input_path)
            print(f"  解析完成：{len(trip.days)} 天行程、{len(trip.flights)} 筆航班、{len(trip.hotels)} 間飯店")
        else:
            print(f"不支援的檔案格式: {suffix}")
            sys.exit(1)
    except SystemExit:
        raise
    except ValueError as e:
        print(f"錯誤：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"錯誤：載入檔案失敗 — {e}")
        sys.exit(1)

    if not trip.days:
        print("警告：未解析到任何行程資料，產生的簡報可能為空")
        print("  提示：可先用 parse 指令檢查解析結果")

    # 覆寫主題
    if args.theme:
        trip.theme = args.theme
    if args.company:
        trip.company = args.company
    if args.title:
        trip.title = args.title

    # AI 內容美化（可選）
    if getattr(args, 'enhance', False):
        from .enhancer import AiEnhancer
        enhancer = AiEnhancer()
        trip = enhancer.enhance(trip)

    # 自動抓取圖片（可選）
    if getattr(args, 'auto_images', False):
        from .images import ImageFetcher
        output_dir = Path(args.output).resolve().parent
        fetcher = ImageFetcher(cache_dir=output_dir / "images")
        trip = fetcher.fetch_for_trip(trip)

    # 計算圖片基礎路徑
    images_base = ""
    if args.images_dir:
        images_base = str(Path(args.images_dir).resolve().as_posix())
    elif getattr(args, 'auto_images', False):
        # 自動抓圖模式：圖片已是絕對路徑，不需要前綴
        images_base = ""
    elif input_path.parent != Path.cwd():
        candidate = input_path.parent
        images_base = str(candidate.as_posix())

    # 渲染 HTML
    renderer = HtmlRenderer()
    html = renderer.render(trip, images_base=images_base)

    # 輸出
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.html_only:
        output_path.write_text(html, encoding="utf-8")
        print(f"✓ HTML 已輸出: {output_path}")
    else:
        # 用圖片所在目錄作為 base_dir（解決相對路徑）
        base_dir = args.images_dir or str(input_path.parent)
        pdf = PdfRenderer()
        pdf.render(html, str(output_path), base_dir=base_dir)
        print(f"✓ PDF 已輸出: {output_path}")


def cmd_parse(args):
    """將 DOCX 解析為 JSON（可手動編輯後再生成）"""
    import json
    from .parser import parse_docx

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"錯誤：找不到輸入檔案 {input_path}")
        sys.exit(1)

    if input_path.suffix.lower() not in ('.docx', '.doc'):
        print(f"錯誤：parse 指令僅支援 .docx 檔案，收到: {input_path.suffix}")
        sys.exit(1)

    print(f"正在解析: {input_path.name} ...")
    try:
        trip = parse_docx(input_path)
    except ValueError as e:
        print(f"錯誤：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"錯誤：DOCX 解析失敗 — {e}")
        sys.exit(1)
    print(f"  解析完成：{len(trip.days)} 天行程、{len(trip.flights)} 筆航班、{len(trip.hotels)} 間飯店")

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = trip.model_dump(exclude_none=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ JSON 已輸出: {output_path}")
    print("  你可以手動編輯此 JSON 後再用 generate 指令生成簡報。")


def cmd_themes(args):
    """列出可用主題"""
    from .themes.registry import list_themes

    themes = list_themes()
    print("\n可用主題：")
    print("-" * 50)
    for t in themes:
        status = "✓" if t["available"] else "✗"
        print(f"  {status} {t['id']:<15} {t['name']}")
        print(f"    {t['description']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="travel-presenter",
        description="旅遊行程簡報生成器 — 從 JSON/DOCX 生成高品質 PDF 簡報",
    )
    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen = subparsers.add_parser("generate", aliases=["gen"], help="生成簡報")
    gen.add_argument("input", help="輸入檔案路徑 (.json 或 .docx)")
    gen.add_argument("-o", "--output", default="output/presentation.pdf",
                     help="輸出路徑 (預設: output/presentation.pdf)")
    gen.add_argument("-t", "--theme", choices=["soft-cream", "dark-modern", "magazine"],
                     help="視覺主題")
    gen.add_argument("--images-dir", help="圖片目錄路徑")
    gen.add_argument("--html-only", action="store_true", help="只輸出 HTML")
    gen.add_argument("--title", help="覆寫標題")
    gen.add_argument("--company", help="公司名稱")
    gen.add_argument("--auto-images", action="store_true",
                     help="自動從 Unsplash 抓取圖片（需設定 UNSPLASH_ACCESS_KEY）")
    gen.add_argument("--enhance", action="store_true",
                     help="用 AI 美化內容（需設定 ANTHROPIC_API_KEY 或 OPENAI_API_KEY）")
    gen.set_defaults(func=cmd_generate)

    # parse
    par = subparsers.add_parser("parse", help="將 DOCX 解析為 JSON")
    par.add_argument("input", help="DOCX 檔案路徑")
    par.add_argument("-o", "--output", default="output/parsed.json",
                     help="輸出 JSON 路徑 (預設: output/parsed.json)")
    par.set_defaults(func=cmd_parse)

    # themes
    th = subparsers.add_parser("themes", help="列出可用主題")
    th.set_defaults(func=cmd_themes)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()

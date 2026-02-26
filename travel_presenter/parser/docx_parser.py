"""DOCX 行程書解析器 — 將旅行社 Word 檔案轉為 TripData"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

from ..models import (
    TripData, DayItinerary, Flight, Hotel, Meals,
    MeetingPoint, Activity,
)


# ── 正則表達式 ──────────────────────────────────────────────
RE_DAY_TITLE = re.compile(r'^D(\d+)\s*[★☆]?\s*(.+)', re.DOTALL)
RE_MEALS = re.compile(
    r'[（(]早[）)]\s*(.+?)\s*[（(]午[）)]\s*(.+?)\s*[（(]晚[）)]\s*(.+)',
    re.DOTALL,
)
RE_HOTEL = re.compile(r'【宿】\s*(.+)')
RE_FLIGHT_ROW = re.compile(
    r'(BR|CI|JL|NH|CX|SQ|TG|OZ|KE|JX|IT|MM|TR|AK|FD|VJ|QR|EK|TK|LH|AF|BA|AA|UA|DL|EVA|CAL|ANA)\s*(\d+)',
    re.IGNORECASE,
)
RE_TIME = re.compile(r'(\d{1,2}:\d{2})')
RE_DATE_RANGE = re.compile(r'(\d{4})[/.](\d{1,2})[/.](\d{1,2})')
RE_OVERVIEW_DATE = re.compile(r'第?(\d+)\s*天')
RE_OVERVIEW_MMDD = re.compile(r'(\d{1,2})[/.](\d{1,2})')
RE_OVERVIEW_WEEKDAY = re.compile(r'[（(]([一二三四五六日])[）)]')
RE_GROUP_NUM = re.compile(r'(WDF|WDA|WDB|WDC|WDD|WDE|WDF|WDG|WDH|WDI|WDJ|WDK|WDL|WDM)\d+', re.IGNORECASE)


# ── 輔助函式 ──────────────────────────────────────────────
def _iter_body_elements(doc: Document):
    """按照文件 body 中的順序走訪段落與表格。"""
    for child in doc.element.body:
        if child.tag == qn('w:p'):
            yield Paragraph(child, doc.element.body)
        elif child.tag == qn('w:tbl'):
            yield Table(child, doc.element.body)


def _cell_text(table: Table, row: int, col: int) -> str:
    """安全取得表格儲存格文字。"""
    try:
        return table.rows[row].cells[col].text.strip()
    except (IndexError, AttributeError):
        return ""


def _table_text(table: Table) -> str:
    """將整張表格的所有文字串接（用於簡單搜尋）。"""
    texts = []
    for row in table.rows:
        for cell in row.cells:
            t = cell.text.strip()
            if t:
                texts.append(t)
    return " ".join(texts)


def _get_nested_tables(table: Table) -> list[Table]:
    """取得表格內的巢狀表格。"""
    nested = []
    for tbl_elem in table._tbl.iter(qn('w:tbl')):
        if tbl_elem is not table._tbl:
            nested.append(Table(tbl_elem, table._tbl))
    return nested


def _para_text_stripped(para: Paragraph) -> str:
    """取得段落純文字（去空白）。"""
    return para.text.strip()


def _is_bold_para(para: Paragraph) -> bool:
    """判斷段落是否為粗體（常用作小標題）。"""
    for run in para.runs:
        if run.bold:
            return True
    return False


# ── 表格分類 ──────────────────────────────────────────────
def _classify_table(table: Table) -> str:
    """
    根據表格結構和內容將表格分類。
    回傳: 'day_itinerary' | 'overview' | 'flight' | 'group_info'
        | 'section_header' | 'notes' | 'unknown'
    """
    nrows = len(table.rows)
    ncols = len(table.columns)
    full_text = _table_text(table)

    # 2×1 表格，Row 0 以 D{數字} 開頭 → 每日行程
    if nrows == 2 and ncols == 1:
        r0 = _cell_text(table, 0, 0)
        if RE_DAY_TITLE.match(r0):
            return 'day_itinerary'
        # 可能是注意事項
        if '注意事項' in r0 or '注意事項' in full_text[:20]:
            return 'notes'

    # 1×1 表格 → section header（如「航班安排」「每日安排」）
    if nrows == 1 and ncols == 1:
        return 'section_header'

    # 含「旅行區間」或「飯店名稱」→ 行程總覽（優先於航班判定，
    # 因為總覽表也可能包含航班欄位）
    if any(k in full_text for k in ['旅行區間', '飯店名稱']):
        return 'overview'

    # 含團號
    if any(k in full_text for k in ['團號', '集合時間', '領隊']):
        return 'group_info'

    # 含航班關鍵字（純航班表）
    if any(k in full_text for k in ['航班', '班機', '出發', '抵達', 'BR', 'CI']):
        if ncols >= 4 and nrows >= 3:
            return 'flight'

    # 有巢狀表格 → 可能是峇厘島式的複合表格
    nested = _get_nested_tables(table)
    if nested:
        for nt in nested:
            nt_text = _table_text(nt)
            if any(k in nt_text for k in ['旅行區間', '飯店名稱']):
                return 'overview'
            if any(k in nt_text for k in ['航班', '班機', '出發', '抵達']):
                return 'flight'

    return 'unknown'


# ── 子解析器 ──────────────────────────────────────────────
def _parse_day_table(table: Table) -> dict:
    """解析 2×1 的每日行程表格，回傳 dict（尚未填入 description）。"""
    r0 = _cell_text(table, 0, 0)
    r1 = _cell_text(table, 1, 0)

    # 天數 + 路線
    m = RE_DAY_TITLE.match(r0)
    day_num = int(m.group(1))
    route_raw = m.group(2).strip()
    # 清理路線：移除星號、多餘空白
    route_raw = re.sub(r'[★☆]', '', route_raw).strip()
    # 路線中用 > / → / ＞ 分隔
    route_clean = re.sub(r'\s*[>＞→]\s*', ' → ', route_raw)

    # 餐食
    meals = Meals()
    mm = RE_MEALS.search(r1)
    if mm:
        meals.breakfast = mm.group(1).strip()
        meals.lunch = mm.group(2).strip()
        # 晚餐可能後面還有 | 或 【宿】，需要清理
        dinner = mm.group(3).strip()
        dinner = re.split(r'[|｜]', dinner)[0].strip()
        dinner = re.split(r'【宿】', dinner)[0].strip()
        meals.dinner = dinner

    # 住宿
    hotel = None
    hm = RE_HOTEL.search(r1)
    if hm:
        hotel_name = hm.group(1).strip()
        # 移除電話和多餘文字（注意：不能用 IGNORECASE 的 TEL，否則會切到 Hotel）
        hotel_name = re.split(r'\s*電話', hotel_name)[0].strip()
        hotel_name = re.split(r'\s+TEL\b', hotel_name)[0].strip()
        # 移除行尾電話號碼
        hotel_name = re.sub(r'\s*[\+]?\d[\d\s\-]{6,}$', '', hotel_name).strip()
        hotel = Hotel(name=hotel_name)

    return {
        'day': day_num,
        'route': route_clean,
        'meals': meals,
        'hotel': hotel,
    }


def _parse_flight_table(table: Table) -> list[dict]:
    """解析航班表格，回傳航班 dict 列表。"""
    flights = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells]
        row_text = ' '.join(cells)

        # 尋找航班號
        fm = RE_FLIGHT_ROW.search(row_text)
        if not fm:
            continue

        airline_code = fm.group(1).upper()
        flight_num = f"{airline_code}{fm.group(2)}"

        # 尋找時間（通常有兩個）
        times = RE_TIME.findall(row_text)

        # 尋找機場代碼（3 字母大寫）
        airports = re.findall(r'\b([A-Z]{3})\b', row_text)
        # 過濾掉航空公司代碼
        airports = [a for a in airports if a not in (airline_code, 'TEL')]

        # 判斷方向
        direction = 'departure'
        if any(k in row_text for k in ['回程', '返回', '返國']):
            direction = 'return'

        flight_data = {
            'flight_number': flight_num,
            'airline_code': airline_code,
            'direction': direction,
        }

        if len(times) >= 2:
            flight_data['departure_time'] = times[0]
            flight_data['arrival_time'] = times[1]
        elif len(times) == 1:
            flight_data['departure_time'] = times[0]
            flight_data['arrival_time'] = ''

        if len(airports) >= 2:
            flight_data['departure_airport'] = airports[0]
            flight_data['arrival_airport'] = airports[1]
        elif len(airports) == 1:
            flight_data['departure_airport'] = airports[0]
            flight_data['arrival_airport'] = ''

        flights.append(flight_data)

    return flights


def _parse_group_info(table: Table) -> dict:
    """解析團體資訊表格。"""
    info = {}
    full_text = _table_text(table)

    for row in table.rows:
        for i, cell in enumerate(row.cells):
            text = cell.text.strip()
            if '團號' in text and i + 1 < len(row.cells):
                info['group_number'] = row.cells[i + 1].text.strip()
            elif '集合時間' in text and i + 1 < len(row.cells):
                info['meeting_time'] = row.cells[i + 1].text.strip()
            elif '集合地點' in text and i + 1 < len(row.cells):
                info['meeting_location'] = row.cells[i + 1].text.strip()
            elif '領隊' in text and i + 1 < len(row.cells):
                info['leader'] = row.cells[i + 1].text.strip()

    return info


def _parse_overview_table(table: Table) -> list[dict]:
    """解析行程總覽表格，回傳每日概要列表。"""
    days_info = []

    # 先檢查是否有巢狀表格（峇厘島格式）
    nested = _get_nested_tables(table)
    target = table
    if nested:
        for nt in nested:
            nt_text = _table_text(nt)
            if any(k in nt_text for k in ['旅行區間', '飯店名稱', '日期']):
                target = nt
                break

    for row in target.rows:
        cells = [c.text.strip() for c in row.cells]
        row_text = ' '.join(cells)

        # 跳過標題行
        if '日期' in row_text and '旅行區間' in row_text:
            continue

        # 第一欄通常含日期和天數，格式可能是：
        #   "3/15\n第1天" 或 "第1天 12/24(三)" 或 "3/15（日）第1天"
        first_cell = cells[0] if cells else ''

        # 解析天數
        day_m = RE_OVERVIEW_DATE.search(first_cell)
        if not day_m:
            day_m = RE_OVERVIEW_DATE.search(row_text)
        if not day_m:
            continue

        day_num = int(day_m.group(1))

        # 解析月/日
        mmdd = RE_OVERVIEW_MMDD.search(first_cell)
        if not mmdd:
            mmdd = RE_OVERVIEW_MMDD.search(row_text)

        # 解析星期
        wd = RE_OVERVIEW_WEEKDAY.search(first_cell)
        if not wd:
            wd = RE_OVERVIEW_WEEKDAY.search(row_text)

        if mmdd:
            month = mmdd.group(1)
            day = mmdd.group(2)
            weekday = wd.group(1) if wd else ''
            date_str = f"{month}/{day}（{weekday}）" if weekday else f"{month}/{day}"
        else:
            date_str = f"Day {day_num}"

        day_info = {
            'day': day_num,
            'date': date_str,
        }

        # 嘗試取得飯店名稱（通常在最後一欄）
        if len(cells) >= 2:
            hotel_text = cells[-1].strip()
            skip_values = ('飯店名稱/電話', '飯店名稱', '', '溫暖的家')
            if hotel_text and hotel_text not in skip_values and '溫暖的家' not in hotel_text:
                # 飯店欄可能是 "區域\n飯店名\n電話"
                hotel_lines = [l.strip() for l in hotel_text.split('\n') if l.strip()]
                if len(hotel_lines) >= 2:
                    day_info['hotel_area'] = hotel_lines[0]
                    day_info['hotel_name'] = hotel_lines[1]
                elif hotel_lines:
                    day_info['hotel_name'] = hotel_lines[0]
                # 嘗試提取電話
                phone_match = re.search(r'(\+?\d[\d\s\-]{6,})', hotel_text)
                if phone_match:
                    day_info['hotel_phone'] = phone_match.group(1).strip()

        days_info.append(day_info)

    return days_info


def _parse_notes_table(table: Table) -> list[str]:
    """解析注意事項表格。"""
    notes = []
    for row in table.rows:
        for cell in row.cells:
            text = cell.text.strip()
            if text and '注意事項' not in text:
                for line in text.split('\n'):
                    line = line.strip()
                    if line:
                        notes.append(line)
    return notes


# ── 主解析器 ──────────────────────────────────────────────
def _infer_airline_name(code: str) -> str:
    """從航空公司代碼推斷名稱。"""
    AIRLINES = {
        'BR': '長榮航空', 'CI': '中華航空', 'JL': '日本航空',
        'NH': '全日空', 'CX': '國泰航空', 'SQ': '新加坡航空',
        'TG': '泰國航空', 'OZ': '韓亞航空', 'KE': '大韓航空',
        'JX': '星宇航空', 'IT': '台灣虎航', 'MM': '樂桃航空',
        'TR': '酷航', 'AK': '亞洲航空', 'EVA': '長榮航空',
        'CAL': '中華航空', 'ANA': '全日空',
    }
    return AIRLINES.get(code.upper(), code)


def _collect_day_descriptions(
    paragraphs: list[Paragraph],
) -> str:
    """將多段段落合併為描述文字。"""
    lines = []
    for para in paragraphs:
        text = _para_text_stripped(para)
        if not text:
            continue
        # 跳過純圖片段落
        if not text and para._element.findall(f'.//{qn("w:drawing")}'):
            continue
        lines.append(text)
    return '\n'.join(lines)


def _extract_title_from_route(route: str) -> str:
    """從路線描述中提取主要目的地作為標題。"""
    # 移除起訖點（機場、桃園等）
    parts = re.split(r'\s*→\s*', route)
    # 過濾掉常見的中繼詞
    skip = {'桃園機場', '桃園', '機場', '飯店', '酒店', '返回', '出發',
            '新千歲機場', '北海道新千歲機場', '桃園國際機場', '台灣桃園機場'}
    meaningful = [p for p in parts if p.strip() and not any(s in p for s in skip)]
    if meaningful:
        return '\n'.join(meaningful[:2])  # 最多取兩個
    return route


def _infer_destination(days: list[dict], overview_data: list[dict]) -> str:
    """從行程資料推斷目的地。"""
    # 從路線中找最常出現的地名
    all_routes = ' '.join(d.get('route', '') for d in days)
    # 常見目的地關鍵字
    destinations = {
        '北海道': all_routes.count('北海道'),
        '東京': all_routes.count('東京'),
        '大阪': all_routes.count('大阪'),
        '京都': all_routes.count('京都'),
        '沖繩': all_routes.count('沖繩'),
        '峇厘島': all_routes.count('峇厘') + all_routes.count('峇里'),
        '韓國': all_routes.count('韓國') + all_routes.count('首爾'),
        '泰國': all_routes.count('泰國') + all_routes.count('曼谷'),
        '歐洲': all_routes.count('歐洲'),
    }
    best = max(destinations, key=destinations.get)
    if destinations[best] > 0:
        return best
    # fallback：取第一天的目的地機場
    return '旅遊'


def parse_docx(docx_path: str | Path) -> TripData:
    """
    解析旅行社 DOCX 行程書，回傳 TripData。

    支援的格式：
    - 2×1 表格式的每日行程（D1~Dn）
    - 餐食：【食】（早）...（午）...（晚）...
    - 住宿：【宿】飯店名
    - 航班表：含航班號、時間、機場代碼
    - 團體資訊表：團號、集合時間/地點
    """
    try:
        doc = Document(str(docx_path))
    except Exception as e:
        raise ValueError(
            f"無法開啟 DOCX 檔案：{docx_path}\n"
            f"  原因：{e}\n"
            f"  提示：請確認檔案未損毀且為有效的 .docx 格式"
        ) from e

    # 收集所有元素（保持順序）
    elements = list(_iter_body_elements(doc))

    # ── 第一輪：分類表格 ─────────────────────────
    day_tables: list[tuple[int, Table]] = []   # (index, table)
    flight_tables: list[Table] = []
    group_tables: list[Table] = []
    overview_tables: list[Table] = []
    notes_tables: list[Table] = []

    for i, elem in enumerate(elements):
        if not isinstance(elem, Table):
            continue
        kind = _classify_table(elem)
        if kind == 'day_itinerary':
            day_tables.append((i, elem))
        elif kind == 'flight':
            flight_tables.append(elem)
        elif kind == 'group_info':
            group_tables.append(elem)
        elif kind == 'overview':
            overview_tables.append(elem)
        elif kind == 'notes':
            notes_tables.append(elem)
        # 巢狀表格也可能含航班
        if kind in ('overview', 'unknown'):
            for nt in _get_nested_tables(elem):
                nt_kind = _classify_table(nt)
                if nt_kind == 'flight':
                    flight_tables.append(nt)
                elif nt_kind == 'overview':
                    overview_tables.append(nt)

    # ── 第二輪：解析每日行程 ─────────────────────
    day_data_list: list[dict] = []
    for idx, (elem_idx, table) in enumerate(day_tables):
        day_info = _parse_day_table(table)

        # 收集表格後面直到下一個表格之前的段落作為描述
        next_table_idx = (
            day_tables[idx + 1][0] if idx + 1 < len(day_tables)
            else len(elements)
        )
        desc_paras = []
        for j in range(elem_idx + 1, next_table_idx):
            if isinstance(elements[j], Paragraph):
                desc_paras.append(elements[j])

        day_info['description'] = _collect_day_descriptions(desc_paras)
        day_data_list.append(day_info)

    # ── 第三輪：解析總覽取得日期和飯店資訊 ────────
    overview_data = []
    for tbl in overview_tables:
        overview_data.extend(_parse_overview_table(tbl))

    # 用總覽資料補充每日行程的日期和飯店資訊
    for i, day_info in enumerate(day_data_list):
        if i < len(overview_data):
            ov = overview_data[i]
            if 'date' in ov:
                day_info['date'] = ov['date']
            # 用總覽的飯店資料補充 area / phone
            if day_info.get('hotel') and ov.get('hotel_area'):
                day_info['hotel'].area = ov['hotel_area'].upper()
            if day_info.get('hotel') and ov.get('hotel_phone'):
                day_info['hotel'].phone = ov['hotel_phone']
            # 如果行程表沒有住宿資訊，從總覽取
            if not day_info.get('hotel') and ov.get('hotel_name'):
                day_info['hotel'] = Hotel(
                    name=ov['hotel_name'],
                    area=ov.get('hotel_area', '').upper() or None,
                    phone=ov.get('hotel_phone'),
                )
        else:
            if not day_info.get('date'):
                day_info['date'] = f"Day {day_info['day']}"

    # ── 第四輪：解析航班 ──────────────────────────
    flight_list_raw = []
    for tbl in flight_tables:
        flight_list_raw.extend(_parse_flight_table(tbl))

    # 推斷去程/回程
    flights: list[Flight] = []
    seen_flights = set()
    for i, fd in enumerate(flight_list_raw):
        fn = fd.get('flight_number', '')
        if fn in seen_flights:
            continue
        seen_flights.add(fn)

        direction = fd.get('direction', 'departure')
        if i > 0 and direction == 'departure':
            direction = 'return'  # 第二筆以後預設回程

        airline_name = _infer_airline_name(fd.get('airline_code', ''))
        flights.append(Flight(
            direction=direction,
            airline=airline_name,
            flight_number=fn,
            date='',  # 從總覽補
            departure_airport=fd.get('departure_airport', ''),
            departure_time=fd.get('departure_time', ''),
            arrival_airport=fd.get('arrival_airport', ''),
            arrival_time=fd.get('arrival_time', ''),
        ))

    # 從總覽補充航班日期
    if flights and overview_data:
        if len(flights) >= 1 and overview_data:
            flights[0].date = overview_data[0].get('date', '')
        if len(flights) >= 2 and len(overview_data) >= 2:
            flights[-1].date = overview_data[-1].get('date', '')

    # ── 第五輪：解析團體資訊 ──────────────────────
    meeting_point = None
    group_number = None
    for tbl in group_tables:
        info = _parse_group_info(tbl)
        if info.get('meeting_time') or info.get('meeting_location'):
            meeting_point = MeetingPoint(
                time=info.get('meeting_time', ''),
                location=info.get('meeting_location', ''),
                group_number=info.get('group_number'),
            )
        if info.get('group_number'):
            group_number = info['group_number']

    # ── 第六輪：注意事項 ──────────────────────────
    notes = []
    for tbl in notes_tables:
        notes.extend(_parse_notes_table(tbl))

    # ── 組裝 TripData ────────────────────────────
    # 取得文件標題（只搜尋第一個表格之前的段落）
    _SKIP_TITLE = ['此處行程', '行程順序', '免責', '注意事項', '✅', '※',
                   'ICON', '入住禮遇', '每日']
    doc_title = ''
    for elem in elements:
        if isinstance(elem, Table):
            break  # 到第一個表格就停止搜尋
        if not isinstance(elem, Paragraph):
            continue
        t = _para_text_stripped(elem)
        if not t or len(t) <= 2 or len(t) > 40:
            continue
        if any(skip in t for skip in _SKIP_TITLE):
            continue
        doc_title = t
        break

    # 推斷目的地
    destination = _infer_destination(day_data_list, overview_data)

    # 建構日期範圍
    date_range = ''
    if overview_data:
        first_date = overview_data[0].get('date', '')
        last_date = overview_data[-1].get('date', '') if len(overview_data) > 1 else ''
        if first_date and last_date:
            date_range = f"{first_date} — {last_date}"
        elif first_date:
            date_range = first_date

    # 建構 DayItinerary 列表
    days: list[DayItinerary] = []
    for d in day_data_list:
        title = _extract_title_from_route(d.get('route', ''))
        days.append(DayItinerary(
            day=d['day'],
            date=d.get('date', f"Day {d['day']}"),
            title=title,
            route=d.get('route'),
            description=d.get('description'),
            meals=d.get('meals', Meals()),
            hotel=d.get('hotel'),
        ))

    # 過濾掉「溫暖的家」等非飯店住宿
    _SKIP_HOTELS = {'溫暖的家', '自宅', '甜蜜的家', '可愛的家'}
    for d in days:
        if d.hotel and d.hotel.name in _SKIP_HOTELS:
            d.hotel = None

    # 建構去重住宿列表
    hotels: list[Hotel] = []
    hotel_names_seen = set()
    for d in days:
        if d.hotel and d.hotel.name not in hotel_names_seen:
            hotel_names_seen.add(d.hotel.name)
            h = Hotel(
                name=d.hotel.name,
                area=d.hotel.area,
                phone=d.hotel.phone,
                nights=[d.day],
            )
            hotels.append(h)
        elif d.hotel and d.hotel.name in hotel_names_seen:
            for h in hotels:
                if h.name == d.hotel.name:
                    if h.nights is None:
                        h.nights = []
                    h.nights.append(d.day)

    trip = TripData(
        title=doc_title or f"{destination}旅遊行程",
        company='',
        date_range=date_range,
        destination=destination,
        flights=flights,
        meeting_point=meeting_point,
        days=days,
        hotels=hotels,
        notes=notes or None,
    )

    return trip

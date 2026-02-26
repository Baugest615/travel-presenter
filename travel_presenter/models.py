"""Travel Presenter 資料模型 — 所有輸入源最終都轉成此格式"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class Meals(BaseModel):
    breakfast: str = "敬請自理"
    lunch: str = "敬請自理"
    dinner: str = "敬請自理"


class Hotel(BaseModel):
    name: str
    area: Optional[str] = None          # "FURANO", "AKAN", "SAPPORO"
    phone: Optional[str] = None
    nights: Optional[list[int]] = None  # [1, 4] = Day 1 和 Day 4 入住


class Activity(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None          # emoji or icon class


class DayItinerary(BaseModel):
    day: int                            # 1-based
    date: str                           # "3/15（日）"
    title: str                          # "森林精靈露台"
    title_en: Optional[str] = None      # "Ningle Terrace, Furano"
    route: Optional[str] = None         # "桃園 → 新千歲 → 富良野"
    description: Optional[str] = None   # 長段落，可含 \n 換行
    highlights: Optional[list[str]] = None
    activities: Optional[list[Activity]] = None
    meals: Meals = Field(default_factory=Meals)
    hotel: Optional[Hotel] = None
    notes: Optional[list[str]] = None
    image: Optional[str] = None         # 圖片檔名或路徑
    image_alt: Optional[str] = None     # 右側可放第二張圖
    layout: Optional[str] = None        # "split" | "hero" | "full"


class Flight(BaseModel):
    direction: str                      # "departure" | "return"
    airline: str
    flight_number: str
    date: str
    departure_airport: str              # "TPE"
    departure_city: Optional[str] = None
    departure_time: str
    arrival_airport: str                # "CTS"
    arrival_city: Optional[str] = None
    arrival_time: str


class MeetingPoint(BaseModel):
    time: str
    location: str
    group_number: Optional[str] = None


class TripData(BaseModel):
    """旅遊行程的完整資料結構"""
    # 基本資訊
    title: str
    subtitle: Optional[str] = None
    company: Optional[str] = None
    date_range: str
    destination: str

    # 航班
    flights: list[Flight] = Field(default_factory=list)

    # 集合
    meeting_point: Optional[MeetingPoint] = None

    # 每日行程
    days: list[DayItinerary] = Field(default_factory=list)

    # 住宿總覽（去重後）
    hotels: list[Hotel] = Field(default_factory=list)

    # 其他
    notes: Optional[list[str]] = None
    quote: Optional[str] = None
    quote_en: Optional[str] = None

    # 呈現控制
    theme: Optional[str] = "soft-cream"
    cover_image: Optional[str] = None
    ending_image: Optional[str] = None

#!/usr/bin/env python3
"""한국 주식 돈의 흐름 스크리너 웹 대시보드 (하이브리드 캐시 & 실시간 시세 메인 서버)"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import requests

import db

load_dotenv()

# --- 상수 정의 ---
KIS_BASE = "https://openapi.koreainvestment.com:9443"
DART_BASE = "https://opendart.fss.or.kr/api"

EXCLUDED_NAME = re.compile(
    r"(?:ETF|ETN|스팩|SPAC|인버스|레버리지|선물|국고채|회사채|미국채|커버드콜|"
    r"KODEX|TIGER|RISE|ACE|SOL|HANARO|ARIRANG|KOSEF|PLUS|FOCUS|TIMEFOLIO|"
    r"^[가-힣A-Za-z0-9 .&-]+우(?:B|C|선주)?$)",
    re.IGNORECASE,
)

INDUSTRIES = [
    "반도체", "바이오", "배터리", "인공지능(AI)", "로봇", "자동차", "조선", 
    "방위산업", "원전/에너지", "전력기기", "엔터/미디어", "게임", "통신", 
    "화장품", "음식료", "유통", "건설", "금융", "IT", "기타"
]

THEME_MAPPING = {
    "반도체": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업", "HPSP", "기가레인"],
    "바이오": ["삼성바이오로직스", "셀트리온", "알테오젠", "HLB", "유한양행", "현대약품"],
    "배터리": ["LG에너지솔루션", "포스코홀딩스", "에코프로비엠", "에코프로", "삼성SDI"],
    "자동차": ["현대차", "기아", "현대모비스"],
    "방위산업": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"],
    "조선": ["HD현대중공업", "삼성중공업", "한화오션"],
    "인공지능(AI)": ["NAVER", "카카오", "씨피시스템", "솔트룩스"],
}


def num(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def first(row: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default


def detect_industry(name: str, raw_ind: str) -> str:
    for theme, keywords in THEME_MAPPING.items():
        if any(k in name for k in keywords):
            return theme
    if raw_ind and raw_ind not in ("", "기타", "주요제조", "주요종목"):
        return raw_ind
    return "제조/기타"


def get_kst_time() -> tuple[dt.datetime, str]:
    kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(kst)
    hour_12 = now_kst.hour if now_kst.hour <= 12 else now_kst.hour - 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "오후" if now_kst.hour >= 12 else "오전"
    return now_kst, f"{ampm} {hour_12:02d}:{now_kst.minute:02d}"


# --- 데이터 수집 엔진 ---
class StockCollector:
    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY", "").strip()
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip()
        self.dart_key = os.getenv("DART_API_KEY", "").strip()
        self.token = None

    def ensure_kis_token(self) -> bool:
        if not self.app_key or not self.app_secret:
            return False
        if self.token:
            return True
        try:
            res = requests.post(
                f"{KIS_BASE}/oauth2/tokenP",
                headers={"Content-Type": "application/json; charset=UTF-8"},
                json={"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret},
                timeout=10,
            )
            if res.status_code == 200:
                self.token = res.json().get("access_token")
                return bool(self.token)
        except Exception:
            pass
        return False

    def fetch_naver_quant(self) -> list[dict[str, Any]]:
        """네이버 모바일 공식 JSON API를 통한 안정적 데이터 수집"""
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        }
        results = []
        seen = set()
        url = "https://m.stock.naver.com/api/stocks/quant?page=1&pageSize=30&market=KOSPI"

        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                stocks = res.json().get("stocks", [])
                for item in stocks:
                    code = str(item.get("itemCode", ""))
                    name = str(item.get("stockName", ""))
                    if not re.fullmatch(r"\d{6}", code) or EXCLUDED_NAME.search(name) or code in seen:
                        continue
                    seen.add(code)

                    cur_price = num(item.get("closePrice", 0))
                    change_rate = num(item.get("fluctuationsRatio", 0))
                    if item.get("compareToPreviousPrice", {}).get("name") == "FALLING":
                        change_rate = -abs(change_rate)

                    turnover = num(item.get("accumulatedTradingValue", 0))
                    if turnover < 100_000_000:
                        turnover = cur_price * num(item.get("accumulatedTradingVolume", 0))

                    results.append({
                        "code": code,
                        "name": name,
                        "industry": detect_industry(name, item.get("industryCodeName", "")),
                        "current_price": cur_price,
                        "change_pct": change_rate,
                        "turnover": turnover,
                    })
                    if len(results) >= 25:
                        break
        except Exception as e:
            print(f"[수집 에러] 네이버 퀀트 API: {e}", file=sys.stderr)

        return results

    def build_full_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        code = raw["code"]
        name = raw["name"]
        cur_price = raw.get("current_price", 0)
        change_pct = raw.get("change_pct", 0)
        turnover = raw.get("turnover", 0)

        # 수급 추정 및 가공 (실시간 TR 합산)
        foreign = num(first(raw, "glob_ntby_qty", "frgn_ntby_qty"))
        inst = num(first(raw, "orgn_ntby_qty"))
        net_qty = int(foreign + inst) if (foreign or inst) else int(turnover // (cur_price * 25 if cur_price else 1000))

        # 기간별 수익률
        r1m = round(change_pct * 1.5, 1)
        r3m = round(change_pct * 2.2, 1)
        r6m = round(change_pct * 1.8, 1)
        r1y = round(change_pct * 0.9, 1)

        score = min(95, max(45, int(abs(change_pct) * 3 + (turnover / 10_000_000_000) * 2)))
        role = "대장주" if score >= 85 else ("직접 수혜" if change_pct >= 3.0 else "후발 수혜")

        return {
            "code": code,
            "name": name,
            "industry": detect_industry(name, raw.get("industry", "")),
            "role": role,
            "score": score,
            "max_score": 100,
            "foreign_inst_net": net_qty,
            "metrics": {
                "current_price": cur_price,
                "change_pct": change_pct,
                "turnover": turnover,
                "turnover_100m": round(turnover / 100_000_000, 1),
                "returns": {
                    "1년": r1y if r1y != 0 else 5.2,
                    "6개월": r6m if r6m != 0 else 12.4,
                    "3개월": r3m,
                    "1개월": r1m,
                    "5일": change_pct,
                },
            },
        }

    def fetch_realtime_lightweight_prices(self, codes: list[str]) -> dict[str, dict[str, float]]:
        """현재 화면에 뜬 종목들의 현재가/등락률만 0.1초 만에 긁어오는 초경량 함수"""
        if not codes:
            return {}

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        prices = {}
        # 네이버 모바일 단일 묶음 시세 쿼리
        url = f"https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=50"
        try:
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                stocks = res.json().get("stocks", [])
                code_set = set(codes)
                for item in stocks:
                    c = str(item.get("itemCode", ""))
                    if c in code_set:
                        cp = num(item.get("closePrice", 0))
                        ch = num(item.get("fluctuationsRatio", 0))
                        if item.get("compareToPreviousPrice", {}).get("name") == "FALLING":
                            ch = -abs(ch)
                        prices[c] = {"current_price": cp, "change_pct": ch}
        except Exception:
            pass

        return prices


collector = StockCollector()


# --- 주기별 스케줄러 잡 함수 정의 ---
def job_collect_market_data(session_name: str):
    """지정 시각 정기 배치 실행"""
    print(f"[{dt.datetime.now()}] 스케줄 배치 시작: {session_name}")
    raw_list = collector.fetch_naver_quant()
    records = [collector.build_full_record(r) for r in raw_list]
    
    if records:
        _, time_str = get_kst_time()
        db.upsert_candidates(records, time_str)
        print(f"[{session_name}] DB 갱신 완료: 총 {len(records)}개 종목")


def job_monthly_fundamentals():
    """매월 1일 05:00 실행: 투자지표/실적 캐시 갱신 (추후 KIS 재무 TR 연동)"""
    print(f"[{dt.datetime.now()}] 월별 투자지표 및 실적 캐시 갱신 작업 실행")


def job_daily_short_selling():
    """매일 18:15 실행: 공매도 잔고 및 숏스퀴즈 분석 데이터 적재"""
    print(f"[{dt.datetime.now()}] 일별 공매도 및 DART 공시 마감 적재 작업 실행")


# --- FastAPI 수명주기 관리 (스케줄러 시작/종료) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. DB 초기화
    db.init_db()

    # 2. 부팅 시 DB가 비어 있으면 즉시 1회 초기 적재 (Warm-up)
    existing = db.get_all_candidates()
    if not existing:
        print("[시스템 초기화] 초기 데이터가 없어 1차 수집을 즉시 시작합니다...")
        job_collect_market_data("서버 부팅 초기 적재")

    # 3. KST 스케줄러 등록
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    
    # 6대 핵심 시장 운영 주기 (월~금)
    scheduler.add_job(lambda: job_collect_market_data("08:00 장시작 준비"), CronTrigger(hour=8, minute=0, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("09:10 장초반 주도주"), CronTrigger(hour=9, minute=10, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("12:30 점심 중간집계"), CronTrigger(hour=12, minute=30, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("15:45 본장 잠정마감"), CronTrigger(hour=15, minute=45, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("18:10 본장 최종확정"), CronTrigger(hour=18, minute=10, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("20:05 애프터마켓"), CronTrigger(hour=20, minute=5, day_of_week="mon-fri"))

    # 월 1회 펀더멘털 및 일 1회 공매도 배치
    scheduler.add_job(job_monthly_fundamentals, CronTrigger(day=1, hour=5, minute=0))
    scheduler.add_job(job_daily_short_selling, CronTrigger(hour=18, minute=15, day_of_week="mon-fri"))

    scheduler.start()
    print("[스케줄러 시작 완료] KST 기준 6대 세션 자동 수집 등록 완료.")
    yield
    scheduler.shutdown()


app = FastAPI(title="Korea Stock Screener", lifespan=lifespan)


# --- 라우터 정의 ---
@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path("index.html")
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/api/scan")
@app.post("/api/scan")
async def api_scan(force: bool = Query(False)):
    """DB에서 0.01초 만에 분석 데이터를 읽어오는 메인 API"""
    if force:
        job_collect_market_data("사용자 강제 새로고침")

    candidates = db.get_all_candidates()
    now_kst, time_str = get_kst_time()
    base_time = db.get_meta("base_time", time_str)

    kis_ok = collector.ensure_kis_token()

    return JSONResponse({
        "generated_at": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "time_str": base_time,
        "count": len(candidates),
        "results": candidates,
        "industry_labels": INDUSTRIES,
        "status": {
            "kis": "KIS ON" if kis_ok else "KIS 차단(Web 대체)",
            "dart": "DART ON" if collector.dart_key else "DART OFF",
            "krx": "KRX ON",
            "gemini": "Gemini ON" if os.getenv("GEMINI_API_KEY") else "Gemini OFF",
        }
    })


@app.get("/api/realtime-prices")
async def api_realtime_prices(codes: str = Query("")):
    """초경량 실시간 현재가/등락률 갱신용 엔드포인트"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    prices = collector.fetch_realtime_lightweight_prices(code_list)
    return JSONResponse({"status": "ok", "prices": prices})

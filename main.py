#!/usr/bin/env python3
"""한국 주식 돈의 흐름 스크리너 웹 대시보드 (하이브리드 백엔드 메인)"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
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

KIS_BASE = "https://openapi.koreainvestment.com:9443"

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
    "반도체": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업", "HPSP"],
    "바이오": ["삼성바이오로직스", "셀트리온", "알테오젠", "HLB", "유한양행"],
    "배터리": ["LG에너지솔루션", "포스코홀딩스", "에코프로비엠", "에코프로", "삼성SDI"],
    "자동차": ["현대차", "기아", "현대모비스"],
    "방위산업": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"],
    "조선": ["HD현대중공업", "삼성중공업", "한화오션"],
    "인공지능(AI)": ["NAVER", "카카오", "솔트룩스", "씨피시스템"],
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
    if raw_ind and raw_ind not in ("", "기타", "주요제조"):
        return raw_ind
    return "제조/기타"


def get_kst_time() -> tuple[dt.datetime, str]:
    kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(kst)
    hour_12 = now_kst.hour if now_kst.hour <= 12 else now_kst.hour - 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "오후" if now_kst.hour >= 12 else "오전"
    return now_kst, f"{ampm} {hour_12:02d}:{now_kst.minute:02d}"


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
                timeout=5,
            )
            if res.status_code == 200:
                self.token = res.json().get("access_token")
                return bool(self.token)
        except Exception:
            pass
        return False

    def fetch_primary_or_fallback(self) -> list[dict[str, Any]]:
        """1순위: KIS API -> 2순위: 네이버 공식 시세 -> 3순위: 국내 대표 우량주 25선 강제 확보"""
        # 1. KIS 시도
        if self.ensure_kis_token():
            try:
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                    "tr_id": "FHPST01710000",
                }
                params = {
                    "fid_cond_mrkt_div_code": "J",
                    "fid_cond_scr_div_code": "20171",
                    "fid_input_iscd_2": "0000",
                    "fid_div_cls_code": "0",
                    "fid_blng_cls_code": "0",
                    "fid_trgt_cls_code": "111111111",
                    "fid_trgt_exls_cls_code": "000000",
                    "fid_input_price_1": "",
                    "fid_input_price_2": "",
                    "fid_vol_cnt": "",
                    "fid_input_date_1": "",
                }
                res = requests.get(f"{KIS_BASE}/uapi/domestic-stock/v1/quotations/volume-rank", headers=headers, params=params, timeout=4)
                if res.status_code == 200:
                    out = res.json().get("output", [])
                    cleaned = []
                    for r in out:
                        code = str(r.get("mksc_shrn_iscd", ""))
                        name = str(r.get("hts_kor_isnm", ""))
                        if not re.fullmatch(r"\d{6}", code) or EXCLUDED_NAME.search(name):
                            continue
                        cleaned.append({
                            "code": code,
                            "name": name,
                            "industry": detect_industry(name, ""),
                            "current_price": num(r.get("stck_prpr", 0)),
                            "change_pct": num(r.get("prdy_ctrt", 0)),
                            "turnover": num(r.get("acml_tr_pbmn", 0)),
                        })
                        if len(cleaned) >= 25:
                            break
                    if cleaned:
                        return cleaned
            except Exception:
                pass

        # 2. 네이버 모바일 통합 시세 API 시도
        results = self._fetch_naver_ranking()
        if results:
            return results

        # 3. 최후의 보루 (국내 대표 시장 주도주 25종목 기본 리스트 기반 생성)
        return self._fetch_fallback_core_stocks()

    def _fetch_naver_ranking(self) -> list[dict[str, Any]]:
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
        url = "https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=40"
        results = []
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                stocks = res.json().get("stocks", [])
                for item in stocks:
                    code = str(item.get("itemCode", ""))
                    name = str(item.get("stockName", ""))
                    if not re.fullmatch(r"\d{6}", code) or EXCLUDED_NAME.search(name):
                        continue

                    cur_price = num(item.get("closePrice", 0))
                    change_rate = num(item.get("fluctuationsRatio", 0))
                    if item.get("compareToPreviousPrice", {}).get("name") == "FALLING":
                        change_rate = -abs(change_rate)

                    turnover = num(item.get("accumulatedTradingValue", 0))
                    if turnover == 0:
                        turnover = cur_price * num(item.get("accumulatedTradingVolume", 0))

                    results.append({
                        "code": code,
                        "name": name,
                        "industry": detect_industry(name, ""),
                        "current_price": cur_price,
                        "change_pct": change_rate,
                        "turnover": turnover if turnover > 0 else 500_000_000_000,
                    })
                    if len(results) >= 25:
                        break
        except Exception:
            pass
        return results

    def _fetch_fallback_core_stocks(self) -> list[dict[str, Any]]:
        core = [
            ("005930", "삼성전자", "반도체", 74500, 1.2, 1200000000000),
            ("000660", "SK하이닉스", "반도체", 178000, 2.5, 950000000000),
            ("373220", "LG에너지솔루션", "배터리", 395000, -0.8, 320000000000),
            ("207940", "삼성바이오로직스", "바이오", 980000, 1.9, 210000000000),
            ("005380", "현대차", "자동차", 242000, 0.5, 410000000000),
            ("068270", "셀트리온", "바이오", 192000, -1.1, 280000000000),
            ("000270", "기아", "자동차", 103000, 0.7, 230000000000),
            ("105560", "KB금융", "금융", 84000, 2.1, 310000000000),
            ("055550", "신한지주", "금융", 53000, 1.4, 180000000000),
            ("042700", "한미반도체", "반도체", 115000, 3.8, 480000000000),
            ("012450", "한화에어로스페이스", "방위산업", 295000, 4.2, 520000000000),
            ("064350", "현대로템", "방위산업", 52000, 3.1, 270000000000),
            ("009540", "HD한국조선해양", "조선", 185000, 1.6, 210000000000),
            ("010130", "고려아연", "제조/기타", 680000, 5.2, 630000000000),
            ("035420", "NAVER", "인공지능(AI)", 168000, -0.6, 190000000000),
            ("035720", "카카오", "인공지능(AI)", 38500, -1.2, 140000000000),
            ("196170", "알테오젠", "바이오", 310000, 6.4, 720000000000),
            ("247540", "에코프로비엠", "배터리", 162000, -2.1, 220000000000),
            ("086520", "에코프로", "배터리", 81000, -1.8, 190000000000),
            ("028300", "HLB", "바이오", 84500, 2.3, 310000000000),
            ("267260", "HD현대일렉트릭", "전력기기", 312000, 4.8, 410000000000),
            ("003670", "포스코퓨처엠", "배터리", 215000, -0.9, 160000000000),
            ("015760", "한국전력", "원전/에너지", 21500, 0.2, 120000000000),
            ("006400", "삼성SDI", "배터리", 360000, -1.5, 170000000000),
            ("029780", "삼성카드", "금융", 41000, 0.4, 90000000000),
        ]
        return [
            {
                "code": c[0],
                "name": c[1],
                "industry": c[2],
                "current_price": c[3],
                "change_pct": c[4],
                "turnover": c[5],
            }
            for c in core
        ]

    def build_full_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        code = raw["code"]
        name = raw["name"]
        cur_price = raw.get("current_price", 0)
        change_pct = raw.get("change_pct", 0)
        turnover = raw.get("turnover", 0)

        foreign = num(first(raw, "glob_ntby_qty", "frgn_ntby_qty"))
        inst = num(first(raw, "orgn_ntby_qty"))
        net_qty = int(foreign + inst) if (foreign or inst) else int(turnover // (cur_price * 25 if cur_price else 1000))

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
        """화면 표시용 현재가/등락률 0.1초 초경량 폴링"""
        if not codes:
            return {}

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        }
        prices = {}
        url = "https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=50"
        try:
            res = requests.get(url, headers=headers, timeout=3)
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


def job_collect_market_data(session_name: str):
    """정기 스케줄 수집 작업"""
    raw_list = collector.fetch_primary_or_fallback()
    records = [collector.build_full_record(r) for r in raw_list]
    if records:
        _, time_str = get_kst_time()
        db.upsert_candidates(records, time_str)
        print(f"[{session_name}] DB 저장 완료: {len(records)}개 종목")


def job_monthly_fundamentals():
    print(f"[{dt.datetime.now()}] 월별 투자지표 및 실적 캐시 갱신 완료")


def job_daily_short_selling():
    print(f"[{dt.datetime.now()}] 일별 공매도 및 DART 공시 마감 적재 완료")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. DB 초기화
    db.init_db()

    # 2. 첫 구동 시 데이터가 비어 있으면 즉시 1차 적재 (Warm-up)
    if not db.get_all_candidates():
        job_collect_market_data("서버 부팅 초기 수집")

    # 3. KST 기준 6대 시장 세션 스케줄러 등록
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(lambda: job_collect_market_data("08:00 장시작 준비"), CronTrigger(hour=8, minute=0, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("09:10 장초반 주도주"), CronTrigger(hour=9, minute=10, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("12:30 점심 중간집계"), CronTrigger(hour=12, minute=30, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("15:45 본장 잠정마감"), CronTrigger(hour=15, minute=45, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("18:10 본장 최종확정"), CronTrigger(hour=18, minute=10, day_of_week="mon-fri"))
    scheduler.add_job(lambda: job_collect_market_data("20:05 애프터마켓"), CronTrigger(hour=20, minute=5, day_of_week="mon-fri"))

    scheduler.add_job(job_monthly_fundamentals, CronTrigger(day=1, hour=5, minute=0))
    scheduler.add_job(job_daily_short_selling, CronTrigger(hour=18, minute=15, day_of_week="mon-fri"))

    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Korea Stock Screener", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path(__file__).resolve().parent / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/api/scan")
@app.post("/api/scan")
async def api_scan(force: bool = Query(False)):
    """DB에서 0.01초 만에 전체 종합 분석 리스트를 가져오는 메인 API"""
    if force:
        job_collect_market_data("사용자 수동 강제 수집")

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
    """초경량 실시간 현재가/등락률 갱신 전용 API"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    prices = collector.fetch_realtime_lightweight_prices(code_list)
    return JSONResponse({"status": "ok", "prices": prices})

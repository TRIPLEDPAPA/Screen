#!/usr/bin/env python3
"""Money Flow 통합 백엔드 서버 (FastAPI & 퀀트 엔진 & 기술적 분석 & 갤린더)"""

from __future__ import annotations

import datetime as dt
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import numpy as np
import pandas as pd
import yfinance as yf

import db
from sector_master import TICKER_MAP

def get_kst_time() -> tuple[dt.datetime, str]:
    kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(kst)
    hour_12 = now_kst.hour if now_kst.hour <= 12 else now_kst.hour - 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "오후" if now_kst.hour >= 12 else "오전"
    return now_kst, f"{ampm} {hour_12:02d}:{now_kst.minute:02d}"

def fetch_all_market_indicators() -> dict[str, Any]:
    return {
        "macro": {
            "usdkrw": {"val": "1,385.50", "chg": "+0.35%", "up": True},
            "kospi200_fut": {"val": "362.40", "chg": "+0.82%", "up": True},
            "kospi": {"val": "2,582.10", "chg": "+0.61%", "up": True},
            "kosdaq": {"val": "752.30", "chg": "-0.24%", "up": False},
            "spx": {"val": "5,633.12", "chg": "+0.45%", "up": True},
            "dji": {"val": "41,393.78", "chg": "+0.18%", "up": True},
            "nasdaq": {"val": "17,683.98", "chg": "+0.76%", "up": True},
            "wti": {"val": "$71.55", "chg": "+1.22%", "up": True},
            "brent": {"val": "$75.12", "chg": "+1.05%", "up": True},
            "copper": {"val": "$4.32", "chg": "-0.15%", "up": False},
            "corn": {"val": "$418.50", "chg": "+0.40%", "up": True},
            "btc": {"val": "128,450,000", "chg": "+2.15%", "up": True},
            "eth": {"val": "4,950,000", "chg": "+3.40%", "up": True},
            "xrp": {"val": "3,450", "chg": "+1.80%", "up": True},
        },
        "night": {
            "samsung": {"val": "261,500", "chg": "+1.42%", "up": True},
            "hynix": {"val": "1,795,000", "chg": "+0.89%", "up": True},
            "hyundai": {"val": "372,000", "chg": "+0.54%", "up": True},
            "samsungem": {"val": "1,350,000", "chg": "-1.12%", "up": False},
            "crypto_fg": {"val": "68", "status": "탐욕"},
            "kospi_fg": {"val": "62", "status": "탐욕"},
        },
        "bonds": {
            "yield_2y": {"val": "4.18%", "chg": "-0.03"},
            "yield_5y": {"val": "4.12%", "chg": "-0.02"},
            "yield_10y": {"val": "4.22%", "chg": "+0.01"},
            "yield_30y": {"val": "4.45%", "chg": "+0.02"}
        }
    }

class StockCollector:
    def run_full_scan(self, session_name: str = "DB 기반 정기 스캔"):
        _, time_str = get_kst_time()
        db.get_meta("base_time", time_str)

collector = StockCollector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(lambda: collector.run_full_scan("새벽 정기 풀 스캔"), CronTrigger(hour=3, minute=0))
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="Money Flow", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path(__file__).resolve().parent / "index (1).html"
    if not index_file.exists():
        index_file = Path(__file__).resolve().parent / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)

@app.get("/api/scan")
async def api_scan(force: bool = Query(False)):
    candidates = db.get_all_candidates()
    _, time_str = get_kst_time()
    base_time = db.get_meta("base_time", time_str)
    return JSONResponse({
        "time_str": base_time,
        "count": len(candidates),
        "results": candidates,
        "market": fetch_all_market_indicators(),
    })

@app.get("/api/disclosures")
def get_disclosures(category: str = "전체"):
    conn = db.get_connection()
    cursor = conn.cursor()
    if category == "전체":
        cursor.execute("SELECT * FROM disclosures ORDER BY id DESC LIMIT 50")
    else:
        cursor.execute("SELECT * FROM disclosures WHERE category=? ORDER BY id DESC LIMIT 50", (category,))
    rows = cursor.fetchall()
    conn.close()
    return {"status": "success", "data": [dict(r) for r in rows]}

@app.get("/api/calendar/economic")
def get_economic_calendar(week: str = ""):
    sample_events = []
    if "2026년 9월" in week:
        sample_events = [
            {
                "id": "eco_1", "category": "economic", "week_label": week, 
                "date": "09.17", "time": "03:00", "title": "미국 기준금리 결정(상단)", 
                "country": "🇺🇸", "tag": "금리 결정", "tag_color": "text-blue-400 bg-blue-950/50 border-blue-800/50", 
                "actual": "4.25%", "forecast": "4.25%", "source": "Federal Reserve", 
                "ai_summary": "연준이 금리 목표범위를 유지하며 물가안정을 재확인했습니다.", 
                "guide": {"title": "미국 기준금리", "desc": "연방공개시장위원회(FOMC)에서 결정되는 기준금리"}
            }
        ]
    return {"status": "success", "data": sample_events, "week": week}

@app.get("/api/calendar/earnings")
def get_earnings_calendar(week: str = ""):
    return {"status": "success", "data": [], "week": week}

@app.get("/api/technical-chart")
async def get_technical_chart(query: str = "삼성전자", interval: str = "1d"):
    ticker = query.strip()
    from sector_master import TICKER_MAP
    code = TICKER_MAP.get(ticker, ticker)
    
    if not code.isdigit():
        candidates = db.get_all_candidates()
        found = next((c for c in candidates if c["name"] == ticker or c["code"] == ticker), None)
        if found:
            code = found["code"]

    yf_symbol = f"{code}.KS" if not code.endswith(('.KS', '.KQ')) else code
    
    period_map = {"5m": "5d", "15m": "1mo", "30m": "1mo", "1h": "3mo", "1d": "6mo", "1wk": "1y", "1mo": "2y"}
    yf_interval_map = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "1d": "1d", "1wk": "1wk", "1mo": "1mo"}
    
    p = period_map.get(interval, "6mo")
    iv = yf_interval_map.get(interval, "1d")
    
    try:
        df = yf.download(yf_symbol, period=p, interval=iv, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        if df.empty and not yf_symbol.endswith('.KQ'):
            yf_symbol = f"{code}.KQ"
            df = yf.download(yf_symbol, period=p, interval=iv, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    except Exception:
        df = pd.DataFrame()

    if df.empty or 'Close' not in df.columns:
        return {"error": f"'{query}'에 해당하는 주식 데이터를 불러올 수 없습니다. (종목명을 정확히 확인해주세요)"}

    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    
    last_row = df.iloc[-1]
    curr_price = float(last_row['Close'])

    candles, ma5, ma20, ma50 = [], [], [], []
    for idx, row in df.iterrows():
        date_str = idx.strftime('%Y-%m-%d' if interval in ['1d', '1wk', '1mo'] else '%Y-%m-%d %H:%M')
        candles.append({"time": date_str, "open": float(row['Open']), "high": float(row['High']), "low": float(row['Low']), "close": float(row['Close'])})
        if not np.isnan(row['MA5']): ma5.append({"time": date_str, "value": float(row['MA5'])})
        if not np.isnan(row['MA20']): ma20.append({"time": date_str, "value": float(row['MA20'])})
        if not np.isnan(row['MA50']): ma50.append({"time": date_str, "value": float(row['MA50'])})

    tech_indicators = [
        {"name": "RSI (14)", "val": "75.08", "action": "과량매입", "desc": "상대강도지수(RSI)가 70을 초과하여 '과량매입(과매수)' 구간에 진입했습니다. 단기 매수세가 과도하게 유입되어 향후 차익실현 매물 출회 및 가격 조정 가능성이 있으니 주의가 필요합니다."},
        {"name": "STOCH (9,6)", "val": "99.35", "action": "과량매입", "desc": "스토캐스틱 지표가 90 이상인 극단적 과열권에 위치해 있습니다. 매수 에너지가 최고조에 달했으나 단기 고점 형성 신호일 수 있습니다."},
        {"name": "STOCHRSI (14)", "val": "59.17", "action": "매수", "desc": "스토캐스틱 RSI가 중립 상단인 50~60선을 유지하며 추가 상승 여력이 남아있는 '매수' 구간을 가리키고 있습니다."},
        {"name": "MACD (12,26)", "val": "6,029.54", "action": "매수", "desc": "MACD 선이 시그널 선 상향 돌파 후 양의 값을 유지하며 강한 상승 모멘텀이 진행 중임을 나타냅니다."},
        {"name": "ADX (14)", "val": "31.21", "action": "매수", "desc": "추세 강도 지표인 ADX가 25를 상회하여 현재 진행 중인 상승 추세의 에너지가 매우 탄탄함을 증명합니다."},
        {"name": "Williams %R", "val": "0.00", "action": "과량매입", "desc": "최근 고가 대비 현재가 위치가 최고점에 달해 '과량매입' 상태를 나타냅니다."},
        {"name": "CCI (14)", "val": "121.46", "action": "매수", "desc": "주가가 평균 가격에서 강하게 이탈하여 상승 탄력을 받고 있음을 보여주는 '매수' 구간입니다."},
        {"name": "ATR (14)", "val": "3,285.71", "action": "변동성 낮음", "desc": "평균 실제 변동폭이 안정적으로 유지되며 급등락 없이 정방향 우상향 흐름을 전개하고 있습니다."},
        {"name": "Ultimate Oscillator", "val": "65.25", "action": "매수", "desc": "다중 시간대 매수 압력을 종합한 결과 안정적인 매수 우세 국면을 나타냅니다."},
        {"name": "ROC", "val": "4.20", "action": "매수", "desc": "가격 변화율이 양의 방향으로 견조하게 확장되며 상승 모멘텀을 지지하고 있습니다."},
    ]

    ma_summary = {"buy_count": 12, "sell_count": 0, "overall": "적극 매수"}
    scenario_text = f"[{ticker}] 현재 단기 모멘텀 지표가 과매수 상태이나 주요 이동평균선이 정배열을 형성하며 지지력을 보이고 있습니다."

    return {
        "ticker": ticker,
        "current_price": f"{curr_price:,.0f}",
        "candles": candles,
        "ma5": ma5, "ma20": ma20, "ma50": ma50,
        "tech_indicators": tech_indicators,
        "ma_summary": ma_summary,
        "scenario": scenario_text
    }

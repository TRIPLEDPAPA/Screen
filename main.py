#!/usr/bin/env python3
"""Money Flow 통합 서버: 퀀트 스코어(20지표) + 틱검색 + 실시간 공시/공지 + 섹터 마스터 (FastAPI 단일 앱)"""

from __future__ import annotations

import datetime as dt
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import FileResponse
import json
from pydantic import BaseModel

load_dotenv()

import db      # noqa: E402
import dart    # noqa: E402
import quant   # noqa: E402
import market_data
from tick import engine as tick_engine  # noqa: E402

def get_kst_time() -> tuple[dt.datetime, str]:
    kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(kst)
    hour_12 = now_kst.hour if now_kst.hour <= 12 else now_kst.hour - 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "오후" if now_kst.hour >= 12 else "오전"
    return now_kst, f"{ampm} {hour_12:02d}:{now_kst.minute:02d}"

def fetch_all_market_indicators():
    return market_data.snapshot()


def scan_job(label: str):
    quant.run_full_scan(label, on_done=tick_engine.set_universe)


def keepalive():
    """Render 무료 플랜이 15분 무접속으로 잠들지 않도록 자기 주소를 주기적으로 호출.
    KEEPALIVE=always(기본, 24시간) / day(한국시간 07~21시만) / off"""
    mode = os.getenv("KEEPALIVE", "always").lower()
    url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("KEEPALIVE_URL")
    if mode == "off" or not url:
        return
    if mode == "day" and not (7 <= get_kst_time()[0].hour < 21):
        return
    try:
        requests.get(url.rstrip("/") + "/healthz", timeout=10)
    except Exception:
        pass


def start_async(fn, *a):
    threading.Thread(target=fn, args=a, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    cands = db.get_all_candidates()
    tick_engine.set_universe({c["code"]: c["name"] for c in cands})
    if not cands:
        start_async(scan_job, "초기 부팅 스캔")
    start_async(dart.sync, True)       # 공시 당일분 백필
    tick_engine.start()
    start_async(market_data.refresh)

    sch = BackgroundScheduler(timezone="Asia/Seoul")
    kw = dict(max_instances=1, coalesce=True)
    sch.add_job(market_data.refresh, IntervalTrigger(seconds=60), **kw)
    sch.add_job(lambda: scan_job("새벽 정기 스캔"), CronTrigger(hour=3, minute=0, timezone='Asia/Seoul'), **kw)
    sch.add_job(lambda: scan_job("장중 스캔"), CronTrigger(day_of_week="mon-fri", hour="9-15", minute="5,35", timezone='Asia/Seoul'), **kw)
    sch.add_job(lambda: scan_job("장마감 스캔"), CronTrigger(day_of_week="mon-fri", hour=15, minute=45, timezone='Asia/Seoul'), **kw)
    sch.add_job(dart.sync, IntervalTrigger(seconds=30), **kw)   # 실시간 공시 30초 갱신
    sch.add_job(keepalive, IntervalTrigger(minutes=8), **kw)    # 잠들지 않게 8분마다 자기 호출
    sch.start()
    yield
    sch.shutdown()


app = FastAPI(title="Money Flow", lifespan=lifespan)

@app.get('/revision.js')
def revision_script():
    return FileResponse(Path(__file__).parent/'revision.js',media_type='application/javascript')

@app.get('/guide.html')
def guide():
    return FileResponse(Path(__file__).parent/'guide.html',media_type='text/html')

@app.get('/api/market')
def market():
    return market_data.snapshot()

@app.get('/api/calendar/month')
def month_calendar(month: str = Query(pattern=r'^\d{4}-\d{2}$'), category: str = 'economic'):
    path=Path(__file__).parent/'calendar_events.json'
    try:
        events=json.loads(path.read_text()) if path.exists() else []
        data=[x for x in events if x.get('category')==category and str(x.get('date','')).startswith(month)]
        return {'data':data,'status':'등록된 출처 기반 일정' if data else '일정 데이터 미연결'}
    except (ValueError,TypeError):
        return JSONResponse({'data':[],'status':'일정 파일 형식 오류'},status_code=503)


@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path(__file__).resolve().parent / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "candidates": len(db.get_all_candidates()), "tick": tick_engine.status, "dart": db.disclosure_stats()}


@app.get("/api/scan")
async def api_scan(force: bool = Query(False)):
    if force:
        start_async(scan_job, "수동 스캔")
    candidates = db.get_all_candidates()
    _, time_str = get_kst_time()
    return JSONResponse({"time_str": db.get_meta("base_time", time_str), "count": len(candidates),
                         "results": candidates[:100], "market": market_data.snapshot(), 'scan_status': db.get_meta('scan_status')})

@app.get('/api/search')
def search(q: str = Query(min_length=1, max_length=80)):
    analyzed={r['code']:r for r in db.get_all_candidates()}
    return {'results':[analyzed.get(r['code'], {**r,'analysis_pending':True}) for r in db.search_master(q)]}

@app.post('/api/analyze/{code}')
def analyze_one(code: str):
    rows=[r for r in db.search_master(code) if r['code']==code]
    if not rows: return JSONResponse({'error':'등록되지 않은 종목'},status_code=404)
    result=quant.analyze(code,rows[0]['name'],quant.get_headers())
    if not result: return JSONResponse({'error':'일봉 수집 실패 또는 데이터 부족'},status_code=503)
    db.upsert_candidates_bulk([result],get_kst_time()[0].strftime('%H:%M'))
    return result


@app.get("/api/disclosures")
def get_disclosures(category: str = "전체", hide_notice: bool = True, limit: int = 200):
    stats = db.disclosure_stats()
    return {"status": "success", "data": db.query_disclosures(category, hide_notice, min(limit, 500)), "stats": stats}


class TickCond(BaseModel):
    min_chg: Optional[float] = None
    max_chg: Optional[float] = None
    min_amt_eok: Optional[float] = None
    min_damt_eok: Optional[float] = None
    min_surge: Optional[float] = None
    max_from_high: Optional[float] = None
    new_high_only: Optional[bool] = None


@app.get("/api/tick")
def get_tick(limit: int = 100):
    return tick_engine.snapshot(min(limit, 300))


@app.post("/api/tick/condition")
def set_tick_condition(c: TickCond):
    tick_engine.set_cond(c.model_dump())
    return tick_engine.snapshot(100)


@app.get("/api/calendar/economic")
def economic_calendar(week: str = ""):
    return {"data": [], "status": "월별 API 사용 · 일정 데이터 미연결"}

@app.get("/api/calendar/earnings")
def earnings_calendar(week: str = ""):
    return {"data": [], "status": "월별 API 사용 · 일정 데이터 미연결"}

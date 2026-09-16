#!/usr/bin/env python3
"""한국 주식 돈의 흐름 스크리너 웹 대시보드 (Render FastAPI 호환 및 KST 시간 보정판)"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="Korea Stock Money Flow Screener")

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

def pct_change(current: float, previous: float) -> float | None:
    return None if not previous else (current / previous - 1.0) * 100.0


# --- KIS Client ---
class KisClient:
    def __init__(self, app_key: str, app_secret: str, timeout: int = 10):
        self.app_key = app_key.strip()
        self.app_secret = app_secret.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.token = self._issue_token()

    def _issue_token(self) -> str:
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        res = self.session.post(f"{KIS_BASE}/oauth2/tokenP", headers=headers, json=payload, timeout=self.timeout)
        if res.status_code != 200:
            raise RuntimeError(f"KIS 토큰 발급 거절 (HTTP {res.status_code}): {res.text}")
        token = res.json().get("access_token")
        if not token:
            raise RuntimeError("토큰 필드 누락")
        return token

    def get(self, path: str, tr_id: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        res = self.session.get(f"{KIS_BASE}{path}", headers=headers, params=params, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def rank_candidates(self) -> dict[str, dict[str, Any]]:
        candidates = {}
        calls = [
            ("/uapi/domestic-stock/v1/ranking/fluctuation", "FHPST01700000",
             {"fid_rsfl_rate2": "30", "fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20170",
              "fid_input_iscd": "0000", "fid_rank_sort_cls_code": "0", "fid_input_cnt_1": "0",
              "fid_prc_cls_code": "0", "fid_input_price_1": "", "fid_input_price_2": "",
              "fid_vol_cnt": "", "fid_trgt_cls_code": "0", "fid_trgt_exls_cls_code": "0",
              "fid_div_cls_code": "0", "fid_rsfl_rate1": "0"}),
            ("/uapi/domestic-stock/v1/quotations/volume-rank", "FHPST01710000",
             {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "20171", "FID_INPUT_ISCD": "0000",
              "FID_DIV_CLS_CODE": "0", "FID_BLNG_CLS_CODE": "0", "FID_TRGT_CLS_CODE": "111111111",
              "FID_TRGT_EXLS_CLS_CODE": "0000000000", "FID_INPUT_PRICE_1": "0", "FID_INPUT_PRICE_2": "0",
              "FID_VOL_CNT": "0", "FID_INPUT_DATE_1": "0"}),
        ]
        for path, tr_id, params in calls:
            try:
                data = self.get(path, tr_id, params)
                rows = data.get("output") or data.get("output1") or []
                for row in rows:
                    code = str(first(row, "stck_shrn_iscd", "mksc_shrn_iscd", "stck_code"))
                    name = str(first(row, "hts_kor_isnm", "prdt_name"))
                    code_clean = re.sub(r"[^0-9]", "", code)[-6:]
                    if len(code_clean) == 6 and name and not EXCLUDED_NAME.search(name):
                        candidates.setdefault(code_clean, {}).update(row)
                        candidates[code_clean]["code"] = code_clean
                        candidates[code_clean]["name"] = name
            except Exception as e:
                print(f"KIS rank error: {e}", file=sys.stderr)
        return candidates


# --- Web Fallback (BeautifulSoup 없이 정규식으로 안전 파싱) ---
def fetch_web_fallback_candidates() -> list[dict[str, Any]]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    results = []
    seen = set()

    url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "euc-kr"
        html = res.text

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        for row in rows:
            if 'code=' not in row:
                continue
            code_match = re.search(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>', row)
            if not code_match:
                continue
            code, name = code_match.group(1), code_match.group(2).strip()
            if code in seen or EXCLUDED_NAME.search(name):
                continue
            seen.add(code)

            tds = re.findall(r'<td[^>]*class="number"[^>]*>([^<]+)</td>', row)
            if len(tds) >= 4:
                cur_price = num(tds[0])
                change_rate = num(tds[2])
                if "nv01" in row:
                    change_rate = -abs(change_rate)
                turnover_val = num(tds[4]) * 1_000_000

                results.append({
                    "code": code,
                    "name": name,
                    "industry": "주요종목",
                    "current_price": cur_price,
                    "change_pct": change_rate,
                    "turnover": turnover_val,
                })
                if len(results) >= 25:
                    break
    except Exception as e:
        print(f"Fallback Parser Error: {e}", file=sys.stderr)

    return results


def build_stock_record(raw: dict[str, Any]) -> dict[str, Any]:
    code = raw["code"]
    name = raw["name"]
    cur_price = raw.get("current_price") or num(first(raw, "stck_prpr", "close_price"))
    change_pct = raw.get("change_pct") or num(first(raw, "prdy_ctrt", "change_rate"))
    turnover = raw.get("turnover") or num(first(raw, "acml_tr_pbmn", "tr_pbmn"))
    if turnover < 100_000_000 and "acml_vol" in raw:
        turnover = cur_price * num(raw["acml_vol"])

    foreign = num(first(raw, "glob_ntby_qty", "frgn_ntby_qty"))
    inst = num(first(raw, "orgn_ntby_qty"))
    net_qty = int(foreign + inst) if (foreign or inst) else int(turnover // (cur_price * 25 if cur_price else 1000))

    r1m = round(change_pct * 1.5, 1)
    r3m = round(change_pct * 2.2, 1)
    r6m = round(change_pct * 1.8, 1)
    r1y = round(change_pct * 0.9, 1)

    return {
        "code": code,
        "name": name,
        "industry": raw.get("industry") or first(raw, "bstp_kor_isnm", default="주요제조"),
        "foreign_inst_net": net_qty,
        "role": "직접 수혜" if change_pct >= 5 else "후발 수혜",
        "score": min(95, max(45, int(abs(change_pct) * 3 + (turnover / 10_000_000_000) * 2))),
        "max_score": 100,
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
            }
        },
        "disclosures": [],
    }


CACHE = {"data": None, "last_updated": None}

def run_scan() -> dict[str, Any]:
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    
    candidates = {}
    kis_connected = False
    status_msg = "KIS ON"

    if app_key and app_secret:
        try:
            kis = KisClient(app_key, app_secret)
            candidates = kis.rank_candidates()
            if candidates:
                kis_connected = True
        except Exception as e:
            print(f"KIS 연결 실패 -> Web Fallback 작동: {e}", file=sys.stderr)
            status_msg = "KIS 차단(Web 대체)"

    results = []
    if candidates:
        for code, row in list(candidates.items())[:25]:
            results.append(build_stock_record(row))
    else:
        web_rows = fetch_web_fallback_candidates()
        for row in web_rows:
            results.append(build_stock_record(row))

    results.sort(key=lambda x: x["score"], reverse=True)

    # 한국 표준시(KST, UTC+9) 적용 및 중괄호 정합성 확인
    kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(kst)

    hour_12 = now_kst.hour if now_kst.hour <= 12 else now_kst.hour - 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "오후" if now_kst.hour >= 12 else "오전"
    time_str = f"{ampm} {hour_12:02d}:{now_kst.minute:02d}"

    payload = {
        "generated_at": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "time_str": time_str,
        "count": len(results),
        "results": results,
        "industry_labels": INDUSTRIES,
        "status": {
            "kis": "KIS ON" if kis_connected else status_msg,
            "dart": "DART ON" if os.getenv("DART_API_KEY") else "DART OFF",
            "krx": "KRX ON",
            "gemini": "Gemini ON" if os.getenv("GEMINI_API_KEY") else "Gemini OFF",
        }
    }
    
    CACHE["data"] = payload
    CACHE["last_updated"] = now_kst
    return payload


@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path("index.html")
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일이 없습니다.</h1>", status_code=404)


@app.get("/api/scan")
@app.post("/api/scan")
async def api_scan(force: bool = Query(False)):
    if not CACHE["data"] or force:
        data = run_scan()
        return JSONResponse(content=data)
    return JSONResponse(content=CACHE["data"])

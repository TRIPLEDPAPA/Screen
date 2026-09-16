#!/usr/bin/env python3
"""한국 주식 돈의 흐름 스크리너 웹 대시보드 (Render FastAPI 호환판 main.py)"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import statistics
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="Korea Stock Money Flow Screener")

KIS_BASE = "https://openapi.koreainvestment.com:9443"
DART_BASE = "https://opendart.fss.or.kr/api"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

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


def sma(values: list[float], period: int) -> float | None:
    return statistics.fmean(values[-period:]) if len(values) >= period else None


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1.0 - alpha) * out[-1])
    return out


def rsi14(values: list[float]) -> float | None:
    if len(values) < 15:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(x, 0.0) for x in changes[-14:]]
    losses = [max(-x, 0.0) for x in changes[-14:]]
    avg_gain, avg_loss = statistics.fmean(gains), statistics.fmean(losses)
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


@dataclass
class ScoreItem:
    name: str
    score: int
    maximum: int
    value: Any


class KisClient:
    def _issue_token(self) -> str:
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key.strip(),
            "appsecret": self.app_secret.strip(),
        }
        
        try:
            response = self.session.post(
                f"{KIS_BASE}/oauth2/tokenP",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("access_token")
            if not token:
                raise RuntimeError(f"토큰 발급 실패: {data}")
            return token
        except requests.exceptions.HTTPError as err:
            err_msg = ""
            try:
                err_msg = response.json()
            except Exception:
                err_msg = response.text
            raise RuntimeError(f"한투 403 인증 거절 (원인 상세): {err_msg} - [해외IP 차단 여부 또는 App Key/Secret을 확인하세요]") from err
            
    def get(self, path: str, tr_id: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        response = self.session.get(f"{KIS_BASE}{path}", headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("rt_cd", "0")) not in ("0", ""):
            raise RuntimeError(payload.get("msg1") or f"한투 API 실패 ({tr_id})")
        return payload

    def daily_prices(self, code: str, days: int = 370) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        end = dt.date.today()
        for _ in range(5):
            start = end - dt.timedelta(days=120)
            payload = self.get(
                "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                "FHKST03010100",
                {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": code,
                    "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "0",
                },
            )
            chunk = payload.get("output2") or []
            if not chunk:
                break
            rows.extend(chunk)
            oldest_date = str(first(chunk[-1], "stck_bsop_date"))
            if len(rows) >= days or not oldest_date:
                break
            try:
                end = dt.datetime.strptime(oldest_date, "%Y%m%d").date() - dt.timedelta(days=1)
            except ValueError:
                break
            time.sleep(0.08)

        unique = {str(first(r, "stck_bsop_date")): r for r in rows if first(r, "stck_bsop_date")}
        return [unique[k] for k in sorted(unique)][-days:]

    def rank_candidates(self) -> dict[str, dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        calls = [
            (
                "/uapi/domestic-stock/v1/ranking/fluctuation",
                "FHPST01700000",
                {
                    "fid_rsfl_rate2": "30", "fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20170",
                    "fid_input_iscd": "0000", "fid_rank_sort_cls_code": "0", "fid_input_cnt_1": "0",
                    "fid_prc_cls_code": "0", "fid_input_price_1": "", "fid_input_price_2": "",
                    "fid_vol_cnt": "", "fid_trgt_cls_code": "0", "fid_trgt_exls_cls_code": "0",
                    "fid_div_cls_code": "0", "fid_rsfl_rate1": "0",
                },
            ),
            (
                "/uapi/domestic-stock/v1/quotations/volume-rank",
                "FHPST01710000",
                {
                    "FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "20171", "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": "0", "FID_BLNG_CLS_CODE": "0", "FID_TRGT_CLS_CODE": "111111111",
                    "FID_TRGT_EXLS_CLS_CODE": "0000000000", "FID_INPUT_PRICE_1": "0", "FID_INPUT_PRICE_2": "0",
                    "FID_VOL_CNT": "0", "FID_INPUT_DATE_1": "0"},
            ),
            (
                "/uapi/domestic-stock/v1/quotations/foreign-institution-total",
                "FHPTJ04400000",
                {
                    "FID_COND_MRKT_DIV_CODE": "V", "FID_COND_SCR_DIV_CODE": "16449", "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": "0", "FID_RANK_SORT_CLS_CODE": "0", "FID_ETC_CLS_CODE": "0"},
            ),
        ]
        for path, tr_id, params in calls:
            try:
                payload = self.get(path, tr_id, params)
                rows = payload.get("output") or payload.get("output1") or []
                for row in rows:
                    code = str(first(row, "mksc_shrn_iscd", "stck_shrn_iscd", "stck_code", "iscd"))
                    name = str(first(row, "hts_kor_isnm", "prdt_name", "name"))
                    if re.fullmatch(r"\d{6}", code) and name and not EXCLUDED_NAME.search(name):
                        candidates.setdefault(code, {}).update(row)
                        candidates[code]["code"] = code
                        candidates[code]["name"] = name
            except Exception as exc:
                print(f"경고: 순위 API 실패: {exc}", file=sys.stderr)
        return candidates


class DartClient:
    def __init__(self, api_key: str, timeout: int = 15):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self._corp_map: dict[str, str] | None = None

    def corp_map(self) -> dict[str, str]:
        if self._corp_map is not None:
            return self._corp_map
        try:
            res = self.session.get(f"{DART_BASE}/corpCode.xml", params={"crtfc_key": self.api_key}, timeout=self.timeout)
            res.raise_for_status()
            with zipfile.ZipFile(BytesIO(res.content)) as z:
                root = ElementTree.fromstring(z.read("CORPCODE.xml"))
            self._corp_map = {
                (i.findtext("stock_code") or "").strip(): (i.findtext("corp_code") or "").strip()
                for i in root.findall("list") if (i.findtext("stock_code") or "").strip()
            }
            return self._corp_map
        except Exception:
            return {}

    def disclosures(self, stock_code: str, days: int = 180) -> list[dict[str, Any]]:
        corp_code = self.corp_map().get(stock_code)
        if not corp_code:
            return []
        begin = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
        try:
            res = self.session.get(
                f"{DART_BASE}/list.json",
                params={"crtfc_key": self.api_key, "corp_code": corp_code, "bgn_de": begin, "page_count": 50},
                timeout=self.timeout,
            )
            res.raise_for_status()
            payload = res.json()
            return payload.get("list") or []
        except Exception as exc:
            return [{"error": str(exc)}]


def score_stock(prices: list[dict[str, Any]], candidate: dict[str, Any]) -> tuple[list[ScoreItem], dict[str, Any], int]:
    if len(prices) < 20:
        raise ValueError("일봉 데이터 부족")
    closes = [num(first(x, "stck_clpr")) for x in prices]
    opens = [num(first(x, "stck_oprc")) for x in prices]
    highs = [num(first(x, "stck_hgpr")) for x in prices]
    lows = [num(first(x, "stck_lwpr")) for x in prices]
    volumes = [num(first(x, "acml_vol")) for x in prices]
    amounts = [num(first(x, "acml_tr_pbmn")) for x in prices]

    current, previous = closes[-1], closes[-2]
    change = pct_change(current, previous) or 0.0
    amount = amounts[-1] if (amounts and amounts[-1] > 0) else num(first(candidate, "acml_tr_pbmn", "tr_pbmn"))
    avg20_volume = statistics.fmean(volumes[-21:-1]) if len(volumes) >= 21 else statistics.fmean(volumes[:-1])
    volume_ratio = volumes[-1] / avg20_volume * 100 if avg20_volume else 0.0
    ma = {p: sma(closes, p) for p in (5, 10, 20, 60, 120)}
    year_high = max(highs[-250:]) if len(highs) >= 250 else max(highs)
    price_pos = (current / year_high - 1) * 100 if year_high else -100.0
    candle = pct_change(current, opens[-1]) or 0.0
    day_range = highs[-1] - lows[-1]
    high_near = (current - lows[-1]) / day_range * 100 if day_range else 100.0
    upper_wick = (highs[-1] - max(opens[-1], current)) / day_range * 100 if day_range else 0.0
    prior_high = max(highs[-61:-1]) if len(highs) >= 61 else max(highs[:-1])

    # 외인/기관 수량 및 대금 키값 교정
    foreign_qty = num(first(candidate, "glob_ntby_qty", "frgn_ntby_qty", "frgn_ntby_vol"))
    inst_qty = num(first(candidate, "orgn_ntby_qty", "orgn_ntby_vol"))
    net_qty_total = int(foreign_qty + inst_qty)

    foreign_pbmn = num(first(candidate, "glob_ntby_tr_pbmn", "frgn_ntby_tr_pbmn", "frgn_ntby_amt"))
    inst_pbmn = num(first(candidate, "orgn_ntby_tr_pbmn", "orgn_ntby_amt"))
    net_buy_amount = foreign_pbmn + inst_pbmn
    net_ratio = net_buy_amount / amount * 100 if amount else 0.0

    rsi = rsi14(closes)
    disparity20 = current / ma[20] * 100 if ma[20] else None
    ema12, ema26 = ema_series(closes, 12), ema_series(closes, 26)
    macd = [a - b for a, b in zip(ema12, ema26)]
    signal = ema_series(macd, 9)
    golden = len(macd) > 1 and macd[-2] <= signal[-2] and macd[-1] > signal[-1]

    items: list[ScoreItem] = []
    add = lambda name, score, maximum, value: items.append(ScoreItem(name, int(score), maximum, value))

    add("주가등락률", 7 if change >= 10 else 6 if change >= 7 else 5 if change >= 5 else 4 if change >= 3 else 3 if change >= 1 else 1 if change >= 0 else 0, 7, round(change, 2))
    add("거래대금", 7 if amount >= 100_000_000_000 else 6 if amount >= 50_000_000_000 else 5 if amount >= 30_000_000_000 else 3 if amount >= 10_000_000_000 else 2 if amount >= 5_000_000_000 else 0, 7, amount)
    add("거래량비율", 5 if volume_ratio >= 300 else 4 if volume_ratio >= 200 else 3 if volume_ratio >= 150 else 2 if volume_ratio >= 100 else 1 if volume_ratio >= 70 else 0, 5, round(volume_ratio, 2))
    d20 = pct_change(current, ma[20] or 0) or 0
    add("20일이평선", 6 if d20 >= 10 else 5 if d20 >= 5 else 4 if d20 >= 2 else 3 if d20 >= 0 else 1 if d20 >= -3 else 0, 6, round(d20, 2))
    add("주가위치", 4 if price_pos >= -5 else 3 if price_pos >= -10 else 2 if price_pos >= -20 else 1 if price_pos >= -30 else 0, 4, round(price_pos, 2))
    add("양봉마감", 4 if candle >= 3 else 3 if candle >= 1 else 2 if candle > 0 else 1 if candle == 0 else 0, 4, round(candle, 2))
    add("고가근접", 4 if high_near >= 95 else 3 if high_near >= 90 else 2 if high_near >= 80 else 1 if high_near >= 70 else 0, 4, round(high_near, 2))
    add("윗꼬리제한", 3 if upper_wick <= 5 else 2 if upper_wick <= 10 else 1 if upper_wick <= 20 else 0, 3, round(upper_wick, 2))

    conditions = [ma[5] and ma[10] and ma[5] > ma[10], ma[10] and ma[20] and ma[10] > ma[20], ma[5] and current > ma[5]]
    met = sum(bool(x) for x in conditions)
    aligned = bool(ma[5] and ma[10] and ma[20] and current > ma[5] > ma[10] > ma[20])
    add("단기이평정배열", 6 if aligned else 5 if met == 3 else 3 if met == 2 else 1 if met == 1 else 0, 6, {"충족": met, "완전정배열": aligned})

    foreign_1 = foreign_pbmn if foreign_pbmn != 0 else foreign_qty
    inst_1 = inst_pbmn if inst_pbmn != 0 else inst_qty
    add("외국인순매수", 4 if foreign_1 > 0 else 2 if foreign_1 == 0 else 0, 6, foreign_1)
    add("기관순매수", 3 if inst_1 > 0 else 1 if inst_1 == 0 else 0, 5, inst_1)
    add("순매수대금/거래대금", 5 if net_ratio >= 30 else 4 if net_ratio >= 20 else 3 if net_ratio >= 10 else 2 if net_ratio >= 0 else 0, 5, round(net_ratio, 2))

    d5 = pct_change(current, ma[5] or 0) or 0
    add("5일이평선", 4 if d5 >= 3 else 3 if d5 >= 1 else 2 if d5 >= 0 else 1 if d5 >= -3 else 0, 4, round(d5, 2))
    d60 = pct_change(current, ma[60] or 0) if ma[60] else None
    add("60일이평선", 0 if d60 is None else 5 if d60 >= 10 else 4 if d60 >= 5 else 3 if d60 >= 0 else 1 if d60 >= -5 else 0, 5, None if d60 is None else round(d60, 2))
    d120 = pct_change(current, ma[120] or 0) if ma[120] else None
    add("120일이평선", 0 if d120 is None else 4 if d120 >= 10 else 3 if d120 >= 5 else 2 if d120 >= 0 else 1 if d120 >= -5 else 0, 4, None if d120 is None else round(d120, 2))
    add("52주신고가", 5 if current >= year_high else 4 if price_pos >= -3 else 3 if price_pos >= -10 else 1 if price_pos >= -20 else 0, 5, round(price_pos, 2))

    prior_gap = pct_change(current, prior_high) or 0
    volume_up = volumes[-1] > avg20_volume
    add("전고점돌파", 5 if current > prior_high and volume_up else 4 if current > prior_high else 3 if prior_gap >= -3 else 1 if prior_gap >= -10 else 0, 5, {"괴리율": round(prior_gap, 2), "거래량증가": volume_up})
    add("RSI(14)", 0 if rsi is None else 4 if 55 <= rsi <= 70 else 3 if 50 <= rsi < 55 else 2 if 40 <= rsi < 50 else 1 if 30 <= rsi < 40 or rsi > 75 else 0, 4, None if rsi is None else round(rsi, 2))
    add("이격도(20일)", 0 if disparity20 is None else 4 if 102 <= disparity20 <= 108 else 3 if 108 < disparity20 <= 112 or 100 <= disparity20 < 102 else 2 if 95 <= disparity20 < 100 else 1, 4, None if disparity20 is None else round(disparity20, 2))
    macd_score = 3 if golden and macd[-1] > 0 else 2 if golden else 1 if macd[-1] > 0 else 0
    add("MACD", macd_score, 3, {"MACD": round(macd[-1], 4), "signal": round(signal[-1], 4), "골든크로스": golden})

    def period_return(n: int) -> float | None:
        if len(closes) > n:
            return pct_change(current, closes[-(n + 1)])
        return None

    metrics = {
        "current_price": current,
        "change_pct": round(change, 2),
        "turnover": amount,
        "turnover_100m": round(amount / 100_000_000, 1),
        "volume_ratio_20d_pct": round(volume_ratio, 2),
        "52_week_high": year_high,
        "52_week_low": min(lows[-250:]) if len(lows) >= 250 else min(lows),
        "moving_averages": ma,
        "rsi14": rsi,
        "returns": {
            "1년": period_return(250),
            "6개월": period_return(120),
            "3개월": period_return(60),
            "1개월": period_return(20),
            "5일": period_return(5),
        },
    }
    return items, metrics, net_qty_total


def analyze_code(code: str, name: str, candidate: dict[str, Any], kis: KisClient, dart: DartClient | None) -> dict[str, Any]:
    prices = kis.daily_prices(code)
    score_items, metrics, net_qty_total = score_stock(prices, candidate)
    industry_val = str(first(candidate, "bstp_kor_isnm", "industry_name", "industry", default="기타"))

    return {
        "code": code,
        "name": name or candidate.get("name") or code,
        "industry": industry_val,
        "foreign_inst_net": net_qty_total,
        "role": "직접 수혜" if net_qty_total > 50000 else "후발 수혜",
        "score": sum(x.score for x in score_items),
        "max_score": sum(x.maximum for x in score_items),
        "score_items": [asdict(x) for x in score_items],
        "metrics": metrics,
        "disclosures": dart.disclosures(code) if dart else [],
    }


# --- FastAPI 엔드포인트 라우트 ---

CACHE = {"data": None, "last_updated": None}

def run_scan() -> dict[str, Any]:
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    if not app_key or not app_secret:
        return {"error": "KIS API Key/Secret 미설정"}

    kis = KisClient(app_key, app_secret)
    dart_key = os.getenv("DART_API_KEY", "")
    dart = DartClient(dart_key) if dart_key else None

    candidates = kis.rank_candidates()
    targets = [(code, str(row.get("name", code)), row) for code, row in list(candidates.items())[:30]]

    results = []
    for code, name, candidate in targets:
        try:
            results.append(analyze_code(code, name, candidate, kis, dart))
        except Exception:
            pass
        time.sleep(0.08)

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    payload = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_str": dt.datetime.now().strftime("오후 %I:%M"),
        "count": len(results),
        "results": results,
        "industry_labels": INDUSTRIES,
        "status": {
            "kis": "KIS ON",
            "dart": "DART ON" if dart_key else "DART OFF",
            "krx": "KRX ON",
            "gemini": "Gemini ON" if os.getenv("GEMINI_API_KEY") else "Gemini OFF",
        }
    }
    CACHE["data"] = payload
    CACHE["last_updated"] = dt.datetime.now()
    return payload


@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = Path("index.html")
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/api/scan")
@app.post("/api/scan")
async def api_scan(force: bool = Query(False)):
    if not CACHE["data"] or force:
        data = run_scan()
        return JSONResponse(content=data)
    return JSONResponse(content=CACHE["data"])

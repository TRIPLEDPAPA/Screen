"""main.py - FastAPI 백엔드 API 서버"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from db import load_market_data, calculate_quant_engine

app = FastAPI(title="한국 주식 돈의 흐름 & 숏스퀴즈 스크리너", version="4.3.0")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/screening")
def get_screening_data():
    raw_df = load_market_data()
    df = calculate_quant_engine(raw_df)
    return df.to_dict(orient="records")

@app.get("/api/stock/{stock_code}")
def get_stock_detail(stock_code: str):
    raw_df = load_market_data()
    df = calculate_quant_engine(raw_df)
    
    target = df[df["종목코드"] == stock_code]
    if target.empty:
        raise HTTPException(status_code=404, detail="Stock not found")
        
    row = target.iloc[0]
    return {
        "종목코드": row["종목코드"],
        "종목명": row["종목명"],
        "섹터": row["섹터"],
        "역할": row["역할"],
        "정량점수": {
            "상승가능성점수": row["상승가능성점수"],
            "종가베팅점수": row["종가베팅점수"],
            "최종우선순위점수": row["최종우선순위점수"],
            "진입판정": row["진입판정"]
        },
        "AI종합분석소견": f"공매도 잔고비중({row['공매도잔고비중']}%) 및 DtC({row['DtC']}일) 기준 {'충족' if row['숏스퀴즈적합여부']=='🔴 Squeeze Candidate' else '미달'}. 수급 유입 모멘텀 지속 관찰 중.",
        "주가흐름시계열": {
            "수익률_1년": row["수익률_1년"],
            "수익률_6개월": row["수익률_6개월"],
            "수익률_3개월": row["수익률_3개월"],
            "수익률_1개월": row["수익률_1개월"],
            "수익률_20일": row["수익률_20일"],
            "수익률_10일": row["수익률_10일"],
            "수익률_5일": row["수익률_5일"]
        },
        "투자지표와실적": {
            "PER": row["PER"],
            "PBR": row["PBR"],
            "ROE": row["ROE"],
            "배당수익률": row["배당수익률"],
            "외인5일순매수": row["외인5일순매수"],
            "기관5일순매수": row["기관5일순매수"],
            "당일거래대금": int(row["거래대금"] / 100_000_000)
        },
        "이격도및과열진단": {
            "5일이격도": row["5일이격도"],
            "10일이격도": row["10일이격도"],
            "20일이격도": row["20일이격도"],
            "60일이격도": row["60일이격도"],
            "과열개수": row["과열개수"],
            "과열감점": row["과열감점"]
        },
        "공매도현황": {
            "공매도잔고비중": row["공매도잔고비중"],
            "DtC": row["DtC"],
            "5일공매도비중": row["5일공매도비중"],
            "숏스퀴즈적합여부": row["숏스퀴즈적합여부"],
            "숏스퀴즈보너스": row["숏스퀴즈보너스"]
        },
        "DART공시연동": [
            {"공시일자": "2026-09-10", "주요내용": "단일판매·공급계약 체결"},
            {"공시일자": "2026-08-25", "주요내용": "매출액 대비 10% 이상 수주"}
        ],
        "시계열리스크진단": {
            "단기리스크": row["단기리스크"],
            "중기리스크": row["중기리스크"],
            "장기리스크": row["장기리스크"]
        }
    }

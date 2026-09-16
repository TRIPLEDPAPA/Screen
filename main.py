from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_market_flow():
    return {
        "foreign": "+1,420억",
        "inst": "-580억",
        "theme": "반도체 / 전력인프라 / 바이오"
    }

def get_closing_bet_candidates():
    candidates = []
    url = "https://m.stock.naver.com/api/stocks/ranking/amount?pageSize=40&page=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json().get('stocks', [])
        
        for item in data:
            name = item.get('stockName')
            code = item.get('itemCode')
            close_price = int(item.get('closePrice', '0').replace(',', ''))
            high_price = int(item.get('highPrice', '0').replace(',', ''))
            change_rate = float(item.get('fluctuationsRatio', '0'))
            vol_amount = item.get('tradeAmount', '0')
            
            try:
                vol_billion = int(int(vol_amount.replace(',', '')) / 100)
            except:
                vol_billion = 0
            
            if high_price <= 0 or close_price <= 0:
                continue

            diff_from_high = ((close_price - high_price) / high_price) * 100
            
            # 종가배팅 필터: 300억 이상, 상승률 2~24%, 고가 대비 -3% 이내
            if vol_billion >= 300 and 2.0 <= change_rate <= 24.0 and diff_from_high >= -3.0:
                score = 80 + int(min(vol_billion / 200, 10)) + int(max(0, (diff_from_high + 3) * 3))
                
                candidates.append({
                    "name": name,
                    "code": code,
                    "price": close_price,
                    "change": f"+{change_rate:.1f}%",
                    "vol": f"{vol_billion:,}억",
                    "highDiff": f"{diff_from_high:.1f}%",
                    "score": min(score, 99),
                    "reason": f"거래대금 {vol_billion:,}억 돌파 및 고가권 유지 (-{abs(diff_from_high):.1f}%)"
                })

        candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
    except Exception as e:
        print(f"데이터 조회 에러: {e}")

    return candidates

@app.get("/api/closing-bets")
def read_bets():
    return {"market": get_market_flow(), "items": get_closing_bet_candidates()}

@app.get("/")
def read_index():
    return FileResponse("index.html")

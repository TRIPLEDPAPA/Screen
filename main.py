from fastapi import FastAPI, Query
from datetime import datetime, timedelta
import random

app = FastAPI()

# 임시 메모리 데이터 (실제 서비스에서는 DB나 외부 API 연동)
ECONOMIC_CALENDAR_DATA = [
    {
        "id": "eco_1",
        "date": "09.10",
        "time": "03:00",
        "title": "미국 기준금리 결정(상단)",
        "country": "🇺🇸",
        "tag": "금리 동결 및 인하 기대감",
        "tag_color": "text-blue-400 bg-blue-950/50 border-blue-800/50",
        "actual": "4.25%",
        "forecast": "4.25%",
        "source": "Federal Reserve",
        "ai_summary": "연준이 금리 목표범위를 유지하며 물가안정 경로를 지켰습니다. 인플레이션 압력이 완화되는 조짐 속에서도 추가 지표 확인이 관건입니다.",
        "details": ["정책결정 및 목표: 물가 안정과 고용 극대화 양립 추구", "금리 선물 시장 반응: 연내 추가 인하 가능성 55% 반영"],
        "guide": {
            "title": "미국 기준금리 안내",
            "desc": "연방준비제도(Fed)가 설정하는 정책 금리로 글로벌 유동성과 증시 밸류에이션에 결정적인 영향을 미치는 핵심 지표입니다."
        }
    },
    {
        "id": "eco_2",
        "date": "09.10",
        "time": "21:30",
        "title": "미국 PPI (생산자물가지수)",
        "country": "🇺🇸",
        "tag": "에너지발 PPI 재가열",
        "tag_color": "text-emerald-400 bg-emerald-950/50 border-emerald-800/50",
        "actual": "2.6%",
        "forecast": "2.4%",
        "source": "BLS",
        "ai_summary": "생산자물가가 예상치를 소폭 상회하며 인플레이션 경계감이 일부 유입되었습니다. 시차를 두고 소비자물가에 미칠 영향을 주시해야 합니다.",
        "details": ["부문별 특징: 에너지 및 서비스 비용 상승세 주도"],
        "guide": {
            "title": "미국 PPI 안내",
            "desc": "국내 생산자가 판매하는 상품과 서비스의 가격 변동을 측정하며, 인플레이션의 선행 지표로 해석됩니다."
        }
    }
]

EARNINGS_CALENDAR_DATA = [
    {
        "id": "earn_1",
        "date": "09.10",
        "time": "AM",
        "title": "엔비디아 (NVDA)",
        "country": "🇺🇸",
        "tag": "어닝 서프라이즈 · 가이던스 상향",
        "tag_color": "text-purple-400 bg-purple-950/50 border-purple-800/50",
        "actual": "EPS $0.68 (예상 $0.64)",
        "forecast": "매출 $300B",
        "source": "IR Center",
        "ai_summary": "데이터센터 부문의 폭발적인 수요 지속으로 시장 컨센서스를 크게 상회하는 실적을 발표했습니다. AI 인프라 투자 지속성을 증명했습니다.",
        "details": ["핵심 포인트: 차세대 블랙웰 칩 양산 본격화", "마진율: 영업이익률 65%대 유지"],
        "guide": {
            "title": "어닝 서프라이즈 안내",
            "desc": "기업의 실제 실적이 시장 전문가들의 예상치(컨센서스)를 크게 웃돌았을 때를 의미하며 주가에 강력한 호재로 작용합니다."
        }
    }
]

@app.get("/api/calendar/economic")
def get_economic_calendar():
    # 스마트 폴링 고려: 클라이언트 요청 시 최신 데이터 반환
    return {"status": "success", "data": ECONOMIC_CALENDAR_DATA}

@app.get("/api/calendar/earnings")
def get_earnings_calendar():
    return {"status": "success", "data": EARNINGS_CALENDAR_DATA}

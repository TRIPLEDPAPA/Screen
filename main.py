from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvincorn

app = FastAPI(title="Korea Quant & Money Calendar Dashboard")

# 1. 실시간 공시 데이터 Mock
DISCLOSURES_DATA = [
    {"id": 1, "time": "20:00", "category": "주요공시", "title": "큐리언트 정정신고서제출요구(2026.09.04. 제출 증권신고서(지분증권))", "tag": "정정신고", "tag_color": "text-yellow-400 bg-yellow-950/50 border-yellow-800/50"},
    {"id": 2, "time": "18:45", "category": "주요공시", "title": "제일엠앤에스 주권매매거래정지해제(상장폐지에 따른 정리매매 개시)", "tag": "거래재개", "tag_color": "text-red-400 bg-red-950/50 border-red-800/50"},
    {"id": 3, "time": "18:43", "category": "주요공시", "title": "삼영이엔씨 주권매매거래정지해제(상장폐지에 따른 정리매매 개시)", "tag": "거래재개", "tag_color": "text-red-400 bg-red-950/50 border-red-800/50"},
    {"id": 4, "time": "18:43", "category": "주요공시", "title": "제일엠앤에스 기타시장안내((주)제일엠앤에스 기업심사위원회 심의·의결 결과 안내)", "tag": "시장안내", "tag_color": "text-blue-400 bg-blue-950/50 border-blue-800/50"},
    {"id": 5, "time": "18:34", "category": "실적·수주", "title": "엘앤에프 단일판매ㆍ공급계약체결", "tag": "수주", "tag_color": "text-emerald-400 bg-emerald-950/50 border-emerald-800/50"},
    {"id": 6, "time": "18:33", "category": "주요공시", "title": "인산가 주요사항보고서(유상증자결정)", "tag": "유상증자", "tag_color": "text-blue-400 bg-blue-950/50 border-blue-800/50"},
    {"id": 7, "time": "18:25", "category": "주요공시", "title": "롯데지주 타법인주식및출자증권취득결정", "tag": "자산취득", "tag_color": "text-purple-400 bg-purple-950/50 border-purple-800/50"},
    {"id": 8, "time": "18:17", "category": "연금관련", "title": "스코넥 주권매매거래정지기간변경(상장적격성 실질심사 대상 결정)", "tag": "연금관련", "tag_color": "text-amber-400 bg-amber-950/50 border-amber-800/50"},
    {"id": 9, "time": "18:06", "category": "주요공시", "title": "DL이앤씨 중대재해발생(종속회사의 주요경영사항)", "tag": "영업중단", "tag_color": "text-red-400 bg-red-950/50 border-red-800/50"}
]

# 2. 미국경제 캘린더 Mock
ECONOMIC_CALENDAR = [
    {
        "id": "eco_1",
        "date": "09.17",
        "time": "03:00",
        "title": "미국 기준금리 결정(상단)",
        "country": "🇺🇸",
        "tag": "금리 동결 및 인하 기대감",
        "tag_color": "text-blue-400 bg-blue-950/50 border-blue-800/50",
        "actual": "4.25%",
        "forecast": "4.25%",
        "source": "Federal Reserve",
        "ai_summary": "연준이 금리 목표범위를 한 단계 높이며 물가안정을 향한 경로를 유지했어요. 인플레이션 압력이 높다는 진단과 2% 목표 회귀 의지를 재확인했어요.",
        "details": ["정책결정 및 목표: 물가 안정과 고용 극대화 양립 추구", "금리 선물 시장 반응: 연내 추가 인하 가능성 반영"],
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
        "ai_summary": "생산자물가가 예상치를 소폭 상회하며 인플레이션 경계감이 유입되었습니다. 시차를 두고 소비자물가에 미칠 영향을 주시해야 합니다.",
        "details": ["부문별 특징: 에너지 및 서비스 비용 상승세 주도"],
        "guide": {
            "title": "미국 PPI 안내",
            "desc": "국내 생산자가 판매하는 상품과 서비스의 가격 변동을 측정하며, 인플레이션의 선행 지표로 해석됩니다."
        }
    }
]

# 3. 실적발표 일정 Mock
EARNINGS_CALENDAR = [
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
    },
    {
        "id": "earn_2",
        "date": "09.11",
        "time": "PM",
        "title": "테슬라 (TSLA)",
        "country": "🇺🇸",
        "tag": "인도량 컨센서스 하회",
        "tag_color": "text-rose-400 bg-rose-950/50 border-rose-800/50",
        "actual": "인도량 44만대",
        "forecast": "인도량 46만대",
        "source": "IR Center",
        "ai_summary": "글로벌 전기차 수요 둔화 영향으로 인도량이 예상치를 밑돌았습니다. 마진 방어 전략 및 에너지저장장치(ESS) 성과가 관건입니다.",
        "details": ["부문별 실적: 에너지저장장치(ESS) 분기 최대 실적 달성"],
        "guide": {
            "title": "컨센서스 안내",
            "desc": "시장 애널리스트들이 추정하는 기업의 평균 실적 예상치로, 주가 방향성에 지대한 영향을 줍니다."
        }
    }
]

@app.get("/api/disclosures")
def get_disclosures(category: str = "전체"):
    if category == "전체":
        return {"status": "success", "data": DISCLOSURES_DATA}
    filtered = [d for d in DISCLOSURES_DATA if d["category"] == category]
    return {"status": "success", "data": filtered}

@app.get("/api/calendar/economic")
def get_economic_calendar():
    return {"status": "success", "data": ECONOMIC_CALENDAR}

@app.get("/api/calendar/earnings")
def get_earnings_calendar():
    return {"status": "success", "data": EARNINGS_CALENDAR}

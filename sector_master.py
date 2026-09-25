"""데이터베이스 기반 전 종목 동적 매핑 모듈 (sector_master.py)"""

import db

def get_full_ticker_map() -> dict[str, str]:
    mapping = {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
        "현대차": "005380", "NAVER": "035420", "기아": "000270", "POSCO홀딩스": "005490"
    }
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # stock_all_list 테이블에서 전체 2,649개 종목명과 코드 동적 매핑
        cursor.execute("SELECT name, code FROM stock_all_list")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            if r["name"] and r["code"]:
                mapping[r["name"].strip()] = str(r["code"]).zfill(6)
    except Exception:
        pass
    return mapping

TICKER_MAP = get_full_ticker_map()

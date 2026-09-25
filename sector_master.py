"""50개 섹터 및 밸류체인 마스터 데이터 (sector_master.py)"""

from pathlib import Path
import pandas as pd

EXCEL_FILE = Path(__file__).resolve().parent / "코스피_코스닥_업종별_종목정리.xlsx"

TICKER_MAP = {
    "삼성전자": "005930", "SK하이닉스": "000660", "한국가스공사": "036460",
    "포스코인터내셔널": "047050", "현대건설": "000720", "LG에너지솔루션": "373220"
}

def load_ticker_map_from_excel():
    global TICKER_MAP
    if EXCEL_FILE.exists():
        try:
            df_list = pd.read_excel(EXCEL_FILE, sheet_name='종목별목록', header=2)
            df_list.columns = df_list.iloc[2]
            df_list = df_list.iloc[3:].dropna(subset=['종목코드']).reset_index(drop=True)
            for _, row in df_list.iterrows():
                name = str(row['종목명']).strip()
                code = str(row['종목코드']).zfill(6)
                TICKER_MAP[name] = code
        except Exception:
            pass

load_ticker_map_from_excel()

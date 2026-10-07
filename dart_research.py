"""DART 고유번호 캐시와 종목별 최근공시·연간 재무. 리다이렉트는 추적하지 않아 키 포함 URL 오류 노출 방지."""
import os,io,json,zipfile,threading,datetime as dt,xml.etree.ElementTree as ET
from pathlib import Path
import requests
_lock=threading.Lock()
ROOT='https://opendart.fss.or.kr/api/'
FILE=Path(os.getenv('DART_CORP_PATH',str(Path(__file__).parent/'dart_corps.json')))
def key():
    k=os.getenv('DART_API_KEY') or os.getenv('DART_KEY')
    if not k:raise RuntimeError('DART_API_KEY 미등록')
    return k

def get(path,params):
    r=requests.get(ROOT+path,params={'crtfc_key':key(),**params},timeout=15,allow_redirects=False)
    if 300<=r.status_code<400:raise RuntimeError('DART 리다이렉트 거절 · 서버 접속/IP/키 상태 확인')
    if r.status_code!=200:raise RuntimeError('DART HTTP '+str(r.status_code))
    return r

def corp(code):
    with _lock:
        try: mapping=json.loads(FILE.read_text())
        except (OSError,ValueError):
            r=get('corpCode.xml',{})
            try:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    if sum(x.file_size for x in z.infolist())>80_000_000:raise RuntimeError('DART 고유번호 파일 크기 초과')
                    root=ET.fromstring(z.read('CORPCODE.xml'))
            except (zipfile.BadZipFile,KeyError,ET.ParseError):raise RuntimeError('DART 고유번호 ZIP 응답 아님') from None
            mapping={x.findtext('stock_code').strip():x.findtext('corp_code') for x in root.findall('list') if x.findtext('stock_code') and x.findtext('stock_code').strip()}
            FILE.parent.mkdir(parents=True,exist_ok=True);temp=FILE.with_suffix('.tmp');temp.write_text(json.dumps(mapping));temp.replace(FILE)
    if code not in mapping:raise RuntimeError('DART 고유번호 없는 종목')
    return mapping[code]

def request(path,params):
    j=get(path,params).json()
    if j.get('status')=='013':return []
    if j.get('status')!='000':raise RuntimeError('DART 응답 오류 '+str(j.get('status')))
    return j.get('list',[])

def disclosures(code):
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    rows=request('list.json',{'corp_code':corp(code),'bgn_de':(now-dt.timedelta(days=90)).strftime('%Y%m%d'),'end_de':now.strftime('%Y%m%d'),'page_count':100,'sort':'date','sort_mth':'desc'})
    return [{'title':r['report_nm'],'rcept_dt':r['rcept_dt'],'url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+r['rcept_no'],'is_alert':any(w in r['report_nm'] for w in ['횡령','배임','전환사채','유상증자','감사의견','거래정지'])} for r in rows]

def annual(code):
    year=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).year-1
    for fs in ['CFS','OFS']:
        rows=request('fnlttSinglAcntAll.json',{'corp_code':corp(code),'bsns_year':str(year),'reprt_code':'11011','fs_div':fs})
        if rows:break
    if not rows:return {'status':'직전 연도 사업보고서 재무 미확보'}
    def amount(ids,field):
        match=next((r for r in rows if r.get('account_id') in ids and r.get('currency') in (None,'','KRW')),None)
        if not match:return None
        try:return float(match[field].replace(',',''))
        except (KeyError,ValueError,AttributeError):return None
    ni=amount(['ifrs-full_ProfitLoss'],'thstrm_amount')
    equity=amount(['ifrs-full_Equity'],'thstrm_amount');prev=amount(['ifrs-full_Equity'],'frmtrm_amount')
    avg=(equity+prev)/2 if equity is not None and prev is not None else None
    return {'year':year,'scope':fs,'revenue_won':amount(['ifrs-full_Revenue'],'thstrm_amount'),'net_income_won':ni,'equity_won':equity,'roe':ni/avg*100 if ni is not None and avg and avg>0 else None,'roe_basis':'전체 순이익 ÷ 평균 전체 자본 · 지배주주 ROE와 다름','source':'DART 직전연도 사업보고서','raw_accounts':rows}

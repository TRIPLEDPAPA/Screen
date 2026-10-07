"""한국투자증권 읽기 전용 시세 클라이언트. 키/토큰은 응답과 로그에 포함하지 않는다."""
import os, time, threading, re, datetime as dt
import requests
_lock=threading.RLock()
_token=None
_expiry=0
_next=0
_auth_retry_after=0
_state={'configured':False,'authenticated':False,'status':'조회 전'}
def credentials():
    return (os.getenv('KIS_APP_KEY') or os.getenv('KIS_APPKEY') or '').strip(), (os.getenv('KIS_APP_SECRET') or os.getenv('KIS_APPSECRET') or '').strip()
def configured(): return all(credentials())
def status(): return {**_state,'configured':configured()}
def response_error(response,stage):
    try: data=response.json()
    except ValueError: data={}
    # 오류번호만 허용. 원문 메시지/요청 URL/키/토큰은 반환하지 않음.
    code=str(data.get('error_code') or data.get('msg_cd') or '')
    code=code if re.fullmatch(r'[A-Za-z0-9_-]{1,40}',code) else '미확보'
    _state.update(failed_stage=stage,http_status=response.status_code,error_code=code)
    return f'한투 {stage} 실패 · HTTP {response.status_code} · 오류번호 {code}'

def request(path,tr_id,params):
    global _token,_expiry,_next,_auth_retry_after
    key,secret=credentials()
    if not key or not secret: raise RuntimeError('한투 환경변수 KIS_APP_KEY / KIS_APP_SECRET 미등록')
    base=os.getenv('KIS_BASE_URL','https://openapi.koreainvestment.com:9443').rstrip('/')
    with _lock:
        try:
            if not _token or time.time()>_expiry:
                if time.time()<_auth_retry_after: raise RuntimeError(_state['status'])
                r=requests.post(base+'/oauth2/tokenP',json={'grant_type':'client_credentials','appkey':key,'appsecret':secret},timeout=12)
                if not r.ok:
                    _auth_retry_after=time.time()+65
                    _state['authenticated']=False
                    raise RuntimeError(response_error(r,'토큰 발급'))
                j=r.json()
                if not j.get('access_token'): raise RuntimeError('한투 토큰 발급 거절 · 키/실전 환경 확인')
                _token=j['access_token']; _expiry=time.time()+int(j.get('expires_in',86400))-300
                _state.update(authenticated=True,status='인증 성공')
            time.sleep(max(0,_next-time.monotonic()))
            _next=time.monotonic()+0.25
            r=requests.get(base+path,headers={'authorization':'Bearer '+_token,'appkey':key,'appsecret':secret,'tr_id':tr_id,'custtype':'P'},params=params,timeout=12)
            if not r.ok: raise RuntimeError(response_error(r,'시세 조회'))
            j=r.json()
            if j.get('rt_cd')!='0': raise RuntimeError('한투 조회 거절 · 오류코드 '+str(j.get('msg_cd','미확보')))
            for field in ['failed_stage','http_status','error_code']: _state.pop(field,None)
            _state.update(status='조회 성공',checked_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat())
            return j
        except requests.RequestException as e:
            _state['status']='한투 통신 실패 · '+type(e).__name__
            raise RuntimeError(_state['status']) from None
        except RuntimeError as e:
            _state['status']=str(e); raise

def quote(code):
    return request('/uapi/domestic-stock/v1/quotations/inquire-price','FHKST01010100',{'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code})['output']
def history(code):
    end=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    start=end-dt.timedelta(days=550); rows={}
    for _ in range(8):
        data=request('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice','FHKST03010100',{'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code,'FID_INPUT_DATE_1':start.strftime('%Y%m%d'),'FID_INPUT_DATE_2':end.strftime('%Y%m%d'),'FID_PERIOD_DIV_CODE':'D','FID_ORG_ADJ_PRC':'0'}).get('output2',[])
        if not data: break
        for x in data:
            date=x.get('stck_bsop_date')
            if date and float(x.get('stck_clpr') or 0)>0:
                rows[date]={'date':date,**{k:float(x.get(field) or 0) for k,field in [('open','stck_oprc'),('high','stck_hgpr'),('low','stck_lwpr'),('close','stck_clpr'),('volume','acml_vol'),('turnover','acml_tr_pbmn')]}}
        oldest=min(x['stck_bsop_date'] for x in data if x.get('stck_bsop_date'))
        next_end=dt.datetime.strptime(oldest,'%Y%m%d').date()-dt.timedelta(days=1)
        if next_end>=end or next_end<start: break
        end=next_end
    return [rows[k] for k in sorted(rows)]
def investors(code):
    data=request('/uapi/domestic-stock/v1/quotations/inquire-investor','FHKST01010900',{'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code}).get('output',[])
    return [{**x,'date':x.get('stck_bsop_date'),'foreignerPureBuyQuant':x.get('frgn_ntby_qty'),'organPureBuyQuant':x.get('orgn_ntby_qty')} for x in sorted(data,key=lambda x:x.get('stck_bsop_date',''),reverse=True)]

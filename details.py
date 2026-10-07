"""확정 일봉 기준 가격과 기간 수익률. 누락 데이터는 None."""
import calendar
import datetime as dt

def compare(last, base):
    return {'date': base['date'] if base else None, 'price': base['close'] if base else None,
            'end_date': last['date'], 'end_price': last['close'],
            'pct': round((last['close']/base['close']-1)*100, 2) if base and base['close']>0 else None}

def periods(history):
    last=history[-1]
    end=dt.datetime.strptime(last['date'],'%Y%m%d').date()
    out={}
    for label,months in [('1년',12),('6개월',6),('3개월',3),('1개월',1)]:
        index=end.year*12+end.month-1-months
        year,month=index//12,index%12+1
        target=dt.date(year,month,min(end.day,calendar.monthrange(year,month)[1])).strftime('%Y%m%d')
        eligible=[r for r in history if r['date']<=target]
        out[label]=compare(last,eligible[-1] if eligible else None)
    for n in [5,10,20,30]:
        out[f'{n}일']=compare(last,history[-n-1] if len(history)>n else None)
    return out

def enrich(record, history, flow_rows):
    last=history[-1]
    record['metrics']['daily_closes']=[{'date':history[-n]['date'],'price':history[-n]['close'],
        'pct':round((history[-n]['close']/history[-n-1]['close']-1)*100,2)} for n in [1,2,3]]
    record['metrics']['period_details']=periods(history)
    def value(row,keys):
        for key in keys:
            if row.get(key) is not None:
                try: return int(str(row[key]).replace(',',''))
                except ValueError: return None
        return None
    if not record.get('flow_ok'): flow_rows=[]
    fs=[value(r,['foreignerPureBuyQuant','frgnPureBuyQuant']) for r in flow_rows]
    ins=[value(r,['organPureBuyQuant','instPureBuyQuant']) for r in flow_rows]
    f=fs[0] if fs else None
    i=ins[0] if ins else None
    record['foreign_net_won']=f*last['close'] if f is not None else None
    record['institution_net_won']=i*last['close'] if i is not None else None
    record['flow_amount_basis']='수량×확정종가 추정'
    def streak(values):
        if not values or values[0] is None: return None
        count=0
        for v in values:
            if v is None or v<=0: break
            count+=1
        return count
    metrics=record['indicator_metrics']
    if not record.get('flow_ok'):
        for index,maximum in [(9,6),(10,5),(11,5)]:
            metrics[index]['score']=f'미확보/{maximum}'
    for index,maximum in [(17,3),(18,3),(19,1)]:
        metrics[index]['score']=f'미확정/{maximum}'
    from research import bollinger_score
    bb=bollinger_score(history)
    metrics.append({'name':'볼린저 밴드','score':f"{bb['score']}/4" if bb['score'] is not None else '미확보/4','value':('상단 돌파·터치 '+str(2 if bb.get('touch') else 0)+'/2 · 수축 후 상승 확산 '+str(2 if bb.get('squeeze_expansion') else 0)+'/2 · '+bb['basis']) if bb.get('score') is not None else bb.get('status')})
    record['bollinger_score_details']=bb
    counts=[streak(fs),streak(ins)]
    continuity=sum(2 if c>=3 else 0 for c in counts if c is not None)
    metrics.append({'name':'외국인·기관 수급 연속성','score':f'{continuity}/4' if all(c is not None for c in counts) else '미확보/4',
                    'value':' / '.join(f'{name}: {c}거래일 (2점)' if c is not None and c>=3 else f'{name}: {c}거래일 (0점)' if c is not None else f'{name}: 미확보' for name,c in zip(['외국인','기관'],counts))})
    for index,metric in enumerate(metrics,1): metric['id']=f'score_{index:02d}'
    assert len(metrics)==22
    assert sum(int(m['score'].split('/')[-1]) for m in metrics)==100
    record['partial_score']=sum(int(m['score'].split('/')[0]) for m in metrics if m['score'].split('/')[0].isdigit())
    record['score_status']='RSI·이격도·MACD 세부 구간 미확정'
    record['score']=None
    record['max_score']=100
    record['upside_probability']=None
    record['ai_briefing']='확정 일봉 기반 분석입니다. 일부 점수 기준이 미확정이므로 총점과 고득점 배지는 보류합니다. 상세 자료 취합 후 Gemini 종합 분석 버튼을 사용하세요.'
    record['fundamentals']={}
    return record

function renderNightQuote(el,d){
 el.textContent=d.val||'미확보';
 const pct=Number(String(d.chg||'').replace('%','').replace('−','-'));
 if(d.chg && Number.isFinite(pct)){
  const change=document.createElement('div');
  change.style.color=pct>0?'#f87171':pct<0?'#60a5fa':'#9ca3af';
  change.style.fontSize='12px';change.style.fontWeight='700';
  change.textContent=(pct>0?'▲ +':pct<0?'▼ -':'')+Math.abs(pct).toFixed(2)+'%';
  el.appendChild(change);
 }
 const info=document.createElement('div');info.style.fontSize='10px';info.style.color='#9ca3af';
 info.textContent=[d.status==='정상'?'':d.status,d.fetched_at?.slice(11,19)].filter(Boolean).join(' · ');
 el.appendChild(info);el.title=[d.source,d.basis].filter(Boolean).join('\n');
}
function flowMoney(v,basis){return v==null?'미확보':`<span class="${v>0?'text-rose-400':v<0?'text-sky-400':'text-gray-400'}">${v>0?'+':''}${(v/1e8).toFixed(2)}억 원<br><small>${esc(basis||'금액 기준 미확보')}</small></span>`;}
function dailyCell(d){return !d?'미확보':`${Number(d.price).toLocaleString()}원<br>${formatPct(d.pct)}<br><small>${d.date}</small>`;}
let searchSequence=0;
async function searchAll(query){
  const sequence=++searchSequence;
  if(!query.trim()){triggerScan(false);return;}
  try{const r=await fetch('/api/search?q='+encodeURIComponent(query));if(!r.ok)throw Error('검색 실패');const j=await r.json();if(sequence!==searchSequence)return;rawStocks=j.results;selectedIndustry=null;currentFilter='ALL';renderTable();}
  catch(e){document.getElementById('stock-tbody').innerHTML='<tr><td colspan="11">검색 실패 · 다시 시도하세요</td></tr>';}
}
async function requestAnalysis(code){
  try{const r=await fetch('/api/analyze/'+encodeURIComponent(code),{method:'POST'});const j=await r.json();if(!r.ok)throw Error(j.error);rawStocks=rawStocks.map(x=>x.code===code?j:x);renderTable();openModal(code);}
  catch(e){alert(e.message);}
}
const originalModal=openModal;
openModal=function(code){
  originalModal(code);const item=rawStocks.find(x=>x.code===code);if(!item)return;
  document.getElementById('modal-score').textContent=item.score==null?'총점 미확정':`${item.score} / 100`;
  const periods=item.metrics?.period_details||{};
  document.getElementById('modal-returns-grid').innerHTML=Object.entries(periods).map(([name,d])=>`<div class="bg-[#142036] p-2 rounded">${esc(name)}<br>${d.price==null?'미확보':Number(d.price).toLocaleString()+'원'}<br>${formatPct(d.pct)}<br><small>기준 ${esc(d.date||'미확보')}<br>최근 ${esc(d.end_date)}<br>${Number(d.end_price).toLocaleString()}원</small></div>`).join('');
};
async function updateMarket(){
 try{const r=await fetch('/api/market');if(!r.ok)throw Error();const j=await r.json();
 Object.entries(j).forEach(([group,rows])=>Object.entries(rows).forEach(([key,d])=>{let id=group==='bonds'?'bond-'+key.replace('yield_',''):group+'-'+key;const el=document.getElementById(id);if(!el)return;if(group==='night'){renderNightQuote(el,d);return;}renderIndicator(el,d);}));}catch(e){console.error('시장 조회 실패');}
}
let selectedMonth=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'}).slice(0,7);
function configureCalendar(){
 const span=document.getElementById('current-week-label');span.textContent=selectedMonth;
 const left=span.previousElementSibling,right=span.nextElementSibling;
 left.onclick=()=>moveMonth(-1);right.onclick=()=>moveMonth(1);
}
function moveMonth(n){const [y,m]=selectedMonth.split('-').map(Number);const d=new Date(y,m-1+n,1);selectedMonth=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;fetchCalendarData(currentCalMode);}
fetchCalendarData=async function(mode){
 document.getElementById('current-week-label').textContent=selectedMonth.replace('-','년 ')+'월';
 try{const r=await fetch('/api/calendar/month?month='+selectedMonth+'&category='+mode);if(!r.ok)throw Error();const j=await r.json();calendarData=j.data||[];
 const [year,month]=selectedMonth.split('-').map(Number),days=new Date(year,month,0).getDate();
 const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'}),day=Number(today.slice(8));
 const order=Array.from({length:days},(_,i)=>i+1);if(today.slice(0,7)===selectedMonth)order.sort((a,b)=>(a<day)-(b<day)||a-b);
 const container=document.getElementById('calendar-timeline');container.className='card p-3 rounded-xl overflow-y-auto';
 container.innerHTML=`<div class="text-xs text-amber-400 mb-3">${esc(j.status)} · 현재월은 오늘 이후 먼저, 지난 날짜 아래</div><div class="calendar-grid">${order.map(d=>`<div class="calendar-day">${d}일${calendarData.filter(x=>x.date===selectedMonth+'-'+String(d).padStart(2,'0')).map(x=>`<button onclick="selectCalendarItem('${esc(x.id)}')">${esc(x.title)}</button>`).join('')}</div>`).join('')}</div>`;
 if(!calendarData.length){document.getElementById('det-title').textContent='실제 일정 데이터 미연결';document.getElementById('det-ai').textContent='예시 일정은 제거했습니다. calendar_events.json에 출처가 확인된 월별 일정을 등록해야 합니다.';document.getElementById('det-actual').textContent='미확보';document.getElementById('det-forecast').textContent='미확보';window.activeGuide=null;}
 }catch(e){document.getElementById('calendar-timeline').textContent='일정 조회 실패';}
};
async function loadGuide(){try{const r=await fetch('/guide.html');const html=await r.text();document.querySelector('#manual-modal .space-y-4').innerHTML=html;}catch(e){}}

function renderIndicator(el,d){
 el.textContent=d.val||'미확보';
 const change=document.createElement('div');change.style.fontSize='12px';
 const pct=d.chg?Number(d.chg.replace('%','').replace('−','-')):null;
 change.style.color=pct>0?'#f87171':pct<0?'#60a5fa':'#9ca3af';
 const diff=d.diff==null?'변동값 미확보':Math.abs(d.diff).toLocaleString()+(d.unit==='yield'?'%p':'');
 change.textContent=[pct>0?'▲':pct<0?'▼':'',diff,d.chg||'등락률 미확보'].filter(Boolean).join(' · ');
 el.appendChild(change);
 const status=document.createElement('small');status.textContent=[d.status==='정상'?'':d.status,d.fetched_at?.slice(11,19)].filter(Boolean).join(' · ');el.appendChild(status);
 el.title=[d.source,d.basis].filter(Boolean).join('\n');
}
let researchSequence=0;
async function loadResearch(code){
 const sequence=++researchSequence;
 document.getElementById('research-panel')?.remove();
 try{
  const r=await fetch('/api/research/'+encodeURIComponent(code));const d=await r.json();if(!r.ok)throw Error(d.error);if(sequence!==researchSequence)return;
  document.getElementById('modal-ai-briefing').textContent=Object.entries(d.research_errors||{}).map(([k,v])=>k+': '+v).join(' · ')||'상세 자료 취합 완료 · AI 종합 분석은 아래 버튼';
  const el=document.getElementById('research-panel')||document.createElement('div');el.id='research-panel';el.className='p-3 text-xs space-y-3';
  document.getElementById('modal-risk-grid').parentElement.appendChild(el);
  const flows=Object.entries(d.flow_periods||{}).map(([n,x])=>`<div>${esc(n)}일: 외국인 ${flowMoney(x.foreign_won,'한투 순매수대금')} / 기관 ${flowMoney(x.institution_won,'한투 순매수대금')} · ${esc(x.status)}</div>`).join('');
  const discs=(d.disclosures||[]).map(x=>`<div><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.rcept_dt)} ${esc(x.title)}</a></div>`).join('');
  const news=(d.news?.items||[]).map(x=>`<div><a href="${esc(x.originallink||x.link)}" target="_blank" rel="noopener">${esc(x.title.replace(/<[^>]*>/g,''))}</a> · ${esc(x.pubDate)}</div>`).join('');
  const ss=d.short_selling||{};
  const rows=(ss.rows||[]).slice(0,30);
  const columns=Object.keys(rows[0]||{});
  const labels={stck_bsop_date:'거래일',stck_clpr:'종가',acml_vol:'거래량',ssts_cntg_qty:'공매도 체결수량',ssts_vol_rlim:'공매도 거래량비중',ssts_tr_pbmn:'공매도 거래대금',ssts_tr_pbmn_rlim:'공매도 대금비중'};
  const shorts=rows.length?`<div class="overflow-x-auto"><table><thead><tr>${columns.map(k=>`<th class="p-2">${esc(labels[k]||k)}</th>`).join('')}</tr></thead><tbody>${rows.map(x=>`<tr>${columns.map(k=>`<td class="p-2 whitespace-nowrap">${esc(x[k]??'미확보')}</td>`).join('')}</tr>`).join('')}</tbody></table></div><small>출처 원문 필드·단위 기준. 대차잔고와 공매도 체결은 별개입니다.</small>`:'';
  el.innerHTML=`<h4>기간별 외국인·기관 수급</h4>${flows||'수급 미확보'}<h4>종목 공시 원문</h4>${discs||'저장된 종목 공시 없음 · 공시 수집 범위 확인'}<h4>뉴스·재료</h4>${news||esc(d.news?.status||'뉴스 미확보')}<h4>공매도 일별 데이터</h4>${esc(ss.status||d.research_errors?.short_selling||'미확보')}${shorts}<h4>차트 상세</h4><pre class="overflow-x-auto">${esc(chartText(d.chart_details||{}))}</pre><h4>기간별 위험 확인</h4>${Object.entries(d.risks||{}).map(([k,v])=>`<div>${esc(k)}: ${esc(v)}</div>`).join('')}<h4>연간 재무</h4><div>${esc(d.annual_financials?.year||'미확보')} · ${esc(d.annual_financials?.scope||'')}</div><div>자료 취합: ${esc(d.researched_at)}</div><button class="bg-cyan-600 rounded p-2" onclick="runAI('${esc(code)}')">Gemini 종합 분석</button><button class="bg-cyan-600 rounded p-2" onclick="evaluateNewsCandidate('${esc(code)}')">기사 기반 상승후보 평가</button><div id="candidate-result"></div><div id="ai-result"></div>`;
  document.getElementById('modal-fundamentals-grid').innerHTML=Object.entries(d.fundamentals||{}).map(([k,v])=>`<div>${esc(k)}<br>${esc(v??'미확보')}</div>`).join('');
 }catch(e){document.getElementById('modal-ai-briefing').textContent='상세 취합 실패 · '+e.message;}
}
async function runAI(code){const el=document.getElementById('ai-result');el.style.whiteSpace='pre-wrap';el.textContent='AI 분석 중';try{const r=await fetch('/api/research/'+code+'/ai',{method:'POST'});const j=await r.json();el.textContent=r.ok?j.analysis:j.error;}catch(e){el.textContent='AI 연결 실패';}}
const modalWithResearch=openModal;openModal=function(code){modalWithResearch(code);loadResearch(code);};

async function evaluateNewsCandidate(code){const el=document.getElementById('candidate-result');el.textContent='기사 근거 평가 중';try{const r=await fetch('/api/recommendations/'+code,{method:'POST'});const j=await r.json();el.textContent=r.ok?({candidate:'상승 후보',hold:'판단 보류',exclude:'제외'}[j.decision]+': '+j.reason):j.error;loadRecommendations();}catch(e){el.textContent='추천 평가 실패';}}
async function loadRecommendations(){try{const r=await fetch('/api/recommendations');const j=await r.json();let el=document.getElementById('news-candidates');if(!el){el=document.createElement('div');el.id='news-candidates';el.className='card p-4 rounded-xl';document.getElementById('tab-money').appendChild(el);}el.innerHTML='<h3>기사 기반 상승 후보</h3><small>'+esc(j.basis)+'</small>'+((j.results||[]).map(x=>`<div>${esc(x.name)}: ${esc(x.reason)} · ${esc(x.evaluated_at)}<br>${x.evidence_urls.map(url=>`<a target="_blank" rel="noopener" href="${esc(url)}">기사 원문</a>`).join(' ')}</div>`).join('')||'<p>기사 평가를 완료한 상승 후보가 없습니다.</p>');}catch(e){}}
window.addEventListener('DOMContentLoaded',loadRecommendations);

function chartText(c){const b=c.bollinger||{};const n=x=>x==null?'미확보':Number(x).toLocaleString('ko-KR',{maximumFractionDigits:2});return ['볼린저 상단: '+n(b.upper)+'원 / 중심: '+n(b.middle)+'원 / 하단: '+n(b.lower)+'원','밴드폭: '+n(b.width_pct)+'%',...Object.entries(c.trends||{}).map(([days,p])=>days+'거래일 수익률: '+n(p)+'%'),'최근 확보 일봉 최저가: '+n(c.low_52w)+'원','박스권: '+(c.box_status||'미확보')].join('\n');}

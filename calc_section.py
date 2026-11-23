"""티즈 매출·영업이익 기여도 계산기 (탑코 케이스 기반, 입력형). build.py에서 html 조각으로 가져다 씀."""
import json


def calc_html(daily_msgs, topco):
    """daily_msgs: 트래커 기준 티즈 하루 메시지. topco: 탑툰챗 벤치마크 요약 dict."""
    D = dict(
        daily=round(daily_msgs or 0),
        core_rev=2636, core_op=218, rev26=2509, op26=184.9, kr_webtoon=1204,
        shares=35646926, per=12, tax=30, price=3245,
        cases={
            'Bear': dict(mult=2, won=50, paid=30, recog=44, opm=-20, pen=3),
            'Base': dict(mult=8.2, won=50, paid=60, recog=44, opm=18, pen=8),
            'Bull': dict(mult=20, won=50, paid=100, recog=44, opm=25, pen=22),
        },
        topco=topco,
    )
    return r'''
<div class="card" id="calc"><h2>티즈 기여도 계산기 (탑코 케이스)</h2>
<p class="cap">숫자를 바꾸면 바로 다시 계산됨. 방법 A = 트래커 실측 하루 메시지에서 출발, 방법 B = 탑툰챗처럼 국내 웹툰 매출의 일정 비율까지 챗이 붙는 경우. 기여도 분모는 2027E 본업(티즈 제외) 매출·영업이익</p>
<div class="bench" id="bench"></div>
<div class="grid2">
<label>2027E 본업 매출(억)<input data-g="core_rev" type="number" step="1"></label>
<label>2027E 본업 영업이익(억)<input data-g="core_op" type="number" step="1"></label>
<label>국내 웹툰 연매출(억, 방법 B)<input data-g="kr_webtoon" type="number" step="1"></label>
<label>티즈 현재 하루 메시지(트래커)<input data-g="daily" type="number" step="1"></label>
<label>적용 PER(배)<input data-g="per" type="number" step="0.5"></label>
<label>세율(%)<input data-g="tax" type="number" step="1"></label>
<label>유통주식(주)<input data-g="shares" type="number" step="1"></label>
<label>현재 주가(원)<input data-g="price" type="number" step="5"></label>
</div>
<div class="tw"><table class="ct"><thead><tr><th>입력</th><th class="n">Bear</th><th class="n">Base</th><th class="n">Bull</th><th>설명</th></tr></thead><tbody id="cin"></tbody></table></div>
<h3>결과</h3>
<div class="tw"><table class="ct"><thead><tr><th>결과 (2027E, 억원)</th><th class="n">Bear</th><th class="n">Base</th><th class="n">Bull</th></tr></thead><tbody id="cout"></tbody></table></div>
<p class="cap" id="cnote"></p>
<button id="creset" type="button">기본값으로</button>
</div>
<script>
(function(){
const DEF=''' + json.dumps(D, ensure_ascii=False) + r''';
let S; try{S=JSON.parse(localStorage.getItem('kd_calc'))}catch(e){}
if(!S||!S.cases) S=JSON.parse(JSON.stringify(DEF)); S.daily=DEF.daily; S.topco=DEF.topco;
const ROWS=[['mult','A · 하루 메시지 배수(현재 대비)','탑코 1Q26→2Q26 챗 매출 ×8.2'],['won','A · 메시지당 과금(원)','탐방: 턴당 40→50원'],['paid','A · 유료 메시지 비중(%)','무료 턴 제외'],
 ['recog','키다리 인식 비율(%)','작가 RS 후 파트너 50:50 → 100당 43~45'],['opm','티즈 영업이익률(%)','토큰비 파트너 부담, 회사 Base 30/165=18%'],['pen','B · 국내 웹툰 대비 챗 매출(%)','탑코 2Q26 22%']];
const f0=v=>isFinite(v)?Math.round(v).toLocaleString():'—', f1=v=>isFinite(v)?(Math.round(v*10)/10).toLocaleString():'—', pc=v=>isFinite(v)?(Math.round(v*10)/10)+'%':'—';
function save(){try{localStorage.setItem('kd_calc',JSON.stringify(S))}catch(e){}}
function build(){
 document.querySelectorAll('[data-g]').forEach(el=>{el.value=S[el.dataset.g];el.oninput=()=>{S[el.dataset.g]=+el.value;save();calc()}});
 const tb=document.getElementById('cin');tb.innerHTML='';
 ROWS.forEach(([k,l,d])=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${l}</td>`+['Bear','Base','Bull'].map(c=>`<td class="n"><input type="number" step="any" data-c="${c}" data-k="${k}" value="${S.cases[c][k]}"></td>`).join('')+`<td class="d">${d}</td>`;tb.appendChild(tr)});
 tb.querySelectorAll('input').forEach(el=>el.oninput=()=>{S.cases[el.dataset.c][el.dataset.k]=+el.value;save();calc()});
 const b=S.topco; document.getElementById('bench').innerHTML=b?`<b>탑코 벤치마크</b> · 챗 매출 1Q26 약 2.5억 → 2Q26 약 20.4억(×8.2, 국내 플랫폼의 22%) · 방문 MAU 3월 22만 → 9월 48만 · 공개 트래커 하루 세션 9월 ${f0(b.sep)} → 11월 ${f0(b.nov)}(${pc((b.nov/b.sep-1)*100)}) · 해외(일본·대만·북미) 세션 비중 ${pc(b.ovs)}`:'';
 calc();
}
function calc(){
 const out={}; const R=(k,v)=>{(out[k]=out[k]||{});return v};
 const rows=[['A · 2027 하루 메시지','mA',f0],['A · 티즈 매출','revA',f1],['A · 티즈 영업이익','opA',f1],['A · 매출 기여도','rsA',pc],['A · 영업이익 기여도','osA',pc],['A · 주당가치 기여(원)','psA',f0],
  ['B · 티즈 매출','revB',f1],['B · 티즈 영업이익','opB',f1],['B · 매출 기여도','rsB',pc],['B · 영업이익 기여도','osB',pc],['B · 주당가치 기여(원)','psB',f0],['B가 요구하는 하루 메시지','needB',f0],['B 요구치 ÷ 현재','xB',v=>isFinite(v)?f1(v)+'배':'—']];
 const res={};
 ['Bear','Base','Bull'].forEach(c=>{const p=S.cases[c];const r={};
  r.mA=S.daily*p.mult; r.revA=r.mA*365*p.won*(p.paid/100)*(p.recog/100)/1e8; r.opA=r.revA*p.opm/100;
  r.rsA=r.revA/(S.core_rev+r.revA)*100; r.osA=r.opA/(S.core_op+r.opA)*100; r.psA=r.opA*(1-S.tax/100)*S.per*1e8/S.shares;
  r.revB=S.kr_webtoon*p.pen/100*(p.recog/100); r.opB=r.revB*p.opm/100;
  r.rsB=r.revB/(S.core_rev+r.revB)*100; r.osB=r.opB/(S.core_op+r.opB)*100; r.psB=r.opB*(1-S.tax/100)*S.per*1e8/S.shares;
  r.needB=r.revB*1e8/(365*p.won*(p.paid/100)*(p.recog/100)); r.xB=r.needB/S.daily; res[c]=r});
 document.getElementById('cout').innerHTML=rows.map(([l,k,fm])=>`<tr><td>${l}</td>`+['Bear','Base','Bull'].map(c=>`<td class="n">${fm(res[c][k])}</td>`).join('')+'</tr>').join('');
 document.getElementById('cnote').textContent=`주당가치 기여 = 티즈 영업이익 × (1−세율) × PER ÷ 유통주식. 현재 주가 ${f0(S.price)}원 대비 Base(A) ${pc(res.Base.psA/S.price*100)}, Base(B) ${pc(res.Base.psB/S.price*100)}.`;
}
document.getElementById('creset').onclick=()=>{S=JSON.parse(JSON.stringify(DEF));save();build()};
build();
})();
</script>'''

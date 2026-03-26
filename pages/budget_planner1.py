"""
pages/budget_planner.py
Drop-in replacement — same imports, same function signature.
Tab 1: Interactive planner (income, expenses, multi-loan, what-ifs) via embedded HTML.
Tab 2: Budget performance vs actual spending (original Streamlit logic, untouched).
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import get_user_preferences, save_user_preferences
from data_loader import load_all_user_data
from utils import get_spending_by_category, calculate_monthly_stats
from config import DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
import json
import calendar


# ---------------------------------------------------------------------------
# Self-contained interactive planner HTML
# ---------------------------------------------------------------------------
_PLANNER_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;font-size:13px;color:#e8eaf0;background:#0f1117;padding:16px}
h3{font-size:13px;font-weight:600;color:#8b8fa8;margin:18px 0 8px;padding-bottom:5px;border-bottom:1px solid #1e2130;text-transform:uppercase;letter-spacing:.04em}
h3:first-of-type{margin-top:0}
input[type=number],input[type=text],select{width:100%;padding:6px 9px;background:#1a1d27;border:1px solid #2a2e45;border-radius:6px;color:#e8eaf0;font-size:13px}
input:focus,select:focus{outline:none;border-color:#4f6bef}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.fld{margin-bottom:8px}
.fld label{font-size:11px;color:#555870;display:block;margin-bottom:3px}
.row{display:flex;align-items:center;gap:7px;padding:5px 0;border-bottom:1px solid #1a1d27}
.row:last-child{border-bottom:none}
.rname{flex:1;background:#1a1d27;border:1px solid #2a2e45;border-radius:6px;color:#e8eaf0;padding:5px 8px;font-size:13px}
.ramt{width:115px;background:#1a1d27;border:1px solid #2a2e45;border-radius:6px;color:#e8eaf0;padding:5px 8px;font-size:13px;text-align:right}
.del{background:transparent;border:1px solid #2a2e45;border-radius:5px;color:#555870;padding:3px 8px;cursor:pointer;font-size:12px}
.del:hover{border-color:#f87171;color:#f87171}
.add-btn{background:transparent;border:1px solid #2a2e45;border-radius:6px;color:#8b8fa8;padding:5px 12px;cursor:pointer;font-size:12px;margin-top:6px}
.add-btn:hover{border-color:#4f6bef;color:#93a8ff}
.lcard{background:#1a1d27;border:1px solid #2a2e45;border-radius:8px;padding:12px;margin-bottom:10px}
.lhdr{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.ltitle{flex:1;background:transparent;border:none;color:#c8cad8;font-size:14px;font-weight:600;padding:0}
.ltitle:focus{outline:none}
.sumgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}
.sc{background:#1a1d27;border-radius:8px;padding:11px}
.sc .lbl{font-size:11px;color:#555870;margin-bottom:3px}
.sc .val{font-size:19px;font-weight:700}
.green{color:#2dd4a0}.red{color:#f87171}.amber{color:#fbbf24}.blue{color:#60a5fa}
.sched{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.sched th{text-align:left;padding:5px 7px;background:#22263a;color:#8b8fa8;font-weight:500}
.sched td{padding:5px 7px;border-bottom:1px solid #1a1d27;color:#c8cad8}
.sched tr:last-child td{font-weight:600;background:#22263a}
.prog{background:#2a2e45;border-radius:999px;height:4px;width:60px;display:inline-block;vertical-align:middle;overflow:hidden}
.pfill{height:4px;background:#4f6bef;border-radius:999px}
.ins{display:flex;gap:8px;align-items:flex-start;background:#1a1d27;border-radius:7px;padding:8px 11px;margin-bottom:5px;font-size:12px;color:#c8cad8}
.dot{width:6px;height:6px;border-radius:50%;margin-top:3px;flex-shrink:0}
.dot.g{background:#2dd4a0}.dot.r{background:#f87171}.dot.a{background:#fbbf24}.dot.b{background:#60a5fa}
.badge{font-size:10px;padding:2px 7px;border-radius:999px;display:inline-block}
.bg{background:#1e2a45;color:#60a5fa}.gg{background:#1a2e25;color:#2dd4a0}.ga{background:#2e2510;color:#fbbf24}.gr{background:#2e1a1a;color:#f87171}
hr{border:none;border-top:1px solid #1e2130;margin:16px 0}
.cw{position:relative;width:100%;height:170px;margin:10px 0}
</style></head><body>

<div class="sumgrid" id="sumCards"></div>
<hr>
<h3>Income sources</h3>
<div id="incRows"></div>
<button class="add-btn" onclick="addInc()">+ Add income source</button>
<h3>Expenses</h3>
<div id="expRows"></div>
<button class="add-btn" onclick="addExp()">+ Add expense</button>
<h3>Loans</h3>
<div id="loanList"></div>
<button class="add-btn" onclick="addLoan()">+ Add loan</button>
<h3>One-time payments</h3>
<div id="otpRows"></div>
<button class="add-btn" onclick="addOTP()">+ Add payment</button>
<div style="margin-top:10px;display:flex;align-items:center;gap:8px">
  <span style="font-size:12px;color:#8b8fa8;white-space:nowrap">Apply to:</span>
  <select id="otpTarget" onchange="recalc()" style="width:200px"></select>
</div>
<hr>
<h3>Cash flow breakdown</h3>
<div class="cw"><canvas id="cfC"></canvas></div>
<h3>Expenses as % of income</h3>
<div class="cw"><canvas id="pctC"></canvas></div>
<h3>Loan schedules</h3>
<div id="scheds"></div>
<h3>Insights</h3>
<div id="ins"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const MO=['January','February','March','April','May','June','July','August','September','October','November','December'];
function nextMo(off,start){const d=new Date(2025,7,1);d.setMonth(d.getMonth()+off+(start||0));return MO[d.getMonth()]+' '+d.getFullYear()}
let incs=[{id:1,name:'Main take-home',amt:187313},{id:2,name:'Uber income',amt:39000}];
let exps=[{id:1,name:'Food',amt:40000},{id:2,name:'Transport',amt:40000},{id:3,name:'Internet & phone',amt:10500},{id:4,name:'Entertainment',amt:15000},{id:5,name:'Miscellaneous',amt:10000},{id:6,name:'Buffer',amt:5000}];
let loans=[{id:1,name:'Property loan',bal:620000,rate:0,pmt:100000,start:0}];
let otps=[{id:1,name:'Shoe allowance',amt:110000,st:'Pending'},{id:2,name:'Uniform allowance',amt:50000,st:'Pending'}];
let ii=3,ei=7,li=2,oi=3,cfCh=null,ptCh=null;
const $=id=>document.getElementById(id);
const fmt=n=>'J$'+Math.abs(Math.round(n)).toLocaleString();
const fmtS=n=>(Math.round(n)>=0?'+J$':'-J$')+Math.abs(Math.round(n)).toLocaleString();

function renderIncs(){
  $('incRows').innerHTML='';
  incs.forEach(x=>{
    const d=document.createElement('div');d.className='row';
    d.innerHTML=`<input class="rname" type="text" value="${x.name}" oninput="incs.find(i=>i.id==${x.id}).name=this.value;recalc()">
    <input class="ramt" type="number" value="${x.amt}" min="0" oninput="incs.find(i=>i.id==${x.id}).amt=+this.value;recalc()">
    <span style="font-size:11px;color:#555870">J$/mo</span>
    <button class="del" onclick="incs=incs.filter(i=>i.id!=${x.id});renderAll()">x</button>`;
    $('incRows').appendChild(d);
  });
}
function renderExps(){
  $('expRows').innerHTML='';
  exps.forEach(x=>{
    const d=document.createElement('div');d.className='row';
    d.innerHTML=`<input class="rname" type="text" value="${x.name}" oninput="exps.find(i=>i.id==${x.id}).name=this.value;recalc()">
    <input class="ramt" type="number" value="${x.amt}" min="0" oninput="exps.find(i=>i.id==${x.id}).amt=+this.value;recalc()">
    <span style="font-size:11px;color:#555870">J$/mo</span>
    <button class="del" onclick="exps=exps.filter(i=>i.id!=${x.id});renderAll()">x</button>`;
    $('expRows').appendChild(d);
  });
}
function renderOTPs(){
  $('otpRows').innerHTML='';
  otps.forEach(x=>{
    const d=document.createElement('div');d.className='row';
    d.innerHTML=`<input class="rname" type="text" value="${x.name}" oninput="otps.find(i=>i.id==${x.id}).name=this.value;recalc()">
    <input class="ramt" type="number" value="${x.amt}" min="0" oninput="otps.find(i=>i.id==${x.id}).amt=+this.value;recalc()">
    <select style="width:90px" onchange="otps.find(i=>i.id==${x.id}).st=this.value;recalc()">
      <option ${x.st==='Pending'?'selected':''}>Pending</option>
      <option ${x.st==='Received'?'selected':''}>Received</option>
    </select>
    <button class="del" onclick="otps=otps.filter(i=>i.id!=${x.id});renderAll()">x</button>`;
    $('otpRows').appendChild(d);
  });
  const sel=$('otpTarget');const prev=sel?sel.value:'';
  if(sel)sel.innerHTML=loans.map((l,i)=>`<option value="${i}">${l.name}</option>`).join('');
  if(sel&&prev!=='')try{sel.value=prev}catch(e){}
}
function renderLoans(){
  $('loanList').innerHTML='';
  loans.forEach(ln=>{
    const d=document.createElement('div');d.className='lcard';
    d.innerHTML=`<div class="lhdr">
      <input class="ltitle" type="text" value="${ln.name}" oninput="loans.find(l=>l.id==${ln.id}).name=this.value;recalc();renderOTPs()">
      <span class="badge ${ln.rate===0?'gg':'ga'}">${ln.rate===0?'Interest-free':ln.rate+'% p.a.'}</span>
      <button class="del" onclick="loans=loans.filter(l=>l.id!=${ln.id});renderAll()">remove</button>
    </div>
    <div class="grid2">
      <div class="fld"><label>Opening balance (J$)</label><input type="number" value="${ln.bal}" min="0" oninput="loans.find(l=>l.id==${ln.id}).bal=+this.value;recalc()"></div>
      <div class="fld"><label>Annual interest rate (%)</label><input type="number" value="${ln.rate}" min="0" max="100" step="0.1" oninput="loans.find(l=>l.id==${ln.id}).rate=+this.value;renderLoans();recalc()"></div>
      <div class="fld"><label>Monthly payment (J$)</label><input type="number" value="${ln.pmt}" min="0" oninput="loans.find(l=>l.id==${ln.id}).pmt=+this.value;recalc()"></div>
      <div class="fld"><label>Start offset (months, 0=now)</label><input type="number" value="${ln.start}" min="0" max="24" oninput="loans.find(l=>l.id==${ln.id}).start=+this.value;recalc()"></div>
    </div>`;
    $('loanList').appendChild(d);
  });
}
function addInc(){incs.push({id:ii++,name:'New income',amt:0});renderAll()}
function addExp(){exps.push({id:ei++,name:'New expense',amt:0});renderAll()}
function addLoan(){loans.push({id:li++,name:'New loan',bal:0,rate:0,pmt:0,start:0});renderAll()}
function addOTP(){otps.push({id:oi++,name:'New payment',amt:0,st:'Pending'});renderAll()}

function calcSched(ln,extra){
  const rows=[];let bal=Math.max(0,ln.bal-extra);const mr=ln.rate/100/12;let m=0;
  while(bal>0&&m<120){
    const interest=Math.round(bal*mr);
    const pmt=Math.min(bal+interest,Math.max(ln.pmt,0));
    if(pmt<=0)break;
    const closing=Math.max(0,Math.round(bal-(pmt-interest)));
    rows.push({m,cal:nextMo(m,ln.start),open:Math.round(bal),interest,pmt:Math.round(pmt),close:closing});
    bal=closing;m++;
  }
  return rows;
}

function recalc(){
  const totInc=incs.reduce((s,x)=>s+x.amt,0);
  const totExp=exps.reduce((s,x)=>s+x.amt,0);
  const totLoan=loans.reduce((s,x)=>s+x.pmt,0);
  const net=totInc-totExp-totLoan;
  const nc=net>=0?'green':net>-15000?'amber':'red';
  $('sumCards').innerHTML=`
    <div class="sc"><div class="lbl">Total income</div><div class="val green">${fmt(totInc)}</div><div style="font-size:11px;color:#555870">per month</div></div>
    <div class="sc"><div class="lbl">Expenses</div><div class="val red">${fmt(totExp)}</div><div style="font-size:11px;color:#555870">ex-loans</div></div>
    <div class="sc"><div class="lbl">Loan payments</div><div class="val blue">${fmt(totLoan)}</div><div style="font-size:11px;color:#555870">${loans.length} loan${loans.length!==1?'s':''}</div></div>
    <div class="sc"><div class="lbl">Net</div><div class="val ${nc}">${fmtS(net)}</div><div style="font-size:11px;color:#555870">${net>=0?'surplus':'deficit'}</div></div>`;

  updateCharts(totInc,totExp,totLoan);

  const tidx=parseInt($('otpTarget')?.value||'0');
  const otp=otps.filter(o=>o.st==='Pending').reduce((s,o)=>s+o.amt,0);

  $('scheds').innerHTML='';
  loans.forEach((ln,i)=>{
    const extra=i===tidx?otp:0;
    const base=calcSched(ln,0);const wOTP=extra>0?calcSched(ln,extra):null;
    const mos=base.length;const bc=mos<=5?'gg':mos<=8?'bg':'gr';
    const ti=base.reduce((s,r)=>s+r.interest,0);const tp=base.reduce((s,r)=>s+r.pmt,0);
    let h=`<div class="lcard"><div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span style="font-size:14px;font-weight:600;color:#c8cad8">${ln.name}</span>
      <span class="badge ${bc}">${mos} month${mos!==1?'s':''} to clear</span>
      ${ln.rate>0?`<span class="badge ga">${ln.rate}% p.a.</span>`:'<span class="badge gg">Interest-free</span>'}
    </div>`;
    if(wOTP&&extra>0)h+=`<div style="font-size:12px;color:#8b8fa8;margin-bottom:8px">With <strong style="color:#e8eaf0">${fmt(extra)}</strong> one-time applied: clears in <strong style="color:#2dd4a0">${wOTP.length} months</strong>${base.length>wOTP.length?' (saves '+(base.length-wOTP.length)+' months)':''}</div>`;
    h+=`<table class="sched"><thead><tr><th>Month</th><th>Calendar</th><th>Opening</th>`;
    if(ln.rate>0)h+=`<th>Interest</th>`;
    h+=`<th>Payment</th><th>Closing</th><th>Progress</th></tr></thead><tbody>`;
    base.forEach(r=>{
      const pct=ln.bal>0?Math.round((1-r.close/ln.bal)*100):100;
      h+=`<tr><td>M${r.m+1}</td><td>${r.cal}</td><td>${fmt(r.open)}</td>`;
      if(ln.rate>0)h+=`<td class="amber">${fmt(r.interest)}</td>`;
      h+=`<td>${fmt(r.pmt)}</td><td style="color:${r.close===0?'#2dd4a0':'#c8cad8'}">${fmt(r.close)}</td>
      <td><div class="prog"><div class="pfill" style="width:${pct}%"></div></div> <span style="font-size:10px;color:#555870">${pct}%</span></td></tr>`;
    });
    h+=`<tr><td colspan="2">Total</td><td>${fmt(Math.max(0,ln.bal-extra))}</td>`;
    if(ln.rate>0)h+=`<td class="amber">${fmt(ti)}</td>`;
    h+=`<td>${fmt(tp)}</td><td class="green">${fmt(0)}</td><td></td></tr></tbody></table>`;
    if(ti>0)h+=`<div style="margin-top:6px;font-size:12px;color:#fbbf24">Total interest: ${fmt(ti)}</div>`;
    h+=`</div>`;
    $('scheds').innerHTML+=h;
  });

  renderIns(totInc,totExp,totLoan,net,otp,tidx);
}

function updateCharts(inc,exp,lp){
  const cfL=incs.map(x=>x.name).concat(exps.map(x=>x.name)).concat(loans.map(x=>x.name+' pmt'));
  const cfD=incs.map(x=>x.amt).concat(exps.map(x=>x.amt)).concat(loans.map(x=>x.pmt));
  const cfC=['#2dd4a0','#34d399'].slice(0,incs.length)
    .concat(['#f87171','#fb923c','#fbbf24','#a78bfa','#60a5fa','#f472b6'].slice(0,exps.length))
    .concat(['#4f6bef','#818cf8','#a5b4fc'].slice(0,loans.length));
  if(cfCh)cfCh.destroy();
  cfCh=new Chart($('cfC'),{type:'bar',data:{labels:cfL,datasets:[{data:cfD,backgroundColor:cfC,borderRadius:4}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'J$'+Math.round(c.raw).toLocaleString()}}},
      scales:{x:{ticks:{color:'#8b8fa8',autoSkip:false,maxRotation:40,font:{size:11}},grid:{color:'#1a1d27'}},
        y:{ticks:{color:'#8b8fa8',callback:v=>'J$'+Math.round(v/1000)+'k',font:{size:11}},grid:{color:'#1e2130'}}}}});
  if(inc>0){
    const pL=exps.map(x=>x.name).concat(loans.map(x=>x.name+' pmt'));
    const pD=exps.map(x=>Math.round(x.amt/inc*1000)/10).concat(loans.map(x=>Math.round(x.pmt/inc*1000)/10));
    const pC=['#4f6bef','#f87171','#2dd4a0','#fbbf24','#fb923c','#a78bfa','#60a5fa','#f472b6'];
    if(ptCh)ptCh.destroy();
    ptCh=new Chart($('pctC'),{type:'bar',data:{labels:pL,datasets:[{data:pD,backgroundColor:pC.slice(0,pL.length),borderRadius:4}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.raw+'% of income'}}},
        scales:{x:{ticks:{color:'#8b8fa8',callback:v=>v+'%',font:{size:11}},grid:{color:'#1e2130'}},
          y:{ticks:{color:'#8b8fa8',font:{size:11}},grid:{color:'#1a1d27'}}}}});
  }
}

function renderIns(inc,exp,lp,net,otp,tidx){
  const el=$('ins');el.innerHTML='';const is=[];
  is.push(net>=0?{t:'g',m:`Monthly surplus <strong>${fmt(net)}</strong> — budget is in the green`}:{t:'r',m:`Monthly deficit <strong>${fmt(Math.abs(net))}</strong> — outgoings exceed income`});
  if(otp>0&&loans[tidx]){const ln=loans[tidx];const b=calcSched(ln,0).length;const a=calcSched(ln,otp).length;if(b>a)is.push({t:'g',m:`Applying ${fmt(otp)} one-time payments to <strong>${ln.name}</strong> saves <strong>${b-a} month${b-a!==1?'s':''}</strong>`});}
  loans.forEach(ln=>{const s=calcSched(ln,0);if(s.length>0)is.push({t:'b',m:`<strong>${ln.name}</strong> clears in <strong>${s.length} months</strong> — ends ${s[s.length-1].cal}`});const ti=s.reduce((a,r)=>a+r.interest,0);if(ti>0)is.push({t:'a',m:`Interest cost on <strong>${ln.name}</strong>: <strong>${fmt(ti)}</strong> total`});});
  if(inc>0)is.push({t:'b',m:`Total outgoings are <strong>${Math.round((exp+lp)/inc*100)}%</strong> of monthly income`});
  if(loans.length>1){const hi=loans.slice().sort((a,b)=>b.rate-a.rate)[0];if(hi.rate>0)is.push({t:'a',m:`Highest-rate loan: <strong>${hi.name}</strong> at ${hi.rate}% p.a. — pay this down first`});}
  is.push({t:'g',m:`Once all loans clear, monthly surplus rises to <strong>${fmt(inc-exp)}</strong>`});
  is.forEach(i=>{el.innerHTML+=`<div class="ins"><div class="dot ${i.t}"></div><div>${i.m}</div></div>`;});
}

function renderAll(){renderIncs();renderExps();renderLoans();renderOTPs();recalc()}
renderAll();
</script></body></html>"""


# ---------------------------------------------------------------------------
# budget_planner_page — same name, same signature, 2-tab body
# ---------------------------------------------------------------------------
def budget_planner_page():
    """Budget Planner - Set and track monthly budgets"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)

    # header (identical to original)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("### 💰 Budget Planner")
    with col2:
        if st.button("💎 Possible Savings", use_container_width=True, type="secondary"):
            st.session_state.selected_sub_feature = 'possible_savings'
            st.rerun()
    with col3:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()

    st.markdown("---")

    tab1, tab2 = st.tabs(["🧮 Interactive planner", "📊 Budget vs actual"])

    # ── TAB 1: interactive HTML planner ────────────────────────────────────
    with tab1:
        st.caption(
            "Edit every field live — add income sources, expenses, and multiple loans "
            "at different interest rates. One-time payments reduce whichever loan you choose."
        )
        components.html(_PLANNER_HTML, height=2500, scrolling=True)

    # ── TAB 2: original budget vs actual logic (unchanged) ──────────────────
    with tab2:
        prefs = get_user_preferences(st.session_state.user['id'])
        if prefs and prefs.get('monthly_budgets'):
            current_budgets = json.loads(prefs['monthly_budgets'])
        else:
            current_budgets = DEFAULT_BUDGETS.copy()

        current_savings_goal = (
            prefs.get('savings_goal', DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
        )

        data = load_all_user_data(st.session_state.user['id'])

        # budget settings
        st.markdown("#### 🎯 Set Your Monthly Budgets")
        st.info("💡 Set realistic spending limits for each category. We'll track your progress and alert you when you're close to limits.")

        col1, col2 = st.columns(2)
        categories = [cat for cat in current_budgets.keys() if cat not in ['Income', 'Other']]
        mid = len(categories) // 2
        new_budgets = current_budgets.copy()

        with col1:
            st.markdown("##### 🏷️ Category Budgets")
            for category in categories[:mid]:
                new_budgets[category] = st.number_input(
                    f"{category}", min_value=0,
                    value=int(current_budgets[category]), step=500,
                    key=f"budget_{category}",
                    help=f"Monthly budget for {category}",
                )
        with col2:
            st.markdown("##### 🏷️ Category Budgets")
            for category in categories[mid:]:
                new_budgets[category] = st.number_input(
                    f"{category}", min_value=0,
                    value=int(current_budgets[category]), step=500,
                    key=f"budget_{category}",
                    help=f"Monthly budget for {category}",
                )

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown("##### 💎 Monthly Savings Goal")
            new_savings_goal = st.number_input(
                "Target amount to save each month", min_value=0,
                value=int(current_savings_goal), step=500,
                key="savings_goal_input",
            )
        with col2:
            st.markdown("##### 📊 Total Budget")
            total_budget = sum(new_budgets.values())
            st.metric("Monthly Limit", f"J${total_budget:,.0f}")
        with col3:
            st.markdown("##### 💰 Target Income")
            st.metric("Needed", f"J${total_budget + new_savings_goal:,.0f}")

        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("💾 Save Budgets", use_container_width=True, type="primary"):
                if prefs and prefs.get('category_keywords'):
                    keywords = json.loads(prefs['category_keywords'])
                else:
                    from config import DEFAULT_CATEGORY_MAPPING
                    keywords = DEFAULT_CATEGORY_MAPPING.copy()
                if save_user_preferences(st.session_state.user['id'], keywords, new_budgets, new_savings_goal):
                    st.success("✅ Budgets saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save budgets")
        with col2:
            if st.button("🔄 Reset to Defaults", use_container_width=True):
                if prefs and prefs.get('category_keywords'):
                    keywords = json.loads(prefs['category_keywords'])
                else:
                    from config import DEFAULT_CATEGORY_MAPPING
                    keywords = DEFAULT_CATEGORY_MAPPING.copy()
                if save_user_preferences(st.session_state.user['id'], keywords, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL):
                    st.success("✅ Reset to defaults!")
                    st.rerun()

        # budget performance (100% original logic)
        if not data.empty and 'YearMonth' in data.columns:
            st.markdown("---")
            st.markdown("#### 📈 Budget Performance")

            available_months = sorted(data['YearMonth'].unique(), reverse=True)
            if available_months:
                col1, col2 = st.columns([1, 3])
                with col1:
                    selected_month = st.selectbox("Select Month", available_months, key="performance_month")

                month_stats = calculate_monthly_stats(data, selected_month)
                month_summary = get_spending_by_category(data, selected_month)

                if not month_summary.empty:
                    comparison_data = []
                    for category in new_budgets.keys():
                        if category in ['Income', 'Other']:
                            continue
                        budget = new_budgets[category]
                        actual = month_summary[month_summary['Spending Category'] == category]['Amount'].sum()
                        comparison_data.append({
                            'Category': category,
                            'Budget': budget,
                            'Actual': actual,
                            'Remaining': budget - actual,
                            'Percentage': (actual / budget * 100) if budget > 0 else 0,
                        })
                    comparison_df = pd.DataFrame(comparison_data)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Budget", f"J${total_budget:,.0f}", help="Total monthly budget limit")
                    with col2:
                        st.metric("Total Spent", f"J${month_stats['spending']:,.0f}",
                                  delta=f"{month_stats['spending'] - total_budget:,.0f}"
                                  if month_stats['spending'] > total_budget else None,
                                  delta_color="inverse")
                    with col3:
                        remaining = total_budget - month_stats['spending']
                        st.metric("Remaining", f"J${remaining:,.0f}",
                                  delta=f"{(remaining / total_budget * 100):.0f}%" if total_budget > 0 else None)
                    with col4:
                        st.metric("Savings", f"J${month_stats['savings']:,.0f}",
                                  delta=f"{month_stats['savings'] - new_savings_goal:,.0f}",
                                  delta_color="normal")

                    st.markdown("---")
                    st.markdown("##### 📊 Budget vs Actual Spending")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name='Budget', x=comparison_df['Category'], y=comparison_df['Budget'],
                        marker_color='#3b82f6',
                        text=comparison_df['Budget'].apply(lambda x: f'J${x:,.0f}'),
                        textposition='outside',
                    ))
                    fig.add_trace(go.Bar(
                        name='Actual', x=comparison_df['Category'], y=comparison_df['Actual'],
                        marker_color=comparison_df['Percentage'].apply(
                            lambda x: '#ef4444' if x > 100 else '#10b981'
                        ),
                        text=comparison_df['Actual'].apply(lambda x: f'J${x:,.0f}'),
                        textposition='outside',
                    ))
                    fig.update_layout(
                        barmode='group', height=400, xaxis_tickangle=-45,
                        yaxis_title='Amount (J$)', showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("##### 📋 Category Details")
                    for _, row in comparison_df.iterrows():
                        pct = row['Percentage']
                        if pct > 100:
                            status, color, bg_color = "🔴 OVER BUDGET", "#ef4444", "#fee2e2"
                        elif pct > 80:
                            status, color, bg_color = "🟡 WARNING", "#f59e0b", "#fef3c7"
                        else:
                            status, color, bg_color = "🟢 ON TRACK", "#10b981", "#d1fae5"
                        st.markdown(f"""
                            <div style='background:{bg_color};padding:1rem;border-radius:8px;margin-bottom:.5rem;border-left:4px solid {color};'>
                                <div style='display:flex;justify-content:space-between;align-items:center;'>
                                    <div style='flex:1;'>
                                        <div style='font-size:1.1rem;font-weight:600;color:#111827;margin-bottom:.25rem;'>{row['Category']}</div>
                                        <div style='font-size:.85rem;color:#6b7280;'>Budget: J${row['Budget']:,.0f} | Spent: J${row['Actual']:,.0f} | Left: J${row['Remaining']:,.0f}</div>
                                    </div>
                                    <div style='text-align:right;'>
                                        <div style='font-size:.9rem;font-weight:600;color:{color};margin-bottom:.25rem;'>{status}</div>
                                        <div style='font-size:1.25rem;font-weight:700;color:{color};'>{pct:.0f}%</div>
                                    </div>
                                </div>
                                <div style='margin-top:.5rem;'><div style='background:white;height:8px;border-radius:4px;overflow:hidden;'>
                                    <div style='background:{color};height:100%;width:{min(pct, 100):.0f}%;'></div>
                                </div></div>
                            </div>""", unsafe_allow_html=True)

                    st.markdown("---")
                    over_budget = comparison_df[comparison_df['Percentage'] > 100]
                    warning_budget = comparison_df[
                        (comparison_df['Percentage'] > 80) & (comparison_df['Percentage'] <= 100)
                    ]

                    if not over_budget.empty:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.error(f"⚠️ **{len(over_budget)} categories over budget!**")
                            for _, row in over_budget.iterrows():
                                st.caption(
                                    f"• **{row['Category']}**: {row['Percentage']:.0f}% used "
                                    f"(J${row['Actual']:,.0f} / J${row['Budget']:,.0f})"
                                )
                        with col2:
                            st.markdown("##### 📧 Email Alert")
                            recipient_email = st.text_input(
                                "Email Address", value=st.session_state.user['email'],
                                key="budget_alert_email", placeholder="your@email.com",
                            )
                            if st.button("📧 Send Alert", use_container_width=True, type="primary",
                                         key="send_budget_alert"):
                                if recipient_email:
                                    from utils import send_email_alert
                                    body_lines = [
                                        f"Dear {st.session_state.user['username']},\n",
                                        f"Budget Alert for {selected_month}:\n\nCategories Over Budget:\n",
                                    ]
                                    for _, row in over_budget.iterrows():
                                        body_lines.append(
                                            f"- {row['Category']}: J${row['Actual']:,.0f} / "
                                            f"J${row['Budget']:,.0f} ({row['Percentage']:.0f}%)"
                                        )
                                    if not warning_budget.empty:
                                        body_lines.append("\n\nCategories Approaching Limit:\n")
                                        for _, row in warning_budget.iterrows():
                                            body_lines.append(
                                                f"- {row['Category']}: J${row['Actual']:,.0f} / "
                                                f"J${row['Budget']:,.0f} ({row['Percentage']:.0f}%)"
                                            )
                                    body_lines.append(
                                        "\n\nPlease review your spending.\n\nBest regards,\nFinance Hub Team"
                                    )
                                    with st.spinner("Sending email..."):
                                        if send_email_alert(
                                            recipient_email,
                                            f"Budget Alert - {selected_month}",
                                            "\n".join(body_lines),
                                        ):
                                            st.success("✅ Email sent successfully!")
                                        else:
                                            st.error("❌ Failed to send email")
                                else:
                                    st.error("Please enter an email address")

                    elif not warning_budget.empty:
                        st.warning(f"⚡ **{len(warning_budget)} categories approaching limit**")
                        for _, row in warning_budget.iterrows():
                            st.caption(
                                f"• **{row['Category']}**: {row['Percentage']:.0f}% used "
                                f"(J${row['Remaining']:,.0f} remaining)"
                            )
                    else:
                        st.success("✅ **All categories within budget! Great job!**")
        else:
            st.info("📊 Upload transaction data in Spending Analysis to see your budget performance")

    st.markdown("</div>", unsafe_allow_html=True)

"""
pages/budget_planner.py
Tab 1: Interactive planner (income, expenses, multi-loan, what-ifs)
Tab 2: Budget vs Actual spending
Tab 3: Subscription Tracker (email-first, with recurring + manual)
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import get_user_preferences, save_user_preferences
from data_loader import load_all_user_data, clear_data_cache
from utils import get_spending_by_category, calculate_monthly_stats
from config import DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL
import json, calendar

# ── Plotly base theme ────────────────────────────────────────────────────
_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#7b7f94", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)"),
    margin=dict(t=40, b=20, l=10, r=10),
)

# ── Known subscription keywords ──────────────────────────────────────────
_KNOWN_SUBS = {
    "netflix":("Netflix","🎬 Streaming"), "spotify":("Spotify","🎵 Music"),
    "disney":("Disney+","🎬 Streaming"), "hulu":("Hulu","🎬 Streaming"),
    "apple":("Apple Services","📱 Tech"), "google":("Google Services","📱 Tech"),
    "amazon":("Amazon Prime","🛍 Shopping"), "youtube":("YouTube Premium","🎬 Streaming"),
    "microsoft":("Microsoft 365","💼 Productivity"), "adobe":("Adobe","🎨 Design"),
    "dropbox":("Dropbox","☁ Cloud"), "icloud":("iCloud","☁ Cloud"),
    "linkedin":("LinkedIn","💼 Productivity"), "zoom":("Zoom","💼 Productivity"),
    "github":("GitHub","💻 Dev"), "gym":("Gym","💪 Fitness"),
    "digicel":("Digicel","📱 Telecom"), "flow":("Flow","📡 Internet"),
    "canva":("Canva","🎨 Design"), "notion":("Notion","💼 Productivity"),
    "chatgpt":("ChatGPT Plus","🤖 AI"), "openai":("OpenAI","🤖 AI"),
    "vpn":("VPN","🔒 Security"), "norton":("Norton","🔒 Security"),
    "duolingo":("Duolingo","📚 Education"), "bumble":("Bumble","💑 Dating"),
    "tinder":("Tinder","💑 Dating"),
}

_PROVIDER_HINTS = {
    "gmail.com":   "Google Account → Security → App passwords",
    "yahoo.com":   "Yahoo Account Security → Generate app password",
    "ymail.com":   "Yahoo Account Security → Generate app password",
    "outlook.com": "Microsoft Account → Security → App passwords",
    "hotmail.com": "Microsoft Account → Security → App passwords",
    "live.com":    "Microsoft Account → Security → App passwords",
    "icloud.com":  "appleid.apple.com → Sign-In and Security → App-Specific Passwords",
    "me.com":      "appleid.apple.com → Sign-In and Security → App-Specific Passwords",
}

# ─────────────────────────────────────────────────────────────────────────
# Self-contained interactive planner HTML
# ─────────────────────────────────────────────────────────────────────────
_PLANNER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', sans-serif; background: #f8fafc; color: #1e293b; font-size: 14px; padding: 16px; }
  h2 { font-size: 1.1rem; font-weight: 700; color: #1e293b; margin-bottom: 12px; }
  h3 { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; margin-top: 20px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; }
  .card { background: #fff; border-radius: 12px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,.07); border-top: 3px solid var(--accent, #667eea); }
  .card .label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
  .card .value { font-size: 1.4rem; font-weight: 700; color: var(--accent, #667eea); }
  .card .sub   { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
  .card.green  { --accent: #10b981; } .card.red { --accent: #ef4444; } .card.blue { --accent: #3b82f6; } .card.orange { --accent: #f59e0b; }
  .section { background: #fff; border-radius: 14px; padding: 18px; box-shadow: 0 1px 4px rgba(0,0,0,.07); margin-bottom: 14px; }
  .row { display: grid; grid-template-columns: 1fr 140px 36px; gap: 8px; align-items: center; margin-bottom: 8px; }
  .row-loan { display: grid; grid-template-columns: 1fr 110px 90px 80px 36px; gap: 8px; align-items: center; margin-bottom: 8px; }
  .row-onetime { display: grid; grid-template-columns: 1fr 120px 140px 36px; gap: 8px; align-items: center; margin-bottom: 8px; }
  input[type=text], input[type=number], select { width: 100%; padding: 7px 10px; border: 1.5px solid #e2e8f0; border-radius: 8px; font-family: 'DM Sans', sans-serif; font-size: 13px; color: #1e293b; background: #f8fafc; outline: none; }
  input:focus, select:focus { border-color: #667eea; background: #fff; }
  .btn-add { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 8px; background: #667eea; color: #fff; border: none; cursor: pointer; font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 12px; }
  .btn-add:hover { opacity: .85; }
  .btn-del { width: 32px; height: 32px; border-radius: 8px; border: none; background: #fee2e2; color: #ef4444; cursor: pointer; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
  .btn-del:hover { background: #fecaca; }
  .progress-wrap { background: #e2e8f0; border-radius: 99px; height: 7px; margin-top: 4px; overflow: hidden; }
  .progress-fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg,#667eea,#764ba2); }
  .loan-status { background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 10px; }
  .loan-status .lname { font-weight: 600; font-size: 0.92rem; margin-bottom: 6px; }
  .loan-status .lrow { display: flex; justify-content: space-between; font-size: 0.8rem; color: #64748b; margin-bottom: 3px; }
  .loan-status .lrow span { font-weight: 600; color: #1e293b; }
  .whatif-toggle { background: #f1f5f9; border-radius: 8px; padding: 8px 12px; font-size: 0.8rem; color: #64748b; cursor: pointer; display: flex; align-items: center; justify-content: space-between; user-select: none; margin-bottom: 8px; }
  .whatif-body { display: none; padding: 10px 0 2px; }
  .whatif-body.open { display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #667eea; color: #fff; padding: 8px 10px; text-align: left; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .05em; }
  th:first-child { border-radius: 8px 0 0 0; } th:last-child { border-radius: 0 8px 0 0; }
  td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; }
  tr:last-child td { border-bottom: none; }
  tr:nth-child(even) td { background: #f8fafc; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.7rem; font-weight: 600; }
  .tag.green { background: #dcfce7; color: #166534; } .tag.red { background: #fee2e2; color: #991b1b; } .tag.yellow { background: #fef9c3; color: #854d0e; }
  .col-headers { display: grid; align-items: end; padding: 0 0 4px; font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; }
  .col-headers-loan { grid-template-columns: 1fr 110px 90px 80px 36px; gap: 8px; }
  .col-headers-row  { grid-template-columns: 1fr 140px 36px; gap: 8px; }
  .col-headers-onetime { grid-template-columns: 1fr 120px 140px 36px; gap: 8px; }
</style>
</head>
<body>
<h2>📊 Monthly Financial Planner</h2>
<div class="grid-4" style="margin-bottom:14px;">
  <div class="card green"><div class="label">Total Income</div><div class="value" id="sumIncome">J$0</div><div class="sub">all sources</div></div>
  <div class="card red"><div class="label">Total Expenses</div><div class="value" id="sumExpenses">J$0</div><div class="sub">bills + debt</div></div>
  <div class="card blue"><div class="label">Net Savings</div><div class="value" id="sumSavings">J$0</div><div class="sub">income – expenses</div></div>
  <div class="card orange"><div class="label">Savings Rate</div><div class="value" id="sumRate">0%</div><div class="sub">of income</div></div>
</div>
<div style="background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#64748b;margin-bottom:6px;"><span>Budget utilisation</span><span id="utilisationPct">0%</span></div>
  <div class="progress-wrap"><div class="progress-fill" id="utilisationBar" style="width:0%"></div></div>
</div>
<div class="section">
  <h2>💰 Income Sources</h2>
  <div class="col-headers col-headers-row"><span>Source</span><span>Monthly (J$)</span><span></span></div>
  <div id="incomeList"></div>
  <button class="btn-add" onclick="addIncome()">+ Add income</button>
</div>
<div class="section">
  <h2>💸 Monthly Expenses</h2>
  <div class="col-headers col-headers-row"><span>Expense</span><span>Monthly (J$)</span><span></span></div>
  <div id="expenseList"></div>
  <button class="btn-add" onclick="addExpense()">+ Add expense</button>
</div>
<div class="section">
  <h2>🏦 Loans & Debt</h2>
  <div class="col-headers col-headers-loan"><span>Loan name</span><span>Balance (J$)</span><span>Rate %/yr</span><span>Min pmt (J$)</span><span></span></div>
  <div id="loanList"></div>
  <button class="btn-add" onclick="addLoan()">+ Add loan</button>
</div>
<div class="section">
  <h2>⚡ One-Time Payments</h2>
  <p style="font-size:0.8rem;color:#94a3b8;margin-bottom:10px;">Apply a lump-sum toward any loan to see how it changes your payoff timeline.</p>
  <div class="col-headers col-headers-onetime"><span>Description</span><span>Amount (J$)</span><span>Apply to loan</span><span></span></div>
  <div id="onetimeList"></div>
  <button class="btn-add" onclick="addOnetime()">+ Add one-time payment</button>
</div>
<div class="section">
  <h2>🔮 What-If Scenarios</h2>
  <div class="whatif-toggle" onclick="toggleWhatif('wi1')"><span>📈 What if I increase my income?</span><span id="wi1arrow">▸</span></div>
  <div class="whatif-body" id="wi1"><div class="row"><label style="font-size:0.82rem;color:#475569;">Extra monthly income (J$)</label><input type="number" id="wiIncome" value="0" min="0" oninput="recalc()"/><span></span></div></div>
  <div class="whatif-toggle" onclick="toggleWhatif('wi2')"><span>✂️ What if I cut my expenses?</span><span id="wi2arrow">▸</span></div>
  <div class="whatif-body" id="wi2"><div class="row"><label style="font-size:0.82rem;color:#475569;">Monthly expense reduction (J$)</label><input type="number" id="wiExpense" value="0" min="0" oninput="recalc()"/><span></span></div></div>
  <div class="whatif-toggle" onclick="toggleWhatif('wi3')"><span>💳 What if I pay extra on a loan?</span><span id="wi3arrow">▸</span></div>
  <div class="whatif-body" id="wi3"><div class="row"><label style="font-size:0.82rem;color:#475569;">Extra monthly payment (J$)</label><input type="number" id="wiLoanExtra" value="0" min="0" oninput="recalc()"/><select id="wiLoanTarget" oninput="recalc()" style="max-width:160px;"><option value="">— pick loan —</option></select><span></span></div></div>
  <div id="whatifResults" style="margin-top:10px;"></div>
</div>
<div class="section"><h2>📅 Loan Payoff Analysis</h2><div id="loanPayoff"></div></div>
<div class="section">
  <h2>📋 Full Breakdown</h2>
  <table id="breakdownTable"><thead><tr><th>Item</th><th>Type</th><th>Monthly (J$)</th><th>% of Income</th><th>Status</th></tr></thead><tbody id="breakdownBody"></tbody></table>
</div>
<script>
let incomes=[{id:1,name:'Primary salary',amount:150000}];
let expenses=[{id:1,name:'Rent / mortgage',amount:40000},{id:2,name:'Groceries',amount:15000},{id:3,name:'Utilities',amount:8000}];
let loans=[{id:1,name:'Car loan',balance:800000,rate:12,min:18000}];
let onetimes=[];let uid=10;
function id(){return ++uid;}
function fmt(n){return 'J$'+Math.abs(n).toLocaleString('en-JM',{minimumFractionDigits:0,maximumFractionDigits:0});}
function pct(n,total){if(!total)return '0%';return (n/total*100).toFixed(1)+'%';}
function renderRow(container,obj,placeholder,onDelete){
  const d=document.createElement('div');d.className='row';
  d.innerHTML=`<input type="text" value="${obj.name}" placeholder="${placeholder}" data-bind="name"/><input type="number" value="${obj.amount}" min="0" data-bind="amount"/><button class="btn-del">×</button>`;
  d.querySelector('[data-bind=name]').addEventListener('input',e=>{obj.name=e.target.value;recalc();});
  d.querySelector('[data-bind=amount]').addEventListener('input',e=>{obj.amount=+e.target.value;recalc();});
  d.querySelector('.btn-del').addEventListener('click',onDelete);
  container.appendChild(d);
}
function renderLoanRow(container,loan,onDelete){
  const d=document.createElement('div');d.className='row-loan';
  d.innerHTML=`<input type="text" value="${loan.name}" placeholder="Loan name"/><input type="number" value="${loan.balance}" min="0"/><input type="number" value="${loan.rate}" min="0" max="100" step="0.1"/><input type="number" value="${loan.min}" min="0"/><button class="btn-del">×</button>`;
  const[nameI,balI,rateI,minI]=d.querySelectorAll('input');
  nameI.addEventListener('input',e=>{loan.name=e.target.value;recalc();});
  balI.addEventListener('input',e=>{loan.balance=+e.target.value;recalc();});
  rateI.addEventListener('input',e=>{loan.rate=+e.target.value;recalc();});
  minI.addEventListener('input',e=>{loan.min=+e.target.value;recalc();});
  d.querySelector('.btn-del').addEventListener('click',onDelete);
  container.appendChild(d);
}
function renderOnetimeRow(container,ot,onDelete){
  const d=document.createElement('div');d.className='row-onetime';
  const opts=loans.map(l=>`<option value="${l.id}" ${ot.loanId===l.id?'selected':''}>${l.name}</option>`).join('');
  d.innerHTML=`<input type="text" value="${ot.desc}" placeholder="Description"/><input type="number" value="${ot.amount}" min="0"/><select>${opts||'<option>No loans</option>'}</select><button class="btn-del">×</button>`;
  const[descI,amtI]=d.querySelectorAll('input');const sel=d.querySelector('select');
  descI.addEventListener('input',e=>{ot.desc=e.target.value;recalc();});
  amtI.addEventListener('input',e=>{ot.amount=+e.target.value;recalc();});
  sel.addEventListener('change',e=>{ot.loanId=+e.target.value;recalc();});
  d.querySelector('.btn-del').addEventListener('click',onDelete);
  container.appendChild(d);
}
function addIncome(){const o={id:id(),name:'',amount:0};incomes.push(o);const c=document.getElementById('incomeList');renderRow(c,o,'e.g. Freelance',()=>{incomes=incomes.filter(x=>x!==o);renderAll();recalc();});recalc();}
function addExpense(){const o={id:id(),name:'',amount:0};expenses.push(o);const c=document.getElementById('expenseList');renderRow(c,o,'e.g. Internet',()=>{expenses=expenses.filter(x=>x!==o);renderAll();recalc();});recalc();}
function addLoan(){const o={id:id(),name:'',balance:0,rate:10,min:0};loans.push(o);renderAll();recalc();}
function addOnetime(){const o={id:id(),desc:'',amount:0,loanId:loans[0]?.id||null};onetimes.push(o);renderAll();recalc();}
function renderAll(){
  const ic=document.getElementById('incomeList');ic.innerHTML='';
  incomes.forEach(o=>renderRow(ic,o,'e.g. Salary',()=>{incomes=incomes.filter(x=>x!==o);renderAll();recalc();}));
  const ec=document.getElementById('expenseList');ec.innerHTML='';
  expenses.forEach(o=>renderRow(ec,o,'e.g. Phone bill',()=>{expenses=expenses.filter(x=>x!==o);renderAll();recalc();}));
  const lc=document.getElementById('loanList');lc.innerHTML='';
  loans.forEach(l=>renderLoanRow(lc,l,()=>{loans=loans.filter(x=>x!==l);renderAll();recalc();}));
  const oc=document.getElementById('onetimeList');oc.innerHTML='';
  onetimes.forEach(o=>renderOnetimeRow(oc,o,()=>{onetimes=onetimes.filter(x=>x!==o);renderAll();recalc();}));
  const sel=document.getElementById('wiLoanTarget');const prev=sel.value;
  sel.innerHTML='<option value="">— pick loan —</option>'+loans.map(l=>`<option value="${l.id}" ${prev==l.id?'selected':''}>${l.name}</option>`).join('');
}
function monthsToPayoff(balance,rate,monthly){if(monthly<=0||balance<=0)return Infinity;const r=rate/100/12;if(r===0)return Math.ceil(balance/monthly);let bal=balance,months=0;while(bal>0&&months<1200){const interest=bal*r;bal-=(monthly-interest);months++;if(monthly<=interest)return Infinity;}return months;}
function totalInterest(balance,rate,monthly){if(monthly<=0||balance<=0)return 0;const r=rate/100/12;let bal=balance,total=0,months=0;while(bal>0&&months<1200){const interest=bal*r;if(monthly<=interest)return Infinity;total+=interest;bal-=(monthly-interest);months++;}return total;}
function recalc(){
  const wiInc=+document.getElementById('wiIncome').value||0;
  const wiExp=+document.getElementById('wiExpense').value||0;
  const wiLEx=+document.getElementById('wiLoanExtra').value||0;
  const wiLTgt=+document.getElementById('wiLoanTarget').value||0;
  const totalIncome=incomes.reduce((s,x)=>s+x.amount,0)+wiInc;
  const totalExpenses=expenses.reduce((s,x)=>s+x.amount,0)-wiExp;
  const totalDebt=loans.reduce((s,l)=>s+l.min,0);
  const totalOut=totalExpenses+totalDebt;
  const netSavings=totalIncome-totalOut;
  const savingsRate=totalIncome?netSavings/totalIncome*100:0;
  const utilisation=totalIncome?Math.min(totalOut/totalIncome*100,100):0;
  document.getElementById('sumIncome').textContent=fmt(totalIncome);
  document.getElementById('sumExpenses').textContent=fmt(totalOut);
  document.getElementById('sumSavings').textContent=fmt(netSavings);
  document.getElementById('sumRate').textContent=savingsRate.toFixed(1)+'%';
  document.getElementById('utilisationPct').textContent=utilisation.toFixed(1)+'%';
  document.getElementById('utilisationBar').style.width=utilisation+'%';
  document.querySelector('.card.blue .value').style.color=netSavings>=0?'#3b82f6':'#ef4444';
  const lpDiv=document.getElementById('loanPayoff');
  if(!loans.length){lpDiv.innerHTML='<p style="color:#94a3b8;font-size:0.82rem;">No loans added.</p>';}
  else{let html='';loans.forEach(l=>{const extra=(wiLTgt===l.id)?wiLEx:0;const oneTimePmt=onetimes.filter(o=>o.loanId===l.id).reduce((s,o)=>s+o.amount,0);const effectiveBal=Math.max(0,l.balance-oneTimePmt);const monthly=l.min+extra;const months=monthsToPayoff(effectiveBal,l.rate,monthly);const interest=totalInterest(effectiveBal,l.rate,monthly);const monthsBase=monthsToPayoff(l.balance,l.rate,l.min);const saved=monthsBase===Infinity?0:Math.max(0,monthsBase-months);const mLabel=months===Infinity?'∞ (increase payment!)':`${Math.floor(months/12)}y ${months%12}m`;const intLabel=interest===Infinity?'∞':fmt(interest);const progress=l.balance>0?Math.min(100,oneTimePmt/l.balance*100):0;html+=`<div class="loan-status"><div class="lname">🏦 ${l.name||'Unnamed loan'}</div><div class="lrow">Balance remaining <span>${fmt(effectiveBal)}</span></div><div class="lrow">Monthly payment <span>${fmt(monthly)}</span></div><div class="lrow">Interest rate <span>${l.rate}% / yr</span></div><div class="lrow">Payoff timeline <span>${mLabel}</span></div><div class="lrow">Total interest <span>${intLabel}</span></div>${saved>0?`<div class="lrow" style="color:#10b981;">Months saved <span style="color:#10b981">${saved}</span></div>`:''}</div>`;});lpDiv.innerHTML=html;}
  const wiDiv=document.getElementById('whatifResults');
  const wiActive=wiInc||wiExp||(wiLEx&&wiLTgt);
  if(wiActive){const baseSav=(totalIncome-wiInc)-((totalExpenses+wiExp)+totalDebt);const delta=netSavings-baseSav;const yr=netSavings*12;wiDiv.innerHTML=`<div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:10px;padding:12px;"><div style="font-weight:700;color:#166534;margin-bottom:6px;">📈 What-if impact</div><div style="font-size:0.82rem;color:#14532d;">Monthly savings change: <strong>${delta>=0?'+':''}${fmt(delta)}</strong><br>New monthly savings: <strong>${fmt(netSavings)}</strong><br>Projected yearly savings: <strong>${fmt(yr)}</strong></div></div>`;}
  else{wiDiv.innerHTML='';}
  const tbody=document.getElementById('breakdownBody');tbody.innerHTML='';
  const addRow=(name,type,amount,ofIncome,status)=>{const tr=document.createElement('tr');const tagClass=status==='Income'?'green':status==='OK'?'green':status==='Watch'?'yellow':'red';tr.innerHTML=`<td>${name}</td><td>${type}</td><td>${fmt(amount)}</td><td>${ofIncome}</td><td><span class="tag ${tagClass}">${status}</span></td>`;tbody.appendChild(tr);};
  incomes.forEach(i=>addRow(i.name||'Income','Income',i.amount,pct(i.amount,totalIncome),'Income'));
  expenses.forEach(e=>{const p=totalIncome?e.amount/totalIncome*100:0;const s=p>40?'High':p>20?'Watch':'OK';addRow(e.name||'Expense','Expense',e.amount,pct(e.amount,totalIncome),s);});
  loans.forEach(l=>{const p=totalIncome?l.min/totalIncome*100:0;const s=p>30?'High':p>15?'Watch':'OK';addRow(l.name||'Loan','Debt pmt',l.min,pct(l.min,totalIncome),s);});
  onetimes.forEach(o=>addRow(o.desc||'One-time','One-time',o.amount,pct(o.amount,totalIncome),'Watch'));
  const tr=document.createElement('tr');tr.style.fontWeight='700';tr.innerHTML=`<td>NET SAVINGS</td><td>—</td><td style="color:${netSavings>=0?'#10b981':'#ef4444'}">${fmt(netSavings)}</td><td>${savingsRate.toFixed(1)}%</td><td><span class="tag ${netSavings>=0?'green':'red'}">${netSavings>=0?'Positive':'Deficit'}</span></td>`;tbody.appendChild(tr);
}
function toggleWhatif(id){const body=document.getElementById(id);const arrow=document.getElementById(id+'arrow');const open=body.classList.toggle('open');arrow.textContent=open?'▾':'▸';}
renderAll();recalc();
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────
# Subscription helpers
# ─────────────────────────────────────────────────────────────────────────

def _detect_recurring(data: pd.DataFrame, min_occ: int = 2) -> pd.DataFrame:
    if data.empty or "Description" not in data.columns:
        return pd.DataFrame()
    debit = data[data["Category"] == "Debit"].copy() if "Category" in data.columns else data.copy()
    if debit.empty:
        return pd.DataFrame()
    debit["desc_clean"] = debit["Description"].str.lower().str.strip()
    g = debit.groupby("desc_clean").agg(
        count=("Amount","count"), avg=("Amount","mean"),
        total=("Amount","sum"), last=("Date","max"), first=("Date","min"),
    ).reset_index()
    rec = g[g["count"] >= min_occ].sort_values("total", ascending=False).copy()

    def _label(desc):
        for kw, (name, cat) in _KNOWN_SUBS.items():
            if kw in desc: return name, cat
        return desc[:40].title(), "📦 Other"

    rec[["label","cat"]] = rec["desc_clean"].apply(lambda d: pd.Series(_label(d)))
    rec["months"] = ((rec["last"] - rec["first"]).dt.days / 30).clip(lower=1).round(1)
    return rec.reset_index(drop=True)


def _render_email_sync_compact(user_id):
    """Compact email sync panel for inside budget planner."""
    try:
        from database import (
            get_all_email_accounts, add_email_account,
            get_email_sync_settings, save_email_sync_settings,
            delete_all_email_transactions,
        )
        from email_scanner import sync_email_account, connect_email
        ok = True
    except ImportError:
        ok = False

    if not ok:
        st.info("Add email_scanner.py to enable email sync.")
        return

    accounts = []
    try: accounts = get_all_email_accounts(user_id)
    except Exception: pass
    if not accounts:
        try:
            cfg = get_email_sync_settings(user_id)
            if cfg and cfg.get("gmail_address"):
                accounts = [{"email_address": cfg["gmail_address"],
                             "app_password": cfg["app_password"],
                             "sync_days": cfg.get("sync_days", 90),
                             "last_sync": cfg.get("last_sync")}]
        except Exception: pass

    if accounts:
        for acct in accounts:
            addr     = acct.get("email_address") or acct.get("gmail_address","")
            last_s   = acct.get("last_sync")
            last_str = last_s.strftime("%d %b %Y %I:%M %p") if last_s else "Never"
            ci, cb = st.columns([5, 1.5])
            with ci:
                st.markdown(f"""
                    <div style="background:rgba(31,207,138,.06);border:1px solid rgba(31,207,138,.18);
                                border-radius:8px;padding:.5rem .9rem;">
                        <span style="color:#1fcf8a;font-weight:600;font-size:.85rem;">✓ {addr}</span>
                        <span style="color:#7b7f94;font-size:.73rem;margin-left:.6rem;">
                            Last sync: {last_str}</span>
                    </div>""", unsafe_allow_html=True)
            with cb:
                if st.button("🔄 Sync now", key=f"bp_sync_{addr}",
                             use_container_width=True, type="primary"):
                    with st.spinner("Scanning…"):
                        n, err = sync_email_account(user_id, addr,
                                                    acct.get("app_password",""),
                                                    acct.get("sync_days", 90))
                    if err: st.error(f"❌ {err}")
                    else:
                        clear_data_cache()
                        st.success(f"✅ {n} new transactions!" if n else "Up to date.")
                        st.rerun()

        if st.button("🗑 Clear email transactions", key="bp_clear_email",
                     use_container_width=False):
            delete_all_email_transactions(user_id)
            clear_data_cache()
            st.rerun()
    else:
        st.info("No email account connected.")

    with st.expander("➕ Connect email account", expanded=not bool(accounts)):
        new_addr = st.text_input("Email address",
                                  placeholder="yourname@gmail.com / yahoo.com / outlook.com",
                                  key="bp_new_addr")
        if new_addr and "@" in new_addr:
            domain = new_addr.split("@")[-1].lower()
            hint   = _PROVIDER_HINTS.get(domain, "Check your provider for App Password setup")
            st.caption(f"💡 {hint}")
        new_pwd  = st.text_input("App Password", type="password",
                                  placeholder="16-character app password",
                                  key="bp_new_pwd")
        new_days = st.slider("Scan last N days", 7, 365, 90, 7, key="bp_new_days")
        if st.button("🔗 Connect", type="primary", key="bp_connect"):
            if not new_addr or "@" not in new_addr:
                st.error("Enter a valid email address.")
            elif len(new_pwd.replace(" ","")) < 16:
                st.error("App password should be 16 characters.")
            else:
                with st.spinner("Testing…"):
                    test = connect_email(new_addr, new_pwd)
                if not test:
                    st.error("❌ Could not connect. Check your app password and IMAP settings.")
                else:
                    test.logout()
                    saved = False
                    try: saved = add_email_account(user_id, new_addr, new_pwd, new_days)
                    except Exception: pass
                    if not saved:
                        try: saved = save_email_sync_settings(user_id, new_addr, new_pwd, new_days)
                        except Exception: pass
                    if saved: st.success(f"✅ {new_addr} connected!"); st.rerun()
                    else: st.error("Failed to save.")


def _render_subscription_tab(user_id):
    """Full subscription tracker rendered as a budget planner tab."""
    data = load_all_user_data(user_id)

    # ── 1. Email sync panel ───────────────────────────────────────────
    st.markdown("""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:0 0 .75rem;">
            📧 Email Sync
        </p>""", unsafe_allow_html=True)
    st.caption("Connect your email to auto-import bank alert transactions.")
    _render_email_sync_compact(user_id)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── 2. Email-flagged subscriptions (primary source) ───────────────
    st.markdown("""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:0 0 .4rem;">
            📧 Subscriptions Detected via Email
        </p>
        <p style="font-size:.82rem;color:#7b7f94;margin:0 0 .75rem;">
            These were flagged directly by the email scanner — the most reliable source.
        </p>""", unsafe_allow_html=True)

    email_sub_rows = []
    if not data.empty and "is_subscription" in data.columns and "source" in data.columns:
        email_subs = data[(data["source"] == "email") & (data["is_subscription"] == 1)].copy()
        if not email_subs.empty:
            email_subs["desc_clean"] = email_subs["Description"].str.lower().str.strip()
            grouped = email_subs.groupby("desc_clean").agg(
                count=("Amount","count"), avg=("Amount","mean"),
                total=("Amount","sum"), last=("Date","max")
            ).reset_index()
            for _, r in grouped.iterrows():
                label = r["desc_clean"]
                for kw, (name, _) in _KNOWN_SUBS.items():
                    if kw in label: label = name; break
                else:
                    label = r["desc_clean"][:40].title()
                email_sub_rows.append({
                    "label": label,
                    "avg":   r["avg"],
                    "count": int(r["count"]),
                    "last":  r["last"],
                })

    if email_sub_rows:
        for row in email_sub_rows:
            c1, c2 = st.columns([4, 2])
            with c1:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-left:3px solid #1fcf8a;border-radius:10px;
                                padding:.65rem 1rem;margin-bottom:.4rem;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.9rem;">
                            {row['label']}
                            <span style="background:rgba(31,207,138,.15);color:#1fcf8a;
                                         font-size:.65rem;font-weight:700;padding:.15rem .45rem;
                                         border-radius:99px;margin-left:.4rem;">📧 from email</span>
                        </div>
                        <div style="font-size:.73rem;color:#7b7f94;margin-top:.15rem;">
                            {row['count']} charge{'s' if row['count']!=1 else ''} detected  •
                            Last: {row['last'].strftime('%d %b %Y') if pd.notna(row['last']) else 'N/A'}
                        </div>
                    </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div style="text-align:right;padding:.65rem 0;">
                        <div style="font-weight:700;color:#f04e5e;font-size:1rem;">
                            J${row['avg']:,.0f}<span style='font-size:.7rem;color:#7b7f94;'>/mo</span>
                        </div>
                        <div style="font-size:.72rem;color:#7b7f94;">J${row['avg']*12:,.0f}/yr</div>
                    </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background:#13151f;border:1px dashed rgba(255,255,255,.1);
                        border-radius:10px;padding:1rem;text-align:center;margin-bottom:.5rem;">
                <div style="color:#7b7f94;font-size:.85rem;">
                    No email-flagged subscriptions yet — connect your email and sync above.</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── 3. Recurring charges from ALL transaction data ────────────────
    st.markdown("""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:0 0 .4rem;">
            🔁 All Recurring Charges
        </p>
        <p style="font-size:.82rem;color:#7b7f94;margin:0 0 .75rem;">
            Merchants appearing 2+ times across your bank files and email data combined.
        </p>""", unsafe_allow_html=True)

    if data.empty:
        st.info("Upload bank statements or sync email to detect recurring charges.")
        recurring = pd.DataFrame()
    else:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        recurring    = _detect_recurring(data)

    if not recurring.empty:
        total_monthly = recurring["avg"].sum()

        c1, c2, c3 = st.columns(3)
        for col, lbl, val, clr in [
            (c1, "Recurring detected",  len(recurring),              "#f5a623"),
            (c2, "Est. monthly cost",   f"J${total_monthly:,.0f}",   "#f04e5e"),
            (c3, "Est. annual cost",    f"J${total_monthly*12:,.0f}","#3d9df6"),
        ]:
            with col:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-left:3px solid {clr};border-radius:10px;
                                padding:.85rem 1rem;text-align:center;margin-bottom:.75rem;">
                        <div style="font-size:.65rem;font-weight:600;text-transform:uppercase;
                                    letter-spacing:.07em;color:#7b7f94;margin-bottom:.3rem;">{lbl}</div>
                        <div style="font-size:1.4rem;font-weight:700;color:{clr};">{val}</div>
                    </div>""", unsafe_allow_html=True)

        for idx, (_, row) in enumerate(recurring.iterrows()):
            source_badge = ""
            if not data.empty and "source" in data.columns:
                src = data[data["Description"].str.lower().str.strip() == row["desc_clean"]]["source"].value_counts()
                if src.get("email", 0) > 0 and src.get("file", 0) == 0:
                    source_badge = '<span style="background:rgba(61,157,246,.2);color:#3d9df6;font-size:.65rem;font-weight:700;padding:.15rem .45rem;border-radius:99px;margin-left:.35rem;">📧 email only</span>'
                elif src.get("file", 0) > 0 and src.get("email", 0) == 0:
                    source_badge = '<span style="background:rgba(245,166,35,.2);color:#f5a623;font-size:.65rem;font-weight:700;padding:.15rem .45rem;border-radius:99px;margin-left:.35rem;">📄 file only</span>'

            ci, cc, ca = st.columns([4, 2, 1.5])
            with ci:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.06);
                                border-radius:10px;padding:.6rem .9rem;margin-bottom:.35rem;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.88rem;">
                            {row['cat'].split(' ')[0]} {row['label']}{source_badge}</div>
                        <div style="font-size:.72rem;color:#7b7f94;margin-top:.12rem;">
                            {int(row['count'])} charges  •  over {row['months']:.0f} months  •
                            Last: {row['last'].strftime('%d %b %Y') if pd.notna(row['last']) else 'N/A'}
                        </div>
                    </div>""", unsafe_allow_html=True)
            with cc:
                st.markdown(f"""
                    <div style="text-align:right;padding:.6rem 0;">
                        <div style="font-weight:700;color:#f04e5e;font-size:.95rem;">
                            J${row['avg']:,.0f}<span style='font-size:.68rem;color:#7b7f94;'>/mo</span></div>
                        <div style="font-size:.7rem;color:#7b7f94;">J${row['avg']*12:,.0f}/yr</div>
                    </div>""", unsafe_allow_html=True)
            with ca:
                action = st.selectbox(
                    "Action", ["✅ Keep", "❌ Cancel", "🤔 Review"],
                    key=f"bp_sub_{idx}", label_visibility="collapsed",
                )
                if action == "❌ Cancel":
                    st.markdown(
                        f"<div style='font-size:.7rem;color:#1fcf8a;'>Saves J${row['avg']*12:,.0f}/yr</div>",
                        unsafe_allow_html=True)

        # Savings banner
        to_cancel = [
            row for idx2, (_, row) in enumerate(recurring.iterrows())
            if st.session_state.get(f"bp_sub_{idx2}", "✅ Keep") == "❌ Cancel"
        ]
        if to_cancel:
            ms = sum(r["avg"] for r in to_cancel)
            st.markdown(f"""
                <div style="background:rgba(31,207,138,.10);border:1px solid rgba(31,207,138,.25);
                            border-radius:12px;padding:1rem 1.5rem;margin:.75rem 0;">
                    <div style="font-weight:700;color:#1fcf8a;margin-bottom:.25rem;">
                        💰 Cancel {len(to_cancel)} charge(s) and free up:</div>
                    <div style="font-size:1.35rem;font-weight:700;color:#e8eaf0;">
                        J${ms:,.0f}/month  ·  J${ms*12:,.0f}/year</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── 4. Manual subscriptions ───────────────────────────────────────
    st.markdown("""
        <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                  font-weight:600;color:#e8eaf0;margin:0 0 .4rem;">
            ➕ Manual Subscriptions
        </p>
        <p style="font-size:.82rem;color:#7b7f94;margin:0 0 .75rem;">
            Annual plans, cash payments, or anything not in your bank data.
        </p>""", unsafe_allow_html=True)

    prefs      = get_user_preferences(user_id)
    raw_manual = {}
    if prefs and prefs.get("category_keywords"):
        try: raw_manual = json.loads(prefs["category_keywords"]).get("__subscriptions__", {})
        except Exception: pass
    if "manual_subs" not in st.session_state:
        st.session_state.manual_subs = raw_manual or {}
    manual_subs = st.session_state.manual_subs

    with st.expander("+ Add a subscription", expanded=len(manual_subs) == 0):
        nc1, nc2, nc3 = st.columns(3)
        with nc1: new_name   = st.text_input("Name", key="bp_new_sub_name", placeholder="e.g. Gym membership")
        with nc2: new_amount = st.number_input("Monthly (J$)", min_value=0, step=100, key="bp_new_sub_amt")
        with nc3: new_cat    = st.selectbox("Category", [
            "🎬 Streaming","🎵 Music","💼 Productivity","💪 Fitness",
            "📱 Telecom","☁ Cloud","🔒 Security","🎨 Design",
            "📚 Education","🤖 AI","💑 Dating","📦 Other",
        ], key="bp_new_sub_cat")
        if st.button("✅ Add", type="primary", key="bp_add_sub"):
            if new_name:
                manual_subs[new_name] = {"amount": new_amount, "category": new_cat}
                st.session_state.manual_subs = manual_subs
                st.success(f"Added {new_name}!")
                st.rerun()

    if manual_subs:
        for sub_name, sub_data in list(manual_subs.items()):
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
            with c1:
                st.markdown(f"""
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-left:3px solid #7c6bf6;border-radius:10px;
                                padding:.6rem .9rem;margin-bottom:.35rem;">
                        <div style="font-weight:600;color:#e8eaf0;font-size:.88rem;">{sub_name}</div>
                        <div style="font-size:.7rem;color:#7b7f94;">{sub_data.get('category','')}</div>
                    </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='padding-top:.5rem;font-weight:700;color:#f04e5e;'>"
                            f"J${sub_data.get('amount',0):,.0f}/mo</div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div style='padding-top:.5rem;font-size:.8rem;color:#7b7f94;'>"
                            f"J${sub_data.get('amount',0)*12:,.0f}/yr</div>", unsafe_allow_html=True)
            with c4:
                if st.button("🗑", key=f"bp_del_{sub_name}"):
                    del manual_subs[sub_name]
                    st.session_state.manual_subs = manual_subs
                    st.rerun()

        manual_total = sum(v.get("amount", 0) for v in manual_subs.values())
        c_tot, c_save = st.columns([3, 1])
        with c_tot:
            st.markdown(f"""
                <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                            border-radius:10px;padding:.8rem 1rem;margin:.25rem 0;
                            display:flex;justify-content:space-between;">
                    <span style="color:#7b7f94;font-size:.85rem;">{len(manual_subs)} manual subs</span>
                    <span style="font-weight:700;color:#f04e5e;">
                        J${manual_total:,.0f}/mo · J${manual_total*12:,.0f}/yr</span>
                </div>""", unsafe_allow_html=True)
        with c_save:
            if st.button("💾 Save", type="primary", use_container_width=True, key="bp_save_subs"):
                ck = {}
                if prefs and prefs.get("category_keywords"):
                    try: ck = json.loads(prefs["category_keywords"])
                    except Exception: pass
                if not ck:
                    from config import DEFAULT_CATEGORY_MAPPING
                    ck = DEFAULT_CATEGORY_MAPPING.copy()
                ck["__subscriptions__"] = manual_subs
                budgets = json.loads(prefs["monthly_budgets"]) if prefs and prefs.get("monthly_budgets") else {}
                goal    = prefs.get("savings_goal", 5000) if prefs else 5000
                if save_user_preferences(user_id, ck, budgets, goal):
                    st.success("Saved!")

    # ── 5. Cost breakdown chart ───────────────────────────────────────
    all_subs = []
    if email_sub_rows:
        for row in email_sub_rows:
            all_subs.append({"Name": row["label"], "Monthly": row["avg"], "Source": "Email"})
    if not recurring.empty:
        for _, r in recurring.iterrows():
            # avoid duplicating email-flagged ones
            if not any(s["Name"].lower() == r["label"].lower() for s in all_subs):
                all_subs.append({"Name": r["label"], "Monthly": r["avg"], "Source": "Bank"})
    for name, d in manual_subs.items():
        all_subs.append({"Name": name, "Monthly": d.get("amount", 0), "Source": "Manual"})

    if all_subs:
        df_subs = pd.DataFrame(all_subs)
        df_subs = df_subs[df_subs["Monthly"] > 0]
        if not df_subs.empty:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            st.markdown("""
                <p style="font-family:'Playfair Display',serif;font-size:1.1rem;
                          font-weight:600;color:#e8eaf0;margin:0 0 .75rem;">
                    📊 Total Subscription Cost
                </p>""", unsafe_allow_html=True)
            ca, cb = st.columns(2)
            with ca:
                fig = px.pie(df_subs, values="Monthly", names="Name",
                             hole=0.5, color="Source",
                             color_discrete_map={"Email":"#1fcf8a","Bank":"#f5a623","Manual":"#7c6bf6"},
                             title="Monthly cost by subscription")
                fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=10)
                fig.update_layout(height=320, showlegend=True, **_PLOTLY)
                st.plotly_chart(fig, use_container_width=True)
            with cb:
                grand = df_subs["Monthly"].sum()
                st.markdown(f"""
                    <div style="background:rgba(240,78,94,.08);border:1px solid rgba(240,78,94,.2);
                                border-radius:12px;padding:1.5rem;text-align:center;margin-top:1rem;">
                        <div style="font-size:.7rem;font-weight:600;letter-spacing:.07em;
                                    text-transform:uppercase;color:#7b7f94;margin-bottom:.5rem;">
                            Total monthly subscription spend</div>
                        <div style="font-size:2rem;font-weight:700;color:#f04e5e;margin-bottom:.25rem;">
                            J${grand:,.0f}</div>
                        <div style="font-size:.85rem;color:#7b7f94;">
                            J${grand*12:,.0f} per year</div>
                    </div>
                    <div style="background:#13151f;border:1px solid rgba(255,255,255,.07);
                                border-radius:10px;padding:.75rem;margin-top:.75rem;">
                        {"".join(f"<div style='display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:.25rem;'><span style='color:#7b7f94;'>{'📧' if r.Source=='Email' else '📄' if r.Source=='Bank' else '✏️'} {r.Name[:30]}</span><span style='color:#e8eaf0;font-weight:600;'>J${r.Monthly:,.0f}/mo</span></div>" for _, r in df_subs.sort_values('Monthly',ascending=False).head(8).iterrows())}
                    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────

def budget_planner_page():
    user_id = st.session_state.user["id"]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("### 💰 Budget Planner")
    with col2:
        if st.button("💎 Possible Savings", use_container_width=True, type="secondary"):
            st.session_state.selected_sub_feature = "possible_savings"
            st.rerun()
    with col3:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.session_state.selected_sub_feature = None
            st.rerun()

    st.markdown("---")

    # Open on Subscriptions tab if routed here via the dashboard subscriptions button
    default_tab = st.session_state.pop("selected_sub_feature", None)

    tab1, tab2, tab3 = st.tabs([
        "🧮 Interactive Planner",
        "📊 Budget vs Actual",
        "🔄 Subscriptions",
    ])

    # ── TAB 1 ────────────────────────────────────────────────────────
    with tab1:
        st.caption(
            "Edit every field live — add income sources, expenses, and loans. "
            "One-time payments reduce whichever loan you choose."
        )
        components.html(_PLANNER_HTML, height=2600, scrolling=True)

    # ── TAB 2 ────────────────────────────────────────────────────────
    with tab2:
        prefs = get_user_preferences(user_id)
        current_budgets = json.loads(prefs["monthly_budgets"]) if prefs and prefs.get("monthly_budgets") else DEFAULT_BUDGETS.copy()
        current_savings_goal = prefs.get("savings_goal", DEFAULT_SAVINGS_GOAL) if prefs else DEFAULT_SAVINGS_GOAL
        data = load_all_user_data(user_id)

        st.markdown("#### 🎯 Set Your Monthly Budgets")
        st.info("💡 Set realistic spending limits for each category.")

        categories  = [c for c in current_budgets if c not in ["Income","Other"]]
        mid         = len(categories) // 2
        new_budgets = current_budgets.copy()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 🏷️ Category Budgets")
            for cat in categories[:mid]:
                new_budgets[cat] = st.number_input(cat, min_value=0,
                    value=int(current_budgets[cat]), step=500, key=f"budget_{cat}")
        with c2:
            st.markdown("##### 🏷️ Category Budgets")
            for cat in categories[mid:]:
                new_budgets[cat] = st.number_input(cat, min_value=0,
                    value=int(current_budgets[cat]), step=500, key=f"budget_{cat}")

        st.markdown("---")
        c1, c2, c3 = st.columns([2,1,1])
        with c1:
            st.markdown("##### 💎 Monthly Savings Goal")
            new_savings_goal = st.number_input(
                "Target amount to save each month", min_value=0,
                value=int(current_savings_goal), step=500, key="savings_goal_input")
        with c2:
            total_budget = sum(new_budgets.values())
            st.metric("Monthly Limit", f"J${total_budget:,.0f}")
        with c3:
            st.metric("Needed Income", f"J${total_budget + new_savings_goal:,.0f}")

        st.markdown("---")
        b1, b2, _ = st.columns([1,1,2])
        with b1:
            if st.button("💾 Save Budgets", use_container_width=True, type="primary"):
                kw = json.loads(prefs["category_keywords"]) if prefs and prefs.get("category_keywords") else {}
                if not kw:
                    from config import DEFAULT_CATEGORY_MAPPING; kw = DEFAULT_CATEGORY_MAPPING.copy()
                if save_user_preferences(user_id, kw, new_budgets, new_savings_goal):
                    st.success("✅ Saved!"); st.rerun()
                else: st.error("❌ Failed to save")
        with b2:
            if st.button("🔄 Reset Defaults", use_container_width=True):
                kw = json.loads(prefs["category_keywords"]) if prefs and prefs.get("category_keywords") else {}
                if not kw:
                    from config import DEFAULT_CATEGORY_MAPPING; kw = DEFAULT_CATEGORY_MAPPING.copy()
                if save_user_preferences(user_id, kw, DEFAULT_BUDGETS, DEFAULT_SAVINGS_GOAL):
                    st.success("✅ Reset!"); st.rerun()

        if not data.empty and "YearMonth" in data.columns:
            st.markdown("---")
            st.markdown("#### 📈 Budget Performance")
            avail = sorted(data["YearMonth"].unique(), reverse=True)
            if avail:
                sm_col, _ = st.columns([1,3])
                with sm_col:
                    sel_month = st.selectbox("Select Month", avail, key="perf_month")

                month_stats   = calculate_monthly_stats(data, sel_month)
                month_summary = get_spending_by_category(data, sel_month)

                if not month_summary.empty:
                    cmp_data = []
                    for cat in new_budgets:
                        if cat in ["Income","Other"]: continue
                        budget = new_budgets[cat]
                        actual = month_summary[month_summary["Spending Category"]==cat]["Amount"].sum()
                        cmp_data.append({"Category":cat,"Budget":budget,"Actual":actual,
                                         "Remaining":budget-actual,
                                         "Percentage":(actual/budget*100) if budget>0 else 0})
                    cmp_df = pd.DataFrame(cmp_data)

                    m1,m2,m3,m4 = st.columns(4)
                    with m1: st.metric("Total Budget",  f"J${total_budget:,.0f}")
                    with m2:
                        st.metric("Total Spent", f"J${month_stats['spending']:,.0f}",
                                  delta=f"{month_stats['spending']-total_budget:,.0f}"
                                  if month_stats['spending']>total_budget else None,
                                  delta_color="inverse")
                    with m3:
                        remaining = total_budget - month_stats["spending"]
                        st.metric("Remaining", f"J${remaining:,.0f}",
                                  delta=f"{remaining/total_budget*100:.0f}%" if total_budget else None)
                    with m4:
                        st.metric("Savings", f"J${month_stats['savings']:,.0f}",
                                  delta=f"{month_stats['savings']-new_savings_goal:,.0f}",
                                  delta_color="normal")

                    st.markdown("---")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Budget", x=cmp_df["Category"], y=cmp_df["Budget"],
                                         marker_color="#3b82f6",
                                         text=cmp_df["Budget"].map(lambda v:f"J${v:,.0f}"),
                                         textposition="outside"))
                    fig.add_trace(go.Bar(name="Actual", x=cmp_df["Category"], y=cmp_df["Actual"],
                                         marker_color=cmp_df["Percentage"].map(
                                             lambda x: "#ef4444" if x>100 else "#10b981"),
                                         text=cmp_df["Actual"].map(lambda v:f"J${v:,.0f}"),
                                         textposition="outside"))
                    _base = {k:v for k,v in _PLOTLY.items() if k!="legend"}
                    fig.update_layout(barmode="group", height=380, xaxis_tickangle=-35,
                                      legend=dict(orientation="h",y=1.06,x=1,xanchor="right"),
                                      **_base)
                    st.plotly_chart(fig, use_container_width=True)

                    for _, row in cmp_df.iterrows():
                        pct = row["Percentage"]
                        if pct>100:   status,clr,bg = "🔴 OVER BUDGET","#ef4444","#fee2e2"
                        elif pct>80:  status,clr,bg = "🟡 WARNING","#f59e0b","#fef3c7"
                        else:         status,clr,bg = "🟢 ON TRACK","#10b981","#d1fae5"
                        st.markdown(f"""
                            <div style='background:{bg};padding:.85rem 1rem;border-radius:8px;
                                        margin-bottom:.4rem;border-left:4px solid {clr};'>
                                <div style='display:flex;justify-content:space-between;align-items:center;'>
                                    <div>
                                        <div style='font-weight:600;color:#111827;'>{row['Category']}</div>
                                        <div style='font-size:.82rem;color:#6b7280;'>
                                            Budget: J${row['Budget']:,.0f} | Spent: J${row['Actual']:,.0f} | Left: J${row['Remaining']:,.0f}
                                        </div>
                                    </div>
                                    <div style='text-align:right;'>
                                        <div style='font-weight:600;color:{clr};'>{status}</div>
                                        <div style='font-size:1.2rem;font-weight:700;color:{clr};'>{pct:.0f}%</div>
                                    </div>
                                </div>
                                <div style='margin-top:.4rem;background:white;height:7px;border-radius:4px;overflow:hidden;'>
                                    <div style='background:{clr};height:100%;width:{min(pct,100):.0f}%;'></div>
                                </div>
                            </div>""", unsafe_allow_html=True)

                    over = cmp_df[cmp_df["Percentage"]>100]
                    if not over.empty:
                        st.error(f"⚠️ **{len(over)} categories over budget**")
                        for _, r in over.iterrows():
                            st.caption(f"• **{r['Category']}**: {r['Percentage']:.0f}% used "
                                       f"(J${r['Actual']:,.0f} / J${r['Budget']:,.0f})")
                    else:
                        st.success("✅ All categories within budget!")
        else:
            st.info("📊 Upload transaction data in Spending Analysis to see budget performance.")

    # ── TAB 3 ────────────────────────────────────────────────────────
    with tab3:
        _render_subscription_tab(user_id)

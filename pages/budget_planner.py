"""
pages/budget_planner.py
Tab 1: Interactive planner (income, expenses, multi-loan, what-ifs) via embedded HTML.
Tab 2: Budget performance vs actual spending.
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
_PLANNER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: #f8fafc;
    color: #1e293b;
    font-size: 14px;
    padding: 16px;
  }

  h2 { font-size: 1.1rem; font-weight: 700; color: #1e293b; margin-bottom: 12px; }
  h3 { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase;
       letter-spacing: .06em; margin-bottom: 8px; margin-top: 20px; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; }

  /* ── summary cards ── */
  .card {
    background: #fff;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    border-top: 3px solid var(--accent, #667eea);
  }
  .card .label { font-size: 0.72rem; font-weight: 600; color: #94a3b8;
                 text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
  .card .value { font-size: 1.4rem; font-weight: 700; color: var(--accent, #667eea); }
  .card .sub   { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }

  .card.green  { --accent: #10b981; }
  .card.red    { --accent: #ef4444; }
  .card.blue   { --accent: #3b82f6; }
  .card.orange { --accent: #f59e0b; }

  /* ── section box ── */
  .section {
    background: #fff;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    margin-bottom: 14px;
  }

  /* ── input row ── */
  .row {
    display: grid;
    grid-template-columns: 1fr 140px 36px;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
  }
  .row-loan {
    display: grid;
    grid-template-columns: 1fr 110px 90px 80px 36px;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
  }
  .row-onetime {
    display: grid;
    grid-template-columns: 1fr 120px 140px 36px;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
  }

  input[type=text], input[type=number], select {
    width: 100%;
    padding: 7px 10px;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: #1e293b;
    background: #f8fafc;
    transition: border-color .2s;
    outline: none;
  }
  input:focus, select:focus { border-color: #667eea; background: #fff; }

  /* ── buttons ── */
  .btn-add {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 7px 14px; border-radius: 8px;
    background: #667eea; color: #fff;
    border: none; cursor: pointer;
    font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 12px;
    transition: opacity .2s;
  }
  .btn-add:hover { opacity: .85; }
  .btn-add.secondary { background: #e2e8f0; color: #475569; }

  .btn-del {
    width: 32px; height: 32px;
    border-radius: 8px; border: none;
    background: #fee2e2; color: #ef4444;
    cursor: pointer; font-size: 14px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    transition: background .2s;
  }
  .btn-del:hover { background: #fecaca; }

  /* ── progress bar ── */
  .progress-wrap { background: #e2e8f0; border-radius: 99px; height: 7px; margin-top: 4px; overflow: hidden; }
  .progress-fill { height: 100%; border-radius: 99px;
                   background: linear-gradient(90deg,#667eea,#764ba2);
                   transition: width .4s ease; }

  /* ── loan card ── */
  .loan-status {
    background: #f8fafc; border: 1.5px solid #e2e8f0;
    border-radius: 10px; padding: 12px; margin-bottom: 10px;
  }
  .loan-status .lname { font-weight: 600; font-size: 0.92rem; margin-bottom: 6px; }
  .loan-status .lrow  { display: flex; justify-content: space-between;
                         font-size: 0.8rem; color: #64748b; margin-bottom: 3px; }
  .loan-status .lrow span { font-weight: 600; color: #1e293b; }

  /* ── what-if toggle ── */
  .whatif-toggle {
    background: #f1f5f9; border-radius: 8px; padding: 8px 12px;
    font-size: 0.8rem; color: #64748b; cursor: pointer;
    display: flex; align-items: center; justify-content: space-between;
    user-select: none; margin-bottom: 8px;
  }
  .whatif-body { display: none; padding: 10px 0 2px; }
  .whatif-body.open { display: block; }

  /* ── results table ── */
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #667eea; color: #fff; padding: 8px 10px;
       text-align: left; font-weight: 600; font-size: 0.75rem;
       text-transform: uppercase; letter-spacing: .05em; }
  th:first-child { border-radius: 8px 0 0 0; }
  th:last-child  { border-radius: 0 8px 0 0; }
  td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; }
  tr:last-child td { border-bottom: none; }
  tr:nth-child(even) td { background: #f8fafc; }

  /* ── tag ── */
  .tag { display: inline-block; padding: 2px 8px; border-radius: 99px;
          font-size: 0.7rem; font-weight: 600; }
  .tag.green  { background: #dcfce7; color: #166534; }
  .tag.red    { background: #fee2e2; color: #991b1b; }
  .tag.yellow { background: #fef9c3; color: #854d0e; }

  .col-headers {
    display: grid; align-items: end;
    padding: 0 0 4px;
    font-size: 0.7rem; font-weight: 600;
    color: #94a3b8; text-transform: uppercase; letter-spacing: .06em;
  }
  .col-headers-loan { grid-template-columns: 1fr 110px 90px 80px 36px; gap: 8px; }
  .col-headers-row  { grid-template-columns: 1fr 140px 36px; gap: 8px; }
  .col-headers-onetime { grid-template-columns: 1fr 120px 140px 36px; gap: 8px; }
</style>
</head>
<body>

<!-- ════════════════════════════════════════════════
     SUMMARY CARDS
════════════════════════════════════════════════ -->
<h2>📊 Monthly Financial Planner</h2>

<div class="grid-4" style="margin-bottom:14px;">
  <div class="card green">
    <div class="label">Total Income</div>
    <div class="value" id="sumIncome">J$0</div>
    <div class="sub">all sources</div>
  </div>
  <div class="card red">
    <div class="label">Total Expenses</div>
    <div class="value" id="sumExpenses">J$0</div>
    <div class="sub">bills + debt</div>
  </div>
  <div class="card blue">
    <div class="label">Net Savings</div>
    <div class="value" id="sumSavings">J$0</div>
    <div class="sub">income – expenses</div>
  </div>
  <div class="card orange">
    <div class="label">Savings Rate</div>
    <div class="value" id="sumRate">0%</div>
    <div class="sub">of income</div>
  </div>
</div>
<div style="background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#64748b;margin-bottom:6px;">
    <span>Budget utilisation</span>
    <span id="utilisationPct">0%</span>
  </div>
  <div class="progress-wrap"><div class="progress-fill" id="utilisationBar" style="width:0%"></div></div>
</div>


<!-- ════════════════════════════════════════════════
     INCOME
════════════════════════════════════════════════ -->
<div class="section">
  <h2>💰 Income Sources</h2>
  <div class="col-headers col-headers-row">
    <span>Source</span><span>Monthly (J$)</span><span></span>
  </div>
  <div id="incomeList"></div>
  <button class="btn-add" onclick="addIncome()">+ Add income</button>
</div>


<!-- ════════════════════════════════════════════════
     EXPENSES
════════════════════════════════════════════════ -->
<div class="section">
  <h2>💸 Monthly Expenses</h2>
  <div class="col-headers col-headers-row">
    <span>Expense</span><span>Monthly (J$)</span><span></span>
  </div>
  <div id="expenseList"></div>
  <button class="btn-add" onclick="addExpense()">+ Add expense</button>
</div>


<!-- ════════════════════════════════════════════════
     LOANS
════════════════════════════════════════════════ -->
<div class="section">
  <h2>🏦 Loans & Debt</h2>
  <div class="col-headers col-headers-loan">
    <span>Loan name</span><span>Balance (J$)</span><span>Rate %/yr</span><span>Min pmt (J$)</span><span></span>
  </div>
  <div id="loanList"></div>
  <button class="btn-add" onclick="addLoan()">+ Add loan</button>
</div>


<!-- ════════════════════════════════════════════════
     ONE-TIME PAYMENTS
════════════════════════════════════════════════ -->
<div class="section">
  <h2>⚡ One-Time Payments</h2>
  <p style="font-size:0.8rem;color:#94a3b8;margin-bottom:10px;">
    Apply a lump-sum toward any loan to see how it changes your payoff timeline.
  </p>
  <div class="col-headers col-headers-onetime">
    <span>Description</span><span>Amount (J$)</span><span>Apply to loan</span><span></span>
  </div>
  <div id="onetimeList"></div>
  <button class="btn-add" onclick="addOnetime()">+ Add one-time payment</button>
</div>


<!-- ════════════════════════════════════════════════
     WHAT-IF SCENARIOS
════════════════════════════════════════════════ -->
<div class="section">
  <h2>🔮 What-If Scenarios</h2>

  <div class="whatif-toggle" onclick="toggleWhatif('wi1')">
    <span>📈 What if I increase my income?</span><span id="wi1arrow">▸</span>
  </div>
  <div class="whatif-body" id="wi1">
    <div class="row">
      <label style="font-size:0.82rem;color:#475569;">Extra monthly income (J$)</label>
      <input type="number" id="wiIncome" value="0" min="0" oninput="recalc()"/>
      <span></span>
    </div>
  </div>

  <div class="whatif-toggle" onclick="toggleWhatif('wi2')">
    <span>✂️ What if I cut my expenses?</span><span id="wi2arrow">▸</span>
  </div>
  <div class="whatif-body" id="wi2">
    <div class="row">
      <label style="font-size:0.82rem;color:#475569;">Monthly expense reduction (J$)</label>
      <input type="number" id="wiExpense" value="0" min="0" oninput="recalc()"/>
      <span></span>
    </div>
  </div>

  <div class="whatif-toggle" onclick="toggleWhatif('wi3')">
    <span>💳 What if I pay extra on a loan?</span><span id="wi3arrow">▸</span>
  </div>
  <div class="whatif-body" id="wi3">
    <div class="row">
      <label style="font-size:0.82rem;color:#475569;">Extra monthly payment (J$)</label>
      <input type="number" id="wiLoanExtra" value="0" min="0" oninput="recalc()"/>
      <select id="wiLoanTarget" oninput="recalc()" style="max-width:160px;">
        <option value="">— pick loan —</option>
      </select>
      <span></span>
    </div>
  </div>

  <div id="whatifResults" style="margin-top:10px;"></div>
</div>


<!-- ════════════════════════════════════════════════
     LOAN PAYOFF ANALYSIS
════════════════════════════════════════════════ -->
<div class="section">
  <h2>📅 Loan Payoff Analysis</h2>
  <div id="loanPayoff"></div>
</div>


<!-- ════════════════════════════════════════════════
     BREAKDOWN TABLE
════════════════════════════════════════════════ -->
<div class="section">
  <h2>📋 Full Breakdown</h2>
  <table id="breakdownTable">
    <thead>
      <tr>
        <th>Item</th><th>Type</th><th>Monthly (J$)</th><th>% of Income</th><th>Status</th>
      </tr>
    </thead>
    <tbody id="breakdownBody"></tbody>
  </table>
</div>


<script>
// ── State ──────────────────────────────────────────────────────────────────
let incomes  = [{id:1, name:'Primary salary',   amount:150000}];
let expenses = [{id:1, name:'Rent / mortgage',  amount:40000},
                {id:2, name:'Groceries',         amount:15000},
                {id:3, name:'Utilities',          amount:8000}];
let loans    = [{id:1, name:'Car loan', balance:800000, rate:12, min:18000}];
let onetimes = [];
let uid = 10;

function id() { return ++uid; }

// ── Formatters ──────────────────────────────────────────────────────────────
function fmt(n) {
  return 'J$' + Math.abs(n).toLocaleString('en-JM', {minimumFractionDigits:0, maximumFractionDigits:0});
}
function pct(n, total) {
  if (!total) return '0%';
  return (n/total*100).toFixed(1) + '%';
}

// ── Render helpers ──────────────────────────────────────────────────────────
function renderRow(container, obj, labelPlaceholder, onDelete) {
  const d = document.createElement('div');
  d.className = 'row';
  d.innerHTML = `
    <input type="text"   value="${obj.name}"   placeholder="${labelPlaceholder}"
           oninput="obj.name=this.value;recalc()" data-bind="name"/>
    <input type="number" value="${obj.amount}" min="0"
           oninput="obj.amount=+this.value;recalc()" data-bind="amount"/>
    <button class="btn-del" onclick="onDelete()">×</button>`;
  // fix closures
  d.querySelector('[data-bind=name]').addEventListener('input', e => { obj.name = e.target.value; recalc(); });
  d.querySelector('[data-bind=amount]').addEventListener('input', e => { obj.amount = +e.target.value; recalc(); });
  d.querySelector('.btn-del').addEventListener('click', onDelete);
  container.appendChild(d);
}

function renderLoanRow(container, loan, onDelete) {
  const d = document.createElement('div');
  d.className = 'row-loan';
  d.innerHTML = `
    <input type="text"   value="${loan.name}"    placeholder="Loan name"/>
    <input type="number" value="${loan.balance}" min="0" placeholder="Balance"/>
    <input type="number" value="${loan.rate}"    min="0" max="100" step="0.1" placeholder="Rate"/>
    <input type="number" value="${loan.min}"     min="0" placeholder="Min pmt"/>
    <button class="btn-del">×</button>`;
  const [nameI, balI, rateI, minI] = d.querySelectorAll('input');
  nameI.addEventListener('input', e => { loan.name    = e.target.value;  recalc(); });
  balI .addEventListener('input', e => { loan.balance = +e.target.value; recalc(); });
  rateI.addEventListener('input', e => { loan.rate    = +e.target.value; recalc(); });
  minI .addEventListener('input', e => { loan.min     = +e.target.value; recalc(); });
  d.querySelector('.btn-del').addEventListener('click', onDelete);
  container.appendChild(d);
}

function renderOnetimeRow(container, ot, onDelete) {
  const d = document.createElement('div');
  d.className = 'row-onetime';
  const opts = loans.map(l => `<option value="${l.id}" ${ot.loanId===l.id?'selected':''}>${l.name}</option>`).join('');
  d.innerHTML = `
    <input type="text"   value="${ot.desc}"   placeholder="Description"/>
    <input type="number" value="${ot.amount}" min="0" placeholder="Amount"/>
    <select>${opts || '<option value="">No loans yet</option>'}</select>
    <button class="btn-del">×</button>`;
  const [descI, amtI] = d.querySelectorAll('input');
  const sel = d.querySelector('select');
  descI.addEventListener('input', e => { ot.desc   = e.target.value;  recalc(); });
  amtI .addEventListener('input', e => { ot.amount = +e.target.value; recalc(); });
  sel  .addEventListener('change',e => { ot.loanId = +e.target.value; recalc(); });
  d.querySelector('.btn-del').addEventListener('click', onDelete);
  container.appendChild(d);
}

// ── Add rows ────────────────────────────────────────────────────────────────
function addIncome() {
  const o = {id:id(), name:'', amount:0};
  incomes.push(o);
  const c = document.getElementById('incomeList');
  renderRow(c, o, 'e.g. Freelance', () => { incomes = incomes.filter(x=>x!==o); renderAll(); recalc(); });
  recalc();
}
function addExpense() {
  const o = {id:id(), name:'', amount:0};
  expenses.push(o);
  const c = document.getElementById('expenseList');
  renderRow(c, o, 'e.g. Internet', () => { expenses = expenses.filter(x=>x!==o); renderAll(); recalc(); });
  recalc();
}
function addLoan() {
  const o = {id:id(), name:'', balance:0, rate:10, min:0};
  loans.push(o);
  renderAll(); recalc();
}
function addOnetime() {
  const o = {id:id(), desc:'', amount:0, loanId: loans[0]?.id || null};
  onetimes.push(o);
  renderAll(); recalc();
}

// ── Render all lists ────────────────────────────────────────────────────────
function renderAll() {
  // income
  const ic = document.getElementById('incomeList'); ic.innerHTML = '';
  incomes.forEach(o => renderRow(ic, o, 'e.g. Salary', () => { incomes=incomes.filter(x=>x!==o); renderAll(); recalc(); }));

  // expenses
  const ec = document.getElementById('expenseList'); ec.innerHTML = '';
  expenses.forEach(o => renderRow(ec, o, 'e.g. Phone bill', () => { expenses=expenses.filter(x=>x!==o); renderAll(); recalc(); }));

  // loans
  const lc = document.getElementById('loanList'); lc.innerHTML = '';
  loans.forEach(l => renderLoanRow(lc, l, () => { loans=loans.filter(x=>x!==l); renderAll(); recalc(); }));

  // one-times
  const oc = document.getElementById('onetimeList'); oc.innerHTML = '';
  onetimes.forEach(o => renderOnetimeRow(oc, o, () => { onetimes=onetimes.filter(x=>x!==o); renderAll(); recalc(); }));

  // what-if loan target dropdown
  const sel = document.getElementById('wiLoanTarget');
  const prev = sel.value;
  sel.innerHTML = '<option value="">— pick loan —</option>' +
    loans.map(l=>`<option value="${l.id}" ${prev==l.id?'selected':''}>${l.name}</option>`).join('');
}

// ── Payoff calculator ────────────────────────────────────────────────────────
function monthsToPayoff(balance, rate, monthly) {
  if (monthly <= 0 || balance <= 0) return Infinity;
  const r = rate / 100 / 12;
  if (r === 0) return Math.ceil(balance / monthly);
  // standard amortisation
  let bal = balance;
  let months = 0;
  while (bal > 0 && months < 1200) {
    const interest = bal * r;
    bal -= (monthly - interest);
    months++;
    if (monthly <= interest) return Infinity; // will never pay off
  }
  return months;
}

function totalInterest(balance, rate, monthly) {
  if (monthly <= 0 || balance <= 0) return 0;
  const r = rate / 100 / 12;
  let bal = balance, total = 0, months = 0;
  while (bal > 0 && months < 1200) {
    const interest = bal * r;
    if (monthly <= interest) return Infinity;
    total += interest;
    bal -= (monthly - interest);
    months++;
  }
  return total;
}

// ── Main recalc ──────────────────────────────────────────────────────────────
function recalc() {
  const wiInc  = +document.getElementById('wiIncome').value    || 0;
  const wiExp  = +document.getElementById('wiExpense').value   || 0;
  const wiLEx  = +document.getElementById('wiLoanExtra').value || 0;
  const wiLTgt = +document.getElementById('wiLoanTarget').value|| 0;

  const totalIncome   = incomes.reduce((s,x)=>s+x.amount,0)  + wiInc;
  const totalExpenses = expenses.reduce((s,x)=>s+x.amount,0) - wiExp;
  const totalDebt     = loans.reduce((s,l)=>s+l.min,0);
  const totalOut      = totalExpenses + totalDebt;
  const netSavings    = totalIncome - totalOut;
  const savingsRate   = totalIncome ? netSavings/totalIncome*100 : 0;
  const utilisation   = totalIncome ? Math.min(totalOut/totalIncome*100,100) : 0;

  // summary cards
  document.getElementById('sumIncome')  .textContent = fmt(totalIncome);
  document.getElementById('sumExpenses').textContent = fmt(totalOut);
  document.getElementById('sumSavings') .textContent = fmt(netSavings);
  document.getElementById('sumRate')    .textContent = savingsRate.toFixed(1)+'%';
  document.getElementById('utilisationPct').textContent = utilisation.toFixed(1)+'%';
  document.getElementById('utilisationBar').style.width = utilisation+'%';

  // colour savings card based on sign
  document.querySelector('.card.blue .value').style.color = netSavings >= 0 ? '#3b82f6' : '#ef4444';

  // ── Loan payoff panel ──
  const lpDiv = document.getElementById('loanPayoff');
  if (!loans.length) {
    lpDiv.innerHTML = '<p style="color:#94a3b8;font-size:0.82rem;">No loans added.</p>';
  } else {
    let html = '';
    loans.forEach(l => {
      const extra      = (wiLTgt === l.id) ? wiLEx : 0;
      // one-time payment toward this loan
      const oneTimePmt = onetimes.filter(o=>o.loanId===l.id).reduce((s,o)=>s+o.amount,0);
      const effectiveBal = Math.max(0, l.balance - oneTimePmt);
      const monthly    = l.min + extra;
      const months     = monthsToPayoff(effectiveBal, l.rate, monthly);
      const interest   = totalInterest(effectiveBal, l.rate, monthly);
      const monthsBase = monthsToPayoff(l.balance, l.rate, l.min);
      const saved      = monthsBase === Infinity ? 0 : Math.max(0, monthsBase - months);

      const mLabel = months === Infinity ? '∞ (increase payment!)' :
                     `${Math.floor(months/12)}y ${months%12}m`;
      const intLabel = interest === Infinity ? '∞' : fmt(interest);
      const progress = l.balance > 0 ? Math.min(100, oneTimePmt / l.balance * 100) : 0;

      html += `
        <div class="loan-status">
          <div class="lname">🏦 ${l.name || 'Unnamed loan'}</div>
          <div class="lrow">Balance remaining <span>${fmt(effectiveBal)}</span></div>
          <div class="lrow">Monthly payment    <span>${fmt(monthly)}</span></div>
          <div class="lrow">Interest rate      <span>${l.rate}% / yr</span></div>
          <div class="lrow">Payoff timeline    <span>${mLabel}</span></div>
          <div class="lrow">Total interest     <span>${intLabel}</span></div>
          ${saved > 0 ? `<div class="lrow" style="color:#10b981;">Months saved vs min-pmt <span style="color:#10b981">${saved}</span></div>` : ''}
          ${oneTimePmt > 0 ? `
            <div style="margin-top:8px;">
              <div style="font-size:0.75rem;color:#64748b;margin-bottom:3px;">One-time payments applied: ${fmt(oneTimePmt)}</div>
              <div class="progress-wrap"><div class="progress-fill" style="width:${progress}%;background:#10b981;"></div></div>
            </div>` : ''}
        </div>`;
    });
    lpDiv.innerHTML = html;
  }

  // ── What-if results ──
  const wiDiv = document.getElementById('whatifResults');
  const wiActive = wiInc || wiExp || (wiLEx && wiLTgt);
  if (wiActive) {
    const baseSav = (totalIncome-wiInc) - ((totalExpenses+wiExp) + totalDebt);
    const delta   = netSavings - baseSav;
    const yr      = netSavings * 12;
    wiDiv.innerHTML = `
      <div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:10px;padding:12px;">
        <div style="font-weight:700;color:#166534;margin-bottom:6px;">📈 What-if impact</div>
        <div style="font-size:0.82rem;color:#14532d;">
          Monthly savings change: <strong>${delta>=0?'+':''}${fmt(delta)}</strong><br>
          New monthly savings: <strong>${fmt(netSavings)}</strong><br>
          Projected yearly savings: <strong>${fmt(yr)}</strong>
        </div>
      </div>`;
  } else {
    wiDiv.innerHTML = '';
  }

  // ── Breakdown table ──
  const tbody = document.getElementById('breakdownBody');
  tbody.innerHTML = '';

  const addRow = (name, type, amount, ofIncome, status) => {
    const tr = document.createElement('tr');
    const tagClass = status==='Income'?'green': status==='OK'?'green': status==='Watch'?'yellow':'red';
    tr.innerHTML = `
      <td>${name}</td>
      <td>${type}</td>
      <td>${fmt(amount)}</td>
      <td>${ofIncome}</td>
      <td><span class="tag ${tagClass}">${status}</span></td>`;
    tbody.appendChild(tr);
  };

  incomes.forEach(i  => addRow(i.name||'Income',    'Income',  i.amount, pct(i.amount, totalIncome), 'Income'));
  expenses.forEach(e => {
    const p = totalIncome ? e.amount/totalIncome*100 : 0;
    const s = p > 40 ? 'High' : p > 20 ? 'Watch' : 'OK';
    addRow(e.name||'Expense', 'Expense', e.amount, pct(e.amount, totalIncome), s);
  });
  loans.forEach(l => {
    const p = totalIncome ? l.min/totalIncome*100 : 0;
    const s = p > 30 ? 'High' : p > 15 ? 'Watch' : 'OK';
    addRow(l.name||'Loan', 'Debt pmt', l.min, pct(l.min, totalIncome), s);
  });
  onetimes.forEach(o => addRow(o.desc||'One-time', 'One-time', o.amount, pct(o.amount,totalIncome), 'Watch'));

  // totals row
  const tr = document.createElement('tr');
  tr.style.fontWeight = '700';
  tr.innerHTML = `
    <td>NET SAVINGS</td><td>—</td>
    <td style="color:${netSavings>=0?'#10b981':'#ef4444'}">${fmt(netSavings)}</td>
    <td>${savingsRate.toFixed(1)}%</td>
    <td><span class="tag ${netSavings>=0?'green':'red'}">${netSavings>=0?'Positive':'Deficit'}</span></td>`;
  tbody.appendChild(tr);
}

// ── What-if accordion ────────────────────────────────────────────────────────
function toggleWhatif(id) {
  const body  = document.getElementById(id);
  const arrow = document.getElementById(id+'arrow');
  const open  = body.classList.toggle('open');
  arrow.textContent = open ? '▾' : '▸';
}

// ── Init ─────────────────────────────────────────────────────────────────────
renderAll();
recalc();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# budget_planner_page — 2-tab layout
# ---------------------------------------------------------------------------
def budget_planner_page():
    """Budget Planner - Set and track monthly budgets"""
    st.markdown("<div class='content-container'>", unsafe_allow_html=True)

    # header
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

    tab1, tab2 = st.tabs(["🧮 Interactive Planner", "📊 Budget vs Actual"])

    # ── TAB 1: interactive HTML planner ─────────────────────────────────────
    with tab1:
        st.caption(
            "Edit every field live — add income sources, expenses, and multiple loans "
            "at different interest rates. One-time payments reduce whichever loan you choose."
        )
        components.html(_PLANNER_HTML, height=2600, scrolling=True)

    # ── TAB 2: budget vs actual ─────────────────────────────────────────────
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

        # ── budget settings ──
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
                    category, min_value=0,
                    value=int(current_budgets[category]), step=500,
                    key=f"budget_{category}",
                )
        with col2:
            st.markdown("##### 🏷️ Category Budgets")
            for category in categories[mid:]:
                new_budgets[category] = st.number_input(
                    category, min_value=0,
                    value=int(current_budgets[category]), step=500,
                    key=f"budget_{category}",
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

        # ── budget performance ──
        if not data.empty and 'YearMonth' in data.columns:
            st.markdown("---")
            st.markdown("#### 📈 Budget Performance")

            available_months = sorted(data['YearMonth'].unique(), reverse=True)
            if available_months:
                col1, col2 = st.columns([1, 3])
                with col1:
                    selected_month = st.selectbox("Select Month", available_months, key="performance_month")

                month_stats   = calculate_monthly_stats(data, selected_month)
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
                        st.metric("Total Budget", f"J${total_budget:,.0f}")
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
                            <div style='background:{bg_color};padding:1rem;border-radius:8px;
                                        margin-bottom:.5rem;border-left:4px solid {color};'>
                                <div style='display:flex;justify-content:space-between;align-items:center;'>
                                    <div style='flex:1;'>
                                        <div style='font-size:1.1rem;font-weight:600;color:#111827;
                                                    margin-bottom:.25rem;'>{row['Category']}</div>
                                        <div style='font-size:.85rem;color:#6b7280;'>
                                            Budget: J${row['Budget']:,.0f} | Spent: J${row['Actual']:,.0f} | Left: J${row['Remaining']:,.0f}
                                        </div>
                                    </div>
                                    <div style='text-align:right;'>
                                        <div style='font-size:.9rem;font-weight:600;color:{color};
                                                    margin-bottom:.25rem;'>{status}</div>
                                        <div style='font-size:1.25rem;font-weight:700;color:{color};'>
                                            {pct:.0f}%
                                        </div>
                                    </div>
                                </div>
                                <div style='margin-top:.5rem;'>
                                    <div style='background:white;height:8px;border-radius:4px;overflow:hidden;'>
                                        <div style='background:{color};height:100%;width:{min(pct,100):.0f}%;'></div>
                                    </div>
                                </div>
                            </div>""", unsafe_allow_html=True)

                    st.markdown("---")
                    over_budget    = comparison_df[comparison_df['Percentage'] > 100]
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
                                key="budget_alert_email",
                            )
                            if st.button("📧 Send Alert", use_container_width=True,
                                         type="primary", key="send_budget_alert"):
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

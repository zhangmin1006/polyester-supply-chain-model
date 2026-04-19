/* app.js — Polyester Supply Chain Web Application */
'use strict';

// ── Plotly default config ────────────────────────────────────────────────────
const PLOTLY_CONFIG = { responsive: true, displayModeBar: true,
  modeBarButtonsToRemove: ['select2d','lasso2d','autoScale2d'], displaylogo: false };

// ── Utility ──────────────────────────────────────────────────────────────────
function spinner(id, msg = 'Loading…') {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="spinner-wrap">
    <div class="spinner-border spinner-border-sm" role="status"></div>
    <span>${msg}</span></div>`;
}

function renderPlotly(divId, figJson) {
  const el = document.getElementById(divId);
  if (!el) return;
  Plotly.newPlot(divId, figJson.data, figJson.layout, PLOTLY_CONFIG);
}

async function fetchChart(endpoint, divId, extraBody = null) {
  spinner(divId);
  try {
    const opts = extraBody
      ? { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(extraBody) }
      : { method: 'GET' };
    const res  = await fetch(endpoint, opts);
    const data = await res.json();
    const fig  = data.figure || data;
    renderPlotly(divId, fig);
    return data;
  } catch (e) {
    const el = document.getElementById(divId);
    if (el) el.innerHTML = `<div class="spinner-wrap text-danger"><i class="fa fa-exclamation-circle"></i> Error: ${e.message}</div>`;
    throw e;
  }
}

function toast(msg, type = 'info') {
  const id  = 'toast-' + Date.now();
  const bg  = type === 'success' ? '#2a9d8f' : type === 'error' ? '#e63946' : '#457b9d';
  const html = `<div id="${id}" class="toast align-items-center text-white border-0 show"
    style="background:${bg};border-radius:8px;" role="alert">
    <div class="d-flex"><div class="toast-body" style="font-size:0.82rem">${msg}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div></div>`;
  document.getElementById('toast-container').insertAdjacentHTML('beforeend', html);
  setTimeout(() => { const el = document.getElementById(id); if (el) el.remove(); }, 4000);
}

// ── Tab switching ────────────────────────────────────────────────────────────
function initTabs(containerSelector) {
  document.querySelectorAll(containerSelector + ' .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const parent = btn.closest('[data-tabs]') || btn.parentElement.parentElement;
      parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parent.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) {
        target.classList.add('active');
        // Trigger Plotly resize for charts that just became visible
        target.querySelectorAll('[id^="chart-"]').forEach(el => {
          if (el._fullData) Plotly.relayout(el.id, {});
        });
      }
    });
  });
}

// ── Range slider display ─────────────────────────────────────────────────────
function bindRange(inputId, displayId) {
  const inp = document.getElementById(inputId);
  const dsp = document.getElementById(displayId);
  if (!inp || !dsp) return;
  dsp.textContent = inp.value;
  inp.addEventListener('input', () => dsp.textContent = inp.value);
}

// ── Table renderer ───────────────────────────────────────────────────────────
function renderTable(containerId, records, colMap = null) {
  const el = document.getElementById(containerId);
  if (!el || !records.length) return;
  const cols = colMap || Object.keys(records[0]);
  let html = '<div class="table-wrap"><table class="data-table"><thead><tr>';
  cols.forEach(c => { html += `<th>${c}</th>`; });
  html += '</tr></thead><tbody>';
  records.forEach(row => {
    html += '<tr>';
    cols.forEach(c => {
      const v = row[c];
      let cell = v !== undefined && v !== null ? v : '—';
      if (typeof v === 'number') cell = Number.isInteger(v) ? v.toLocaleString() : v.toFixed(3);
      html += `<td>${cell}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: HOME
// ══════════════════════════════════════════════════════════════════════════════
async function initHome() {
  await fetchChart('/api/hmrc/trends', 'chart-trends');
  await fetchChart('/api/hmrc/seasonal','chart-seasonal');
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: MARKET DATA
// ══════════════════════════════════════════════════════════════════════════════
async function initMarket() {
  initTabs('#market-tabs');

  // Tab 1: Trends
  await Promise.all([
    fetchChart('/api/hmrc/trends', 'chart-trends'),
    fetchChart('/api/hmrc/yoy',    'chart-yoy'),
  ]);

  // Tab 2: Country breakdown
  const yearSel = document.getElementById('sel-year');
  async function loadPie() {
    const year = yearSel ? yearSel.value : new Date().getFullYear()-1;
    await fetchChart(`/api/hmrc/pie/${year}`, 'chart-pie');
  }
  if (yearSel) yearSel.addEventListener('change', loadPie);
  await loadPie();

  // Tab 3: Seasonal
  await fetchChart('/api/hmrc/seasonal', 'chart-seasonal');
  await fetchChart('/api/hmrc/eu_noneu', 'chart-eu-noneu');

  // Tab 4: Unit price
  const unitBtn = document.getElementById('btn-unitprice');
  async function loadUnitPrice() {
    const boxes = document.querySelectorAll('.country-check:checked');
    const countries = Array.from(boxes).map(b => b.value);
    const qs = countries.map(c => `c=${encodeURIComponent(c)}`).join('&');
    await fetchChart(`/api/hmrc/unitprice?${qs}`, 'chart-unitprice');
  }
  if (unitBtn) unitBtn.addEventListener('click', loadUnitPrice);
  await loadUnitPrice();
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: STRUCTURE
// ══════════════════════════════════════════════════════════════════════════════
function initStructure() {
  initTabs('#structure-tabs');

  // Sankey (built client-side for instant rendering)
  const nodeLabels = [
    'Oil Extraction','Chemical Processing','PTA Production','PET / Yarn',
    'Fabric Weaving','Garment Assembly','UK Wholesale','UK Retail',
    'China','Bangladesh','Vietnam','Turkey','India','EU',
  ];
  const nodeColors = [
    '#264653','#2a9d8f','#1d6a9d','#1d3557',
    '#2a9d8f','#1d6a9d','#e9c46a','#2a9d8f',
    '#e63946','#2a9d8f','#264653','#e9c46a','#f4a261','#457b9d',
  ];
  const src = [0,1,2,3,4,5,6,  8, 8, 9,10,11,12,13];
  const tgt = [1,2,3,4,5,6,7,  5, 4, 5, 5, 5, 5, 6];
  const val = [100,90,85,80,75,70,65, 27,15,12,10,9,8,24];

  const fig = {
    data: [{
      type: 'sankey',
      node: { label: nodeLabels, color: nodeColors, pad: 14, thickness: 20 },
      link: { source: src, target: tgt, value: val,
              color: Array(src.length).fill('rgba(180,180,180,0.25)') },
    }],
    layout: {
      template: 'plotly_dark', font: { color: 'white', size: 12 },
      margin: { l:10,r:10,t:20,b:10 },
    },
  };
  Plotly.newPlot('chart-sankey', fig.data, fig.layout, PLOTLY_CONFIG);
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: BASELINE
// ══════════════════════════════════════════════════════════════════════════════
async function initBaseline() {
  initTabs('#baseline-tabs');

  // HHI
  spinner('chart-hhi');
  const hhiData = await (await fetch('/api/baseline/hhi')).json();
  renderPlotly('chart-hhi', hhiData.figure);
  renderTable('table-hhi', hhiData.table,
    ['Sector','HHI','HHI_Category','N_Suppliers','China_Share_%','Top_Supplier','Top_Share_%']);

  // China dependency
  spinner('chart-china');
  const chinaData = await (await fetch('/api/baseline/china')).json();
  renderPlotly('chart-china', chinaData.figure);
  renderTable('table-china', chinaData.table);

  // Scorecard / radar
  spinner('chart-scorecard');
  const scData = await (await fetch('/api/baseline/scorecard')).json();
  renderPlotly('chart-scorecard', scData.figure);
  renderTable('table-scorecard', scData.table,
    ['Sector','HHI_Score','Redundancy_Score','Substitution_Score',
     'Buffer_Score','China_Dep_Score','Composite_Resilience','Resilience_Grade']);
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: MRIO
// ══════════════════════════════════════════════════════════════════════════════
async function initMRIO() {
  initTabs('#mrio-tabs');
  bindRange('shock-severity','severity-display');

  // VA decomposition
  spinner('chart-va-heatmap'); spinner('chart-va-pie');
  const vaData = await (await fetch('/api/mrio/va')).json();
  renderPlotly('chart-va-heatmap', vaData.heatmap);
  renderPlotly('chart-va-pie', vaData.pie);
  renderTable('table-va-summary', vaData.summary);

  // China exposure
  spinner('chart-mrio-china');
  const chData = await (await fetch('/api/mrio/china')).json();
  renderPlotly('chart-mrio-china', chData.figure);
  renderTable('table-mrio-china', chData.table);

  // Shock form
  const runBtn = document.getElementById('btn-mrio-shock');
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running…';
      const region   = document.getElementById('shock-region').value;
      const sector   = document.getElementById('shock-sector').value;
      const severity = document.getElementById('shock-severity').value;
      try {
        const res  = await fetch('/api/mrio/shock', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ region, sector, severity }),
        });
        const data = await res.json();
        renderPlotly('chart-mrio-shock', data.figure);
        renderTable('table-mrio-shock', data.table);
        toast('MRIO shock computed', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      runBtn.disabled = false;
      runBtn.innerHTML = '<i class="fa fa-bolt"></i> Run Shock';
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: GHOSH
// ══════════════════════════════════════════════════════════════════════════════
async function initGhosh() {
  initTabs('#ghosh-tabs');
  bindRange('ghosh-severity','ghosh-sev-display');

  // Forward linkages
  spinner('chart-ghosh-fl');
  const flData = await (await fetch('/api/ghosh/linkages')).json();
  renderPlotly('chart-ghosh-fl', flData.figure);
  renderTable('table-ghosh-fl', flData.table,
    ['Sector','FL_Ghosh_Norm','Supply_Critical','Value_Added_GBP','VA_Share_%']);

  // Quadrant
  spinner('chart-ghosh-quad');
  await fetchChart('/api/ghosh/quadrant', 'chart-ghosh-quad');

  // Scenario shock
  const runBtn = document.getElementById('btn-ghosh-shock');
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running…';
      const sc  = document.getElementById('ghosh-scenario').value;
      const sev = document.getElementById('ghosh-severity').value;
      try {
        const res  = await fetch('/api/ghosh/shock', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ scenario: sc, severity: sev }),
        });
        const data = await res.json();
        renderPlotly('chart-ghosh-shock', data.figure);
        document.getElementById('ghosh-loss').textContent =
          `£${(data.loss_gbp/1e9).toFixed(3)}bn output lost`;
        toast('Ghosh shock computed', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      runBtn.disabled = false;
      runBtn.innerHTML = '<i class="fa fa-bolt"></i> Run Scenario';
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: SCENARIOS
// ══════════════════════════════════════════════════════════════════════════════
function initScenarios() {
  bindRange('sim-weeks', 'weeks-display');

  // Wire GS lambda display
  const gsLambdaEl   = document.getElementById('gs-lambda');
  const gsLambdaDisp = document.getElementById('gs-lambda-display');
  if (gsLambdaEl && gsLambdaDisp) {
    gsLambdaDisp.textContent = parseFloat(gsLambdaEl.value).toFixed(2);
    gsLambdaEl.addEventListener('input', () =>
      gsLambdaDisp.textContent = parseFloat(gsLambdaEl.value).toFixed(2));
  }

  const simBtn = document.getElementById('btn-run-sim');
  if (!simBtn) return;

  simBtn.addEventListener('click', async () => {
    const sc       = document.getElementById('sel-scenario').value;
    const weeks    = document.getElementById('sim-weeks').value;
    const stMonth  = document.getElementById('sim-start-month').value;
    const seasonal = document.getElementById('sim-seasonal').checked;
    const lambdaA  = parseFloat(document.getElementById('gs-lambda').value);
    const maxInner = parseInt(document.getElementById('gs-max-inner').value);

    simBtn.disabled = true;
    simBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running…';

    // Show both result sections immediately
    document.getElementById('coupled-result-section').style.display = '';
    document.getElementById('gs-result-section').style.display = '';
    initTabs('#cp-result-tabs');
    initTabs('#gs-result-tabs');
    ['cp-chart-io','cp-chart-prices','cp-chart-sf','cp-chart-abm'].forEach(id => spinner(id));
    ['gs-chart-io','gs-chart-prices','gs-chart-abm','gs-chart-sf',
     'gs-chart-gs','gs-chart-A'].forEach(id => spinner(id));

    const cpPayload = { scenario:sc, weeks, start_month:stMonth, seasonality:seasonal };
    const gsPayload = { scenario:sc, weeks, start_month:stMonth, seasonality:seasonal,
                        lambda_A:lambdaA, max_inner:maxInner };

    // Run both in parallel
    const [cpRes, gsRes] = await Promise.allSettled([
      fetch('/api/integrated/coupled', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(cpPayload),
      }).then(r => r.json()),
      fetch('/api/integrated/coupled_gs', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(gsPayload),
      }).then(r => r.json()),
    ]);

    // ── Bidirectional Coupled results ────────────────────────────────────────
    if (cpRes.status === 'fulfilled') {
      const data = cpRes.value;
      if (data.error) {
        toast('Coupled error: ' + data.error, 'error');
      } else {
        const k = data.kpis;
        document.getElementById('cp-kpi-welfare').textContent  = k.welfare;
        document.getElementById('cp-kpi-price').textContent    = k.max_price + ' · ' + k.max_price_sector;
        document.getElementById('cp-kpi-shortage').textContent = k.io_shortage;
        document.getElementById('cp-kpi-recovery').textContent = k.avg_recovery;
        renderPlotly('cp-chart-io',     data.io_chart);
        renderPlotly('cp-chart-prices', data.price_chart);
        renderPlotly('cp-chart-sf',     data.sf_chart);
        renderPlotly('cp-chart-abm',    data.abm_chart);
        renderTable('cp-table-bullwhip', data.bullwhip, ['Sector','Order_Variance','Bullwhip_Ratio']);
        renderTable('cp-table-service',  data.service_level, ['Sector','Service_Level_%','Fill_Rate_%','Total_Shortage']);
        renderTable('cp-table-recovery', data.recovery_time, ['Sector','Recovery_Week','Trough_Cap_%','Shock_Onset_Week']);
        toast(`Coupled (${sc}) — welfare ${k.welfare}`, 'success');
      }
    } else {
      toast('Coupled simulation error: ' + cpRes.reason, 'error');
    }

    // ── Gauss–Seidel results ─────────────────────────────────────────────────
    if (gsRes.status === 'fulfilled') {
      const data = gsRes.value;
      if (data.error) {
        toast('GS error: ' + data.error, 'error');
      } else {
        const k = data.kpis;
        document.getElementById('gs-kpi-welfare').textContent  = k.welfare;
        document.getElementById('gs-kpi-price').textContent    = k.max_price + ' · ' + k.max_price_sector;
        document.getElementById('gs-kpi-shortage').textContent = k.io_shortage;
        document.getElementById('gs-kpi-iters').textContent    = k.gs_mean_iters + ' / ' + k.gs_max_iters;
        document.getElementById('gs-kpi-drift').textContent    = k.A_drift_final;
        renderPlotly('gs-chart-io',     data.io_chart);
        renderPlotly('gs-chart-prices', data.price_chart);
        renderPlotly('gs-chart-abm',    data.abm_chart);
        renderPlotly('gs-chart-sf',     data.sf_chart);
        renderPlotly('gs-chart-gs',     data.gs_chart);
        renderPlotly('gs-chart-A',      data.A_chart);
        renderTable('gs-table-bullwhip', data.bullwhip, ['Sector','Order_Variance','Bullwhip_Ratio']);
        renderTable('gs-table-service',  data.service_level, ['Sector','Service_Level_%','Fill_Rate_%','Total_Shortage']);
        renderTable('gs-table-recovery', data.recovery_time, ['Sector','Recovery_Week','Trough_Cap_%','Shock_Onset_Week']);
        toast(`GS (${sc}) — mean ${k.gs_mean_iters} iters`, 'success');
      }
    } else {
      toast('GS simulation error: ' + gsRes.reason, 'error');
    }

    simBtn.disabled = false;
    simBtn.innerHTML = '<i class="fa fa-play"></i> Run Simulation';
  });
}


// ══════════════════════════════════════════════════════════════════════════════
// PAGE: VALIDATION
// ══════════════════════════════════════════════════════════════════════════════
async function initValidation() {
  const res   = await fetch('/api/validation');
  const data  = await res.json();

  // Benchmark table
  const tbody = document.getElementById('bench-tbody');
  if (tbody) {
    const catColors = {
      'Volume shock':'badge-ok','Shipping':'badge-warn',
      'Price/energy':'badge-danger','Price shock':'badge-danger',
    };
    data.benchmarks.forEach(b => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${b.event}</td>
        <td>${b.metric}</td>
        <td><strong>${b.hmrc}</strong></td>
        <td><span class="badge-pill ${catColors[b.category]||'badge-info'}">${b.category}</span></td>`;
      tbody.appendChild(tr);
    });
  }

  // YoY chart
  await fetchChart('/api/hmrc/yoy', 'chart-val-yoy');
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: GALLERY
// ══════════════════════════════════════════════════════════════════════════════
function initGallery() {
  const genBtn = document.getElementById('btn-generate');
  const status = document.getElementById('gen-status');

  if (genBtn) {
    genBtn.addEventListener('click', async () => {
      genBtn.disabled = true;
      genBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generating…';
      status.textContent = 'Pipeline started — takes ~60 seconds. Refresh gallery when done.';
      status.style.display = '';
      try {
        const res  = await fetch('/api/gallery/generate', { method: 'POST' });
        const data = await res.json();
        toast(data.message, 'info');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      setTimeout(() => {
        genBtn.disabled = false;
        genBtn.innerHTML = '<i class="fa fa-cogs"></i> Generate All 49 Figures';
      }, 5000);
    });
  }

  // Lightbox for gallery images
  document.querySelectorAll('.gallery-item:not(.missing)').forEach(item => {
    item.addEventListener('click', () => {
      const img = item.querySelector('img');
      const cap = item.querySelector('.gallery-cap');
      if (!img) return;
      const modal = document.createElement('div');
      modal.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9999;
        display:flex;align-items:center;justify-content:center;cursor:zoom-out;flex-direction:column;gap:12px`;
      modal.innerHTML = `<img src="${img.src}" style="max-width:90vw;max-height:85vh;border-radius:6px">
        <span style="color:#94a3b8;font-size:0.8rem">${cap ? cap.textContent : ''}</span>`;
      modal.addEventListener('click', () => modal.remove());
      document.body.appendChild(modal);
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: IO ANALYSIS
// ══════════════════════════════════════════════════════════════════════════════
async function initIO() {
  initTabs('#io-top-tabs');
  initTabs('#io-tabs');
  initTabs('#mrio-tabs');
  initTabs('#ghosh-tabs');
  bindRange('io-shock-sev',   'io-shock-sev-display');
  bindRange('io-sim-frac',    'io-sim-frac-display');
  bindRange('io-sim-onset',   'io-sim-onset-display');
  bindRange('io-sim-dur',     'io-sim-dur-display');
  bindRange('io-sim-T',       'io-sim-T-display');

  // Load multipliers + linkages on page load
  spinner('chart-io-mult');
  const analysis = await (await fetch('/api/io/analysis')).json();
  renderPlotly('chart-io-mult', analysis.multipliers_chart);
  renderPlotly('chart-io-link', analysis.linkages_chart);
  renderTable('table-io-mult', analysis.multipliers_table, ['Sector','Output_Multiplier']);
  renderTable('table-io-link', analysis.linkages_table,
    ['Sector','Backward_Link','BL_Normalised','Forward_Link','FL_Normalised','Key_Sector']);
  renderTable('table-io-calib', analysis.calibration_table);

  // Shock impact button
  const shockBtn = document.getElementById('btn-io-shock');
  if (shockBtn) {
    shockBtn.addEventListener('click', async () => {
      shockBtn.disabled = true;
      shockBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Calculating…';
      spinner('chart-io-shock', 'Calculating impact…');
      const sec = document.getElementById('io-shock-sector').value;
      const sev = document.getElementById('io-shock-sev').value;
      try {
        const res  = await fetch('/api/io/shock-impact', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ sector_idx: sec, shock_fraction: sev / 100 }),
        });
        const data = await res.json();
        renderPlotly('chart-io-shock', data.figure);
        renderTable('table-io-shock', data.table, ['Sector','Pct_Change_%']);
        document.getElementById('io-kpi-loss').textContent =
          `£${(data.disruption_gbp / 1e9).toFixed(3)}bn`;
        document.getElementById('io-kpi-sector').textContent = data.sector_shocked || '—';
        document.getElementById('io-shock-kpi').style.display = '';
        toast('Shock impact calculated', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      shockBtn.disabled = false;
      shockBtn.innerHTML = '<i class="fa fa-bolt"></i> Calculate Impact';
    });
  }

  // Dynamic simulation button
  const simBtn = document.getElementById('btn-io-sim');
  if (simBtn) {
    simBtn.addEventListener('click', async () => {
      simBtn.disabled = true;
      simBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Simulating…';
      document.getElementById('io-sim-results').style.display = '';
      initTabs('#io-sim-subtabs');
      ['chart-io-sim-out','chart-io-sim-short','chart-io-sim-price','chart-io-sim-cap','chart-io-sim-inv'].forEach(id => spinner(id));
      const body = {
        sector_idx:    document.getElementById('io-sim-sector').value,
        shock_fraction: document.getElementById('io-sim-frac').value / 100,
        onset_week:    parseInt(document.getElementById('io-sim-onset').value),
        duration_weeks: parseInt(document.getElementById('io-sim-dur').value),
        T:             parseInt(document.getElementById('io-sim-T').value),
      };
      try {
        const res  = await fetch('/api/io/simulate', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
        const data = await res.json();
        renderPlotly('chart-io-sim-out',   data.output_chart);
        renderPlotly('chart-io-sim-short', data.shortage_chart);
        renderPlotly('chart-io-sim-price', data.prices_chart);
        renderPlotly('chart-io-sim-cap',   data.capacity_chart);
        renderPlotly('chart-io-sim-inv',   data.investment_chart);
        const s = data.summary;
        document.getElementById('io-sim-kpi-shortage').textContent =
          parseFloat(s.total_shortage).toFixed(3);
        document.getElementById('io-sim-kpi-drop').textContent =
          parseFloat(s.max_output_drop).toFixed(1) + '%';
        document.getElementById('io-sim-kpi-sector').textContent = s.most_affected || '—';
        document.getElementById('io-sim-kpi').style.display = '';
        toast('IO simulation complete', 'success');
      } catch(e) { toast('Simulation error: ' + e.message, 'error'); }
      simBtn.disabled = false;
      simBtn.innerHTML = '<i class="fa fa-play"></i> Run Simulation';
    });
  }

  // ── MRIO section (lazy-loaded when tab becomes visible) ──────────────────
  let mrioLoaded = false;
  async function loadMRIO() {
    if (mrioLoaded) return;
    mrioLoaded = true;
    spinner('chart-va-pie', 'Loading…');
    const data = await (await fetch('/api/mrio/va')).json();
    renderPlotly('chart-va-pie',     data.pie_chart);
    renderPlotly('chart-va-heatmap', data.heatmap_chart);
    renderTable('table-va-summary',  data.summary_table,
      ['Region','Value_Added_GBP_bn','Share_%']);
    const chinaData = await (await fetch('/api/mrio/china-exposure')).json();
    renderPlotly('chart-mrio-china', chinaData.figure);
    renderTable('table-mrio-china',  chinaData.table,
      ['Stage','Direct_%','Effective_%']);
  }

  document.querySelectorAll('#io-top-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.tab === 'tab-mrio') loadMRIO();
      if (btn.dataset.tab === 'tab-ghosh') loadGhoshSection();
    });
  });

  bindRange('shock-severity', 'severity-display');
  const mShockBtn = document.getElementById('btn-mrio-shock');
  if (mShockBtn) {
    mShockBtn.addEventListener('click', async () => {
      mShockBtn.disabled = true;
      mShockBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running…';
      spinner('chart-mrio-shock', 'Simulating…');
      const region = document.getElementById('shock-region').value;
      const sector = document.getElementById('shock-sector').value;
      const sev    = document.getElementById('shock-severity').value / 100;
      try {
        const res  = await fetch('/api/mrio/shock', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ region, sector, severity: sev }),
        });
        const data = await res.json();
        renderPlotly('chart-mrio-shock', data.figure);
        renderTable('table-mrio-shock', data.table, ['Sector','Output_Change_%']);
        toast('Regional shock complete', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      mShockBtn.disabled = false;
      mShockBtn.innerHTML = '<i class="fa fa-bolt"></i> Run Shock';
    });
  }

  // ── Ghosh section ─────────────────────────────────────────────────────────
  let ghoshLoaded = false;
  async function loadGhoshSection() {
    if (ghoshLoaded) return;
    ghoshLoaded = true;
    spinner('chart-ghosh-fl', 'Loading…');
    const data = await (await fetch('/api/ghosh/analysis')).json();
    renderPlotly('chart-ghosh-fl',   data.fl_chart);
    renderPlotly('chart-ghosh-quad', data.quad_chart);
    renderTable('table-ghosh-fl',    data.fl_table,
      ['Sector','Forward_Linkage','BL_Normalised','FL_Normalised']);
  }

  bindRange('ghosh-severity', 'ghosh-sev-display');
  const gShockBtn = document.getElementById('btn-ghosh-shock');
  if (gShockBtn) {
    gShockBtn.addEventListener('click', async () => {
      gShockBtn.disabled = true;
      gShockBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running…';
      spinner('chart-ghosh-shock', 'Simulating…');
      const sc  = document.getElementById('ghosh-scenario').value;
      const sev = document.getElementById('ghosh-severity').value / 100;
      try {
        const res  = await fetch('/api/ghosh/shock', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ scenario: sc, severity: sev }),
        });
        const data = await res.json();
        renderPlotly('chart-ghosh-shock', data.figure);
        const lossEl = document.getElementById('ghosh-loss');
        if (lossEl) lossEl.textContent = data.summary || '';
        toast('Ghosh scenario complete', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      gShockBtn.disabled = false;
      gShockBtn.innerHTML = '<i class="fa fa-bolt"></i> Run Scenario';
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: CGE ANALYSIS
// ══════════════════════════════════════════════════════════════════════════════
async function initCGE() {
  initTabs('#cge-tabs');
  bindRange('cge-sub-pct', 'cge-sub-pct-display');

  // Load risk on page load
  spinner('chart-cge-hhi');
  const risk = await (await fetch('/api/cge/risk')).json();
  renderPlotly('chart-cge-hhi',  risk.hhi_chart);
  renderPlotly('chart-cge-risk', risk.risk_chart);
  renderTable('table-cge-hhi',  risk.hhi_table,
    ['Sector','HHI','Concentration','China_Share_%','Top_Supplier','Top_Share_%']);
  renderTable('table-cge-risk', risk.risk_table,
    ['Sector','HHI','China_Share_%','Geographic_Risk','Risk_Category']);

  // Equilibrium button
  const eqBtn = document.getElementById('btn-cge-eq');
  if (eqBtn) {
    eqBtn.addEventListener('click', async () => {
      eqBtn.disabled = true;
      eqBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Solving…';
      document.getElementById('cge-eq-results').style.display = '';
      initTabs('#cge-eq-subtabs');
      ['chart-cge-price','chart-cge-conv','chart-cge-trade'].forEach(id => spinner(id));

      const shocks = [];
      document.querySelectorAll('.cge-shock-input').forEach(inp => {
        const v = parseFloat(inp.value);
        if (v !== 0) shocks.push({ sector_idx: inp.dataset.sector, magnitude: v / 100 });
      });
      const body = {
        shocks,
        tariff_sector: document.getElementById('cge-tariff-sector').value,
        tariff_rate:   parseFloat(document.getElementById('cge-tariff-rate').value),
      };
      try {
        const res  = await fetch('/api/cge/equilibrium', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
        const data = await res.json();
        renderPlotly('chart-cge-price', data.price_chart);
        renderPlotly('chart-cge-conv',  data.convergence_chart);
        renderPlotly('chart-cge-trade', data.trade_chart);
        renderTable('table-cge-trade', data.trade_table,
          ['Sector','Country','Baseline_Share','Shocked_Share','Share_Change_%']);
        document.getElementById('cge-kpi-welfare').textContent =
          `£${(data.welfare_gbp / 1e9).toFixed(3)}bn`;
        document.getElementById('cge-kpi-iters').textContent  = data.iterations;
        document.getElementById('cge-kpi-conv').textContent   =
          data.converged ? 'Converged' : 'Not converged';
        document.getElementById('cge-eq-kpi').style.display = '';
        toast('CGE equilibrium solved', 'success');
      } catch(e) { toast('CGE error: ' + e.message, 'error'); }
      eqBtn.disabled = false;
      eqBtn.innerHTML = '<i class="fa fa-calculator"></i> Run Equilibrium';
    });
  }

  // Substitution button
  const subBtn = document.getElementById('btn-cge-sub');
  if (subBtn) {
    subBtn.addEventListener('click', async () => {
      subBtn.disabled = true;
      subBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Calculating…';
      spinner('chart-cge-sub');
      const body = {
        sector_idx:      document.getElementById('cge-sub-sector').value,
        country:         document.getElementById('cge-sub-country').value,
        price_change_pct: parseFloat(document.getElementById('cge-sub-pct').value),
      };
      try {
        const res  = await fetch('/api/cge/substitution', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
        const data = await res.json();
        renderPlotly('chart-cge-sub', data.figure);
        renderTable('table-cge-sub', data.table,
          ['Country','Base_Demand','New_Demand','Change_%']);
        toast('Substitution calculated', 'success');
      } catch(e) { toast('Error: ' + e.message, 'error'); }
      subBtn.disabled = false;
      subBtn.innerHTML = '<i class="fa fa-shuffle"></i> Calculate Substitution';
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE: ABM DYNAMICS
// ══════════════════════════════════════════════════════════════════════════════
function initABM() {
  initTabs('#abm-result-tabs');
  bindRange('abm-sev',    'abm-sev-display');
  bindRange('abm-onset',  'abm-onset-display');
  bindRange('abm-dur',    'abm-dur-display');
  bindRange('abm-T',      'abm-T-display');

  // Advanced parameter sliders with formatted display
  const alphaInp = document.getElementById('abm-alpha');
  const alphaDisp = document.getElementById('abm-alpha-display');
  if (alphaInp && alphaDisp) {
    alphaDisp.textContent = parseFloat(alphaInp.value).toFixed(2);
    alphaInp.addEventListener('input', () =>
      alphaDisp.textContent = parseFloat(alphaInp.value).toFixed(2));
  }
  const noiseInp = document.getElementById('abm-noise');
  const noiseDisp = document.getElementById('abm-noise-display');
  if (noiseInp && noiseDisp) {
    noiseDisp.textContent = parseFloat(noiseInp.value).toFixed(3);
    noiseInp.addEventListener('input', () =>
      noiseDisp.textContent = parseFloat(noiseInp.value).toFixed(3));
  }

  const runBtn = document.getElementById('btn-abm-run');
  if (!runBtn) return;

  runBtn.addEventListener('click', async () => {
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Simulating agents…';

    document.getElementById('abm-result-tabs').style.display = '';
    ['chart-abm-inv','chart-abm-short','chart-abm-ord',
     'chart-abm-cap','chart-abm-price','chart-abm-bw',
     'chart-abm-sl','chart-abm-rt'].forEach(id => spinner(id, 'Running…'));

    const body = {
      sector_idx:    document.getElementById('abm-sector').value,
      shock_fraction: document.getElementById('abm-sev').value / 100,
      onset_week:    parseInt(document.getElementById('abm-onset').value),
      duration_weeks: parseInt(document.getElementById('abm-dur').value),
      T:             parseInt(document.getElementById('abm-T').value),
      start_month:   parseInt(document.getElementById('abm-month').value),
      seasonal:      document.getElementById('abm-seasonal').checked,
      alpha:         parseFloat(document.getElementById('abm-alpha')?.value ?? 0.3),
      demand_noise:  parseFloat(document.getElementById('abm-noise')?.value ?? 0.03),
    };

    try {
      const res  = await fetch('/api/abm/run', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      const data = await res.json();

      renderPlotly('chart-abm-inv',   data.inventory_chart);
      renderPlotly('chart-abm-short', data.shortage_chart);
      renderPlotly('chart-abm-ord',   data.orders_chart);
      renderPlotly('chart-abm-cap',   data.capacity_chart);
      renderPlotly('chart-abm-price', data.prices_chart);
      renderPlotly('chart-abm-bw',    data.bullwhip_chart);
      renderPlotly('chart-abm-sl',    data.service_chart);
      renderPlotly('chart-abm-rt',    data.recovery_chart);

      renderTable('table-abm-bw', data.bullwhip_table,
        ['Sector','Order_Variance','Bullwhip_Ratio']);
      renderTable('table-abm-sl', data.service_table,
        ['Sector','Service_Level_%','Fill_Rate_%','Total_Shortage']);
      renderTable('table-abm-rt', data.recovery_table,
        ['Sector','Recovery_Week','Trough_Cap_%','Shock_Onset_Week']);

      const s = data.summary;
      document.getElementById('abm-kpi-shortage').textContent =
        parseFloat(s.total_shortage).toFixed(3);
      document.getElementById('abm-kpi-bullwhip').textContent =
        parseFloat(s.max_bullwhip).toFixed(2) + 'x';
      document.getElementById('abm-kpi-service').textContent =
        parseFloat(s.avg_service).toFixed(1) + '%';
      document.getElementById('abm-kpi-recovery').textContent = s.avg_recovery || '—';
      document.getElementById('abm-kpis').style.display = '';

      toast('ABM simulation complete', 'success');
    } catch(e) { toast('ABM error: ' + e.message, 'error'); }

    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fa fa-play"></i> Run ABM';
  });
}

// ── Auto-init based on page body data attribute ──────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  const fns  = {
    home:       initHome,
    market:     initMarket,
    structure:  initStructure,
    baseline:   initBaseline,
    mrio:       initMRIO,
    ghosh:      initGhosh,
    io:         initIO,
    cge:        initCGE,
    abm:        initABM,
    scenarios:  initScenarios,
    validation: initValidation,
    gallery:    initGallery,
  };
  if (fns[page]) fns[page]();
});

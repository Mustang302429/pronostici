const $ = s => document.querySelector(s);
const pct = v => v == null ? '–' : Math.round(v * 100) + '%';
const GIORNI = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab'];
let DATA = null, giorno = null;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dKey = s => s.slice(0, 10);
const fmtDay = k => { const d = new Date(k + 'T12:00'); return `${GIORNI[d.getDay()]} ${d.getDate()}/${d.getMonth() + 1}`; };
// 'oggi' calcolato sempre sull'ora italiana, come gli orari delle partite
const oggiKey = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Rome', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const numPick = s => { const m = /\((\d+)%\)/.exec(s || ''); return m ? +m[1] : 0; };
const effetto = p => { const m = /1 ([+-]\d+)% \/ 2 ([+-]\d+)%/.exec(p['Effetto assenze'] || ''); return m ? Math.max(Math.abs(+m[1]), Math.abs(+m[2])) : 0; };
const disacc = p => { const m = /([+-]\d+)%/.exec(p['Disaccordo col mercato'] || ''); return m ? Math.abs(+m[1]) : 0; };

document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + b.dataset.view));
  window.scrollTo(0, 0);
});

function forma(s) { return `<span class="forma">${[...(s || '')].map(c => `<i class="f${c}">${c}</i>`).join('')}</span>`; }

function card(p) {
  const ora = p.Data.slice(11, 16);
  const tags = [];
  tags.push(`<span class="tag">Segno <b>${esc(p['Segno favorito'])}</b></span>`);
  if (p['Effetto assenze'] && p['Effetto assenze'] !== 'trascurabile') tags.push(`<span class="tag warn">Assenze: ${esc(p['Effetto assenze'])}</span>`);
  if (p['Disaccordo col mercato']) tags.push(`<span class="tag bad">Disaccordo mercato ${esc(p['Disaccordo col mercato'])}</span>`);
  if (p['Affidabilità dati'] !== 'ALTA') tags.push(`<span class="tag">Affidabilità ${esc(p['Affidabilità dati'].toLowerCase())}</span>`);
  if (p.Formazioni && /probabile|ufficiale/.test(p.Formazioni)) tags.push(`<span class="tag acc">Formazione ${esc(p.Formazioni)}</span>`);
  const best = (p['Esito più probabile'] || '').split(' (')[0];
  const mk = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Under 2.5', 'Over 3.5', 'Gol', 'NoGol']
    .map(k => `<div class="${k === best ? 'hi' : ''}"><small>${k}</small><b>${pct(p[k])}</b></div>`).join('');
  const ass = s => s && s !== 'nessun assente segnalato'
    ? `<ul class="ass">${s.split('; ').map(x => { const i = x.indexOf(' ('); return `<li>${esc(i > 0 ? x.slice(0, i) : x)} <em>${esc(i > 0 ? x.slice(i) : '')}</em></li>`; }).join('')}</ul>`
    : '<p class="note">Nessun assente segnalato</p>';
  const sc = p.scheda || {};
  const book = p['Bookmaker 1'] != null
    ? `<span>Bookmaker 1-X-2</span><span>${pct(p['Bookmaker 1'])} · ${pct(p['Bookmaker X'])} · ${pct(p['Bookmaker 2'])}</span>` : '';
  const h2h = (sc['Precedenti (ult.5)'] || '').split(' | ').map(x => `<span>${esc(x)}</span>`).join('');
  return `<article class="card">
    <button class="card-h" aria-expanded="false">
      <div class="ora">${ora}<small>${fmtDay(dKey(p.Data))}</small></div>
      <div class="teams"><div class="t">${esc(p.Casa)}</div><div class="t">${esc(p.Ospite)}</div><div class="c">${esc(p.Competizione)}</div></div>
      <div class="pick"><div class="k">Più probabile</div><div class="v">${esc(p['Esito più probabile'])}</div></div>
    </button>
    <div class="bar" role="img" aria-label="1 ${pct(p['1'])}, X ${pct(p.X)}, 2 ${pct(p['2'])}">
      <div class="b1" style="flex:${p['1']}">1 ${pct(p['1'])}</div><div class="bx" style="flex:${p.X}">X ${pct(p.X)}</div><div class="b2" style="flex:${p['2']}">2 ${pct(p['2'])}</div>
    </div>
    <div class="tags">${tags.join('')}</div>
    <div class="det">
      <div class="box"><h3>Mercati</h3><div class="mk">${mk}</div></div>
      <div class="box"><h3>Numeri</h3><div class="kv">
        <span>Gol attesi</span><span>${p['xG casa'].toFixed(2)} – ${p['xG ospite'].toFixed(2)}</span>
        <span>Risultati esatti</span><span>${esc(p['Risultati esatti probabili'])}</span>
        <span>Solo statistica 1-X-2</span><span>${esc(p['Solo statistica 1-X-2'])}</span>${book}
        <span>Formazioni</span><span>${esc(p.Formazioni)}</span></div></div>
      <div class="box"><h3>Assenti ${esc(p.Casa)}</h3>${ass(p['Assenti casa'])}</div>
      <div class="box"><h3>Assenti ${esc(p.Ospite)}</h3>${ass(p['Assenti ospite'])}</div>
      <div class="box"><h3>Forma e gol</h3><div class="kv">
        <span>${esc(p.Casa)} ult.5</span><span>${forma(sc['Forma casa (ult.5)'])}</span>
        <span>${esc(p.Ospite)} ult.5</span><span>${forma(sc['Forma ospite (ult.5)'])}</span>
        <span>In casa ult.8</span><span>${forma(sc['Rendimento in casa ult.8 casa'])}</span>
        <span>In trasferta ult.8</span><span>${forma(sc['Rendimento in trasferta ult.8 ospite'])}</span>
        <span>Gol fatti/subiti ult.10</span><span>${esc(sc['Gol fatti/subiti ult.10 casa'])} | ${esc(sc['Gol fatti/subiti ult.10 ospite'])}</span>
        <span>% Over 2.5 ult.10</span><span>${sc['% Over2.5 ult.10 casa'] ?? '–'}% | ${sc['% Over2.5 ult.10 ospite'] ?? '–'}%</span>
        <span>% Gol ult.10</span><span>${sc['% Gol ult.10 casa'] ?? '–'}% | ${sc['% Gol ult.10 ospite'] ?? '–'}%</span></div></div>
      <div class="box"><h3>Precedenti</h3><div class="h2h">${h2h}</div></div>
    </div></article>`;
}

function render() {
  const comp = $('#comp').value, q = $('#q').value.trim().toLowerCase(), alta = $('#alta').checked, ord = $('#ord').value;
  let L = DATA.partite.filter(p => (!giorno || dKey(p.Data) === giorno) && (!comp || p.Competizione === comp)
    && (!alta || p['Affidabilità dati'] === 'ALTA') && (!q || (p.Casa + ' ' + p.Ospite).toLowerCase().includes(q)));
  const sorters = { data: (a, b) => a.Data.localeCompare(b.Data), forte: (a, b) => numPick(b['Esito più probabile']) - numPick(a['Esito più probabile']),
    assenze: (a, b) => effetto(b) - effetto(a), disaccordo: (a, b) => disacc(b) - disacc(a) };
  L.sort(sorters[ord]);
  if (!L.length) { $('#lista').innerHTML = '<div class="empty">Nessuna partita con questi filtri.</div>'; return; }
  $('#lista').innerHTML = L.map(card).join('');
  document.querySelectorAll('.card-h').forEach(h => h.onclick = () => {
    const c = h.parentElement; c.classList.toggle('open'); h.setAttribute('aria-expanded', c.classList.contains('open'));
  });
}

function giorni() {
  const cnt = {};
  DATA.partite.forEach(p => cnt[dKey(p.Data)] = (cnt[dKey(p.Data)] || 0) + 1);
  const keys = Object.keys(cnt).sort(), oggi = oggiKey();
  giorno = keys.includes(oggi) ? oggi : keys.find(k => k >= oggi) || keys[0];
  const lab = k => k === oggi ? 'Oggi' : (new Date(new Date(oggi + 'T12:00').getTime() + 864e5).toISOString().slice(0, 10) === k ? 'Domani' : '');
  $('#days').innerHTML = `<button class="day" data-k="">Tutti<small>${DATA.partite.length}</small></button>` +
    keys.map(k => `<button class="day" data-k="${k}">${lab(k) ? `<b>${lab(k)}</b>` : ''}${fmtDay(k)}<small>${cnt[k]}</small></button>`).join('');
  const sync = () => document.querySelectorAll('.day').forEach(b => b.classList.toggle('on', (b.dataset.k || null) === giorno));
  document.querySelectorAll('.day').forEach(b => b.onclick = () => { giorno = b.dataset.k || null; sync(); render(); });
  sync();
}

function verifica() {
  const v = DATA.verifica || [];
  $('#verifica').innerHTML = v.length ? `<table><thead><tr><th>Ramo</th><th class="n">Partite</th><th class="n">Favorito 1X2</th><th class="n">Over/Under 2.5</th><th class="n">Gol/NoGol</th></tr></thead><tbody>` +
    v.map(r => `<tr><td>${esc(r.Ramo)}</td><td class="n">${r['Partite verificate']}</td><td class="n">${pct(r['Favorito 1X2 indovinato'])}</td><td class="n">${pct(r['Over/Under 2.5 indovinato'])}</td><td class="n">${pct(r['Gol/NoGol indovinato'])}</td></tr>`).join('') + '</tbody></table>'
    : '<div class="empty">Ancora nessuna partita verificata. I numeri compariranno dopo le prime partite giocate.</div>';
  const b = DATA.backtest || {};
  if (!b.partite) { $('#backtest').innerHTML = ''; return; }
  $('#backtest').innerHTML = `<div class="stats">
    <div class="stat"><small>Partite testate</small><b>${b.partite.toLocaleString('it-IT')}</b></div>
    <div class="stat"><small>Favorito indovinato</small><b>${pct(b.favorito)}</b></div>
    <div class="stat"><small>Over/Under 2.5 indovinato</small><b>${pct(b.over25)}</b></div>
    <div class="stat"><small>Gol/NoGol indovinato</small><b>${pct(b.gg)}</b></div></div>
    <h2>Calibrazione</h2><p class="note">Quando il modello dice X%, quanto spesso succede davvero?</p>
    <table><thead><tr><th>Fascia</th><th class="n">Previsto</th><th class="n">Reale</th><th class="n">Casi</th></tr></thead><tbody>` +
    b.calibrazione.map(c => `<tr><td>${esc(c.fascia.replace(/[\(\]]/g, '').replace(', ', ' – '))}</td><td class="n">${pct(c.previsto)}</td><td class="n">${pct(c.reale)}</td><td class="n">${c.n}</td></tr>`).join('') + '</tbody></table>';
}

(async () => {
  $('#lista').innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div>';
  try {
    DATA = await (await fetch('data.json?' + Date.now())).json();
  } catch (e) { $('#lista').innerHTML = '<div class="empty">Impossibile caricare i dati. Riprova tra qualche minuto.</div>'; return; }
  const a = DATA.aggiornato;
  $('#agg').textContent = `Aggiornato ${fmtDay(a.slice(0, 10))} alle ${a.slice(11, 16)} · ${DATA.partite.length} partite`;
  [...new Set(DATA.partite.map(p => p.Competizione))].sort().forEach(c => $('#comp').insertAdjacentHTML('beforeend', `<option>${esc(c)}</option>`));
  ['#comp', '#ord', '#alta'].forEach(s => $(s).onchange = render); $('#q').oninput = render;
  giorni(); render(); verifica();
})();

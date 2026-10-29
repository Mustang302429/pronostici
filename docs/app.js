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
const disacc = p => { const m = /\(([+-]\d+) punti\)/.exec(p['Disaccordo col mercato'] || ''); return m ? Math.abs(+m[1]) : 0; };
const X = p => p.extra || {};
const quota = v => v > 0 ? (1 / v).toFixed(2) : '–';
// catalogo dei mercati di una partita, per famiglia
const FAM = { esito: 'Esito e doppia chance', gol: 'Gol: Over/Under, Gol/NoGol', combo: 'Combo', t1: '1° tempo', t2: '2° tempo', cart: 'Cartellini' };
function mercatiDi(p) {
  const e = X(p), L = [];
  const add = (fam, k, v, lab) => { if (v != null && !isNaN(v)) L.push({ fam, k, p: v, lab: lab || k }); };
  ['1', 'X', '2', '1X', 'X2'].forEach(k => add('esito', k, p[k]));
  add('esito', '12', p['1'] != null ? p['1'] + p['2'] : null);
  ['Over 1.5', 'Over 2.5', 'Under 2.5', 'Over 3.5', 'Gol', 'NoGol'].forEach(k => add('gol', k, p[k]));
  add('gol', 'Under 3.5', p['Over 3.5'] != null ? 1 - p['Over 3.5'] : null);
  Object.keys(e).filter(k => k.includes(' + ')).forEach(k => add('combo', k, e[k]));
  ['1', 'X', '2', '1X', 'X2', 'Over 0.5', 'Under 0.5', 'Over 1.5', 'Under 1.5'].forEach(k => { add('t1', '1T ' + k, e['1T ' + k], '1° tempo ' + k); add('t2', '2T ' + k, e['2T ' + k], '2° tempo ' + k); });
  ['3.5', '4.5', '5.5'].forEach(s => { add('cart', 'Gialli Over ' + s, e['Gialli Over ' + s], 'Cartellini gialli Over ' + s); add('cart', 'Gialli Under ' + s, e['Gialli Under ' + s], 'Cartellini gialli Under ' + s); });
  return L;
}
const pid = p => p.Data + '|' + p.Casa + '|' + p.Ospite;
let MIA = [];   // schedina personale: {id, k}
const inMia = (p, k) => MIA.some(x => x.id === pid(p) && x.k === k);

document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + b.dataset.view));
  window.scrollTo(0, 0);
});

function forma(s) { return `<span class="forma">${[...(s || '')].map(c => `<i class="f${c}">${c}</i>`).join('')}</span>`; }

function cella(p, k, lab, v, hi) {
  return `<button class="mc${hi ? ' hi' : ''}${inMia(p, k) ? ' sel' : ''}" data-id="${esc(pid(p))}" data-k="${esc(k)}" title="Tocca per aggiungere alla tua schedina"><small>${esc(lab)}</small><b>${pct(v)}</b></button>`;
}
function griglia(p, items, best) { return `<div class="mk">${items.filter(([, , v]) => v != null).map(([k, lab, v]) => cella(p, k, lab, v, k === best)).join('')}</div>`; }

const MESI = { January: 'gennaio', February: 'febbraio', March: 'marzo', April: 'aprile', May: 'maggio', June: 'giugno', July: 'luglio', August: 'agosto', September: 'settembre', October: 'ottobre', November: 'novembre', December: 'dicembre' };
const rientroIT = r => String(r || '').replace(/\bEarly\b/, 'inizio').replace(/\bMid\b/, 'metà').replace(/\bLate\b/, 'fine').replace(/\bEnd of season\b/i, 'fine stagione')
  .replace(/^Day to day$/i, 'da valutare giorno per giorno').replace(/^Back in training$/i, 'tornato ad allenarsi').replace(/^A few weeks$/i, 'qualche settimana').replace(/^A few days$/i, 'pochi giorni').replace(/^About a week$/i, 'circa una settimana').replace(/^About (\d+)-(\d+) weeks$/i, 'circa $1-$2 settimane').replace(/^Out for season$/i, 'fuori per la stagione').replace(/^Late October 2026$/, 'fine ottobre 2026').replace(/\bUnknown\b/i, 'non noto').replace(/\b(January|February|March|April|May|June|July|August|September|October|November|December)\b/, m => MESI[m]);
function assenti(lista, testo) {
  if (lista && lista.length) {
    return `<ul class="ass">${lista.map(a => {
      const imp = (a.impatto || '').toLowerCase();
      const info = [a.ruolo, a.motivo, a.gol ? `${a.gol} gol` : '', a.rientro && !/doubt/i.test(a.rientro) ? `rientro: ${rientroIT(a.rientro)}` : ''].filter(Boolean).join(' · ');
      return `<li><div class="ass-h"><b>${esc(a.nome)}</b><span class="imp imp-${imp}">Impatto ${esc(imp || 'n.d.')}</span></div>
        <div class="ass-i">${esc(info)}</div><div class="ass-t">${esc(a.titolare || '')}</div></li>`;
    }).join('')}</ul>`;
  }
  return testo && testo !== 'nessun assente segnalato' ? `<p class="note">${esc(testo)}</p>` : '<p class="note">Nessun assente segnalato</p>';
}

function card(p) {
  const ora = p.Data.slice(11, 16), e = X(p), sc = p.scheda || {};
  const tags = [];
  tags.push(`<span class="tag">Segno <b>${esc(p['Segno favorito'])}</b></span>`);
  if (p['Effetto assenze'] && p['Effetto assenze'] !== 'trascurabile') tags.push(`<span class="tag warn">Assenze: ${esc(p['Effetto assenze'])}</span>`);
  if (p['Disaccordo col mercato']) {
    const m = /segno (\w)/.exec(p['Disaccordo col mercato']), d = /\(([+-]\d+) punti\)/.exec(p['Disaccordo col mercato']);
    tags.push(`<span class="tag bad">Mercato diverso sul ${m ? m[1] : ''}: ${d ? d[1].replace('-', '−') : ''} punti</span>`);
  }
  if (p['Affidabilità dati'] !== 'ALTA') tags.push(`<span class="tag">Affidabilità ${esc(p['Affidabilità dati'].toLowerCase())}</span>`);
  if (p.Formazioni && /probabile|ufficiale/.test(p.Formazioni)) tags.push(`<span class="tag acc">Formazione ${esc(p.Formazioni)}</span>`);
  const best = (p['Esito più probabile'] || '').split(' (')[0];
  const mk = griglia(p, ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Under 2.5', 'Over 3.5', 'Gol', 'NoGol'].map(k => [k, k, p[k]]), best);
  const tempo = n => griglia(p, ['1', 'X', '2', '1X', 'X2', 'Over 0.5', 'Over 1.5', 'Under 1.5'].map(k => [`${n} ${k}`, k, e[`${n} ${k}`]]));
  const cart = griglia(p, ['Over 3.5', 'Under 3.5', 'Over 4.5', 'Under 4.5', 'Over 5.5', 'Under 5.5'].map(k => [`Gialli ${k}`, k, e[`Gialli ${k}`]]));
  const combos = Object.keys(e).filter(k => k.includes(' + ')).sort((a, b) => e[b] - e[a]).slice(0, 8);
  const cmb = griglia(p, combos.map(k => [k, k, e[k]])).replace('class="mk"', 'class="mk mk2"');
  const book = p['Bookmaker 1'] != null
    ? `<span>Bookmaker 1-X-2</span><span>${pct(p['Bookmaker 1'])} · ${pct(p['Bookmaker X'])} · ${pct(p['Bookmaker 2'])}</span>` : '';
  const dis = p['Disaccordo col mercato'] ? `<span>Disaccordo col mercato</span><span>${esc(p['Disaccordo col mercato'].replace('-', '−'))}</span>` : '';
  const h2h = (sc['Precedenti (ult.5)'] || '').split(' | ').map(x => `<span>${esc(x)}</span>`).join('');
  const C = esc(p.Casa), O = esc(p.Ospite), n = v => v == null ? '–' : v;
  const gfs = s => { const [a, b] = String(s || '').split(' / '); return b ? `${a} fatti · ${b} subiti` : '–'; };
  return `<article class="card" data-id="${esc(pid(p))}">
    <button class="card-h" aria-expanded="false">
      <div class="ora">${ora}<small>${fmtDay(dKey(p.Data))}</small></div>
      <div class="teams"><div class="t">${C}</div><div class="t">${O}</div><div class="c">${esc(p.Competizione)}</div></div>
      <div class="pick"><div class="k">Più probabile</div><div class="v">${esc(p['Esito più probabile'])}</div></div>
    </button>
    <div class="bar" role="img" aria-label="1 ${pct(p['1'])}, X ${pct(p.X)}, 2 ${pct(p['2'])}">
      <div class="b1" style="flex:${p['1']}">1 ${pct(p['1'])}</div><div class="bx" style="flex:${p.X}">X ${pct(p.X)}</div><div class="b2" style="flex:${p['2']}">2 ${pct(p['2'])}</div>
    </div>
    <div class="tags">${tags.join('')}</div>
    <div class="det">
      <p class="hint">Tocca una percentuale per aggiungerla alla tua schedina (scheda Schedina).</p>
      <div class="box"><h3>Mercati (partita intera)</h3>${mk}</div>
      <div class="box"><h3>Numeri</h3><div class="kv">
        <span>Gol attesi</span><span>${C} ${p['xG casa'].toFixed(2)} – ${p['xG ospite'].toFixed(2)} ${O}</span>
        <span>Risultati esatti</span><span>${esc(p['Risultati esatti probabili'])}</span>
        <span>Solo statistica 1-X-2</span><span>${esc(p['Solo statistica 1-X-2'])}</span>${book}${dis}
        <span>Formazioni</span><span>${esc(p.Formazioni)}</span>${p.Arbitro ? `<span>Arbitro</span><span>${esc(p.Arbitro)}</span>` : ''}</div></div>
      <div class="box"><h3>1° tempo</h3>${tempo('1T')}<p class="note">Risultati più probabili all'intervallo: ${esc(e['1T risultati probabili'] || '–')}</p></div>
      <div class="box"><h3>2° tempo (solo gol del secondo tempo)</h3>${tempo('2T')}<p class="note">Tempo con più gol: 1° ${pct(e['Tempo più gol: 1°'])} · 2° ${pct(e['Tempo più gol: 2°'])} · pari ${pct(e['Tempo più gol: pari'])}</p></div>
      <div class="box"><h3>Cartellini gialli (totale partita)</h3>${cart}<div class="kv">
        <span>Gialli attesi</span><span>${e['Gialli attesi'] != null ? e['Gialli attesi'].toFixed(1) : '–'} (${C} ${e['Gialli casa attesi'] != null ? e['Gialli casa attesi'].toFixed(1) : '–'} · ${O} ${e['Gialli ospite attesi'] != null ? e['Gialli ospite attesi'].toFixed(1) : '–'})</span>
        <span>Almeno un rosso</span><span>${pct(e['Almeno un rosso'])}</span>
        <span>Media gialli ult.10</span><span>${C} ${n(sc['Gialli medi ult.10 casa'])} · ${O} ${n(sc['Gialli medi ult.10 ospite'])}</span></div></div>
      <div class="box"><h3>Combo più probabili</h3>${cmb}<p class="note">Probabilità che si verifichino entrambe le cose nella stessa partita.</p></div>
      <div class="box"><h3>Assenti ${C}</h3>${assenti(p['Assenti casa (lista)'], p['Assenti casa'])}</div>
      <div class="box"><h3>Assenti ${O}</h3>${assenti(p['Assenti ospite (lista)'], p['Assenti ospite'])}</div>
      <div class="box"><h3>Forma e gol</h3><div class="kv">
        <span>${C} – ultime 5 (tutte)</span><span>${forma(sc['Forma casa (ult.5)'])}</span>
        <span>${O} – ultime 5 (tutte)</span><span>${forma(sc['Forma ospite (ult.5)'])}</span>
        <span>${C} – ultime 8 in casa</span><span>${forma(sc['Rendimento in casa ult.8 casa'])}</span>
        <span>${O} – ultime 8 in trasferta</span><span>${forma(sc['Rendimento in trasferta ult.8 ospite'])}</span>
        <span>${C} – media gol ult.10</span><span>${gfs(sc['Gol fatti/subiti ult.10 casa'])}</span>
        <span>${O} – media gol ult.10</span><span>${gfs(sc['Gol fatti/subiti ult.10 ospite'])}</span>
        <span>% partite Over 2.5 ult.10</span><span>${C} ${n(sc['% Over2.5 ult.10 casa'])}% · ${O} ${n(sc['% Over2.5 ult.10 ospite'])}%</span>
        <span>% partite con Gol (segnano entrambe) ult.10</span><span>${C} ${n(sc['% Gol ult.10 casa'])}% · ${O} ${n(sc['% Gol ult.10 ospite'])}%</span>
        <span>% partite con gol nel 1° tempo ult.10</span><span>${C} ${n(sc['% gol nel 1T ult.10 casa'])}% · ${O} ${n(sc['% gol nel 1T ult.10 ospite'])}%</span></div>
        <p class="note">Le lettere vanno dalla più vecchia (sinistra) alla più recente (destra). V = vittoria, N = pareggio, P = sconfitta.</p></div>
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
  bindCelle($('#lista'));
}

function bindCelle(root) {
  root.querySelectorAll('.mc').forEach(b => b.onclick = ev => {
    ev.stopPropagation();
    const id = b.dataset.id, k = b.dataset.k;
    const i = MIA.findIndex(x => x.id === id && x.k === k);
    if (i >= 0) MIA.splice(i, 1);
    else { MIA = MIA.filter(x => x.id !== id); MIA.push({ id, k }); }   // una sola giocata per partita
    document.querySelectorAll(`.mc[data-id="${CSS.escape(id)}"]`).forEach(x => x.classList.toggle('sel', MIA.some(m => m.id === id && m.k === x.dataset.k)));
    contaMia(); schedina();
  });
}
function contaMia() { const t = $('#tab-sch'); t.textContent = MIA.length ? `Schedina (${MIA.length})` : 'Schedina'; }

// ---------------------------------------------------------------- schedina automatica
function ticket(titolo, sel, nota) {
  if (!sel.length) return `<div class="ticket"><div class="t-h"><b>${titolo}</b></div><div class="empty">${nota}</div></div>`;
  const tot = sel.reduce((a, s) => a * s.m.p, 1);
  return `<div class="ticket"><div class="t-h"><b>${titolo}</b><span>${sel.length} partit${sel.length === 1 ? 'a' : 'e'}</span></div>
    ${sel.map(s => `<div class="t-r">
      <div class="t-m"><small>${fmtDay(dKey(s.p.Data))} ${s.p.Data.slice(11, 16)} · ${esc(s.p.Competizione)}</small><b>${esc(s.p.Casa)} – ${esc(s.p.Ospite)}</b></div>
      <div class="t-p"><span class="t-k">${esc(s.m.lab)}</span><span class="t-v">${pct(s.m.p)} <small>quota equa ${quota(s.m.p)}</small></span></div>
      ${s.manuale ? `<button class="t-x" data-id="${esc(pid(s.p))}" aria-label="Togli">×</button>` : ''}</div>`).join('')}
    <div class="t-f"><div><small>Probabilità che escano tutte</small><b>${(tot * 100).toFixed(tot < 0.1 ? 1 : 0)}%</b></div>
      <div><small>Quota equa totale</small><b>${quota(tot)}</b></div></div></div>`;
}

function schedina() {
  if (!DATA) return;
  const soglia = +$('#s-soglia').value / 100, modo = $('#s-modo').value, qmin = +$('#s-qmin').value, max = +$('#s-max').value;
  const g = $('#s-giorno').value, comp = $('#s-comp').value, alta = $('#s-alta').checked;
  const fam = [...document.querySelectorAll('.s-fam:checked')].map(x => x.value);
  $('#s-soglia-v').textContent = Math.round(soglia * 100) + '%';
  const lim = g === 'p4' ? new Date(new Date(oggiKey() + 'T12:00').getTime() + 3 * 864e5).toISOString().slice(0, 10) : null;
  const okG = k => !g || (g === 'p4' ? k >= oggiKey() && k <= lim : k === g);
  const P = DATA.partite.filter(p => okG(dKey(p.Data)) && (!comp || p.Competizione === comp) && (!alta || p['Affidabilità dati'] === 'ALTA'));
  const scelte = [];
  P.forEach(p => {
    const C = mercatiDi(p).filter(m => fam.includes(m.fam) && m.p >= soglia && 1 / m.p >= qmin);
    if (!C.length) return;
    C.sort((a, b) => modo === 'sicura' ? b.p - a.p : a.p - b.p);
    scelte.push({ p, m: C[0] });
  });
  scelte.sort((a, b) => modo === 'sicura' ? b.m.p - a.m.p : a.m.p - b.m.p);
  const sel = scelte.slice(0, max).sort((a, b) => a.p.Data.localeCompare(b.p.Data));
  $('#s-out').innerHTML = ticket('Schedina proposta', sel,
    `Nessuna giocata supera il ${Math.round(soglia * 100)}% con quota equa almeno ${qmin.toFixed(2)}. Abbassa la soglia, la quota minima o aggiungi altri mercati.`) +
    `<p class="note">Partite considerate: ${P.length} · con almeno una giocata valida: ${scelte.length}.</p>`;
  const mie = MIA.map(x => { const p = DATA.partite.find(q => pid(q) === x.id); const m = p && mercatiDi(p).find(m => m.k === x.k); return p && m ? { p, m, manuale: true } : null; }).filter(Boolean)
    .sort((a, b) => a.p.Data.localeCompare(b.p.Data));
  $('#s-mia').innerHTML = ticket('La tua schedina', mie, 'Vuota. Nella scheda Partite apri una partita e tocca una percentuale per aggiungerla.') +
    (mie.length ? '<button class="btn-sec" id="s-svuota">Svuota</button>' : '');
  document.querySelectorAll('#s-mia .t-x').forEach(b => b.onclick = () => { MIA = MIA.filter(x => x.id !== b.dataset.id); contaMia(); schedina(); render(); });
  const sv = $('#s-svuota'); if (sv) sv.onclick = () => { MIA = []; contaMia(); schedina(); render(); };
}

function initSchedina() {
  const keys = [...new Set(DATA.partite.map(p => dKey(p.Data)))].sort(), oggi = oggiKey();
  $('#s-giorno').innerHTML = '<option value="">Tutti i giorni</option><option value="p4">Prossimi 4 giorni (una giornata)</option>' + keys.map(k => `<option value="${k}">${k === oggi ? 'Oggi – ' : ''}${fmtDay(k)}</option>`).join('');
  $('#s-giorno').value = keys.includes(oggi) ? oggi : (keys.find(k => k >= oggi) || '');
  [...new Set(DATA.partite.map(p => p.Competizione))].sort().forEach(c => $('#s-comp').insertAdjacentHTML('beforeend', `<option>${esc(c)}</option>`));
  $('#s-fam').innerHTML = Object.entries(FAM).map(([k, v]) => `<label class="chk"><input type="checkbox" class="s-fam" value="${k}" ${['esito', 'gol', 'combo'].includes(k) ? 'checked' : ''}> ${v}</label>`).join('');
  document.querySelectorAll('#v-schedina select, #v-schedina input').forEach(x => x.oninput = x.onchange = schedina);
  schedina();
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
    b.calibrazione.map(c => `<tr><td>${esc(c.fascia.replace(/[\(\]]/g, '').replace(', ', ' – '))}</td><td class="n">${pct(c.previsto)}</td><td class="n">${pct(c.reale)}</td><td class="n">${c.n}</td></tr>`).join('') + '</tbody></table>' + extraBT();
}
function extraBT() {
  const e = DATA.backtest_extra || {}; const k = Object.keys(e); if (!k.length) return '';
  return `<h2>Nuovi mercati: tempi e cartellini (backtest 2025/26)</h2><p class="note">Previsto medio contro frequenza reale: più sono vicini, più il sistema è tarato bene. "Meglio della media" confronta il sistema con chi giocasse sempre la frequenza del campionato.</p>
  <table><thead><tr><th>Mercato</th><th class="n">Partite</th><th class="n">Previsto</th><th class="n">Reale</th><th class="n">Meglio della media</th></tr></thead><tbody>` +
  k.map(m => { const r = e[m], g = (1 - r.brier_modello / r.brier_media_fissa) * 100; return `<tr><td>${esc(m.replace('1T', '1° tempo').replace('2T', '2° tempo'))}</td><td class="n">${r.partite}</td><td class="n">${pct(r.previsto_medio)}</td><td class="n">${pct(r.frequenza_reale)}</td><td class="n">${g >= 1 ? '+' + g.toFixed(1) + '%' : 'quasi uguale'}</td></tr>`; }).join('') + '</tbody></table>';
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
  giorni(); render(); verifica(); initSchedina();
})();

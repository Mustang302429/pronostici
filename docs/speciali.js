// ---------------------------------------------------------------- schedine speciali
// 1) Solo 1X2 nei campionati serali (Sudamerica, Messico, MLS)
// 2) Campionati da gol: una sola scommessa uguale per tutte le partite (Over 2.5, Over 1.5, 1° tempo Over 0.5...)
let MONDO = null, SPM = '1x2', spGiorno = null;
const SPSEL = { '1x2': [], gol: [], naz: [] };
const SEZ = { '1x2': 'N', gol: 'G', naz: 'Z' };            // {id, k}
const STATK = { 'Over 2.5': 'O25', 'Over 1.5': 'O15', 'Over 3.5': 'O35', Gol: 'GG', '1T Over 0.5': 'T1O05', '1T Over 1.5': 'T1O15' };
const NOMEM = { 'Over 2.5': 'Over 2.5', 'Over 1.5': 'Over 1.5', 'Over 3.5': 'Over 3.5', Gol: 'Gol', '1T Over 0.5': '1° tempo Over 0.5', '1T Over 1.5': '1° tempo Over 1.5',
  '1X': '1X', X2: 'X2', 12: '12', 'Under 2.5': 'Under 2.5', 'Under 3.5': 'Under 3.5', NoGol: 'No Gol', 1: '1', X: 'X', 2: '2' };
const PRINC = { Bundesliga: 'D1', 'Eredivisie (NED)': 'N1' };
const INTRO = {
  '1x2': 'Campionati che in Italia si giocano di sera o di notte: Argentina, Brasile (A e B), Colombia, Cile, Uruguay, Perù, Ecuador, Paraguay, Bolivia, Messico e MLS. Solo 1, X o 2: niente gol, niente doppie chance.',
  gol: 'Campionati scelti perché nell\'ultimo anno hanno avuto più gol della media (dati reali qui sotto). Scegli una scommessa: la schedina userà solo quella, su tutte le partite.',
  naz: 'Nations League UEFA e CONCACAF, qualificazioni alla Coppa d\'Africa e amichevoli. Modello allenato su oltre 6.000 partite tra nazionali dal 2019, unito alle quote DraftKings quando ci sono. Scegli il tipo di scommessa qui sotto. Attenzione alle amichevoli: i ct cambiano spesso formazione.'
};

function spPartite() {
  if (!MONDO) return [];
  const sez = SEZ[SPM];
  const L = MONDO.partite.filter(p => (MONDO.leghe[p.comp] || {}).sez.includes(sez)).map(p => ({ ...p, sid: 'M|' + p.id }));
  if (SPM === 'gol' && DATA) {
    DATA.partite.filter(p => PRINC[p.Competizione]).forEach(p => {
      const e = p.extra || {};
      L.push({ sid: 'P|' + pid(p), data: p.Data, comp: PRINC[p.Competizione], casa: p.Casa, ospite: p.Ospite, affidabilita: p['Affidabilità dati'],
        p: { 1: p['1'], X: p.X, 2: p['2'], 'Over 1.5': p['Over 1.5'], 'Over 2.5': p['Over 2.5'], 'Over 3.5': p['Over 3.5'], Gol: p.Gol,
          '1T Over 0.5': e['1T Over 0.5'], '1T Over 1.5': e['1T Over 1.5'] }, quote: p.Quote || {}, fonte: p['Fonte quote'] });
    });
  }
  return L.sort((a, b) => a.data.localeCompare(b.data));
}
const spNome = c => { const l = MONDO.leghe[c] || {}; return `${l.paese || ''} · ${l.nome || c}`; };
function spBook(p, k) {
  const q = p.quote || {};
  if (k === '1') return q.q1; if (k === 'X') return q.qx; if (k === '2') return q.q2;
  const m = /^Over (\d\.5)$/.exec(k);
  if (m && q.linea != null && +q.linea === +m[1]) return q.qover;
  const u = /^Under (\d\.5)$/.exec(k);
  if (u && q.linea != null && +q.linea === +u[1]) return q.qunder;
  return null;
}
const spSera = p => { const h = +p.data.slice(11, 13); return h >= 20 || h < 7; };

function spFiltrate(conGiorno = true) {
  const lega = $('#sp-lega').value, sera = $('#sp-sera').checked, alta = $('#sp-alta').checked;
  return spPartite().filter(p => (!conGiorno || !spGiorno || dKey(p.data) === spGiorno) && (!lega || p.comp === lega)
    && (!sera || SPM !== '1x2' || spSera(p)) && (!alta || p.affidabilita === 'ALTA'));
}
// la giocata di una partita: in 1X2 il segno più probabile, nei gol il mercato scelto
function spGiocata(p) {
  if (SPM === '1x2') { const k = ['1', 'X', '2'].reduce((a, b) => p.p[b] > p.p[a] ? b : a, '1'); return { k, v: p.p[k] }; }
  if (SPM === 'naz') {
    const m = $('#sp-merc-naz').value, best = ks => ks.reduce((a, b) => (p.p[b] || 0) > (p.p[a] || 0) ? b : a);
    const k = m === 'auto' ? best(['1', 'X', '2']) : m === 'dc' ? best(['1X', 'X2', '12']) : m;
    return { k, v: p.p[k] };
  }
  const k = $('#sp-merc').value; return { k, v: p.p[k] };
}
function spCella(p, k, lab, v, hi) {
  if (v == null) return '';
  const bk = spBook(p, k), val = bk && bk > 1 / v, sel = SPSEL[SPM].some(x => x.id === p.sid && x.k === k);
  return `<button class="mc${hi ? ' hi' : ''}${sel ? ' sel' : ''}" data-id="${esc(p.sid)}" data-k="${esc(k)}"><small>${esc(lab)}</small><b>${pct(v)}</b><em>equa ${quota(v)}</em>${bk ? `<em class="bk${val ? ' val' : ''}">book ${(+bk).toFixed(2)}</em>` : ''}</button>`;
}
function spRiga(p) {
  const g = spGiocata(p);
  const celle = SPM === 'naz' ? ['1', 'X', '2'].map(k => spCella(p, k, k, p.p[k], k === g.k)).join('') + (['1', 'X', '2'].includes(g.k) ? '' : spCella(p, g.k, NOMEM[g.k] || g.k, g.v, true).replace('class="mc', 'class="mc wide'))
    : SPM === '1x2' ? ['1', 'X', '2'].map(k => spCella(p, k, k, p.p[k], k === g.k)).join('')
    : spCella(p, g.k, NOMEM[g.k], g.v, true);
  const aff = p.affidabilita !== 'ALTA' ? `<span class="tag">Storico ${esc((p.affidabilita || '').toLowerCase())}</span>` : '';
  const fonte = p.fonte ? `<span class="tag acc">Quote ${esc(p.fonte)}</span>` : '<span class="tag">Senza quote: solo modello</span>';
  return `<article class="sp-r"><div class="ora">${p.data.slice(11, 16)}<small>${fmtDay(dKey(p.data))}</small></div>
    <div class="teams"><div class="t">${esc(p.casa)}</div><div class="t">${esc(p.ospite)}</div><div class="c">${esc(spNome(p.comp))}</div>
    ${p.ris ? `<div class="c">Risultati più probabili: ${esc(p.ris)}</div>` : ''}<div class="tags sp-tags">${fonte}${aff}${p.neutro ? '<span class="tag">Campo neutro</span>' : ''}</div></div>
    <div class="mk sp-mk${SPM === 'gol' ? ' uno' : ''}">${celle}</div></article>`;
}

function spLeghe() {
  const box = $('#sp-leghe'), all = spPartite(), cnt = {};
  all.forEach(p => cnt[p.comp] = (cnt[p.comp] || 0) + 1);
  const sez = SEZ[SPM];
  if (SPM === 'naz') {
    const R = Object.entries(MONDO.leghe).filter(([c, l]) => (l.sez === 'Z' && cnt[c]) || c === 'naz.TUTTE').filter(([, l]) => l.stats);
    box.innerHTML = `<details class="sez"><summary>Come finiscono le partite tra nazionali (ultimi 12 mesi)</summary><div class="sez-b tbl"><table><thead><tr><th>Competizione</th><th class="n">1</th><th class="n">X</th><th class="n">2</th><th class="n">Over 2.5</th><th class="n">Gol</th><th class="n">In programma</th></tr></thead><tbody>` +
      R.map(([c, l]) => { const s = l.stats; return `<tr><td>${esc(l.paese)} · ${esc(l.nome)}</td><td class="n">${pct(s['1'])}</td><td class="n">${pct(s.X)}</td><td class="n">${pct(s['2'])}</td><td class="n">${pct(s.O25)}</td><td class="n">${pct(s.GG)}</td><td class="n">${cnt[c] || ''}</td></tr>`; }).join('') +
      '</tbody></table><p class="note">Le percentuali sono della confederazione (le amichevoli: tutte le nazionali). Tra nazionali le differenze di forza sono enormi (es. Spagna contro San Marino): per questo i favoriti netti escono spesso, ma pagano poco.</p></div></details>';
    return;
  }
  const L = Object.entries(MONDO.leghe).filter(([, l]) => l.sez.includes(sez) && l.stats);
  if (SPM === '1x2') {
    L.sort((a, b) => (cnt[b[0]] || 0) - (cnt[a[0]] || 0));
    box.innerHTML = `<details class="sez"><summary>I campionati della sezione (ultimi 12 mesi)</summary><div class="sez-b tbl"><table><thead><tr><th>Campionato</th><th class="n">Vince casa</th><th class="n">Pareggio</th><th class="n">Vince ospite</th><th class="n">In programma</th></tr></thead><tbody>` +
      L.map(([c, l]) => `<tr><td>${esc(l.paese)} · ${esc(l.nome)}</td><td class="n">${pct(l.stats['1'])}</td><td class="n">${pct(l.stats.X)}</td><td class="n">${pct(l.stats['2'])}</td><td class="n">${cnt[c] || 0}</td></tr>`).join('') +
      '</tbody></table><p class="note">In Sudamerica il pareggio esce spesso (circa 1 partita su 3 in Argentina): i favoriti netti sono meno frequenti che in Europa.</p></div></details>';
    return;
  }
  const m = $('#sp-merc').value, sk = STATK[m];
  L.sort((a, b) => (b[1].stats[sk] || 0) - (a[1].stats[sk] || 0));
  box.innerHTML = `<details class="sez" open><summary>Quanto esce davvero: ${esc(NOMEM[m])} per campionato (ultimi 12 mesi)</summary><div class="sez-b tbl"><table><thead><tr><th>Campionato</th><th class="n">Gol a partita</th><th class="n">Over 1.5</th><th class="n">Over 2.5</th><th class="n">1°T Over 0.5</th><th class="n">Gol</th><th class="n">In programma</th></tr></thead><tbody>` +
    L.map(([c, l]) => { const s = l.stats; const h = k => k === sk ? ' class="n hi"' : ' class="n"';
      return `<tr><td>${esc(l.paese)} · ${esc(l.nome)}</td><td class="n">${s.gol.toFixed(2)}</td><td${h('O15')}>${pct(s.O15)}</td><td${h('O25')}>${pct(s.O25)}</td><td${h('T1O05')}>${pct(s.T1O05)}</td><td${h('GG')}>${pct(s.GG)}</td><td class="n">${cnt[c] || 0}</td></tr>`; }).join('') +
    `</tbody></table><p class="note">Per confronto, la Serie A sta intorno al 50% di Over 2.5. Attenzione: "esce spesso" non vuol dire "conviene". I bookmaker conoscono queste percentuali e abbassano la quota (in Eredivisie un Over 2.5 paga spesso 1,50-1,60). La giocata ha valore solo quando la quota del bookmaker è più alta della quota equa: in quel caso la casella "book" è verde.</p></div></details>`;
}

function spDays() {
  const L = spFiltrate(false), cnt = {};
  L.forEach(p => cnt[dKey(p.data)] = (cnt[dKey(p.data)] || 0) + 1);
  const keys = Object.keys(cnt).sort(), oggi = oggiKey();
  if (spGiorno && !keys.includes(spGiorno)) spGiorno = null;
  $('#sp-days').innerHTML = `<button class="day" data-k="">Tutti<small>${L.length}</small></button>` +
    keys.map(k => `<button class="day" data-k="${k}">${k === oggi ? '<b>Oggi</b>' : ''}${fmtDay(k)}<small>${cnt[k]}</small></button>`).join('');
  document.querySelectorAll('#sp-days .day').forEach(b => { b.classList.toggle('on', (b.dataset.k || null) === spGiorno); b.onclick = () => { spGiorno = b.dataset.k || null; spRender(); }; });
}

function spTicket(titolo, sel, vuoto, manuale) {
  if (!sel.length) return `<div class="ticket"><div class="t-h"><b>${titolo}</b></div><div class="empty">${vuoto}</div></div>`;
  const tot = sel.reduce((a, s) => a * s.v, 1), bks = sel.map(s => spBook(s.p, s.k)), tb = bks.every(Boolean) ? bks.reduce((a, b) => a * b, 1) : null;
  return `<div class="ticket"><div class="t-h"><b>${titolo}</b><span>${sel.length} partit${sel.length === 1 ? 'a' : 'e'}</span></div>
    ${sel.map((s, i) => `<div class="t-r"><div class="t-m"><small>${fmtDay(dKey(s.p.data))} ${s.p.data.slice(11, 16)} · ${esc(spNome(s.p.comp))}</small><b>${esc(s.p.casa)} – ${esc(s.p.ospite)}</b></div>
      <div class="t-p"><span class="t-k">${esc(NOMEM[s.k] || s.k)}</span><span class="t-v">${pct(s.v)} <small>equa ${quota(s.v)}${bks[i] ? ` · book ${(+bks[i]).toFixed(2)}` : ''}</small></span></div>
      ${manuale ? `<button class="t-x" data-id="${esc(s.p.sid)}" aria-label="Togli">×</button>` : ''}</div>`).join('')}
    <div class="t-f"><div><small>Probabilità che escano tutte</small><b>${(tot * 100).toFixed(tot < 0.1 ? 1 : 0)}%</b></div>
      <div><small>Quota equa totale</small><b>${quota(tot)}</b></div>${tb ? `<div><small>Quota book totale</small><b>${tb.toFixed(2)}</b></div>` : ''}</div>
    <p class="note">Le quote "book" sono DraftKings o la media dei bookmaker: su Sisal possono essere un po' diverse, controlla prima di giocare.</p></div>`;
}

function spSchedina() {
  const soglia = +$('#sp-soglia').value / 100, max = +$('#sp-max').value, modo = $('#sp-modo').value;
  $('#sp-soglia-v').textContent = Math.round(soglia * 100) + '%';
  const qmin = +$('#sp-qmin').value;
  const C = spFiltrate().map(p => ({ p, ...spGiocata(p) })).filter(s => s.v != null && s.v >= soglia && 1 / s.v >= qmin);
  const val = s => { const b = spBook(s.p, s.k); return b ? b * s.v : 0; };
  C.sort((a, b) => modo === 'valore' ? (val(b) - val(a)) || (b.v - a.v) : b.v - a.v);
  const sel = C.slice(0, max).sort((a, b) => a.p.data.localeCompare(b.p.data));
  $('#sp-out').innerHTML = spTicket('Proposta', sel, `Nessuna partita supera il ${Math.round(soglia * 100)}%. Abbassa la soglia o la quota minima, oppure scegli "Tutti" i giorni.`) +
    `<p class="note">Partite considerate: ${spFiltrate().length} · sopra soglia: ${C.length}.</p>`;
  const tutte = spPartite();
  const mie = SPSEL[SPM].map(x => { const p = tutte.find(q => q.sid === x.id); return p ? { p, k: x.k, v: p.p[x.k] } : null; }).filter(Boolean).sort((a, b) => a.p.data.localeCompare(b.p.data));
  $('#sp-mia').innerHTML = spTicket(SPM === '1x2' ? 'La tua schedina 1X2' : SPM === 'naz' ? 'La tua schedina nazionali' : 'La tua schedina gol', mie, 'Vuota. Tocca una percentuale nella lista qui sotto per aggiungerla.', true) +
    (mie.length ? '<button class="btn-sec" id="sp-svuota">Svuota</button>' : '');
  document.querySelectorAll('#sp-mia .t-x').forEach(b => b.onclick = () => { SPSEL[SPM] = SPSEL[SPM].filter(x => x.id !== b.dataset.id); spRender(); });
  const sv = $('#sp-svuota'); if (sv) sv.onclick = () => { SPSEL[SPM] = []; spRender(); };
}

function spRender() {
  if (!MONDO) return;
  $('#sp-intro').textContent = INTRO[SPM];
  $('#sp-merc').hidden = SPM !== 'gol'; $('#sp-merc-naz').hidden = SPM !== 'naz'; $('#sp-sera-l').hidden = SPM !== '1x2';
  const sez = SEZ[SPM], v = $('#sp-lega').value;
  $('#sp-lega').innerHTML = `<option value="">${SPM === 'naz' ? 'Tutte le competizioni' : 'Tutti i campionati'}</option>` + Object.entries(MONDO.leghe).filter(([, l]) => l.sez && l.sez.includes(sez))
    .map(([c, l]) => `<option value="${c}">${esc(l.paese)} · ${esc(l.nome)}</option>`).join('');
  $('#sp-lega').value = [...$('#sp-lega').options].some(o => o.value === v) ? v : '';
  spDays(); spLeghe(); spSchedina();
  const L = spFiltrate();
  $('#sp-lista').innerHTML = L.length ? L.map(spRiga).join('') : '<div class="empty">Nessuna partita con questi filtri.</div>';
  document.querySelectorAll('#sp-lista .mc').forEach(b => b.onclick = () => {
    const id = b.dataset.id, k = b.dataset.k, S = SPSEL[SPM], i = S.findIndex(x => x.id === id && x.k === k);
    if (i >= 0) S.splice(i, 1); else { SPSEL[SPM] = S.filter(x => x.id !== id); SPSEL[SPM].push({ id, k }); }
    const y = window.scrollY; spRender(); window.scrollTo(0, y);
  });
}

document.querySelectorAll('.seg-b').forEach(b => b.onclick = () => {
  if (b.dataset.m === SPM) return;
  SPM = b.dataset.m; spGiorno = null;
  document.querySelectorAll('.seg-b').forEach(x => x.classList.toggle('on', x === b));
  $('#sp-soglia').value = SPM === '1x2' ? 55 : SPM === 'naz' ? 60 : 65; $('#sp-lega').value = '';
  spRender();
});
['#sp-lega', '#sp-merc', '#sp-merc-naz', '#sp-sera', '#sp-alta', '#sp-soglia', '#sp-max', '#sp-modo', '#sp-qmin'].forEach(s => $(s).addEventListener('input', () => ['#sp-soglia', '#sp-max', '#sp-modo', '#sp-qmin'].includes(s) ? spSchedina() : spRender()));

(async () => {
  try { MONDO = await (await fetch('mondo.json?' + Date.now())).json(); }
  catch (e) { $('#sp-agg').textContent = 'Dati non ancora disponibili: compariranno dopo il prossimo aggiornamento.'; $('#sp-lista').innerHTML = ''; return; }
  const a = MONDO.aggiornato;
  $('#sp-agg').textContent = `Aggiornato ${fmtDay(a.slice(0, 10))} alle ${a.slice(11, 16)} · ${MONDO.partite.length} partite (fonte ESPN)`;
  spRender();
  // quando arrivano anche i dati principali, aggiungo Bundesliga ed Eredivisie alla sezione gol
  const t = setInterval(() => { if (DATA) { clearInterval(t); if (SPM === 'gol') spRender(); } }, 500);
})();

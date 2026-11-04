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
const FAM = { esito: 'Esito e doppia chance', gol: 'Gol: Over/Under, Gol/NoGol', multigol: 'Multigol', combo: 'Combo', esatti: 'Risultati esatti a gruppi',
  t1: '1° tempo', t2: '2° tempo', cart: 'Cartellini', corner: 'Corner', tiri: 'Tiri e tiri in porta', marc: 'Marcatori' };
const LINEE = { Gialli: ['2.5', '3.5', '4.5', '5.5', '6.5'], Corner: ['7.5', '8.5', '9.5', '10.5', '11.5'], Tiri: ['20.5', '22.5', '24.5', '26.5', '28.5'], 'Tiri in porta': ['6.5', '7.5', '8.5', '9.5', '10.5'] };
const LINEE_SQ = { Gialli: ['0.5', '1.5', '2.5'], Corner: ['2.5', '3.5', '4.5', '5.5', '6.5'], Tiri: ['8.5', '10.5', '12.5', '14.5'], 'Tiri in porta': ['2.5', '3.5', '4.5', '5.5'] };
const SENZA_DC = ['Gialli', 'Corner'];
const esitiStat = N => SENZA_DC.includes(N) ? ['1', 'X', '2'] : ['1', 'X', '2', '1X', 'X2', '12'];
const ETI = { Gialli: '1X2 ammonizioni', Corner: '1X2 corner', Tiri: '1X2 tiri totali', 'Tiri in porta': '1X2 tiri in porta' };
const FAMSTAT = { Gialli: 'cart', Corner: 'corner', Tiri: 'tiri', 'Tiri in porta': 'tiri' };
const NOMESTAT = { Gialli: 'Cartellini gialli', Corner: 'Corner', Tiri: 'Tiri totali', 'Tiri in porta': 'Tiri in porta' };
const SHORTME = m => m.replace('Multi Esiti', 'ME').replace('Cluster risultati esatti', 'Cluster');
function mercatiDi(p) {
  if (p._mk) return p._mk;
  const e = X(p), L = [], G = p.Gruppi || {};
  const add = (fam, k, v, lab) => { if (v != null && !isNaN(v)) L.push({ fam, k, p: v, lab: lab || k }); };
  ['1', 'X', '2', '1X', 'X2'].forEach(k => add('esito', k, p[k]));
  add('esito', '12', p['1'] != null ? p['1'] + p['2'] : null);
  ['0.5', '1.5', '2.5', '3.5', '4.5'].forEach(s => { add('gol', 'Over ' + s, p['Over ' + s] ?? e['Over ' + s]); add('gol', 'Under ' + s, p['Under ' + s] ?? e['Under ' + s]); });
  add('gol', 'Gol', p.Gol); add('gol', 'NoGol', p.NoGol);
  Object.keys(e).filter(k => k.includes(' + ')).forEach(k => add('combo', k, e[k]));
  ['1', 'X', '2', '1X', 'X2', 'Over 0.5', 'Under 0.5', 'Over 1.5', 'Under 1.5', 'Gol'].forEach(k => { add('t1', '1T ' + k, e['1T ' + k], '1° tempo ' + k); add('t2', '2T ' + k, e['2T ' + k], '2° tempo ' + k); });
  Object.keys(LINEE).forEach(N => {
    const f = FAMSTAT[N], nm = NOMESTAT[N];
    LINEE[N].forEach(s => { add(f, `${N} Over ${s}`, e[`${N} Over ${s}`], `${nm} Over ${s}`); add(f, `${N} Under ${s}`, e[`${N} Under ${s}`], `${nm} Under ${s}`); });
    esitiStat(N).forEach(k => add(f, `${ETI[N]} ${k}`, e[`${ETI[N]} ${k}`]));
    ['casa', 'ospite'].forEach(sq => LINEE_SQ[N].forEach(s => {
      const t = sq === 'casa' ? p.Casa : p.Ospite;
      add(f, `${N} ${sq} Over ${s}`, e[`${N} ${sq} Over ${s}`], `${nm} ${t} Over ${s}`); add(f, `${N} ${sq} Under ${s}`, e[`${N} ${sq} Under ${s}`], `${nm} ${t} Under ${s}`);
    }));
  });
  Object.keys(G).forEach(m => {
    if (m === 'Cluster personalizzato') return;
    const fam = m.startsWith('Multigol') ? 'multigol' : 'esatti';
    G[m].forEach(x => add(fam, `G|${m}|${x.esito}`, x.p, m.startsWith('Multigol') ? x.esito : m === 'Esatti' ? `Risultato esatto ${x.esito}` : `${SHORTME(m)}: ${x.esito}`));
  });
  ['casa', 'ospite'].forEach(sq => ((p.Marcatori || {})[sq] || []).forEach(a => add('marc', `M|${a.nome}`, a.p, `Segna ${a.nome}`)));
  return (p._mk = L);
}
// quote reali del bookmaker (quando disponibili) per i mercati principali
function book(p, k) {
  const q = p.Quote || {};
  if (k === '1') return q.q1; if (k === 'X') return q.qx; if (k === '2') return q.q2;
  if (q.linea != null && k === 'Over ' + q.linea) return q.qover;
  if (q.linea != null && k === 'Under ' + q.linea) return q.qunder;
  return null;
}
const pid = p => p.Data + '|' + p.Casa + '|' + p.Ospite;
let MIA = [];   // schedina personale: {id, k}
const inMia = (p, k) => MIA.some(x => x.id === pid(p) && x.k === k);

// cambiando scheda si ricorda dove eri arrivato (posizione e partite aperte restano uguali)
const SCROLL = {}; let VISTA = 'partite';
const OPEN = new Set();
document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  if (b.dataset.view === VISTA) { window.scrollTo(0, 0); return; }
  SCROLL[VISTA] = window.scrollY;
  VISTA = b.dataset.view;
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + VISTA));
  if (VISTA === 'schedina') schedina();
  requestAnimationFrame(() => window.scrollTo(0, SCROLL[VISTA] || 0));
});

function forma(s) { return `<span class="forma">${[...(s || '')].map(c => `<i class="f${c}">${c}</i>`).join('')}</span>`; }

function cella(p, k, lab, v, hi) {
  const bk = book(p, k), val = bk && v > 0 && bk > 1 / v;
  return `<button class="mc${hi ? ' hi' : ''}${inMia(p, k) ? ' sel' : ''}" data-id="${esc(pid(p))}" data-k="${esc(k)}" title="Tocca per aggiungere alla tua schedina"><small>${esc(lab)}</small><b>${pct(v)}</b><em>equa ${quota(v)}</em>${bk ? `<em class="bk${val ? ' val' : ''}">book ${(+bk).toFixed(2)}</em>` : ''}</button>`;
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

const sez = (id, titolo, corpo, aperta) => `<details class="sez" data-s="${id}"${aperta ? ' open' : ''}><summary>${titolo}</summary><div class="sez-b">${corpo}</div></details>`;
const f1 = v => v == null ? '–' : (+v).toFixed(1);

function card(p) {
  const ora = p.Data.slice(11, 16);
  const tags = [];
  tags.push(`<span class="tag">Segno <b>${esc(p['Segno favorito'])}</b></span>`);
  if (p['Effetto assenze'] && p['Effetto assenze'] !== 'trascurabile') tags.push(`<span class="tag warn">Assenze: ${esc(p['Effetto assenze'])}</span>`);
  if (p['Disaccordo col mercato']) {
    const m = /segno (\w)/.exec(p['Disaccordo col mercato']), d = /\(([+-]\d+) punti\)/.exec(p['Disaccordo col mercato']);
    tags.push(`<span class="tag bad">Modello diverso dal mercato sul ${m ? m[1] : ''}: ${d ? d[1].replace('-', '−') : ''} punti</span>`);
  }
  if (p['Fonte quote']) tags.push(`<span class="tag acc">Quote ${esc(p['Fonte quote'])}</span>`);
  if (p['Affidabilità dati'] !== 'ALTA') tags.push(`<span class="tag">Affidabilità ${esc(p['Affidabilità dati'].toLowerCase())}</span>`);
  if (p.Formazioni && /probabile|ufficiale/.test(p.Formazioni)) tags.push(`<span class="tag acc">Formazione ${esc(p.Formazioni)}</span>`);
  const id = pid(p), aperta = OPEN.has(id);
  return `<article class="card${aperta ? ' open' : ''}" data-id="${esc(id)}">
    <button class="card-h" aria-expanded="${aperta}">
      <div class="ora">${ora}<small>${fmtDay(dKey(p.Data))}</small></div>
      <div class="teams"><div class="t">${esc(p.Casa)}</div><div class="t">${esc(p.Ospite)}</div><div class="c">${esc(p.Competizione)}</div></div>
      <div class="pick"><div class="k">Più probabile</div><div class="v">${esc(p['Esito più probabile'])}</div></div>
    </button>
    <div class="bar" role="img" aria-label="1 ${pct(p['1'])}, X ${pct(p.X)}, 2 ${pct(p['2'])}">
      <div class="b1" style="flex:${p['1']}">1 ${pct(p['1'])}</div><div class="bx" style="flex:${p.X}">X ${pct(p.X)}</div><div class="b2" style="flex:${p['2']}">2 ${pct(p['2'])}</div>
    </div>
    <div class="tags">${tags.join('')}</div>
    <div class="det">${aperta ? dettagli(p) : ''}</div></article>`;
}

function gruppoTab(p, m, righe) {
  const top = [...righe].sort((a, b) => b.p - a.p).slice(0, 3).map(x => x.esito);
  return `<div class="mk mk2">${righe.map(x => cella(p, `G|${m}|${x.esito}`, x.esito, x.p, top.includes(x.esito))).join('')}</div>`;
}

function dettagli(p) {
  const e = X(p), sc = p.scheda || {}, G = p.Gruppi || {}, Q = p.Quote || {};
  const C = esc(p.Casa), O = esc(p.Ospite), n = v => v == null ? '–' : v;
  const best = (p['Esito più probabile'] || '').split(' (')[0];
  const gfs = s => { const [a, b] = String(s || '').split(' / '); return b ? `${a} fatti · ${b} subiti` : '–'; };
  // --- principali
  const esiti = griglia(p, ['1', 'X', '2', '1X', 'X2', '12'].map(k => [k, k, k === '12' ? p['1'] + p['2'] : p[k]]), best);
  const gol = griglia(p, ['0.5', '1.5', '2.5', '3.5', '4.5'].flatMap(s => [['Over ' + s, 'Over ' + s, p['Over ' + s] ?? e['Over ' + s]], ['Under ' + s, 'Under ' + s, p['Under ' + s] ?? e['Under ' + s]]]).concat([['Gol', 'Gol', p.Gol], ['NoGol', 'NoGol', p.NoGol]]), best);
  const quoteTxt = p['Fonte quote'] ? `<span>Quote ${esc(p['Fonte quote'])}</span><span>1 ${n(Q.q1)} · X ${n(Q.qx)} · 2 ${n(Q.q2)}${Q.linea != null ? ` · Over ${Q.linea} ${n(Q.qover)} · Under ${Q.linea} ${n(Q.qunder)}` : ''}</span>
      <span>Bookmaker 1-X-2 (senza margine)</span><span>${pct(p['Bookmaker 1'])} · ${pct(p['Bookmaker X'])} · ${pct(p['Bookmaker 2'])}</span>` : `<span>Quote</span><span>non ancora disponibili (di solito escono 2-4 giorni prima)</span>`;
  const dis = p['Disaccordo col mercato'] ? `<span>Modello vs mercato</span><span>${esc(p['Disaccordo col mercato'].replace('-', '−'))}</span>` : '';
  const principali = `<p class="hint">Tocca una casella per aggiungerla alla tua schedina. "equa" = quota giusta secondo il sistema; "book" = quota reale del bookmaker (verde se paga più dell'equa).</p>
    <div class="lab2">Esito e doppia chance</div>${esiti}<div class="lab2">Gol</div>${gol}
    <div class="kv">
      <span>Gol attesi</span><span>${C} ${p['xG casa'].toFixed(2)} – ${p['xG ospite'].toFixed(2)} ${O}</span>
      <span>Solo statistica 1-X-2</span><span>${esc(p['Solo statistica 1-X-2'])}</span>
      <span>Statistica + assenze 1-X-2</span><span>${esc(p['Solo modello 1-X-2'] || '–')}</span>${quoteTxt}${dis}
      <span>Formazioni</span><span>${esc(p.Formazioni)}</span>${p.Arbitro ? `<span>Arbitro</span><span>${esc(p.Arbitro)}</span>` : ''}</div>`;
  // --- risultati esatti e gruppi
  let esatti = '';
  if (G.Esatti) {
    const pers = (G['Cluster personalizzato'] || []).slice(1, 5);
    // il gruppo più probabile per numero di risultati, tra quelli che si giocano davvero
    const cand = Object.keys(G).filter(m => /^Multi Esiti|^Cluster risultati/.test(m)).flatMap(m => G[m].filter(x => !/ALTRO|pareggio/.test(x.esito)).map(x => ({ m, ...x, n: x.esito.split('/').length })));
    const migliori = [2, 3, 4].map(k => cand.filter(x => x.n === k).sort((a, b) => b.p - a.p)[0]).filter(Boolean);
    esatti = `<div class="lab2">Risultati esatti più probabili</div>${griglia(p, G.Esatti.slice(0, 8).map(x => [`G|Esatti|${x.esito}`, x.esito, x.p]))}
      <div class="lab2">I gruppi migliori che trovi in schedina (Multi Esiti / Cluster)</div>
      <div class="mk mk2">${migliori.map(x => cella(p, `G|${x.m}|${x.esito}`, `${SHORTME(x.m)} · ${x.esito}`, x.p, true)).join('')}</div>
      <p class="note">Il tuo "cluster su misura": i ${pers.length + 1} risultati più probabili messi insieme coprono ${pers.length ? pct(pers[pers.length - 1].p) : '–'} dei casi (${pers.map(x => `${x.k} risultati ${pct(x.p)}`).join(' · ')}).</p>
      ${['Multi Esiti 1', 'Multi Esiti 2', 'Multi Esiti 3', 'Multi Esiti 4', 'Multi Esiti 5', 'Cluster risultati esatti'].filter(m => G[m]).map(m => `<div class="lab2">${m}</div>${gruppoTab(p, m, G[m])}`).join('')}
      <p class="note">Gruppi standard ADM, uguali su Sisal, Lottomatica, Snai. In evidenza i 3 esiti più probabili di ogni mercato.</p>`;
  }
  const multigol = G.Multigol ? `${gruppoTab(p, 'Multigol', G.Multigol)}<div class="lab2">Multigol ${C}</div>${gruppoTab(p, 'Multigol casa', G['Multigol casa'] || [])}<div class="lab2">Multigol ${O}</div>${gruppoTab(p, 'Multigol ospite', G['Multigol ospite'] || [])}` : '';
  // --- combo
  const combos = Object.keys(e).filter(k => k.includes(' + ')).sort((a, b) => e[b] - e[a]);
  const cmb = griglia(p, combos.map(k => [k, k, e[k]])).replace('class="mk"', 'class="mk mk2"') + '<p class="note">Probabilità che si verifichino tutte le condizioni nella stessa partita.</p>';
  // --- tempi
  const tempo = n => griglia(p, ['1', 'X', '2', '1X', 'X2', 'Over 0.5', 'Under 0.5', 'Over 1.5', 'Under 1.5', 'Gol'].map(k => [`${n} ${k}`, k, e[`${n} ${k}`]]));
  const tempi = `<div class="lab2">1° tempo</div>${tempo('1T')}<p class="note">Risultati più probabili all'intervallo: ${esc(e['1T risultati probabili'] || '–')}</p>
    <div class="lab2">2° tempo (solo gol del secondo tempo)</div>${tempo('2T')}<p class="note">Tempo con più gol: 1° ${pct(e['Tempo più gol: 1°'])} · 2° ${pct(e['Tempo più gol: 2°'])} · pari ${pct(e['Tempo più gol: pari'])}</p>`;
  // --- statistiche contabili (gialli, corner, tiri)
  const stat = (N, extraKV = '') => {
    if (e[`${N} attesi`] == null) return '<p class="note">Dato non disponibile per questa partita.</p>';
    const tot = griglia(p, LINEE[N].flatMap(s => [[`${N} Over ${s}`, `Over ${s}`, e[`${N} Over ${s}`]], [`${N} Under ${s}`, `Under ${s}`, e[`${N} Under ${s}`]]]));
    const x12 = griglia(p, esitiStat(N).map(k => [`${ETI[N]} ${k}`, k, e[`${ETI[N]} ${k}`]]));
    const sq = s => griglia(p, LINEE_SQ[N].flatMap(l => [[`${N} ${s} Over ${l}`, `Over ${l}`, e[`${N} ${s} Over ${l}`]], [`${N} ${s} Under ${l}`, `Under ${l}`, e[`${N} ${s} Under ${l}`]]]));
    return `<div class="kv"><span>${NOMESTAT[N]} attesi</span><span>${f1(e[`${N} attesi`])} (${C} ${f1(e[`${N} casa attesi`])} · ${O} ${f1(e[`${N} ospite attesi`])})</span>${extraKV}</div>
      <div class="lab2">Totale partita</div>${tot}<div class="lab2">${ETI[N]} (chi ne fa di più)</div>${x12}
      <div class="lab2">${C}</div>${sq('casa')}<div class="lab2">${O}</div>${sq('ospite')}`;
  };
  const cart = stat('Gialli', `<span>Almeno un rosso</span><span>${pct(e['Almeno un rosso'])}</span><span>Media gialli ult.10</span><span>${C} ${n(sc['Gialli medi ult.10 casa'])} · ${O} ${n(sc['Gialli medi ult.10 ospite'])}</span>`);
  const tiri = `<div class="lab2 big">Tiri in porta</div>${stat('Tiri in porta')}<div class="lab2 big">Tiri totali</div>${stat('Tiri')}`;
  // --- marcatori
  const M = p.Marcatori || {};
  const marcSq = (lista, nome) => !lista || !lista.length ? `<p class="note">${nome}: dati marcatori non disponibili.</p>` :
    `<div class="lab2">${nome}</div><div class="mk mk2">${lista.map(a => cella(p, `M|${a.nome}`, `${a.nome}${a.titolare ? ' (tit.)' : ''}`, a.p)).join('')}</div>
     <p class="note">${lista.slice(0, 4).map(a => `${esc(a.nome)}: ${a.gol} gol, xG ${a.xg}, doppietta ${pct(a.p2)}`).join(' · ')}</p>`;
  const marc = marcSq(M.casa, C) + marcSq(M.ospite, O) + '<p class="note">Probabilità che il giocatore segni almeno un gol (rigori compresi). Si basa su gol e xG stagionali, sui minuti attesi (titolare ~80\') e sui gol attesi della squadra. Gli indisponibili sono esclusi.</p>';
  const forma = `<div class="kv">
        <span>${C} – ultime 5 (tutte)</span><span>${forma_(sc['Forma casa (ult.5)'])}</span>
        <span>${O} – ultime 5 (tutte)</span><span>${forma_(sc['Forma ospite (ult.5)'])}</span>
        <span>${C} – ultime 8 in casa</span><span>${forma_(sc['Rendimento in casa ult.8 casa'])}</span>
        <span>${O} – ultime 8 in trasferta</span><span>${forma_(sc['Rendimento in trasferta ult.8 ospite'])}</span>
        <span>${C} – media gol ult.10</span><span>${gfs(sc['Gol fatti/subiti ult.10 casa'])}</span>
        <span>${O} – media gol ult.10</span><span>${gfs(sc['Gol fatti/subiti ult.10 ospite'])}</span>
        <span>% partite Over 2.5 ult.10</span><span>${C} ${n(sc['% Over2.5 ult.10 casa'])}% · ${O} ${n(sc['% Over2.5 ult.10 ospite'])}%</span>
        <span>% partite con Gol (segnano entrambe) ult.10</span><span>${C} ${n(sc['% Gol ult.10 casa'])}% · ${O} ${n(sc['% Gol ult.10 ospite'])}%</span>
        <span>% partite con gol nel 1° tempo ult.10</span><span>${C} ${n(sc['% gol nel 1T ult.10 casa'])}% · ${O} ${n(sc['% gol nel 1T ult.10 ospite'])}%</span></div>
        <p class="note">Le lettere vanno dalla più vecchia (sinistra) alla più recente (destra). V = vittoria, N = pareggio, P = sconfitta.</p>
        <div class="lab2">Precedenti</div><div class="h2h">${(sc['Precedenti (ult.5)'] || '').split(' | ').map(x => `<span>${esc(x)}</span>`).join('')}</div>`;
  const S = [['princ', 'Mercati principali e quote', principali], ['esatti', 'Risultati esatti a gruppi', esatti], ['multigol', 'Multigol', multigol],
    ['combo', 'Combo', cmb], ['tempi', '1° e 2° tempo', tempi], ['cart', 'Cartellini', cart], ['corner', 'Corner', stat('Corner')],
    ['tiri', 'Tiri in porta e tiri totali', tiri], ['marc', 'Marcatori', marc],
    ['ass', 'Assenti', `<div class="lab2">${C}</div>${assenti(p['Assenti casa (lista)'], p['Assenti casa'])}<div class="lab2">${O}</div>${assenti(p['Assenti ospite (lista)'], p['Assenti ospite'])}`],
    ['forma', 'Forma e precedenti', forma]];
  const ap = SEZ_APERTE[pid(p)] || new Set(['princ']);
  return S.filter(x => x[2]).map(([k, t, c]) => sez(k, t, c, ap.has(k))).join('');
}
const forma_ = s => forma(s);
const SEZ_APERTE = {};

function apri(card, p) {
  const id = card.dataset.id, det = card.querySelector('.det');
  if (card.classList.toggle('open')) {
    OPEN.add(id); det.innerHTML = dettagli(p); bindCelle(det); bindSez(det, id);
  } else { OPEN.delete(id); det.innerHTML = ''; }
  card.querySelector('.card-h').setAttribute('aria-expanded', card.classList.contains('open'));
}
function bindSez(root, id) {
  root.querySelectorAll('details.sez').forEach(d => d.ontoggle = () => {
    const s = SEZ_APERTE[id] || (SEZ_APERTE[id] = new Set(['princ']));
    d.open ? s.add(d.dataset.s) : s.delete(d.dataset.s);
  });
}

let VISIBILI = [];
function render() {
  const comp = $('#comp').value, q = $('#q').value.trim().toLowerCase(), alta = $('#alta').checked, ord = $('#ord').value;
  let L = DATA.partite.filter(p => (!giorno || dKey(p.Data) === giorno) && (!comp || p.Competizione === comp)
    && (!alta || p['Affidabilità dati'] === 'ALTA') && (!q || (p.Casa + ' ' + p.Ospite).toLowerCase().includes(q)));
  const sorters = { data: (a, b) => a.Data.localeCompare(b.Data), forte: (a, b) => numPick(b['Esito più probabile']) - numPick(a['Esito più probabile']),
    assenze: (a, b) => effetto(b) - effetto(a), disaccordo: (a, b) => disacc(b) - disacc(a) };
  L.sort(sorters[ord]); VISIBILI = L;
  if (!L.length) { $('#lista').innerHTML = '<div class="empty">Nessuna partita con questi filtri.</div>'; return; }
  $('#lista').innerHTML = L.map(card).join('');
  const byId = Object.fromEntries(L.map(p => [pid(p), p]));
  document.querySelectorAll('#lista .card').forEach(c => {
    c.querySelector('.card-h').onclick = () => apri(c, byId[c.dataset.id]);
    if (c.classList.contains('open')) { const det = c.querySelector('.det'); bindCelle(det); bindSez(det, c.dataset.id); }
  });
}

function bindCelle(root) {
  root.querySelectorAll('.mc').forEach(b => b.onclick = ev => {
    ev.stopPropagation();
    const id = b.dataset.id, k = b.dataset.k;
    const i = MIA.findIndex(x => x.id === id && x.k === k);
    if (i >= 0) MIA.splice(i, 1);
    else { MIA = MIA.filter(x => x.id !== id); MIA.push({ id, k }); }   // una sola giocata per partita
    syncSel(); contaMia(); schedina();
  });
}
function syncSel() { document.querySelectorAll('.mc').forEach(x => x.classList.toggle('sel', MIA.some(m => m.id === x.dataset.id && m.k === x.dataset.k))); }
function contaMia() { const t = $('#tab-sch'); t.textContent = MIA.length ? `Schedina (${MIA.length})` : 'Schedina'; }

// ---------------------------------------------------------------- schedina automatica
function ticket(titolo, sel, nota) {
  if (!sel.length) return `<div class="ticket"><div class="t-h"><b>${titolo}</b></div><div class="empty">${nota}</div></div>`;
  const tot = sel.reduce((a, s) => a * s.m.p, 1);
  return `<div class="ticket"><div class="t-h"><b>${titolo}</b><span>${sel.length} partit${sel.length === 1 ? 'a' : 'e'}</span></div>
    ${sel.map(s => `<div class="t-r">
      <div class="t-m"><small>${fmtDay(dKey(s.p.Data))} ${s.p.Data.slice(11, 16)} · ${esc(s.p.Competizione)}</small><b>${esc(s.p.Casa)} – ${esc(s.p.Ospite)}</b></div>
      <div class="t-p"><span class="t-k">${esc(s.m.lab)}</span><span class="t-v">${pct(s.m.p)} <small>quota equa ${quota(s.m.p)}${book(s.p, s.m.k) ? ` · book ${(+book(s.p, s.m.k)).toFixed(2)}` : ''}</small></span></div>
      ${s.manuale ? `<button class="t-x" data-id="${esc(pid(s.p))}" aria-label="Togli">×</button>` : ''}</div>`).join('')}
    <div class="t-f"><div><small>Probabilità che escano tutte</small><b>${(tot * 100).toFixed(tot < 0.1 ? 1 : 0)}%</b></div>
      <div><small>Quota equa totale</small><b>${quota(tot)}</b></div></div>
    <p class="note">Confronta la quota equa con quella che ti offre Sisal: se Sisal paga di più, secondo il sistema la giocata ha valore.</p></div>`;
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
    const C = modo === 'gruppi'
      ? mercatiDi(p).filter(m => m.fam === 'esatti' && /Multi Esiti|Cluster risultati/.test(m.k) && !/ALTRO|pareggio/.test(m.k) && m.p >= soglia)
      : mercatiDi(p).filter(m => fam.includes(m.fam) && m.p >= soglia && 1 / m.p >= qmin);
    if (!C.length) return;
    C.sort((a, b) => modo === 'quota' ? a.p - b.p : b.p - a.p);
    scelte.push({ p, m: C[0] });
  });
  scelte.sort((a, b) => modo === 'quota' ? a.m.p - b.m.p : b.m.p - a.m.p);
  const sel = scelte.slice(0, max).sort((a, b) => a.p.Data.localeCompare(b.p.Data));
  $('#s-out').innerHTML = ticket('Schedina proposta', sel,
    `Nessuna giocata supera il ${Math.round(soglia * 100)}% con quota equa almeno ${qmin.toFixed(2)}. Abbassa la soglia, la quota minima o aggiungi altri mercati.`) +
    `<p class="note">Partite considerate: ${P.length} · con almeno una giocata valida: ${scelte.length}.</p>`;
  const mie = MIA.map(x => { const p = DATA.partite.find(q => pid(q) === x.id); const m = p && mercatiDi(p).find(m => m.k === x.k); return p && m ? { p, m, manuale: true } : null; }).filter(Boolean)
    .sort((a, b) => a.p.Data.localeCompare(b.p.Data));
  $('#s-mia').innerHTML = ticket('La tua schedina', mie, 'Vuota. Nella scheda Partite apri una partita e tocca una percentuale per aggiungerla.') +
    (mie.length ? '<button class="btn-sec" id="s-svuota">Svuota</button>' : '');
  document.querySelectorAll('#s-mia .t-x').forEach(b => b.onclick = () => { MIA = MIA.filter(x => x.id !== b.dataset.id); contaMia(); schedina(); syncSel(); });
  const sv = $('#s-svuota'); if (sv) sv.onclick = () => { MIA = []; contaMia(); schedina(); syncSel(); };
}

function initSchedina() {
  const keys = [...new Set(DATA.partite.map(p => dKey(p.Data)))].sort(), oggi = oggiKey();
  $('#s-giorno').innerHTML = '<option value="">Tutti i giorni</option><option value="p4">Prossimi 4 giorni (una giornata)</option>' + keys.map(k => `<option value="${k}">${k === oggi ? 'Oggi – ' : ''}${fmtDay(k)}</option>`).join('');
  $('#s-giorno').value = keys.includes(oggi) ? oggi : (keys.find(k => k >= oggi) || '');
  [...new Set(DATA.partite.map(p => p.Competizione))].sort().forEach(c => $('#s-comp').insertAdjacentHTML('beforeend', `<option>${esc(c)}</option>`));
  $('#s-fam').innerHTML = Object.entries(FAM).map(([k, v]) => `<label class="chk"><input type="checkbox" class="s-fam" value="${k}" ${['esito', 'gol', 'combo', 'multigol'].includes(k) ? 'checked' : ''}> ${v}</label>`).join('');
  document.querySelectorAll('#v-schedina select, #v-schedina input').forEach(x => x.oninput = x.onchange = schedina);
  $('#s-modo').onchange = () => { if ($('#s-modo').value === 'gruppi' && +$('#s-soglia').value > 40) $('#s-soglia').value = 30; schedina(); };
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
function mercatoBT() {
  const m = DATA.backtest_mercato; if (!m || !m.partite) return '';
  const r = (a, b) => `${((1 - a / b) * 100).toFixed(1)}%`;
  return `<h2>Modello + quote del mercato (backtest 2025/26)</h2><p class="note">Log-loss: più è bassa, meglio prevede. Mescolare il modello con le quote (peso mercato ${Math.round(m.peso_mercato * 100)}%) migliora soprattutto i risultati esatti e rende coerenti tutti i mercati.</p>
  <table><thead><tr><th>Mercato</th><th class="n">Solo modello</th><th class="n">Modello + mercato</th><th class="n">Miglioramento</th></tr></thead><tbody>
  <tr><td>1-X-2</td><td class="n">${m.logloss_1x2.modello.toFixed(3)}</td><td class="n">${m.logloss_1x2.mix.toFixed(3)}</td><td class="n">${r(m.logloss_1x2.mix, m.logloss_1x2.modello)}</td></tr>
  <tr><td>Over/Under 2.5</td><td class="n">${m.logloss_ou25.modello.toFixed(3)}</td><td class="n">${m.logloss_ou25.mix.toFixed(3)}</td><td class="n">${r(m.logloss_ou25.mix, m.logloss_ou25.modello)}</td></tr>
  <tr><td>Risultato esatto</td><td class="n">${m.logloss_esatto.modello.toFixed(3)}</td><td class="n">${m.logloss_esatto.mix.toFixed(3)}</td><td class="n">${r(m.logloss_esatto.mix, m.logloss_esatto.modello)}</td></tr></tbody></table>`;
}
function extraBT() {
  const e = DATA.backtest_extra || {}; const k = Object.keys(e); if (!k.length) return mercatoBT();
  return mercatoBT() + `<h2>Altri mercati (backtest 2025/26)</h2><p class="note">Previsto medio contro frequenza reale: più sono vicini, più il sistema è tarato bene. "Meglio della media" confronta il sistema con chi giocasse sempre la frequenza del campionato.</p>
  <table><thead><tr><th>Mercato</th><th class="n">Partite</th><th class="n">Previsto</th><th class="n">Reale</th><th class="n">Meglio della media</th></tr></thead><tbody>` +
  k.map(m => { const r = e[m], g = (1 - r.brier_modello / r.brier_media_fissa) * 100; return `<tr><td>${esc(m.replace('1T', '1° tempo').replace('2T', '2° tempo').replace('ME4', 'Multi Esiti 4').replace('Top3 esatti', 'I 3 risultati esatti più probabili'))}</td><td class="n">${r.partite}</td><td class="n">${pct(r.previsto_medio)}</td><td class="n">${pct(r.frequenza_reale)}</td><td class="n">${g >= 1 ? '+' + g.toFixed(1) + '%' : 'quasi uguale'}</td></tr>`; }).join('') + '</tbody></table>';
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

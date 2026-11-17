// ---------------------------------------------------------------- tipster a confronto
// Scrivi la giocata di un tipster (Pengwin o altri): l'app la confronta con la probabilità del sistema,
// la chiude da sola quando arriva il risultato e tiene il bilancio vero di ogni tipster.
// Tutto resta salvato solo su questo telefono/browser.
let TIP = LS('tip', []);
const TIPN = () => [...new Set(['Pengwin', ...TIP.map(t => t.t)])];

function tipPartite() {   // partite future: principali + speciali/nazionali
  const ora = oraIT(), L = [];
  (DATA ? DATA.partite : []).forEach(p => { if (p.Data.slice(0, 16) > ora) L.push({ src: 'P', id: pid(p), data: p.Data, casa: p.Casa, ospite: p.Ospite, comp: p.Competizione, p }); });
  if (typeof MONDO !== 'undefined' && MONDO) MONDO.partite.forEach(p => { if (p.data > ora) L.push({ src: 'M', id: 'M|' + p.id, rid: String(p.id), data: p.data, casa: p.casa, ospite: p.ospite, comp: spNome(p.comp), p }); });
  return L.sort((a, b) => a.data.localeCompare(b.data));
}
function tipMercati(x) {
  if (x.src === 'P') return mercatiDi(x.p).map(m => ({ k: m.k, lab: m.lab, v: m.p, fam: m.fam, bk: book(x.p, m.k) }));
  const pp = { ...x.p.p };
  if (pp['1'] != null) { pp['1X'] ??= pp['1'] + pp.X; pp.X2 ??= pp.X + pp['2']; pp['12'] ??= pp['1'] + pp['2']; }
  ['1.5', '2.5', '3.5'].forEach(s => { if (pp['Over ' + s] != null) pp['Under ' + s] ??= 1 - pp['Over ' + s]; });
  if (pp.Gol != null) pp.NoGol ??= 1 - pp.Gol;
  return Object.keys(pp).filter(k => pp[k] != null).map(k => ({ k, lab: (typeof NOMEM !== 'undefined' && NOMEM[k]) || k, v: pp[k], fam: 'esito', bk: spBook(x.p, k) }));
}

// esito automatico dal risultato: r = [gol casa, gol ospite, gol casa 1T, gol ospite 1T]
function tipEsito(t, r) {
  if (!r || r[0] == null) return null;
  const [a, b, ha, hb] = r;
  const base = (k, a, b) => {
    if (k === '1') return a > b; if (k === 'X') return a === b; if (k === '2') return a < b;
    if (k === '1X') return a >= b; if (k === 'X2') return a <= b; if (k === '12') return a !== b;
    let m = /^Over (\d+(?:\.\d)?)$/.exec(k); if (m) return a + b > +m[1];
    m = /^Under (\d+(?:\.\d)?)$/.exec(k); if (m) return a + b < +m[1];
    if (k === 'Gol') return a > 0 && b > 0; if (k === 'NoGol') return !(a > 0 && b > 0);
    return null;
  };
  const una = k => {
    if (k.startsWith('1T ')) return ha == null ? null : base(k.slice(3), ha, hb);
    if (k.startsWith('2T ')) return ha == null ? null : base(k.slice(3), a - ha, b - hb);
    if (k.startsWith('G|')) {
      const [, m, e] = k.split('|'), ris = `${a}-${b}`;
      if (m.startsWith('Multigol')) {
        const n = /(\d+)-(\d+)$/.exec(e); if (!n) return null;
        const g = m === 'Multigol casa' ? a : m === 'Multigol ospite' ? b : a + b; return g >= +n[1] && g <= +n[2];
      }
      if (m === 'Esatti') return e === ris;
      const tok = e.split('/'); if (tok.includes(ris)) return true;
      const alt = new Set(t.alt || []);
      if (e === 'X (pareggio)') return a === b;
      if (e === '1 ALTRO') return a > b && !alt.has(ris);
      if (e === '2 ALTRO') return a < b && !alt.has(ris);
      if (tok.includes('ALTRO')) return t.alt ? !alt.has(ris) : null;
      return false;
    }
    return base(k, a, b);
  };
  const parti = t.k.split(' + '), e = parti.map(una);
  return e.includes(null) ? null : e.every(Boolean);
}
function tipRis(t) {
  if (t.src === 'P') return (DATA && DATA.risultati || {})[t.id];
  return (typeof MONDO !== 'undefined' && MONDO && MONDO.risultati || {})[t.rid];
}
// stato: 'V' vinta, 'P' persa, 'N' nulla (rimborsata), null = in attesa
function tipStato(t) {
  if (t.man) return t.man;
  const e = tipEsito(t, tipRis(t));
  return e == null ? null : e ? 'V' : 'P';
}

function tipForm() {
  const L = tipPartite(), f = ($('#t-cerca').value || '').toLowerCase();
  const sel = $('#t-partita').value;
  const V = L.filter(x => !f || (x.casa + ' ' + x.ospite + ' ' + x.comp).toLowerCase().includes(f)).slice(0, 300);
  $('#t-partita').innerHTML = V.length ? V.map(x => `<option value="${esc(x.id)}">${fmtDay(dKey(x.data))} ${x.data.slice(11, 16)} · ${esc(x.casa)} – ${esc(x.ospite)} (${esc(x.comp)})</option>`).join('') : '<option value="">Nessuna partita trovata</option>';
  if (V.some(x => x.id === sel)) $('#t-partita').value = sel;
  $('#t-nomi').innerHTML = TIPN().map(n => `<option value="${esc(n)}">`).join('');
  tipMerc();
}
function tipMerc() {
  const x = tipPartite().find(y => y.id === $('#t-partita').value), keep = $('#t-merc').value;
  if (!x) { $('#t-merc').innerHTML = ''; tipAnteprima(); return; }
  const M = tipMercati(x), fam = typeof FAM !== 'undefined' ? FAM : {};
  const gr = {}; M.forEach(m => (gr[m.fam] ||= []).push(m));
  $('#t-merc').innerHTML = Object.entries(gr).map(([g, ms]) => `<optgroup label="${esc(fam[g] || g)}">${ms.map(m => `<option value="${esc(m.k)}">${esc(m.lab)} · ${pct(m.v)}</option>`).join('')}</optgroup>`).join('');
  if (M.some(m => m.k === keep)) $('#t-merc').value = keep;
  tipAnteprima();
}
function tipAnteprima() {
  const x = tipPartite().find(y => y.id === $('#t-partita').value), q = numIt($('#t-quota').value);
  const m = x && tipMercati(x).find(z => z.k === $('#t-merc').value);
  if (!m) { $('#t-ant').innerHTML = ''; return; }
  const ev = q ? m.v * q - 1 : null;
  $('#t-ant').innerHTML = `Il sistema: <b>${pct(m.v)}</b> · quota equa <b>${quota(m.v)}</b>${m.bk ? ` · book ${(+m.bk).toFixed(2)}` : ''}` +
    (ev == null ? ' · scrivi la quota per vedere il valore' : ev > 0 ? ` · <b class="pos">d'accordo: valore +${(ev * 100).toFixed(1)}%</b>` : ` · <b class="neg">non d'accordo: valore ${(ev * 100).toFixed(1)}%</b>`);
}
function tipSalva() {
  const x = tipPartite().find(y => y.id === $('#t-partita').value), q = numIt($('#t-quota').value), nome = ($('#t-nome').value || 'Pengwin').trim();
  const m = x && tipMercati(x).find(z => z.k === $('#t-merc').value);
  if (!m) return;
  if (!q) { $('#t-ant').innerHTML = '<b class="neg">Scrivi la quota della giocata (es. 1,85).</b>'; $('#t-quota').focus(); return; }
  const t = { n: Date.now(), t: nome, src: x.src, id: x.id, rid: x.rid, data: x.data, comp: x.comp, casa: x.casa, ospite: x.ospite, k: m.k, lab: m.lab, v: m.v, q };
  if (m.k.startsWith('G|') && x.src === 'P') {   // per "ALTRO": tutti i risultati elencati negli altri gruppi dello stesso mercato
    const g = m.k.split('|')[1]; t.alt = ((x.p.Gruppi || {})[g] || []).flatMap(y => y.esito.split('/')).filter(s => /^\d+-\d+$/.test(s));
  }
  TIP.push(t); LSset('tip', TIP); LSset('tipnome', nome);
  $('#t-quota').value = ''; tipRender();
}

function bilancio(L) {
  const c = L.map(t => [t, tipStato(t)]).filter(x => x[1] === 'V' || x[1] === 'P');
  const n = c.length, v = c.filter(x => x[1] === 'V').length, prof = c.reduce((s, [t, e]) => s + (e === 'V' ? t.q - 1 : -1), 0);
  return { n, v, prof, roi: n ? prof / n : null, qm: n ? c.reduce((s, [t]) => s + t.q, 0) / n : null, pm: n ? c.reduce((s, [t]) => s + t.v, 0) / n : null };
}
function tipRender() {
  if (!$('#t-box') || !DATA) return;
  tipForm();
  const att = TIP.filter(t => tipStato(t) == null).length;
  const righe = [...TIP].sort((a, b) => b.data.localeCompare(a.data)).slice(0, 60).map(t => {
    const st = tipStato(t), ev = t.v * t.q - 1, giocata = t.data <= oraIT(), r = tipRis(t);
    const stato = st === 'V' ? '<b class="pos">Vinta</b>' : st === 'P' ? '<b class="neg">Persa</b>' : st === 'N' ? 'Nulla'
      : giocata ? `<span class="t-man"><button data-n="${t.n}" data-e="V">Vinta</button><button data-n="${t.n}" data-e="P">Persa</button></span>` : 'In attesa';
    return `<div class="t-r"><div><small>${fmtDay(dKey(t.data))} ${t.data.slice(11, 16)} · ${esc(t.comp)} · <b>${esc(t.t)}</b></small><b>${esc(t.casa)} – ${esc(t.ospite)}</b>${r && r[0] != null ? ` <small>(${r[0]}-${r[1]})</small>` : ''}</div>
      <div><span class="t-k">${esc(t.lab)}</span> <small>quota ${t.q.toFixed(2)} · sistema ${pct(t.v)} · <span class="${ev > 0 ? 'pos' : 'neg'}">${ev > 0 ? "d'accordo" : "non d'accordo"} ${ev > 0 ? '+' : ''}${(ev * 100).toFixed(0)}%</span></small></div>
      <div class="t-s">${stato}</div><button class="t-x" data-n="${t.n}" aria-label="Elimina">×</button></div>`;
  }).join('');
  const nomi = [...new Set(TIP.map(t => t.t))];
  const riga = (lab, b) => `<tr><td>${lab}</td><td class="n">${b.n}</td><td class="n">${b.n ? pct(b.v / b.n) : '–'}</td><td class="n">${b.n ? pct(b.pm) : '–'}</td><td class="n">${b.qm ? b.qm.toFixed(2) : '–'}</td><td class="n ${b.prof > 0 ? 'pos' : b.prof < 0 ? 'neg' : ''}">${b.n ? (b.prof > 0 ? '+' : '') + b.prof.toFixed(2) : '–'}</td><td class="n">${b.roi == null ? '–' : (b.roi > 0 ? '+' : '') + Math.round(b.roi * 100) + '%'}</td></tr>`;
  const tab = nomi.length ? `<div class="tbl"><table><thead><tr><th>Tipster</th><th class="n">Chiuse</th><th class="n">Vinte</th><th class="n">Prob. sistema</th><th class="n">Quota media</th><th class="n">Profitto (1 € a giocata)</th><th class="n">Resa</th></tr></thead><tbody>` +
    nomi.map(nm => { const L = TIP.filter(t => t.t === nm); return riga(esc(nm), bilancio(L)) + riga(`<small>↳ quando il sistema era d'accordo</small>`, bilancio(L.filter(t => t.v * t.q > 1))) + riga(`<small>↳ quando non era d'accordo</small>`, bilancio(L.filter(t => t.v * t.q <= 1))); }).join('') + '</tbody></table></div>' : '';
  $('#t-lista').innerHTML = TIP.length ? tab + `<p class="note">${TIP.length} giocate salvate${att ? `, ${att} ancora da chiudere` : ''}. Le giocate su gol, esito, tempi, multigol e risultati esatti si chiudono da sole quando arriva il risultato (anche qualche ora dopo la partita). Cartellini, corner, tiri e marcatori: tocca Vinta o Persa. Servono almeno 50-100 giocate chiuse prima di dire se un tipster batte davvero le quote.</p>` + righe
    : '<div class="empty">Nessuna giocata salvata. Quando il Pengwin (o un altro tipster) pubblica una giocata, scrivila qui sopra: l\'app ti dice se il sistema è d\'accordo e tiene il suo bilancio.</div>';
  document.querySelectorAll('#t-lista .t-x').forEach(b => b.onclick = () => { TIP = TIP.filter(t => t.n !== +b.dataset.n); LSset('tip', TIP); tipRender(); });
  document.querySelectorAll('#t-lista .t-man button').forEach(b => b.onclick = () => { const t = TIP.find(x => x.n === +b.dataset.n); if (t) { t.man = b.dataset.e; LSset('tip', TIP); tipRender(); } });
}
function initTipster() {
  if (!$('#t-box')) return;
  $('#t-nome').value = LS('tipnome', 'Pengwin');
  $('#t-cerca').oninput = tipForm; $('#t-partita').onchange = tipMerc; $('#t-merc').onchange = tipAnteprima; $('#t-quota').oninput = tipAnteprima;
  $('#t-salva').onclick = tipSalva;
  const t = setInterval(() => { if (DATA) { clearInterval(t); tipRender(); } }, 300);
}
initTipster();

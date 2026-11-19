(function () {
  'use strict';
  var COL = { v: '#2fa35a', a: '#f0b90b', r: '#e0443a' };
  var RAMP = ['#c0392b', '#e07b39', '#e8c547', '#8cc152', '#2fa35a'];
  var SHADE = {
    0: ['#c7e9c0', '#a1d99b', '#74c476', '#31a354', '#006d2c'],
    1: ['#fff3b0', '#ffe066', '#f5c400', '#d19a00', '#9c6b00'],
    2: ['#fcbba1', '#fc9272', '#fb6a4a', '#de2d26', '#a50f15']
  };
  var STYLES = {
    dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
    light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
  };
  var LEVELS = ['secciones', 'barrios', 'distritos'];
  var NAMES = { v: 'Menos de 250 m', a: '250–500 m', r: 'Más de 500 m' };
  // useGrouping 'always': en es-ES los números de 4 cifras no llevan punto por defecto, lo que queda incoherente en listas.
  var nf = (function () { try { return new Intl.NumberFormat('es-ES', { useGrouping: 'always' }); } catch (e) { return new Intl.NumberFormat('es-ES'); } })();
  var fmt = function (x) { return x == null || isNaN(x) ? '—' : nf.format(Math.round(x)); };
  var pc = function (x) { return x == null || isNaN(x) ? '—' : x.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %'; };
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ESC[c]; }); };
  var getJSON = function (f) { return fetch('data/' + f).then(function (r) { if (!r.ok) throw new Error(f); return r.json(); }); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  var S = {
    level: 'secciones', theme: document.documentElement.dataset.theme === 'light' ? 'light' : 'dark',
    rl: 'distritos', order: 'best', sort: 'v', q: '', tab: 'rank', tsort: { k: 'nombre', d: 1 },
    sk: 'a', sord: 'desc', sq: '', near: false, k: 0
  };
  var AMP = { curve: null, pts: null, rows: [], drawn: 0, max: 0, raf: 0 };
  // movil: la pagina se desplaza (mapa arriba, panel debajo)
  var movil = function () { return window.matchMedia && window.matchMedia('(max-width: 800px)').matches; };
  function verMapa() { if (movil()) try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, 0); } }
  function verPanel() { if (movil()) { var t = document.querySelector('.tabs'); if (t) try { t.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { t.scrollIntoView(); } } }
  var ampOn = function () { return S.tab === 'amp' && !!AMP.curve && !!AMP.pts; };
  var meta = {}, agg = null, geo = {}, bases = null, hasPM = false, map, popup;
  var val = function (p, k) { var x = p[k]; return x == null || x === '' ? null : Number(x); };

  // ---------- tema ----------
  function applyTheme() {
    document.documentElement.dataset.theme = S.theme;
    $('#theme').textContent = S.theme === 'dark' ? '☀' : '☾';
  }
  $('#theme').onclick = function () {
    S.theme = S.theme === 'dark' ? 'light' : 'dark';
    store.set('bicing_tema', S.theme); applyTheme();
    if (map) map.setStyle(STYLES[S.theme], { diff: false });
    renderLegend();
  };
  applyTheme();

  // ---------- onboarding ----------
  var step = 0;
  function steps() {
    var gen = meta.generado ? new Date(meta.generado).toLocaleDateString('es-ES') : '—';
    return [
      '<h2>Qué muestra este mapa</h2><p>Cuánta población de Barcelona vive cerca de una estación de Bicing, midiendo <b>andando por la red peatonal real</b> hasta la base más cercana.</p><ul class="lv"><li><i style="background:' + COL.v + '"></i><b>Verde</b>: a menos de 250 m</li><li><i style="background:' + COL.a + '"></i><b>Amarillo</b>: de 250 a 500 m</li><li><i style="background:' + COL.r + '"></i><b>Rojo</b>: a más de 500 m</li></ul>',
      '<h2>Método</h2><p>La población del padrón/censo por sección se reparte entre los edificios residenciales del Catastro según su número de viviendas.</p><p>La distancia se calcula por la red peatonal de OpenStreetMap con un Dijkstra multiorigen desde todas las bases.</p><p class="muted">Datos generados el ' + esc(gen) + '.</p>',
      '<h2>Cómo usarlo</h2><ul><li>Elige la <b>agregación</b> (secciones, barrios o distritos) en la barra superior.</li><li><b>Zonas</b> ordena distritos y barrios; <b>Estaciones</b> ordena las bases por población residente a menos de 250 m y a 250–500 m. Pasa el ratón para resaltar y púlsalo para acercarte.</li><li>Acerca el mapa y <b>pulsa un edificio</b> para ver su población y su distancia a la base.</li></ul>',
      '<h2>Fuentes</h2><ul class="src">' + (meta.fuentes || []).map(function (f) {
        return '<li><a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.nombre) + '</a>' + (f.referencia ? ' · ref. ' + esc(f.referencia) : '') + (f.fecha_descarga ? ' · descargado ' + esc(f.fecha_descarga) : '') + '</li>';
      }).join('') + '</ul>'
    ];
  }
  function renderOb() {
    var s = steps();
    $('#ob-body').innerHTML = s[step];
    $('#ob-dots').innerHTML = s.map(function (_, i) { return '<i class="' + (i === step ? 'on' : '') + '"></i>'; }).join('');
    $('#ob-next').textContent = step === s.length - 1 ? 'Empezar' : 'Siguiente';
  }
  function openOb() { step = 0; renderOb(); $('#modal').hidden = false; }
  function closeOb() { $('#modal').hidden = true; store.set('bicing_visto', '1'); }
  $('#ob-next').onclick = function () { if (step >= steps().length - 1) closeOb(); else { step++; renderOb(); } };
  $('#ob-skip').onclick = function (e) { e.preventDefault(); closeOb(); };
  $('#modal').addEventListener('click', function (e) { if (e.target === this) closeOb(); });
  $('#about').onclick = function (e) { e.preventDefault(); openOb(); };
  $('#help').onclick = openOb;
  $('#legend').addEventListener('click', function (e) { if (e.target.closest('.lg-tg')) this.classList.toggle('open'); });

  // ---------- leyenda ----------
  function renderLegend() {
    var c = meta.cortes_poblacion_edificio, bk = '';
    if (c && c.length >= 4) bk = '<div class="bk"><span>≤' + fmt(c[0]) + '</span><span>' + fmt(c[1]) + '</span><span>' + fmt(c[2]) + '</span><span>&gt;' + fmt(c[3]) + ' hab.</span></div>';
    var rows = [0, 1, 2].map(function (n) {
      return '<div class="brow"><b>' + ['&lt; 250 m', '250–500', '&gt; 500 m'][n] + '</b><div class="sw">' + SHADE[n].map(function (x) { return '<i style="background:' + x + '"></i>'; }).join('') + '</div></div>';
    }).join('');
    var amp = ampOn();
    $('#legend').innerHTML = '<button class="lg-tg" type="button" aria-label="Mostrar u ocultar leyenda">Leyenda</button>' + (amp ? '' : '<h4>% población a &lt; 250 m (' + (S.level) + ')</h4><div class="ramp">' +
      RAMP.map(function (x) { return '<span style="background:' + x + '"></span>'; }).join('') + '</div><div class="rl"><span>0 %</span><span>100 %</span></div>') +
      '<h4>' + (amp ? 'Edificios con las estaciones nuevas' : 'Edificios (zoom 14+)') + '</h4>' + rows + '<div class="rl" style="margin-left:52px;font-size:9px"><span>menos → más población por edificio</span></div>' + bk +
      '<div class="st"><i></i>Estación de Bicing</div>' + (amp ? '<div class="st stn"><i></i>Estación nueva propuesta</div>' : '');
  }

  // ---------- mapa ----------
  function colorExpr() {
    var f = 'pct_v';
    return ['case', ['<=', ['to-number', ['get', 'pob'], 0], 0], 'rgba(0,0,0,0)', ['has', f], ['step', ['to-number', ['get', f], 0], RAMP[0], 20, RAMP[1], 40, RAMP[2], 60, RAMP[3], 80, RAMP[4]], S.theme === 'dark' ? '#3a3d44' : '#d5d8de'];
  }
  function bColor(lvl) {
    var k = ['coalesce', ['get', 'k'], 0]; // k = clase de población (sombreado), no confundir con S.k (estaciones nuevas)
    var m = function (n) { return ['match', k, 0, SHADE[n][0], 1, SHADE[n][1], 2, SHADE[n][2], 3, SHADE[n][3], SHADE[n][4]]; };
    return ['match', lvl || ['get', 'n'], 0, m(0), 1, m(1), m(2)];
  }
  // nivel con S.k estaciones nuevas: kv<=k -> 0; ka<=k -> 1; si no, el actual n
  function ampLevel(kk) {
    return ['case', ['all', ['has', 'kv'], ['<=', ['to-number', ['get', 'kv'], 1e9], kk]], 0,
      ['all', ['has', 'ka'], ['<=', ['to-number', ['get', 'ka'], 1e9], kk]], 1, ['to-number', ['get', 'n'], 2]];
  }
  function ampBuildingLevel(p, kk) {
    if (p.kv != null && p.kv !== 'null' && Number(p.kv) <= kk) return 0;
    if (p.ka != null && p.ka !== 'null' && Number(p.ka) <= kk) return 1;
    return Number(p.n);
  }
  var cssv = function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
  var baseFilter = function (id) { return ['==', ['to-string', ['get', 'base_id']], String(id)]; };
  var hlFilter = function (cod) { return ['==', ['to-string', ['get', 'cod']], String(cod)]; };

  // Idempotentes: setStyle encadenados (cambios de tema rápidos) pueden disparar style.load varias veces.
  function addSrc(id, src) { if (!map.getSource(id)) map.addSource(id, src); }
  function addLyr(l) { if (!map.getLayer(l.id)) map.addLayer(l); }
  function addAll() { addAllInner(); setLevel(S.level); applyAmpMode(); }
  function addAllInner() {
    var dark = S.theme === 'dark';
    LEVELS.forEach(function (n) {
      if (!geo[n]) return;
      addSrc(n, { type: 'geojson', data: geo[n] });
      var vis = n === S.level ? 'visible' : 'none';
      addLyr({ id: 'fill-' + n, type: 'fill', source: n, layout: { visibility: vis },
        paint: { 'fill-color': colorExpr(), 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 10, 0.8, 13, 0.72, 15, 0.12] } });
      addLyr({ id: 'line-' + n, type: 'line', source: n, layout: { visibility: vis },
        paint: { 'line-color': dark ? '#ffffff' : '#222222', 'line-opacity': ['interpolate', ['linear'], ['zoom'], 12, 0.25, 15, 0.12], 'line-width': n === 'secciones' ? 0.3 : 0.8 } });
    });
    if (hasPM) {
      addSrc('edificios', { type: 'vector', url: 'pmtiles://' + new URL('data/edificios.pmtiles', location.href).href, minzoom: 12, maxzoom: 16 });
      addLyr({ id: 'edif-fill', type: 'fill', source: 'edificios', 'source-layer': 'edificios', minzoom: 13.5,
        paint: { 'fill-color': bColor(), 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 13.5, 0, 14.5, 0.85, 16, 0.95] } });
      addLyr({ id: 'edif-fill-amp', type: 'fill', source: 'edificios', 'source-layer': 'edificios', minzoom: 12,
        layout: { visibility: 'none' },
        paint: { 'fill-color': bColor(ampLevel(S.k)), 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 12, 0.8, 14.5, 0.85, 16, 0.95] } });
      addLyr({ id: 'edif-line', type: 'line', source: 'edificios', 'source-layer': 'edificios', minzoom: 16,
        paint: { 'line-color': dark ? 'rgba(0,0,0,.55)' : 'rgba(0,0,0,.35)', 'line-width': 0.5 } });
    }
    ['distritos', 'barrios'].forEach(function (n) {
      if (!geo[n]) return;
      if (!map.getSource(n)) return;
      addLyr({ id: 'hl-' + n, type: 'line', source: n, filter: hlFilter('__none__'),
        paint: { 'line-color': cssv('--accent-hover') || '#5AA8FF', 'line-width': 3 } });
    });
    addSrc('bases', { type: 'geojson', data: bases || 'data/bases.geojson' });
    addLyr({ id: 'bases-hl', type: 'circle', source: 'bases', filter: baseFilter('__none__'),
      paint: { 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': cssv('--accent-hover') || '#5AA8FF', 'circle-stroke-width': 3,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 8, 16, 14] } });
    addLyr({ id: 'bases', type: 'circle', source: 'bases',
      paint: { 'circle-color': cssv('--accent') || '#2D8EFF', 'circle-stroke-color': cssv('--bg-panel') || '#1A1C20', 'circle-stroke-width': 1.5,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 2.5, 16, 6] } });
    if (AMP.pts) {
      // Círculos y resaltado se controlan con opacidad (propiedad de pintado): setFilter obliga a
      // reprocesar la fuente en el worker, que queda en cola tras las teselas de edificios y no se ve al mover el deslizador.
      addSrc('amp', { type: 'geojson', data: AMP.pts });
      addSrc('amp-l', { type: 'geojson', data: AMP.pts }); // fuente aparte para etiquetas (sí usan filtro, por la colisión)
      addLyr({ id: 'amp-hl', type: 'circle', source: 'amp', layout: { visibility: 'none' },
        paint: { 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 3, 'circle-stroke-opacity': ampHlOp(-1), 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 9, 16, 16] } });
      addLyr({ id: 'amp-pts', type: 'circle', source: 'amp', layout: { visibility: 'none' },
        paint: { 'circle-color': '#ff4fd8', 'circle-stroke-color': dark ? '#ffffff' : '#1A1C20', 'circle-stroke-width': 1.5,
          'circle-opacity': ampKOp(S.k), 'circle-stroke-opacity': ampKOp(S.k),
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 3.5, 16, 8] } });
      addLyr({ id: 'amp-lbl', type: 'symbol', source: 'amp-l', filter: ['<=', ['get', 'r'], S.k], minzoom: 13, layout: { visibility: 'none', 'text-field': ['to-string', ['get', 'r']],
        'symbol-sort-key': ['get', 'r'],
        'text-font': ['Montserrat Medium', 'Montserrat Regular'], 'text-size': 11, 'text-offset': [0, -1.1], 'text-allow-overlap': false },
        paint: { 'text-color': dark ? '#ffd0f4' : '#8a0a73', 'text-halo-color': dark ? '#111214' : '#ffffff', 'text-halo-width': 1.5 } });
    }
  }
  function ampKOp(k) { return ['case', ['<=', ['get', 'r'], k], 1, 0]; }
  function ampHlOp(r) { return ['case', ['==', ['get', 'r'], r], 1, 0]; }
  function ampHl(r) { if (map && map.getLayer('amp-hl')) map.setPaintProperty('amp-hl', 'circle-stroke-opacity', ampHlOp(r)); }
  // Modo ampliación: oculta coropletas y edificios normales, muestra edificios recalculados y estaciones nuevas
  function applyAmpMode() {
    if (!map || !map.getStyle()) return;
    var on = ampOn(), v = function (b) { return b ? 'visible' : 'none'; };
    ['amp-pts', 'amp-lbl', 'amp-hl', 'edif-fill-amp'].forEach(function (id) { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', v(on)); });
    if (map.getLayer('edif-fill')) map.setLayoutProperty('edif-fill', 'visibility', v(!on));
    LEVELS.forEach(function (l) {
      if (map.getLayer('fill-' + l)) map.setLayoutProperty('fill-' + l, 'visibility', v(!on && l === S.level));
      if (map.getLayer('line-' + l)) map.setPaintProperty('line-' + l, 'line-opacity', on ? ['interpolate', ['linear'], ['zoom'], 12, 0.12, 15, 0.08] : ['interpolate', ['linear'], ['zoom'], 12, 0.25, 15, 0.12]);
    });
    if (on) applyAmpK();
  }
  function applyAmpK() {
    if (!map || !map.getStyle()) return;
    if (map.getLayer('amp-pts')) { map.setPaintProperty('amp-pts', 'circle-opacity', ampKOp(S.k)); map.setPaintProperty('amp-pts', 'circle-stroke-opacity', ampKOp(S.k)); }
    if (map.getLayer('amp-lbl')) map.setFilter('amp-lbl', ['<=', ['get', 'r'], S.k]);
    if (map.getLayer('edif-fill-amp')) map.setPaintProperty('edif-fill-amp', 'fill-color', bColor(ampLevel(S.k)));
  }
  function setLevel(n) {
    S.level = n;
    LEVELS.forEach(function (l) {
      ['fill-', 'line-'].forEach(function (p) { if (map && map.getLayer(p + l)) map.setLayoutProperty(p + l, 'visibility', l === n && !(p === 'fill-' && ampOn()) ? 'visible' : 'none'); });
    });
    $$('#seg-lvl button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === n); });
    renderLegend();
  }
  $('#seg-lvl').onclick = function (e) { if (e.target.dataset.v) setLevel(e.target.dataset.v); };

  function popupHtml(p, title, sub) {
    var rows = ['v', 'a', 'r'].map(function (k) {
      return '<tr><td><span style="color:' + COL[k] + '">●</span> ' + NAMES[k] + '</td><td>' + fmt(val(p, 'pob_' + k)) + '</td><td>' + pc(val(p, 'pct_' + k)) + '</td></tr>';
    }).join('');
    return '<div class="pop"><h3>' + esc(title) + '</h3>' + (sub ? '<div class="muted">' + esc(sub) + '</div>' : '') +
      '<div>Población: <b>' + fmt(val(p, 'pob')) + '</b></div>' + stack(p, 0) + '<table>' + rows + '</table></div>';
  }
  function stack(p, lab) {
    return '<div class="sbar">' + ['v', 'a', 'r'].map(function (k) {
      var w = val(p, 'pct_' + k) || 0;
      return '<div class="' + k + '" style="width:' + w + '%">' + (lab && w >= 9 ? Math.round(w) + ' %' : '') + '</div>';
    }).join('') + '</div>';
  }
  function showPopup(ll, html) {
    if (popup) popup.remove();
    popup = new maplibregl.Popup({ maxWidth: '300px' }).setLngLat(ll).setHTML(html).addTo(map);
  }
  function onClick(e) {
    var has = function (id) { return map.getLayer(id); };
    var f = has('bases') && map.queryRenderedFeatures(e.point, { layers: ['bases'] })[0];
    if (f) return showPopup(f.geometry.coordinates, stationPopup(f.properties));
    f = has('amp-pts') && ampOn() && map.queryRenderedFeatures(e.point, { layers: ['amp-pts'] })[0];
    if (f) return showPopup(f.geometry.coordinates, ampPopup(f.properties));
    var bl = ampOn() ? 'edif-fill-amp' : 'edif-fill';
    f = has(bl) && map.queryRenderedFeatures(e.point, { layers: [bl] })[0];
    if (f) {
      var p = f.properties, d = (p.d == null || p.d === 'null' || p.d === '') ? null : Number(p.d), n = Number(p.n);
      var lv = ['Menos de 250 m', '250–500 m', 'Más de 500 m'][n] || '—';
      return showPopup(e.lngLat, '<div class="pop"><h3>Edificio</h3>Población estimada: <b>' + fmt(p.p) + ' hab.</b><br>Distancia andando: <b>' +
        (d == null ? '&gt; 1.500 m' : fmt(d) + ' m') + '</b><br>Base más cercana: <b>' + esc(p.b && p.b !== 'null' ? p.b : '—') + '</b><br>Nivel: <b style="color:' + [COL.v, COL.a, COL.r][n] + '">' + lv + '</b>' +
        (ampOn() ? '<br>Con ' + S.k + ' estaci' + (S.k === 1 ? 'ón nueva' : 'ones nuevas') + ': <b style="color:' + [COL.v, COL.a, COL.r][ampBuildingLevel(p, S.k)] + '">' + (['Menos de 250 m', '250–500 m', 'Más de 500 m'][ampBuildingLevel(p, S.k)] || '—') + '</b>' : '') + '</div>');
    }
    f = has('fill-' + S.level) && map.queryRenderedFeatures(e.point, { layers: ['fill-' + S.level] })[0];
    if (f) {
      var q = f.properties;
      showPopup(e.lngLat, popupHtml(q, q.nombre || ('Sección ' + q.cod), S.level === 'barrios' ? q.distrito : ''));
    }
  }
  function onMove(e) {
    var l = ['bases', 'amp-pts', 'edif-fill', 'edif-fill-amp', 'fill-' + S.level].filter(function (i) { return map.getLayer(i); });
    map.getCanvas().style.cursor = l.length && map.queryRenderedFeatures(e.point, { layers: l }).length ? 'pointer' : '';
  }

  function highlight(level, cod) {
    ['distritos', 'barrios'].forEach(function (n) {
      if (map && map.getLayer('hl-' + n)) map.setFilter('hl-' + n, hlFilter(n === level && cod != null ? cod : '__none__'));
    });
  }
  function bbox(f) {
    var b = [Infinity, Infinity, -Infinity, -Infinity];
    (function walk(c) {
      if (typeof c[0] === 'number') { b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]); } else c.forEach(walk);
    })(f.geometry.coordinates);
    return b;
  }
  function zoomTo(level, cod) {
    if (S.level !== level) setLevel(level);
    var f = (geo[level] ? geo[level].features : []).filter(function (x) { return String(x.properties.cod) === String(cod); })[0];
    if (f && map) { verMapa(); map.fitBounds(bbox(f), { padding: 40, maxZoom: 15, duration: 600 }); }
  }

  // ---------- panel ----------
  function cityProps() {
    if (agg && agg.ciudad) return agg.ciudad;
    var t = { pob: 0, pob_v: 0, pob_a: 0, pob_r: 0 };
    ((geo.distritos || {}).features || []).forEach(function (f) { for (var k in t) t[k] += Number(f.properties[k] || 0); });
    t.pct_v = t.pob ? 100 * t.pob_v / t.pob : 0; t.pct_a = t.pob ? 100 * t.pob_a / t.pob : 0; t.pct_r = t.pob ? 100 * t.pob_r / t.pob : 0;
    return t;
  }
  function renderSum() {
    var c = cityProps(), lab = 'Población total';
    if (val(c, 'pob') == null) { $('#sum').innerHTML = '<div class="lb">' + lab + '</div><div class="muted">Datos no disponibles.</div>'; return; }
    $('#sum').innerHTML = '<div class="lb">' + lab + ' · Barcelona</div><div class="big">' + fmt(val(c, 'pob')) + '</div>' +
      stack(c, 1) + '<div class="kp">' + ['v', 'a', 'r'].map(function (k) {
        return '<div style="border-color:' + COL[k] + '">' + NAMES[k] + '<b>' + pc(val(c, 'pct_' + k)) + '</b>' + fmt(val(c, 'pob_' + k)) + ' hab.</div>';
      }).join('') + '</div>';
  }
  function rows() {
    var feats = (geo[S.rl] ? geo[S.rl].features : []);
    var q = S.q.trim().toLowerCase();
    return feats.map(function (f) { return f.properties; }).filter(function (p) {
      return !q || String(p.nombre).toLowerCase().indexOf(q) >= 0 || String(p.distrito || '').toLowerCase().indexOf(q) >= 0;
    });
  }
  function score(p) {
    var k = S.sort === 'v' ? val(p, 'pct_v') : S.sort === 'r' ? -val(p, 'pct_r') : -val(p, 'pob_r');
    return k == null || isNaN(k) ? -Infinity : k;
  }
  function renderRank() {
    var c = cityProps(), avg = val(c, 'pct_v');
    var rs = rows().filter(function (p) { return val(p, 'pob') != null; });
    rs.sort(function (a, b) { return S.order === 'best' ? score(b) - score(a) : score(a) - score(b); });
    if (!rs.length) { $('#rank').innerHTML = '<div class="empty">Sin datos.</div>'; return; }
    $('#rank').innerHTML = rs.map(function (p, i) {
      var bar = ['v', 'a', 'r'].map(function (k) {
        var w = val(p, 'pct_' + k) || 0;
        return '<div class="' + k + '" style="width:' + w + '%">' + (w >= 9 ? Math.round(w) + ' %' : '') + '</div>';
      }).join('');
      return '<div class="rk" data-cod="' + esc(p.cod) + '"><span class="n">' + (i + 1) + '</span><span class="nm">' + esc(p.nombre) +
        (S.rl === 'barrios' && p.distrito ? '<small>' + esc(p.distrito) + '</small>' : '') + '</span><span class="pp">' + fmt(val(p, 'pob')) + '<br><span class="muted" style="font-size:10px">hab.</span></span>' +
        '<div class="rbar">' + bar + (avg != null ? '<i style="left:' + avg + '%"></i>' : '') + '</div></div>';
    }).join('');
  }
  $('#rank').addEventListener('mouseover', function (e) { var r = e.target.closest('.rk'); highlight(S.rl, r ? r.dataset.cod : null); });
  $('#rank').addEventListener('mouseleave', function () { highlight(null, null); });
  $('#rank').addEventListener('click', function (e) { var r = e.target.closest('.rk'); if (r) zoomTo(S.rl, r.dataset.cod); });

  var COLS = [['nombre', 'Nombre'], ['pob', 'Población'], ['pct_v', '% &lt;250'], ['pct_a', '% 250–500'], ['pct_r', '% &gt;500'], ['pob_r', 'Sin cob.']];
  function renderTable() {
    var rs = rows().filter(function (p) { return val(p, 'pob') != null; }), t = S.tsort;
    rs.sort(function (a, b) {
      if (t.k === 'nombre') return t.d * String(a.nombre).localeCompare(String(b.nombre), 'es');
      return t.d * ((val(a, t.k) || 0) - (val(b, t.k) || 0));
    });
    $('#tcount').textContent = rs.length + ' ' + S.rl;
    $('#tabla').innerHTML = '<table><thead><tr>' + COLS.map(function (c) {
      return '<th data-k="' + c[0] + '">' + c[1] + (t.k === c[0] ? (t.d > 0 ? ' ▲' : ' ▼') : '') + '</th>';
    }).join('') + '</tr></thead><tbody>' + rs.map(function (p) {
      return '<tr data-cod="' + esc(p.cod) + '"><td>' + esc(p.nombre) + (S.rl === 'barrios' && p.distrito ? '<small>' + esc(p.distrito) + '</small>' : '') + '</td><td>' + fmt(val(p, 'pob')) +
        '</td><td>' + pc(val(p, 'pct_v')).replace(' %','%') + '</td><td>' + pc(val(p, 'pct_a')).replace(' %','%') + '</td><td>' + pc(val(p, 'pct_r')).replace(' %','%') + '</td><td>' + fmt(val(p, 'pob_r')) + '</td></tr>';
    }).join('') + '</tbody></table>';
  }
  $('#tabla').addEventListener('click', function (e) {
    var th = e.target.closest('th');
    if (th) { var k = th.dataset.k; S.tsort = { k: k, d: S.tsort.k === k ? -S.tsort.d : (k === 'nombre' ? 1 : -1) }; return renderTable(); }
    var tr = e.target.closest('tbody tr'); if (tr) zoomTo(S.rl, tr.dataset.cod);
  });
  // ---------- estaciones ----------
  var num = function (x) { return x == null || x === '' || isNaN(x) ? null : Number(x); };
  var fa = function () { return S.near ? 'p250_cercana' : 'p250'; };
  var fb = function () { return S.near ? 'p500_cercana' : 'p500'; };
  var stKey = function (p) {
    var a = num(p[fa()]), b = num(p[fb()]);
    if (S.sk === 'a') return a;
    if (S.sk === 'b') return b;
    return a == null && b == null ? null : (a || 0) + (b || 0);
  };
  function baseList() { return bases ? bases.features.map(function (f) { return f.properties; }) : []; }
  function renderStations() {
    var all = baseList(), a = fa(), b = fb(), q = S.sq.trim().toLowerCase();
    $('#st-note').textContent = S.near ? 'Cada persona cuenta solo en su base más cercana' : 'Personas que viven a menos de 250 m o entre 250 y 500 m andando de cada estación (una persona puede contar en varias)';
    var vals = all.map(function (p) { return num(p[a]); }).filter(function (x) { return x != null; }).sort(function (x, y) { return x - y; });
    var med = vals.length ? (vals[(vals.length - 1) >> 1] + vals[vals.length >> 1]) / 2 : null;
    var zeros = vals.filter(function (x) { return x === 0; }).length;
    $('#st-sum').innerHTML = '<div><b>' + fmt(all.length) + '</b>estaciones</div><div><b>' + fmt(med) + '</b>mediana &lt; 250 m</div><div><b>' + (vals.length ? fmt(zeros) : '—') + '</b>con 0 a &lt; 250 m</div>';
    var max = 0; all.forEach(function (p) { max = Math.max(max, (num(p[a]) || 0) + (num(p[b]) || 0)); });
    var rs = all.filter(function (p) {
      return !q || [p.nombre, p.distrito, p.barrio].some(function (x) { return String(x || '').toLowerCase().indexOf(q) >= 0; });
    });
    var d = S.sord === 'desc' ? -1 : 1;
    rs = rs.map(function (p) { var k = stKey(p); return { p: p, k: k == null ? -1 : k }; })
      .sort(function (x, y) { return x.k === y.k ? 0 : d * (x.k - y.k); }).map(function (x) { return x.p; });
    if (!rs.length) { $('#stlist').innerHTML = '<div class="empty">Sin estaciones.</div>'; return; }
    $('#stlist').innerHTML = rs.map(function (p, i) {
      var va = num(p[a]), vb = num(p[b]), wa = max && va ? 100 * va / max : 0, wb = max && vb ? 100 * vb / max : 0;
      return '<div class="rk es" data-id="' + esc(p.base_id) + '"><span class="n">' + (i + 1) + '</span><span class="nm"><b>' + esc(p.nombre) + '</b><small>' +
        (p.distrito ? esc(p.distrito) + (p.barrio ? ' · ' + esc(p.barrio) : '') : 'Fuera del municipio') + '</small></span>' +
        '<span class="pp"><i class="dt v"></i>' + fmt(va) + ' · <i class="dt a"></i>' + fmt(vb) + '</span>' +
        '<div class="rbar"><div class="v" style="width:' + wa + '%"></div><div class="a" style="width:' + wb + '%"></div></div></div>';
    }).join('');
  }
  function stationPopup(p) {
    var all = baseList().filter(function (x) { return num(x.p250) != null; }), pos = '';
    if (num(p.p250) != null) {
      var n = 1; all.forEach(function (x) { if (num(x.p250) > num(p.p250)) n++; });
      pos = '<div class="sm">Posición por población a &lt; 250 m: <b>nº ' + n + ' de ' + all.length + '</b></div>';
    }
    return '<div class="pop"><h3>' + esc(p.nombre) + '</h3><div class="muted">' + (p.distrito ? esc(p.distrito) + (p.barrio ? ' · ' + esc(p.barrio) : '') : 'Fuera del municipio') + '</div>' +
      '<div><span style="color:' + COL.v + '">●</span> &lt; 250 m: <b>' + fmt(num(p.p250)) + '</b> personas</div>' +
      '<div><span style="color:' + COL.a + '">●</span> 250–500 m: <b>' + fmt(num(p.p500)) + '</b> personas</div>' + pos +
      '<div class="sm muted">como base más cercana: ' + fmt(num(p.p250_cercana)) + ' / ' + fmt(num(p.p500_cercana)) + '</div></div>';
  }
  function hlBase(id) { if (map && map.getLayer('bases-hl')) map.setFilter('bases-hl', baseFilter(id == null ? '__none__' : id)); }
  function baseById(id) { return bases && bases.features.filter(function (f) { return String(f.properties.base_id) === String(id); })[0]; }
  $('#stlist').addEventListener('mouseover', function (e) { var r = e.target.closest('.rk'); hlBase(r ? r.dataset.id : null); });
  $('#stlist').addEventListener('mouseleave', function () { hlBase(null); });
  $('#stlist').addEventListener('click', function (e) {
    var r = e.target.closest('.rk'), f = r && baseById(r.dataset.id);
    if (!f || !map) return;
    verMapa(); map.flyTo({ center: f.geometry.coordinates, zoom: 16, duration: 700 });
    showPopup(f.geometry.coordinates, stationPopup(f.properties));
  });
  $('#seg-st').onclick = function (e) {
    if (!e.target.dataset.v) return;
    S.sk = e.target.dataset.v;
    $$('#seg-st button').forEach(function (x) { x.classList.toggle('on', x === e.target); });
    renderStations();
  };
  $('#st-order').onclick = function () {
    S.sord = S.sord === 'desc' ? 'asc' : 'desc';
    this.textContent = S.sord === 'desc' ? 'Más → menos' : 'Menos → más'; renderStations();
  };
  $('#st-q').oninput = function () { S.sq = this.value; renderStations(); };
  $('#st-near').onchange = function () { S.near = this.checked; renderStations(); };


  // ---------- ampliación ----------
  var AMPQ = [25, 50, 100, 250, 500];
  var ampPct = function (a, k) { return 100 * a[k] / AMP.curve.total; };
  var sgn = function (x) { return x > 0 ? '+' : x < 0 ? '−' : ''; };
  var pp1 = function (x) { return sgn(x) + Math.abs(x).toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); };
  var cx = function (k) { return 32 + 360 * k / AMP.max; };
  function ampPopup(p) {
    return '<div class="pop"><h3>Estación nueva nº ' + fmt(p.r) + '</h3><div class="muted">' + (p.distrito ? esc(p.distrito) + (p.barrio && p.barrio !== 'null' ? ' · ' + esc(p.barrio) : '') : '—') + '</div>' +
      '<div><span style="color:' + COL.v + '">●</span> <b>+' + fmt(p.gv) + '</b> personas pasan a verde</div><div><span style="color:' + COL.r + '">●</span> <b>' + fmt(p.gr) + '</b> dejan de estar en rojo</div></div>';
  }
  function ampInit() {
    var m = (meta.ampliacion || {}), c = AMP.curve;
    AMP.max = Math.min(m.max || (c.v.length - 1), c.v.length - 1);
    var pts = AMP.pts.features.slice().sort(function (a, b) { return a.properties.r - b.properties.r; });
    var gmax = 0; pts.forEach(function (f) { gmax = Math.max(gmax, Number(f.properties.g) || 0); });
    AMP.rows = pts.map(function (f) {
      var p = f.properties, w = gmax ? 100 * (Number(p.g) || 0) / gmax : 0;
      return '<div class="rk am" data-r="' + p.r + '"><span class="n">#' + p.r + '</span><span class="nm">' + esc(p.distrito || '—') + (p.barrio && p.barrio !== 'null' ? ' · ' + esc(p.barrio) : '') +
        '<small>+' + fmt(p.gv) + ' a verde · +' + fmt(p.gr) + ' fuera de rojo</small></span><div class="rbar"><div style="width:' + w + '%"></div></div></div>';
    });
    AMP.coords = {}; pts.forEach(function (f) { AMP.coords[f.properties.r] = f.geometry.coordinates; });
    $('#amp-top').innerHTML = '<p class="amp-in">Estaciones nuevas elegidas una a una: cada una es la que más mejora la cobertura teniendo en cuenta las anteriores.' +
      (m.objetivo ? ' <b>Objetivo:</b> ' + esc(m.objetivo) + '.' : '') + '</p>' +
      '<div class="amp-val"><button class="btn" id="amp-m" aria-label="Una menos">−</button><div class="bv" id="amp-bv"></div><button class="btn" id="amp-p" aria-label="Una más">+</button></div>' +
      '<input type="range" id="amp-r" min="0" max="' + AMP.max + '" step="1" value="' + S.k + '" aria-label="Número de estaciones nuevas">' +
      '<div class="amp-q">' + AMPQ.filter(function (q) { return q <= AMP.max; }).map(function (q) { return '<button class="btn" data-q="' + q + '">' + q + '</button>'; }).join('') + '</div>' +
      '<div class="amp-tot" id="amp-tot"></div><div class="sbar" id="amp-sb"></div><div class="amp-k" id="amp-k"></div>' +
      '<svg id="amp-svg" viewBox="0 0 400 140" preserveAspectRatio="xMidYMid meet"><g id="amp-st"></g><g id="amp-mk"></g></svg>';
    $('#amp-r').oninput = function () { setK(+this.value); };
    $('#amp-m').onclick = function () { setK(S.k - 1); };
    $('#amp-p').onclick = function () { setK(S.k + 1); };
    $('#amp-top').onclick = function (e) { var q = e.target.closest('[data-q]'); if (q) setK(+q.dataset.q); };
    var svg = $('#amp-svg'), drag = false;
    var fromEv = function (e) { var r = svg.getBoundingClientRect(); setK(Math.max(0, Math.min(1, ((e.clientX - r.left) / r.width * 400 - 32) / 360)) * AMP.max); };
    svg.addEventListener('pointerdown', function (e) { drag = true; try { svg.setPointerCapture(e.pointerId); } catch (x) {} fromEv(e); });
    svg.addEventListener('pointermove', function (e) { if (drag) fromEv(e); });
    svg.addEventListener('pointerup', function () { drag = false; });
    svg.addEventListener('pointercancel', function () { drag = false; });
    ampChartStatic();
    AMP.drawn = 0; $('#amplist').innerHTML = '';
    ampRender();
  }
  function ampChartStatic() {
    var c = AMP.curve, lo = 100, hi = 0;
    ['v', 'a', 'r'].forEach(function (s) { for (var i = 0; i <= AMP.max; i++) { var y = ampPct(c[s], i); lo = Math.min(lo, y); hi = Math.max(hi, y); } });
    lo = Math.max(0, Math.floor(lo / 10) * 10); hi = Math.min(100, Math.ceil(hi / 10) * 10); if (hi - lo < 20) hi = Math.min(100, lo + 20);
    var cy = function (v) { return 8 + 114 * (1 - (v - lo) / (hi - lo)); }; AMP.cy = cy;
    var g = '', step = (hi - lo) > 50 ? 20 : 10;
    for (var t = lo; t <= hi; t += step) g += '<line x1="32" x2="392" y1="' + cy(t) + '" y2="' + cy(t) + '" stroke="var(--b2)" stroke-width="1"/><text x="28" y="' + (cy(t) + 3) + '" text-anchor="end">' + t + ' %</text>';
    [0, .25, .5, .75, 1].forEach(function (f) { var k = Math.round(f * AMP.max); g += '<text x="' + cx(k) + '" y="135" text-anchor="' + (f === 0 ? 'start' : f === 1 ? 'end' : 'middle') + '">' + k + '</text>'; });
    var stp = Math.max(1, Math.floor(AMP.max / 400));
    ['a', 'r', 'v'].forEach(function (s) {
      var d = ''; for (var i = 0; i <= AMP.max; i += stp) d += (d ? 'L' : 'M') + cx(i).toFixed(1) + ' ' + cy(ampPct(c[s], i)).toFixed(1);
      d += 'L' + cx(AMP.max).toFixed(1) + ' ' + cy(ampPct(c[s], AMP.max)).toFixed(1);
      g += '<path d="' + d + '" fill="none" stroke="' + COL[s] + '" stroke-width="' + (s === 'a' ? 1.2 : 2) + '"' + (s === 'a' ? ' stroke-dasharray="4 3"' : '') + '/>';
    });
    $('#amp-st').innerHTML = g;
  }
  function ampRender() {
    var c = AMP.curve, k = S.k;
    $('#amp-bv').innerHTML = fmt(k) + ' <small>' + (k === 1 ? 'estación nueva' : 'estaciones nuevas') + '</small>';
    if ($('#amp-r').value != k) $('#amp-r').value = k;
    $$('.amp-q .btn').forEach(function (b) { b.classList.toggle('on', +b.dataset.q === k); });
    $('#amp-tot').innerHTML = 'Total de estaciones: <b>' + fmt(bases ? bases.features.length : 0) + ' + ' + fmt(k) + '</b>';
    $('#amp-sb').innerHTML = ['v', 'a', 'r'].map(function (s) { var w = ampPct(c[s], k); return '<div class="' + s + '" style="width:' + w + '%">' + (w >= 9 ? Math.round(w) + ' %' : '') + '</div>'; }).join('');
    $('#amp-k').innerHTML = ['v', 'a', 'r'].map(function (s) {
      var dp = c[s][k] - c[s][0], dpp = ampPct(c[s], k) - ampPct(c[s], 0);
      return '<div style="border-color:' + COL[s] + '">' + NAMES[s] + '<b>' + pc(ampPct(c[s], k)) + '</b><em>' + (k ? pp1(dpp) + ' pp · ' + sgn(dp) + fmt(Math.abs(dp)) + ' hab.' : 'situación actual') + '</em></div>';
    }).join('');
    var mk = '<line x1="' + cx(k) + '" x2="' + cx(k) + '" y1="8" y2="122" stroke="var(--tx)" stroke-width="1" stroke-dasharray="3 2"/>';
    var lbl = k > AMP.max * .6 ? 'end' : 'start', dx = lbl === 'end' ? -6 : 6;
    ['v', 'a', 'r'].forEach(function (s) {
      var y = AMP.cy(ampPct(c[s], k));
      mk += '<circle cx="' + cx(k) + '" cy="' + y + '" r="3.5" fill="' + COL[s] + '" stroke="var(--bg-panel)" stroke-width="1.5"/>';
      if (s !== 'a') mk += '<text x="' + (cx(k) + dx) + '" y="' + (y + (s === 'v' && y > 20 ? -6 : 12)) + '" text-anchor="' + lbl + '" style="fill:' + COL[s] + ';font-weight:600;font-size:10px">' + ampPct(c[s], k).toLocaleString('es-ES', { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + ' %</text>';
    });
    $('#amp-mk').innerHTML = mk;
    var L = $('#amplist');
    if (!k) { L.innerHTML = '<div class="empty">Mueve el control para añadir estaciones nuevas.</div>'; AMP.drawn = 0; return; }
    if (!AMP.drawn) L.innerHTML = '';
    if (k < AMP.drawn) { while (AMP.drawn > k) { L.removeChild(L.lastChild); AMP.drawn--; } }
    else if (k > AMP.drawn) { L.insertAdjacentHTML('beforeend', AMP.rows.slice(AMP.drawn, k).join('')); AMP.drawn = k; }
  }
  function setK(k) {
    k = Math.max(0, Math.min(AMP.max, Math.round(k) || 0));
    if (k === S.k) return;
    S.k = k;
    if (AMP.raf) return;
    AMP.raf = requestAnimationFrame(function () { AMP.raf = 0; ampRender(); applyAmpK(); });
  }
  $('#amplist').addEventListener('mouseover', function (e) {
    var r = e.target.closest('.rk'); ampHl(r ? +r.dataset.r : -1);
  });
  $('#amplist').addEventListener('mouseleave', function () { ampHl(-1); });
  $('#amplist').addEventListener('click', function (e) {
    var r = e.target.closest('.rk'), c = r && AMP.coords[r.dataset.r];
    if (c && map) { verMapa(); map.flyTo({ center: c, zoom: 15.5, duration: 700 }); }
  });

  function renderAll() { renderSum(); renderRank(); renderTable(); renderStations(); }

  $$('.tabs button').forEach(function (b) {
    b.onclick = function () {
      S.tab = b.dataset.tab;
      $$('.tabs button').forEach(function (x) { x.classList.toggle('on', x === b); });
      var t = S.tab;
      $('#amp').hidden = t !== 'amp';
      $('#rank').hidden = t !== 'rank'; $('#tabla').hidden = t !== 'tabla'; $('#stlist').hidden = t !== 'est';
      $('#rank-tools').hidden = t !== 'rank'; $('#tab-tools').hidden = t !== 'tabla'; $('#zone-tools').hidden = t === 'est' || t === 'amp';
      ['#st-tools', '#st-tools2', '#st-note', '#st-sum'].forEach(function (i) { $(i).hidden = t !== 'est'; });
      if (t !== 'est') hlBase(null);
      if (t === 'amp' && AMP.curve) ampRender();
      renderLegend(); applyAmpMode(); simLabel();
    };
  });
  // boton destacado de la barra superior: abre (o cierra) el simulador de ampliacion
  function simLabel() {
    var on = S.tab === 'amp', b = $('#sim');
    b.classList.toggle('on', on);
    b.querySelector('.sim-ic').textContent = on ? '←' : '＋';
    b.querySelector('.sim-l').textContent = on ? 'Volver al análisis' : 'Simula una ampliación del sistema';
    b.querySelector('.sim-s').textContent = on ? 'Volver' : 'Simular ampliación';
  }
  $('#sim').onclick = function () {
    var p = $('#panel');
    if (p.classList.contains('closed')) { p.classList.remove('closed'); $('#collapse').textContent = '⇥'; if (map) setTimeout(function () { map.resize(); }, 250); }
    $('.tabs button[data-tab="' + (S.tab === 'amp' ? 'rank' : 'amp') + '"]').click();
    verPanel();
  };
  $('#seg-rank').onclick = function (e) {
    if (!e.target.dataset.v) return;
    S.rl = e.target.dataset.v;
    $$('#seg-rank button').forEach(function (b) { b.classList.toggle('on', b === e.target); });
    renderRank(); renderTable();
  };
  $('#q').oninput = function () { S.q = this.value; renderRank(); renderTable(); };
  $('#sort').onchange = function () { S.sort = this.value; renderRank(); };
  $('#order').onclick = function () {
    S.order = S.order === 'best' ? 'worst' : 'best';
    this.textContent = S.order === 'best' ? 'Mejor → peor' : 'Peor → mejor'; renderRank();
  };
  $('#collapse').onclick = function () {
    var p = $('#panel'); p.classList.toggle('closed');
    this.textContent = p.classList.contains('closed') ? '⇤' : '⇥';
    var n = 0, t = setInterval(function () { if (map) map.resize(); if (++n > 12) clearInterval(t); }, 30);
  };

  // ---------- CSV ----------
  $('#csv').onclick = function () {
    if (!agg) return;
    var f = ['pob', 'pob_v', 'pob_a', 'pob_r', 'pct_v', 'pct_a', 'pct_r'];
    var head = ['nivel', 'cod', 'nombre', 'distrito'];
    f.forEach(function (k) { head.push(k); });
    var cell = function (v) {
      if (v == null) return '';
      if (typeof v === 'number') return String(v).replace('.', ',');
      v = String(v); return /[;"\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
    };
    var lines = [head.join(';')];
    [['distrito', agg.distritos], ['barrio', agg.barrios]].forEach(function (g) {
      (g[1] || []).forEach(function (r) {
        var row = [g[0], r.cod, r.nombre, r.distrito || ''];
        f.forEach(function (k) { row.push(r[k]); });
        lines.push(row.map(cell).join(';'));
      });
    });
    if (bases) {
      lines.push('', ['base_id', 'nombre', 'distrito', 'barrio', 'p250', 'p500', 'p250_cercana', 'p500_cercana'].join(';'));
      bases.features.forEach(function (b) {
        var p = b.properties;
        lines.push([p.base_id, p.nombre, p.distrito, p.barrio, p.p250, p.p500, p.p250_cercana, p.p500_cercana].map(cell).join(';'));
      });
    }
    var blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'cobertura_bicing.csv';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  };

  // ---------- arranque ----------
  function init() {
    map = new maplibregl.Map({ container: 'map', style: STYLES[S.theme], center: [2.165, 41.395], zoom: 12, minZoom: 9, hash: true, attributionControl: { compact: true } });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    map.on('style.load', addAll);
    map.on('click', onClick);
    map.on('mousemove', onMove);
  }
  if (window.pmtiles && window.maplibregl) {
    try { maplibregl.addProtocol('pmtiles', new pmtiles.Protocol().tile); } catch (e) {}
  }
  var pr = [
    getJSON('metadata.json').then(function (m) { meta = m; }).catch(function () {}),
    getJSON('agregados.json').then(function (a) { agg = a; }).catch(function () {}),
    getJSON('bases.geojson').then(function (g) { bases = g; }).catch(function () {}),
    getJSON('ampliacion_curva.json').then(function (c) { if (c && c.v && c.total) AMP.curve = c; }).catch(function () {}),
    getJSON('ampliacion_estaciones.geojson').then(function (g) { AMP.pts = g; }).catch(function () {}),
    fetch('data/edificios.pmtiles', { method: 'HEAD' }).then(function (r) { hasPM = r.ok && !!window.pmtiles; }).catch(function () {})
  ].concat(LEVELS.map(function (n) { return getJSON(n + '.geojson').then(function (g) { geo[n] = g; }).catch(function () {}); }));
  Promise.all(pr).then(function () {
    if (AMP.curve && AMP.pts) ampInit(); else { AMP.curve = AMP.pts = null; $('#amp-top').innerHTML = '<div class="empty">Datos de ampliación no disponibles</div>'; }
    renderLegend(); renderAll(); init();
    $('#sim').hidden = !(AMP.curve && AMP.pts);
    if (!store.get('bicing_visto')) openOb();
  });
})();

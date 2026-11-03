/* Taggle card 0.3.1. MIT. Home Assistant states and recorder history; no external requests. */
(() => {
  'use strict';
  const KEYS = ['last_hour_litres', 'today_litres', 'total_litres', 'last_hour',
    'today', 'meter_count', 'snr', 'signal_level', 'last_seen', 'calibration_status', 'meter_reading', 'possible_leak',
    'dial_unit', 'dial_reading', 'read_dial_now'];
  const CONTROLS = {dial_unit:'select', dial_reading:'text'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g,
    c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const number = entity => entity && entity.state != null && !['unknown', 'unavailable', ''].includes(entity.state)
    && Number.isFinite(Number(entity.state)) ? Number(entity.state) : null;
  const css = `
    :host { container-type:inline-size; display:block; color:var(--primary-text-color,#0d2233);
      font-family:var(--primary-font-family,Manrope,system-ui,sans-serif); }
    * { box-sizing:border-box; }
    ha-card { display:block; overflow:hidden; background:var(--ha-card-background,var(--card-background-color,#fff));
      border:var(--ha-card-border-width,1px) solid var(--ha-card-border-color,var(--divider-color,#e3eaee));
      border-radius:var(--ha-card-border-radius,24px); box-shadow:var(--ha-card-box-shadow,none);
      --ink:var(--primary-text-color,#0d2233); --muted:var(--secondary-text-color,#5a6f7e);
      --water:var(--primary-color,#2bb3d6); --line:var(--divider-color,#e3eaee);
      --surface:var(--ha-card-background,var(--card-background-color,#fff));
      --chip:color-mix(in srgb,var(--water) 12%,var(--surface));
      --chip-ink:color-mix(in srgb,var(--water) 38%,var(--ink));
      --ok:var(--success-color,#1d8a4a); --warn:var(--warning-color,#e07b1f); }
    ::selection { background:var(--water); color:var(--text-primary-color,#fff); }
    h2,h3,h4,p { margin:0; overflow-wrap:anywhere; }
    h2 { padding:20px 24px 0; font-size:18px; font-weight:700; }
    h3 { font-size:16px; font-weight:700; line-height:1.4; }
    p { font-size:14px; line-height:1.5; color:var(--muted); }
    .meter+ .meter { border-top:1px solid var(--line); }
    .header { position:relative; overflow:hidden; padding:24px 24px 28px; }
    .wave { position:absolute; left:0; bottom:0; width:200%; height:120px; opacity:.12;
      fill:var(--water); animation:tg-wave 9s linear infinite; pointer-events:none; }
    .heading,.hero { position:relative; }
    .heading { display:flex; align-items:center; justify-content:space-between; gap:10px 12px; flex-wrap:wrap; }
    .identity { display:flex; align-items:center; flex-wrap:wrap; gap:6px 10px; min-width:0; }
    .dot { width:10px; height:10px; flex:none; border-radius:50%; background:var(--muted); }
    .dot.live { background:var(--water); animation:tg-pulse 2s infinite; }
    .status { font-size:13px; color:var(--muted); }
    .status.stale { background:color-mix(in srgb,var(--muted) 10%,var(--surface)); padding:4px 8px; border-radius:20px; }
    .chip { padding:5px 10px; border-radius:999px; background:var(--chip); color:var(--chip-ink);
      font-size:12px; font-weight:700; white-space:nowrap; }
    .hero { display:flex; align-items:center; gap:24px; margin-top:22px; }
    .ring { position:relative; width:132px; height:132px; flex:none; }
    .ring svg { width:100%; height:100%; overflow:visible; }
    .track { stroke:var(--line); } .progress { stroke:var(--water); } .overflow { stroke:var(--warn); }
    .ring-label { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }
    .ring-label strong { font-size:22px; font-weight:800; } .ring-label span { font-size:11px; color:var(--muted); }
    .today { min-width:0; } .today-label { color:var(--muted); font-size:13px; font-weight:600; }
    .today-value { font-size:52px; font-weight:800; line-height:1.05; letter-spacing:-.03em; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
    .today-value small { font-size:22px; font-weight:700; margin-inline-start:4px; letter-spacing:0; }
    .usual { margin-top:6px; line-height:1.5; }
    .stats { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); margin:0;
      border-block:1px solid var(--line); font-variant-numeric:tabular-nums; }
    .stats>div { padding:16px 20px; min-width:0; } .stats>div+div { border-inline-start:1px solid var(--line); }
    dt,.stat-note { font-size:12px; color:var(--muted); line-height:1.5; }
    dd { margin:2px 0 0; font-size:22px; font-weight:800; overflow-wrap:anywhere; }
    dd small { font-size:14px; font-weight:600; }
    .chart { padding:20px 24px 8px; }
    .chart-heading { display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin-bottom:12px; }
    .chart-heading h4 { font-size:15px; font-weight:700; } .chart-heading span { font-size:12px; color:var(--muted); }
    .plot { display:flex; height:140px; align-items:stretch; gap:4px; }
    .bar { position:relative; display:flex; flex:1 1 0; min-width:0; align-items:flex-end;
      padding:0; border:0; background:transparent; color:var(--ink); cursor:pointer; touch-action:manipulation; }
    .bar-fill { display:block; width:100%; height:var(--height); min-height:3px; border-radius:4px;
      background:color-mix(in srgb,var(--water) 40%,var(--surface)); transform-origin:bottom; }
    .enter .bar-fill { animation:tg-grow .8s cubic-bezier(.2,.8,.2,1) both; animation-delay:var(--delay); }
    .bar.peak .bar-fill { background:var(--water); }
    .bar.zero .bar-fill { height:3px; background:var(--water); }
    .bar.missing .bar-fill,.day.missing .day-fill { height:18%; background:repeating-linear-gradient(135deg,
      var(--line) 0 3px,transparent 3px 7px); }
    .bar:hover .bar-fill,.bar:focus-visible .bar-fill { outline:1px solid var(--chip-ink); outline-offset:2px; }
    .axis { display:flex; justify-content:space-between; font-size:11px; color:var(--muted); margin-top:6px; }
    .chart-tip { min-height:22px; margin-top:6px; font-size:12px; color:var(--muted); }
    .week { padding:8px 24px 16px; }
    .week h4 { margin-bottom:10px; font-size:12px; font-weight:600; color:var(--muted); }
    .days { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; }
    .day { display:flex; flex-direction:column; gap:4px; align-items:center; min-width:0; font-size:11px; color:var(--muted); }
    .day-plot { width:100%; height:30px; display:flex; align-items:flex-end; }
    .day-fill { width:100%; height:var(--height); min-height:2px; border-radius:3px; background:var(--chip); }
    .day.yesterday { color:var(--ink); font-weight:700; } .yesterday .day-fill { background:var(--water); }
    .day-value { font-variant-numeric:tabular-nums; }
    .statuses { padding:0 24px; display:grid; gap:10px; }
    .status-row { display:flex; align-items:center; gap:12px; padding:12px 14px; border-radius:14px; background:var(--chip); font-size:14px; line-height:1.5; }
    .status-row svg { width:20px; height:20px; flex:none; fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
    .status-row strong { color:var(--ink); } .status-row span { color:var(--muted); }
    .leak-ok { background:color-mix(in srgb,var(--ok) 12%,var(--surface)); color:var(--ok); }
    .leak-warning { background:color-mix(in srgb,var(--warn) 14%,var(--surface)); color:var(--warn); }
    .comparison { color:var(--chip-ink); }
    .comparison-details { margin-top:3px; font-size:12px; }
    .footer { padding:14px 24px 20px; font-size:12px; color:var(--muted); text-align:end; }
    .support { padding:0 24px; }
    .support>details.read-panel { margin-top:16px; padding-top:4px; } .support:empty { display:none; }
    .empty,.uncalibrated { margin-top:16px; }
    .uncalibrated { padding:12px 14px; border-radius:14px; background:var(--chip); }
    .calibration { margin-top:12px; } .calibration a { color:var(--chip-ink); text-underline-offset:3px; }
    .calibration.warning,.form-feedback.error { color:var(--error-color,#b3261e); }
    details { margin-top:12px; } summary { font-size:14px; cursor:pointer; padding-block:10px; color:var(--chip-ink); }
    summary:hover { text-decoration:underline; text-underline-offset:3px; }
    summary:focus-visible,button:focus-visible,a:focus-visible,input:focus-visible,
    .units input:focus-visible+span { outline:2px solid var(--water); outline-offset:3px; }
    .scroll { overflow:auto; max-height:240px; scrollbar-color:var(--muted) transparent; }
    table { width:100%; border-collapse:collapse; font-size:14px; font-variant-numeric:tabular-nums; }
    th,td { padding:10px 0; border-bottom:1px solid var(--line); text-align:start; }
    th { color:var(--muted); font-weight:400; } th:last-child,td:last-child { text-align:end; padding-inline-start:16px; }
    .note { margin-top:12px; }
    .read-panel { margin-top:20px; padding-top:20px; border-top:1px solid var(--divider-color,#ddd); }
    .read-now { padding:12px; color:var(--primary-text-color,#171717);
      background:color-mix(in srgb,var(--water) 18%,var(--ha-card-background,var(--card-background-color,#fff)));
      border-radius:10px; margin-bottom:12px; }
    .read-now strong { font-size:20px; }
    .routine-step { margin-bottom:8px; color:var(--primary-text-color,#171717); font-weight:600; }
    .routine { padding-left:20px; font-size:14px; line-height:1.5; color:var(--muted); }
    .routine [aria-current=step] { color:var(--primary-text-color,#171717); font-weight:600; }
    .read-panel h4 { margin:0 0 8px; font-size:17px; font-weight:500; }
    .read-panel figure { margin:16px 0 0; }
    .dial-picture { display:block; width:100%; max-width:320px; height:auto; }
    .dial-picture .dial-face { fill:var(--ha-card-background,var(--card-background-color,#fff)); stroke:var(--muted); }
    .dial-picture .dial-red { fill:var(--taggle-dial-red,#b3261e); }
    .dial-caption { margin-top:4px; font-size:14px; line-height:1.5; }
    .read-panel details { margin-top:8px; }
    .read-panel ul { padding-left:20px; margin:4px 0 12px; font-size:14px; line-height:1.5; color:var(--muted); }
    .read-panel li+li { margin-top:8px; }
    .reading-form { margin-top:16px; font-size:14px; }
    .reading-form fieldset { border:0; padding:0; margin:0; min-width:0; }
    .reading-form legend { padding:0; margin-bottom:8px; }
    .units { display:flex; width:100%; max-width:320px; }
    .units label { position:relative; flex:1; cursor:pointer; }
    .units input { position:absolute; width:1px; height:1px; opacity:0; }
    .units span { display:flex; align-items:center; justify-content:center; min-height:44px;
      border:1px solid var(--divider-color,#ddd); background:var(--ha-card-background,var(--card-background-color,#fff)); }
    .units label+label span { border-inline-start:0; }
    .units label:first-child span { border-radius:6px 0 0 6px; }
    .units label:last-child span { border-radius:0 6px 6px 0; }
    .units input:checked+span { color:var(--primary-text-color,#171717); font-weight:600;
      background:color-mix(in srgb,var(--water) 15%,var(--ha-card-background,var(--card-background-color,#fff)));
      box-shadow:inset 0 -3px var(--water); }
    .units label:hover span { background:color-mix(in srgb,var(--water) 10%,var(--ha-card-background,var(--card-background-color,#fff))); }
    .reading-fields { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; margin-top:16px; }
    .reading-fields label { display:block; margin-bottom:8px; }
    .reading-fields input { width:100%; min-width:0; min-height:44px; padding:10px 8px; border:1px solid var(--muted);
      border-radius:6px; background:var(--ha-card-background,var(--card-background-color,#fff));
      color:var(--primary-text-color,#171717); font:inherit; caret-color:var(--water); }
    .reading-fields input[aria-invalid=true] { border-color:var(--error-color,#b3261e); }
    .reading-form button { margin-top:12px; min-height:44px; padding:10px 20px; border:1px solid var(--water);
      border-radius:6px; background:color-mix(in srgb,var(--water) 18%,var(--ha-card-background,var(--card-background-color,#fff)));
      color:var(--primary-text-color,#171717); font:inherit; cursor:pointer; }
    .reading-form button:hover { background:color-mix(in srgb,var(--water) 26%,var(--ha-card-background,var(--card-background-color,#fff))); }
    .reading-form button:active { background:color-mix(in srgb,var(--water) 34%,var(--ha-card-background,var(--card-background-color,#fff))); }
    .reading-form button:disabled,.reading-form button[aria-disabled=true] { opacity:.6; cursor:default; }
    .form-feedback:not(:empty) { margin-top:12px; }
    .form-feedback.error { color:var(--error-color,#b3261e); }
    .read-panel .reading-list { list-style:none; padding:0; margin:16px 0 0; }
    .reading-list li { padding-block:8px; border-top:1px solid var(--divider-color,#ddd); }
    .reading-list strong { color:var(--primary-text-color,#171717); font-weight:500; font-variant-numeric:tabular-nums; }
    .reading-list time { display:block; }

    @keyframes tg-wave { from { transform:translateX(0); } to { transform:translateX(-50%); } }
    @keyframes tg-grow { from { transform:scaleY(0); } to { transform:scaleY(1); } }
    @keyframes tg-pulse { 0%,100% { box-shadow:0 0 0 0 color-mix(in srgb,var(--water) 45%,transparent); }
      70% { box-shadow:0 0 0 10px transparent; } }
    @media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none !important; transition:none !important; } }
    :host([data-reduced-motion]) *, :host([data-reduced-motion]) *::before { animation:none !important; transition:none !important; }
    @container (max-width:400px) {
      .header { padding:20px 16px 24px; } .hero { gap:16px; }
      .ring { width:104px; height:104px; } .ring-label strong { font-size:20px; }
      .today-value { font-size:44px; } .today-value small { font-size:18px; } .usual { font-size:12px; }
      .stats>div { padding:14px 12px; } dd { font-size:19px; } .stats>div:last-child dd { font-size:16px; white-space:nowrap; }
      .chart { padding-inline:16px; } .plot { gap:3px; } .chart-heading span { font-size:11px; }
      .week { padding-inline:16px; } .days { gap:5px; } .day { font-size:10px; }
      .statuses { padding-inline:16px; } .support { padding:0 16px; } .footer { padding-inline:16px; }
    }
  `;

  class TaggleCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({mode: 'open'});
      this._registry = [];
      this._historyCache = new Map();
      this._entrances = new WeakMap();
      this._motion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
      this._motionChanged = () => this.render();
      this._seenMeters = new WeakSet();
      this._drafts = new WeakMap();
    }
    setConfig(config) {
      const meters = config?.meters || [config];
      if (!Array.isArray(meters) || !meters.length || meters.some(m => !m || typeof m !== 'object' || (!m.entities && !m.device))) {
        throw new Error('Configure entities or a device for each Taggle meter.');
      }
      this._config = {...config, meters};
      this._registryRequested = false;
      this._historyCache.clear();
      this._lastMarkup = '';
      this.render();
    }
    connectedCallback() {
      clearInterval(this._timer);
      this._motion?.addEventListener('change', this._motionChanged);
      this._timer = setInterval(() => this.render(), 60000);
      this.render();
    }
    disconnectedCallback() {
      clearInterval(this._timer);
      this._motion?.removeEventListener('change', this._motionChanged);
    }
    getCardSize() { return 16 * (this._config?.meters.length || 1); }
    getGridOptions() { return {columns: 12, min_columns: 6}; }
    set hass(hass) {
      this._hass = hass;
      if (this._config && !this._registryRequested && hass.callWS) {
        this._registryRequested = true;
        hass.callWS({type: 'config/entity_registry/list'}).then(registry => {
          this._registry = Array.isArray(registry) ? registry : [];
          this.render();
        }).catch(() => {
          this._registryRequested = false;
          this._registryError = true;
          this.render();
        });
      }
      this.render();
    }
    entityRegistry() {
      // The frontend's entity map may omit unique_id; the full registry includes it.
      const entries = new Map(Object.values(this._hass?.entities || {}).map(e => [e.entity_id, e]));
      for (const entry of this._registry) entries.set(entry.entity_id, {...entries.get(entry.entity_id), ...entry});
      return [...entries.values()];
    }
    resolve(meter) {
      const result = {};
      if (meter.entities && !Array.isArray(meter.entities)) Object.assign(result, meter.entities);
      const registry = this.entityRegistry();
      const selected = meter.device ? registry.filter(e => e.device_id === meter.device) : [];
      const ids = Array.isArray(meter.entities) ? meter.entities : selected.map(e => e.entity_id);
      for (const id of ids) {
        const entry = registry.find(e => e.entity_id === id);
        const uniqueKey = entry?.unique_id?.match(/^.+_\d+_(.+)$/)?.[1];
        const entityKey = id.match(/^(?:sensor|binary_sensor|select|number|text)\.taggle_\d+_(?:water_)?(.+)$/)?.[1];
        const key = KEYS.includes(uniqueKey) ? uniqueKey : entityKey;
        if (KEYS.includes(key) && !result[key]) result[key] = id;
      }
      // Existing pulse mappings also acquire calibration, litre and reading controls.
      const anchor = Object.values(result).find(id => /^(?:sensor|select|text|binary_sensor)\.taggle_\d+_/.test(id));
      const base = anchor?.match(/^[^.]+\.(taggle_\d+_)/)?.[1];
      const device = registry.find(e => Object.values(result).includes(e.entity_id) && e.device_id)?.device_id;
      if (!meter.device) for (const key of ['calibration_status', 'meter_reading', 'last_hour_litres', 'today_litres', 'total_litres', 'possible_leak', 'read_dial_now', ...Object.keys(CONTROLS)]) {
        const found = device && registry.find(e => e.device_id === device && (e.unique_id || '').endsWith('_' + key));
        const fallback = (CONTROLS[key] || (['read_dial_now', 'possible_leak'].includes(key) ? 'binary_sensor' : 'sensor')) + '.' + base + key;
        if (!result[key] && found) result[key] = found.entity_id;
        if (!result[key] && base && this._hass.states[fallback]) result[key] = fallback;
      }
      return result;
    }
    calibrationState(ids) {
      const entity = this._hass.states[ids.calibration_status];
      const attrs = entity?.attributes || {};
      const valid = entity && !['unknown', 'unavailable', ''].includes(entity.state);
      const warning = valid && /warn|disagree|check|1000×|sequence changed|hide wraps|wrong|invalid|negative|too large|future|implausible|must|use HH:MM|does not exist|occurs twice|resolve the absolute/i.test(entity.state);
      const calibrated = Number.isFinite(attrs.chosen_k);
      return {entity, attrs, valid, warning, calibrated};
    }
    calibration(meter, ids) {
      const {entity, attrs, valid, warning, calibrated} = this.calibrationState(ids);
      const registry = this.entityRegistry();
      const device = meter.device || registry.find(e => Object.values(ids).includes(e.entity_id) && e.device_id)?.device_id;
      const link = device ? '/config/devices/device/' + encodeURIComponent(device) : '/config/devices';
      const message = valid ? entity.state : 'Enter your dial reading to show litres';
      let next = '';
      if (attrs.next_transmission && Number.isFinite(Date.parse(attrs.next_transmission))) {
        const clock = new Intl.DateTimeFormat(this._hass?.locale?.language || undefined, {
          timeZone: this._hass?.config?.time_zone || 'UTC', hour:'2-digit', minute:'2-digit', hourCycle:'h23'
        }).format(new Date(attrs.next_transmission));
        next = `Next transmission expected ≈ ${clock} — best read within 10 minutes, before water use`;
      }
      return `<p class="calibration ${warning ? 'warning' : ''}" role="status">${esc(message)}${!calibrated || warning
        ? ` · <a href="${esc(link)}">Open meter device</a>` : ''}${next ? '<br>'+esc(next) : ''}</p>`;
    }
    draft(meter, ids) {
      if (!this._drafts.has(meter)) this._drafts.set(meter, {reading:'', time:'', unit:null, message:'', error:'', busy:false});
      const draft = this._drafts.get(meter);
      const savedUnit = this._hass.states[ids.dial_unit]?.state || this.calibrationState(ids).attrs.dial_unit;
      return {...draft, unit:draft.unit || (['m³', 'kL', 'L'].includes(savedUnit) ? savedUnit : 'm³')};
    }
    controlsReady(ids) {
      return Object.keys(CONTROLS).every(key => ids[key] && this._hass.states[ids[key]]
        && this._hass.states[ids[key]].state !== 'unavailable');
    }
    readingError(draft, ids) {
      const value = Number(draft.reading.replace(',', '.')), text = draft.reading.trim();
      if (draft.badInput) return ['reading', 'Type a number with a decimal point, such as 1597.765.'];
      if (!text) return ['reading', 'Enter the complete reading from your dial.'];
      if (value < 0) return ['reading', 'A dial reading cannot be negative. Check the digits.'];
      if (!Number.isFinite(value) || !/^(?:\d+(?:[.,]\d*)?|[.,]\d+)$/.test(text)) {
        return ['reading', 'Type a number with a decimal point or comma, without grouping separators or unit letters.'];
      }
      if (!['m³', 'kL', 'L'].includes(draft.unit)) return ['unit', 'Choose the unit printed on your meter.'];
      if (draft.time && !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(draft.time)) return ['time', 'Use a photo time in HH:MM, or leave it blank for a fresh reading.'];
      const litres = value * (draft.unit === 'L' ? 1 : 1000);
      if (litres > 1e15) return ['reading', 'That reading is too large. Check the digits and the unit on the face.'];
      const rows = this.calibrationState(ids).attrs.readings;
      const last = Array.isArray(rows) ? rows.slice().reverse().find(r => r && Number.isFinite(r.litres)
        && r.litres > 0 && (r.used || !(r.base_interval || r.count_interval))) : null;
      const reference = last?.litres || number(this._hass.states[ids.meter_reading]);
      const ratio = reference > 0 ? litres / reference : null;
      if (ratio !== null && ((ratio >= 900 && ratio <= 1100) || (ratio >= .0009 && ratio <= .0011))) {
        return ['reading', 'This is about 1000× different from the last reading. Check the unit: m³ and kL are the same; L is 1000× smaller.'];
      }
      return null;
    }
    async saveReading(meter) {
      const ids = this.resolve(meter), draft = this.draft(meter, ids);
      if (draft.busy) return;
      const error = this.readingError(draft, ids);
      if (error) {
        Object.assign(this._drafts.get(meter), {error:error[0], message:error[1]});
        this.render();
        const index = this._config.meters.indexOf(meter);
        this.shadowRoot.querySelector?.(`[data-focus="${index}-${error[0]}"]`)?.focus();
        return;
      }
      if (!this.controlsReady(ids) || !this._hass.callService) {
        Object.assign(this._drafts.get(meter), {error:'service', message:'Reading controls are unavailable. Check the receiver connection and entity mappings.'});
        this.render();
        return;
      }
      Object.assign(this._drafts.get(meter), {busy:true, error:'', message:''});
      this.render();
      try {
        await this._hass.callService('select', 'select_option', {entity_id:ids.dial_unit, option:draft.unit});
        const value = draft.reading.trim() + (draft.time ? ' ' + draft.time : '');
        await this._hass.callService('text', 'set_value', {entity_id:ids.dial_reading, value});
        Object.assign(this._drafts.get(meter), {reading:'', time:'', badInput:false,
          message:'Reading sent. Check the status below; it may wait for the next transmission.'});
      } catch (_) {
        Object.assign(this._drafts.get(meter), {error:'service',
          message:'Could not send the reading. Check the connection and calibration status before trying again.'});
      } finally {
        this._drafts.get(meter).busy = false;
        this.render();
      }
    }
    readPanel(meter, ids, index) {
      const {attrs, calibrated, warning} = this.calibrationState(ids);
      const draft = this.draft(meter, ids), prefix = `dial-${index}`;
      const ready = this.controlsReady(ids), collapsed = calibrated && !warning;
      const rows = Array.isArray(attrs.readings) ? attrs.readings.filter(r => r && typeof r === 'object').slice(-10) : [];
      const window = this._hass.states[ids.read_dial_now]?.attributes || attrs.read_dial_now || {};
      const remaining = Math.max(0, Math.ceil((Date.parse(window.until) - Date.now()) / 60000));
      const open = Number.isFinite(remaining) && remaining > 0 && Date.parse(window.since) <= Date.now();
      const first = rows[0];
      const step = !first ? 1 : open && Date.parse(window.since) > Date.parse(first.time) ? 3 : 2;
      const body = `<h4>Read your dial</h4>
        ${open ? `<p class="read-now" role="status"><strong>Read now</strong> · ${remaining} min left<br>Before anyone uses water.</p>` : ''}
        <p class="routine-step">Step ${step} of 3</p>
        <p>Your meter's dial is the only source of real litres. Calibrate in about one hour:</p>
        <ol class="routine">
          <li ${step === 1 ? 'aria-current="step"' : ''}>Just after a transmission, read within 10 minutes, before anyone uses water.</li>
          <li ${step === 2 ? 'aria-current="step"' : ''}>Use some water this hour: fill buckets or run a shower (20–50 L; reuse it).</li>
          <li ${step === 3 ? 'aria-current="step"' : ''}>Just after the NEXT transmission, read again. Follow the calibration status.</li>
        </ol>
        <p class="note">Outside the window is less precise; take readings about a day apart. A third reading may be needed.</p>
        <figure><svg class="dial-picture" viewBox="0 0 320 118" role="img" aria-labelledby="${prefix}-picture-title ${prefix}-picture-desc">
          <title id="${prefix}-picture-title">Example mechanical register: 01597 black wheels and 765 red wheels</title>
          <desc id="${prefix}-picture-desc">Fictional reading: 1597.765 cubic metres. Black digits are whole cubic metres or kilolitres; red digits are litres.</desc>
          <rect class="dial-face" x="1" y="1" width="318" height="116" rx="16"/>
          <rect x="16" y="14" width="175" height="46" rx="4" fill="#203744"/>
          <rect class="dial-red" x="197" y="14" width="105" height="46" rx="4"/>
          <g fill="#fff" font-size="29" text-anchor="middle" font-family="monospace">
            ${[...'01597765'].map((n,i) => `<text x="${i < 5 ? 33.5+i*35 : 214.5+(i-5)*35}" y="47">${n}</text>`).join('')}
          </g>
          <path d="M51 17V57M86 17V57M121 17V57M156 17V57M232 17V57M267 17V57" stroke="#fff" stroke-opacity=".3"/>
          <g fill="currentColor" font-size="14" text-anchor="middle">
            <text x="103" y="83">black = whole m³ (kL)</text><text x="249" y="83">red = litres</text>
            <text x="160" y="106">m³ / kL</text>
          </g></svg><figcaption class="dial-caption">Example: type <strong>1597.765</strong>, unit <strong>m³</strong>.</figcaption></figure>
        <details data-disclosure="other-${index}"><summary data-focus="other-${index}">Other meters</summary><ul>
          <li>Black digits with small red pointer dials ×0.1, ×0.01, ×0.001: read the digits, then add each dial’s value. For example, 1597 + 0.7 + 0.06 + 0.005 = 1597.765 m³. Do not add fractions already shown in red digits.</li>
          <li>All digits one colour, with “L” or “litres” printed: choose L and type every digit.</li>
          <li>Digital/LCD display: type exactly what it shows and choose the unit printed next to it.</li>
          <li>The small star/triangle spinner shows flow; ignore it when reading the total.</li>
        </ul></details>
        <p class="note">Always check the unit printed on the face (m³ or kL are the same; L is 1000× smaller).</p>
        <form class="reading-form" data-meter="${index}" novalidate aria-label="Dial reading for ${esc(meter.name || 'Water meter')}" aria-busy="${draft.busy}">
          <fieldset ${draft.busy ? 'disabled' : ''}><legend>Dial unit</legend><div class="units">
            ${['m³', 'kL', 'L'].map((unit,i) => `<label><input type="radio" name="unit-${index}" value="${unit}" data-field="unit" data-focus="${index}-${i === 0 ? 'unit' : 'unit-'+i}" ${draft.unit === unit ? 'checked' : ''}><span>${unit}</span></label>`).join('')}
          </div></fieldset><div class="reading-fields">
            <div><label for="${prefix}-reading">Meter reading</label><input id="${prefix}-reading" type="text" inputmode="decimal" required data-field="reading" data-focus="${index}-reading" value="${esc(draft.reading)}" ${draft.busy ? 'disabled' : ''} aria-invalid="${draft.error === 'reading'}" aria-describedby="${prefix}-feedback"></div>
            <div><label for="${prefix}-time">Photo taken at</label><input id="${prefix}-time" type="time" step="60" data-field="time" data-focus="${index}-time" value="${esc(draft.time)}" ${draft.busy ? 'disabled' : ''} aria-invalid="${draft.error === 'time'}" aria-describedby="${prefix}-time-help ${prefix}-feedback"></div>
          </div>
          <p class="note" id="${prefix}-time-help">Photo time is optional: leave blank for a fresh reading. Uses the receiver’s timezone; a time ahead of now means yesterday.</p>
          ${!ready ? '<p class="note">Reading controls are unavailable. Check the receiver connection, or configure dial_unit and dial_reading entities.</p>' : ''}
          <button type="submit" data-focus="${index}-save" aria-disabled="${draft.busy || !ready}" ${!ready ? 'disabled' : ''}>${draft.busy ? 'Sending…' : 'Save reading'}</button>
          <p id="${prefix}-feedback" class="form-feedback ${draft.error ? 'error' : ''}" role="status" aria-live="polite" aria-atomic="true">${esc(draft.message)}</p>
        </form>
        ${this.calibration(meter, ids)}
        ${rows.length ? `<ul class="reading-list" aria-label="Last ${rows.length} entered readings">${rows.slice().reverse().map(r => `<li>
          <time datetime="${esc(r.time)}">${esc(this.time(r.time, true))}</time>
          <strong>${esc(Number.isFinite(r.value) ? String(r.value) : Number.isFinite(r.litres) ? String(r.litres) : '—')} ${esc(Number.isFinite(r.value) ? r.unit : 'L')}</strong>
          <br>${r.used ? 'Used' : r.base_interval || r.count_interval ? 'Excluded' : 'Pending'}${r.exact ? ' · Exact' : ' · Less precise'}${r.reason ? ' — '+esc(r.reason) : ''}</li>`).join('')}</ul>`
          : '<p class="note">No dial readings entered yet. Add your first reading above.</p>'}`;
      return collapsed ? `<details class="read-panel" data-disclosure="check-${index}"><summary class="${open ? 'read-now' : ''}" data-focus="check-${index}">${open ? 'Read now · ' + remaining + ' min left' : 'Add a check reading'}</summary>${body}</details>`
        : `<div class="read-panel">${body}</div>`;
    }
    format(value) {
      return value === null ? '—' : new Intl.NumberFormat(this._hass?.locale?.language || undefined,
        {maximumFractionDigits: 2}).format(value);
    }
    comparison(meter, today, unit) {
      const config = meter.neighbourhood ?? this._config.neighbourhood;
      if (config === false) return '';
      const registry = this.entityRegistry();
      const get = key => {
        const selected = config?.device ? registry.filter(e => e.device_id === config.device) : registry;
        const defaultId = 'sensor.taggle_neighbourhood_' + key;
        const id = config?.[key] || (!config?.device && this._hass.states[defaultId] ? defaultId
          : selected.find(e => (e.unique_id || '').endsWith('_neighbourhood_' + key))?.entity_id);
        return this._hass.states[id];
      };
      const average = get('average_today'), median = get('median_today'), counted = get('meters_counted');
      const avg = number(average), med = number(median), homes = number(counted), own = number(today);
      const neighbourUnit = average?.attributes?.unit_of_measurement || 'pulses';
      const ready = avg !== null && homes !== null && homes >= 3;
      const ratio = ready && own !== null && avg > 0 && unit === neighbourUnit ? (own / avg - 1) * 100 : null;
      const difference = ratio === null ? '' : Math.round(Math.abs(ratio)) === 0 ? 'Same as your street'
        : `${this.format(Math.round(Math.abs(ratio)))}% ${ratio < 0 ? 'below' : 'above'} your street`;
      return `<div class="status-row comparison">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7M5 10v10h14V10"/></svg>
        <div><strong>${difference ? esc(difference) : 'Your street'}</strong>${!ready
          ? '<span> · average appears once 3 homes are heard</span>'
          : `<p class="comparison-details">Neighbourhood avg ${esc(this.format(avg))} ${esc(neighbourUnit)}${med === null ? '' : ` · Median ${esc(this.format(med))} ${esc(neighbourUnit)}`} · ${esc(this.format(homes))} homes${ratio === null ? ' · Comparable usage unavailable' : ''}</p>`}</div></div>`;
    }
    timeOptions() {
      const format = this._hass?.locale?.time_format;
      return format === '24' ? {hour12:false} : format === '12' ? {hour12:true} : {};
    }
    time(value, full = false) {
      const date = new Date(value);
      if (!Number.isFinite(date.getTime())) return 'No reading yet';
      return new Intl.DateTimeFormat(this._hass?.locale?.language || undefined, {
        timeZone: this._hass?.config?.time_zone || 'UTC', ...this.timeOptions(),
        ...(full ? {month:'short', day:'numeric'} : {}), hour:'numeric', minute:'2-digit'
      }).format(date);
    }
    localParts(stamp, zone = this._hass?.config?.time_zone || 'UTC') {
      return Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
        timeZone:zone, year:'numeric', month:'2-digit', day:'2-digit',
        hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23'
      }).formatToParts(new Date(stamp)).filter(p => p.type !== 'literal').map(p => [p.type, p.value]));
    }
    dayKey(stamp, zone) {
      const p = this.localParts(stamp, zone);
      return `${p.year}-${p.month}-${p.day}`;
    }
    shiftDay(day, amount) {
      const date = new Date(day + 'T12:00:00Z');
      date.setUTCDate(date.getUTCDate() + amount);
      return date.toISOString().slice(0,10);
    }
    dayStart(day) {
      // Convert a local calendar boundary to UTC, including offset changes at DST.
      const target = Date.parse(day + 'T00:00:00Z');
      let stamp = target;
      for (let i = 0; i < 4; i++) {
        const p = this.localParts(stamp);
        const wall = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
        const delta = target - wall;
        stamp += delta;
        if (!delta) break;
      }
      return stamp;
    }
    dailyHistory(id) {
      const today = this.dayKey(Date.now());
      const zone = this._hass?.config?.time_zone || 'UTC';
      const key = `${id}|${zone}`;
      let entry = this._historyCache.get(key);
      if (id && this._hass.callWS && (!entry || (!entry.pending && (entry.day !== today || Date.now() - entry.updated >= 3600000)))) {
        entry = {day:today, updated:Date.now(), pending:true, totals:entry?.totals || new Map()};
        this._historyCache.set(key, entry);
        const start = this.dayStart(this.shiftDay(today, -7)), end = this.dayStart(today);
        const request = {type:'history/history_during_period', entity_ids:[id],
          start_time:new Date(start).toISOString(), end_time:new Date(end).toISOString(),
          include_start_time_state:false, significant_changes_only:false, minimal_response:false, no_attributes:true};
        // Include attribute-only updates so a heard zero-use day remains an observed zero.
        // No synthetic start state: carrying yesterday's value into a missing day is misleading.
        Promise.resolve().then(() => this._hass.callWS(request)).then(result => {
          const totals = new Map();
          for (const row of Array.isArray(result?.[id]) ? result[id] : []) {
            if (!row || typeof row !== 'object') continue;
            const rawStamp = row.lu ?? row.last_updated ?? row.last_changed;
            const stamp = typeof rawStamp === 'number' ? rawStamp * 1000 : Date.parse(rawStamp);
            const value = number({state:row.s ?? row.state});
            if (!Number.isFinite(stamp) || stamp < start || stamp >= end || value === null || value < 0) continue;
            const day = this.dayKey(stamp, zone);
            totals.set(day, Math.max(totals.get(day) ?? 0, value));
          }
          entry.totals = totals;
        }).catch(() => { /* Recorder may be disabled, excluded, or not yet have history. */ })
          .finally(() => {
            entry.pending = false;
            if (this._historyCache.get(key) === entry) this.render();
          });
      }
      const days = Array.from({length:7}, (_, i) => {
        const day = this.shiftDay(today, i - 7);
        return {day, value:entry?.totals.get(day) ?? null};
      });
      const known = days.filter(d => d.value !== null);
      return {days, usual:known.length ? known.reduce((sum,d) => sum + d.value, 0) / known.length : null, count:known.length};
    }
    hourLabel(hour) {
      return new Intl.DateTimeFormat(this._hass?.locale?.language || undefined, {
        timeZone:'UTC', hour:'numeric', ...this.timeOptions()
      }).format(new Date(Date.UTC(2026, 0, 1, hour)));
    }
    hourlyData(entity, factor) {
      const rows = entity?.attributes?.history;
      const day = this.dayKey(Date.now());
      const hours = Array(24).fill(null);
      const valid = Array.isArray(rows) ? rows.filter(r => r && Number.isFinite(Date.parse(r.end))
        && Date.parse(r.end) <= Date.now() && Number.isFinite(r.counts) && r.counts >= 0)
        .sort((a,b) => Date.parse(a.end) - Date.parse(b.end)) : [];
      const unique = new Map(valid.map(r => [Date.parse(r.end), r]));
      for (const [stamp, row] of unique) {
        if (this.dayKey(stamp) !== day) continue;
        const hour = +this.localParts(stamp).hour;
        // A repeated DST hour shares one local-hour bar; both observed intervals count.
        hours[hour] = (hours[hour] ?? 0) + row.counts * factor;
      }
      const observed = hours.filter(v => v !== null).length;
      const max = observed ? Math.max(...hours.filter(v => v !== null)) : null;
      return {hours, observed, elapsed:+this.localParts(Date.now()).hour + 1,
        peak:max, peakHour:max === null ? null : hours.indexOf(max), valid:[...unique.values()]};
    }
    ring(value, usual) {
      const ratio = value !== null && usual > 0 ? value / usual : null;
      const arc = 2 * Math.PI * 56;
      const label = ratio === null ? 'Learning your usual day' : `Today is ${this.format(Math.round(ratio * 100))} percent of your usual day`;
      return `<div class="ring"><svg viewBox="0 0 132 132" role="img" aria-label="${esc(label)}">
        <circle class="track" cx="66" cy="66" r="56" fill="none" stroke-width="12"/>
        ${ratio === null ? '' : `<circle class="progress" cx="66" cy="66" r="56" fill="none" stroke-width="12" stroke-linecap="round"
          stroke-dasharray="${Math.min(1,ratio) * arc} ${arc}" transform="rotate(-90 66 66)"/>
        ${ratio > 1 ? `<circle class="overflow" cx="66" cy="66" r="56" fill="none" stroke-width="12" stroke-linecap="round"
          stroke-dasharray="${Math.min(1,ratio - 1) * arc} ${arc}" transform="rotate(-90 66 66)"/>` : ''}`}</svg>
        <div class="ring-label" aria-hidden="true"><strong>${ratio === null ? '—' : esc(this.format(Math.round(ratio * 100)))+'%'}</strong><span>${ratio === null ? 'usual day' : 'of usual'}</span></div></div>`;
    }
    history(data, unit, factor, index, animate) {
      const max = Math.max(1, data.peak || 0);
      const bars = data.hours.map((value, hour) => {
        const label = `${this.hourLabel(hour)} hour: ${value === null ? 'Not heard · No observation' : this.format(value)+' '+unit}`;
        return `<button type="button" class="bar ${value === null ? 'missing' : value === 0 ? 'zero' : hour === data.peakHour ? 'peak' : ''}"
          data-focus="bar-${index}-${hour}" data-chart="${index}" aria-label="${esc(label)}" title="${esc(label)}"
          style="--height:${value === null ? 18 : Math.max(2,value/max*100)}%;--delay:${hour * 25}ms"><span class="bar-fill"></span></button>`;
      }).join('');
      return `<div class="chart"><div class="chart-heading"><h4>Today by hour</h4><span>Hatched = not heard</span></div>
        <div class="plot ${animate ? 'enter' : ''}" role="group" aria-label="Hourly water use today in ${esc(unit)}">${bars}</div>
        <div class="axis" aria-hidden="true">${[0,6,12,18].map(h => `<span>${esc(this.hourLabel(h))}</span>`).join('')}<span>${esc(this.hourLabel(23))}</span></div>
        <p class="chart-tip" data-tooltip="${index}" role="status">Tap a bar for usage and time</p>
        <details data-disclosure="history-${index}"><summary data-focus="history-${index}">Hourly history · values table</summary>
        <div class="scroll"><table><caption>Today by hour · ${esc(unit)}. Missing observations are not zero.</caption>
          <thead><tr><th scope="col">Hour</th><th scope="col">${esc(unit)}</th></tr></thead><tbody>
          ${data.hours.map((v,h) => `<tr><th scope="row">${esc(this.hourLabel(h))}</th><td>${v === null ? 'Not heard' : esc(this.format(v))}</td></tr>`).join('')}</tbody></table></div>
        ${data.valid.length ? `<div class="scroll"><table><caption>Recent transmitter intervals</caption><thead><tr><th scope="col">Interval ending</th><th scope="col">${esc(unit)}</th></tr></thead>
          <tbody>${data.valid.slice().reverse().map(r => `<tr><td>${esc(this.time(r.end,true))}</td><td>${esc(this.format(r.counts*factor))}</td></tr>`).join('')}</tbody></table></div>` : ''}
        <p class="note">Intervals follow the transmitter’s hourly cycle. Gaps are missing observations. Today includes observed intervals only; missed intervals are not estimated.</p></details></div>`;
    }
    week(history, unit) {
      const max = Math.max(1,...history.days.map(d => d.value || 0));
      const yesterday = history.days[6].value;
      return `<div class="week"><h4>Previous 7 days · Yesterday ${yesterday === null ? 'not heard' : esc(this.format(yesterday))+' '+esc(unit)}</h4>
        <div class="days" role="list" aria-label="Daily totals from recorded history">${history.days.map(({day,value},i) => {
          const date = new Date(day + 'T12:00:00Z');
          const weekday = new Intl.DateTimeFormat(this._hass?.locale?.language || undefined,{timeZone:'UTC',weekday:'short'}).format(date);
          const label = `${i === 6 ? 'Yesterday, ' : ''}${day}: ${value === null ? 'Not heard' : this.format(value)+' '+unit}`;
          return `<div role="listitem" class="day ${value === null ? 'missing' : ''} ${i === 6 ? 'yesterday' : ''}" aria-label="${esc(label)}" title="${esc(label)}">
            <div class="day-plot" aria-hidden="true"><span class="day-fill" style="--height:${value === null ? 18 : Math.max(3,value/max*100)}%"></span></div>
            <span aria-hidden="true">${i === 6 ? 'Yest.' : esc(weekday)}</span><span class="day-value" aria-hidden="true">${value === null ? '—' : esc(this.format(value))}</span></div>`;
        }).join('')}</div></div>`;
    }
    meter(meter, index) {
      const ids = this.resolve(meter), states = this._hass.states;
      const get = key => states[ids[key]];
      const hasLitres = !!(get('last_hour_litres') || get('today_litres') || get('total_litres'));
      const hour = get(hasLitres ? 'last_hour_litres' : 'last_hour');
      const todayKey = hasLitres ? 'today_litres' : 'today';
      const today = get(todayKey), total = get(hasLitres ? 'total_litres' : 'meter_count');
      const seen = get('last_seen'), stamp = Date.parse(seen?.state);
      const live = Number.isFinite(stamp) && Date.now() - stamp < 75 * 60000 && stamp <= Date.now();
      const unavailable = hour?.state === 'unavailable';
      const attrs = hour?.attributes || {};
      if (Number.isFinite(stamp) || [hour, today, total, get('snr'), get('signal_level')]
          .some(entity => number(entity) !== null) || typeof attrs.encrypted === 'boolean'
          || attrs.history?.length) this._seenMeters.add(meter);
      const waiting = !this._seenMeters.has(meter);
      const unit = hour?.attributes?.unit_of_measurement || (hasLitres ? 'L' : 'pulses');
      const name = meter.name || 'Water meter';
      if (!Object.values(ids).some(id => states[id])) {
        return `<section class="meter"><div class="header"><h3>${esc(name)}</h3><p class="empty">${this._registryError ? 'Device lookup failed. Configure entity IDs to continue.' : 'Waiting for MQTT entities. Check the configured entities or device and receiver configuration.'}</p></div></section>`;
      }
      const absolute = number(get('meter_reading'));
      const {calibrated, attrs:calibration} = this.calibrationState(ids);
      const factor = hasLitres ? (Number.isFinite(attrs.litres_per_count) ? attrs.litres_per_count
        : calibrated ? calibration.chosen_k : 1) : 1;
      const dialReady = calibrated || hasLitres;
      const data = this.hourlyData(hour, factor);
      const past = attrs.encrypted ? null : this.dailyHistory(ids[todayKey]);
      const status = waiting ? 'Waiting for first reading (can take up to an hour)' : unavailable ? 'Usage unavailable'
        : live ? 'Live · '+this.time(seen.state) : Number.isFinite(stamp) ? 'Last heard '+this.time(seen.state,true) : 'Waiting for a reading';
      const leak = get('possible_leak');
      const identity = Object.values(ids).map(id => id.match(/taggle_(\d+)_/)?.[1]).find(Boolean)
        || this.entityRegistry().find(e => Object.values(ids).includes(e.entity_id))?.unique_id?.match(/_(\d+)_/)?.[1];
      if (!this._entrances.has(meter)) this._entrances.set(meter, Date.now());
      return `<section class="meter"><div class="header">
        <svg class="wave" viewBox="0 0 960 120" preserveAspectRatio="none" aria-hidden="true"><path d="M0 70 Q60 40 120 70 T240 70 T360 70 T480 70 T600 70 T720 70 T840 70 T960 70 V120 H0 Z"/></svg>
        <div class="heading"><div class="identity"><span class="dot ${live && !unavailable ? 'live' : ''}" aria-hidden="true"></span><h3>${esc(name)}</h3>
        <span class="status${!waiting && (!live || unavailable) ? ' stale' : ''}">${esc(status)}</span></div>
        <span class="chip">${calibrated ? esc(this.format(calibration.chosen_k))+' L per pulse' : 'Not calibrated'}</span></div>
        ${attrs.encrypted ? '<p class="empty">Encrypted transmitter. Only identity and signal diagnostics are available.</p>' : `
        <div class="hero">${this.ring(number(today), past.usual)}<div class="today"><div class="today-label">Today</div>
          <div class="today-value">${esc(this.format(number(today)))}<small>${esc(unit)}</small></div>
          <p class="usual" title="${past.count} of the previous 7 days recorded">${past.usual === null ? 'Learning your usual day' : `Usual day ${esc(this.format(past.usual))} ${esc(unit)}`} · ${data.observed} of ${data.elapsed} hours heard</p></div></div>
        ${!hasLitres ? '<p class="uncalibrated" role="note"><strong>Not litres yet.</strong> These are raw pulses from the transmitter. Calibrate with the dial readings below.</p>' : ''}`}</div>
        ${attrs.encrypted ? '' : `<dl class="stats"><div><dt>Last hour</dt><dd>${esc(this.format(number(hour)))} <small>${esc(unit)}</small></dd></div>
          <div><dt>Peak</dt><dd>${esc(this.format(data.peak))} <small>${esc(unit)}</small></dd><div class="stat-note">${data.peakHour === null ? 'No hours heard' : esc(this.hourLabel(data.peakHour))+' hour'}</div></div>
          <div><dt>${dialReady ? 'Meter' : 'Meter count'}</dt><dd>${dialReady ? (absolute === null ? '—' : esc(new Intl.NumberFormat(this._hass?.locale?.language || undefined,
            {minimumFractionDigits:2,maximumFractionDigits:2}).format(absolute / 1000))) : esc(this.format(number(get('meter_count'))))}</dd><div class="stat-note">${dialReady ? 'kL on the dial' : 'pulses'}</div></div></dl>
        ${this.history(data, unit, factor, index, Date.now() - this._entrances.get(meter) < 1500)}${this.week(past, unit)}
        <div class="statuses"><div class="status-row ${leak?.state === 'on' ? 'leak-warning' : leak?.state === 'off' ? 'leak-ok' : ''}" role="status">
          <svg viewBox="0 0 24 24" aria-hidden="true">${leak?.state === 'off' ? '<path d="M20 6L9 17l-5-5"/>' : '<path d="M12 3L2 21h20L12 3zM12 9v5M12 17h.01"/>'}</svg>
          <div><strong>${leak?.state === 'on' ? 'Possible leak.' : leak?.state === 'off' ? 'No leak signs.' : 'Leak status unavailable.'}</strong>
          <span>${leak?.state === 'on' ? esc(leak.attributes?.reason || 'Check for running taps or continuous water use.') : leak?.state === 'off' ? 'Water stopped between uses today.' : 'Check the meter’s possible_leak entity.'}</span></div></div>
        ${this.comparison(meter, today, unit)}</div>`}
        <div class="support">${!attrs.encrypted ? this.readPanel(meter, ids, index) : ''}</div>
        <div class="footer" title="Signal level ${esc(this.format(number(get('signal_level'))))} dBFS">Signal ${esc(this.format(number(get('snr'))))} dB · ${esc(identity ? 'Taggle '+identity : name)}</div></section>`;
    }
    render() {
      if (!this._config || !this._hass) return;
      this.toggleAttribute?.('data-reduced-motion', !!this._motion?.matches);
      const markup = `<style>${css}</style><ha-card>${this._config.title ? '<h2>'+esc(this._config.title)+'</h2>' : ''}
        ${this._config.meters.map((m,i) => this.meter(m,i)).join('')}</ha-card>`;
      if (markup === this._lastMarkup) return;
      const opened = new Map([...this.shadowRoot.querySelectorAll('details')].map(d => [d.dataset.disclosure, d.open]));
      const active = this.shadowRoot.activeElement;
      const focus = active?.dataset.focus;
      const selection = active?.selectionStart;
      const selectionEnd = active?.selectionEnd;
      this.shadowRoot.innerHTML = markup;
      this.shadowRoot.querySelectorAll('details').forEach(d => { d.open = !!opened.get(d.dataset.disclosure); });
      this.shadowRoot.querySelectorAll('.reading-form').forEach(form => {
        const meter = this._config.meters[Number(form.dataset.meter)];
        const draft = this._drafts.get(meter);
        form.addEventListener('input', event => {
          const field = event.target.dataset.field;
          if (!field) return;
          draft[field] = event.target.value;
          if (field === 'reading') draft.badInput = event.target.validity.badInput;
          draft.error = draft.message = '';
          event.target.setAttribute('aria-invalid', 'false');
          form.querySelector('.form-feedback').textContent = '';
        });
        form.addEventListener('submit', event => { event.preventDefault(); this.saveReading(meter); });
      });
      this.shadowRoot.querySelectorAll('.bar').forEach(bar => {
        const show = () => {
          const tip = this.shadowRoot.querySelector(`[data-tooltip="${bar.dataset.chart}"]`);
          if (tip) tip.textContent = bar.getAttribute('aria-label');
        };
        for (const event of ['pointerenter', 'focus', 'click']) bar.addEventListener(event, show);
      });
      if (focus) {
        let target = this.shadowRoot.querySelector(`[data-focus="${focus}"]`);
        // Keep the native editor's transient decimal/time state during HA refreshes.
        // The browser may expose an incomplete number as an empty value.
        if (target && ['reading', 'time'].includes(active.dataset.field) && target.value === active.value
            && target.closest('.reading-form')?.getAttribute('aria-busy') === 'false') {
          active.setAttribute('aria-invalid', target.getAttribute('aria-invalid'));
          target.replaceWith(active);
          target = active;
        }
        if (target?.matches(':disabled')) target = target.closest('form')?.querySelector('button:not(:disabled)') || target;
        target?.focus({preventScroll:true});
        if (selection !== null && selection !== undefined && target?.setSelectionRange) target.setSelectionRange(selection, selectionEnd);
      }
      this._lastMarkup = markup;
    }
  }
  if (!customElements.get('taggle-card')) customElements.define('taggle-card', TaggleCard);
  window.customCards = window.customCards || [];
  window.customCards.push({type: 'taggle-card', name: 'Taggle water meter',
    description: 'Hourly usage and signal diagnostics from MQTT-discovered Taggle meters.'});
})();

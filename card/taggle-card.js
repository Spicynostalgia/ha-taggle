/* Taggle card 0.3.0. MIT. Home Assistant states only; no external requests. */
(() => {
  'use strict';
  const KEYS = ['last_hour_litres', 'today_litres', 'total_litres', 'last_hour',
    'today', 'meter_count', 'snr', 'signal_level', 'last_seen', 'calibration_status', 'meter_reading', 'possible_leak',
    'dial_unit', 'dial_reading', 'read_dial_now'];
  const CONTROLS = {dial_unit:'select', dial_reading:'text'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g,
    c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const number = entity => entity && !['unknown', 'unavailable', ''].includes(entity.state)
    && Number.isFinite(Number(entity.state)) ? Number(entity.state) : null;
  const css = `
    :host { container-type:inline-size; display:block; color:var(--primary-text-color,#171717); font-family:var(--primary-font-family,Roboto,system-ui,sans-serif); }
    * { box-sizing:border-box; }
    ha-card { display:block; padding:24px; background:var(--ha-card-background,var(--card-background-color,#fff));
      border:1px solid var(--divider-color,#ddd); border-radius:var(--ha-card-border-radius,12px); box-shadow:none;
      --muted:var(--secondary-text-color,#606060); --water:var(--primary-color,#1769aa); }
    ::selection { background:var(--water); color:var(--text-primary-color,#fff); }
    h2,h3,p { margin:0; overflow-wrap:anywhere; } h2 { font-size:22px; font-weight:500; line-height:1.3; }
    h3 { font-size:17px; font-weight:500; } p { font-size:14px; line-height:1.5; color:var(--muted); }
    section { margin-top:24px; } section+section { padding-top:24px; border-top:1px solid var(--divider-color,#ddd); }
    .heading { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:baseline; gap:8px 16px; }
    .status { font-size:14px; color:var(--muted); } .stale { color:var(--error-color,#b3261e); }
    dl { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin:20px 0; }
    dl div { min-width:0; } dt { color:var(--muted); font-size:14px; line-height:1.5; }
    dd { margin:6px 0 0; font-size:28px; line-height:1.3; overflow-wrap:anywhere; font-variant-numeric:tabular-nums; }
    dd small { font-size:14px; color:var(--muted); } .diagnostics { display:flex; gap:8px 20px; flex-wrap:wrap; font-size:14px; color:var(--muted); }
    details { margin-top:20px; } summary { font-size:14px; cursor:pointer; padding-block:10px; color:var(--water); }
    summary:hover { text-decoration:underline; text-underline-offset:3px; }
    summary:focus-visible,button:focus-visible,a:focus-visible,input:focus-visible,
    .units input:focus-visible+span { outline:2px solid var(--water); outline-offset:3px; }
    .plot { display:flex; height:104px; align-items:flex-end; gap:3px; margin:16px 0 8px; border-bottom:1px solid var(--divider-color,#ddd); }
    .bar { display:block; flex:1; min-width:0; background:var(--water); height:var(--height); }
    .bar.zero { background:transparent; border-bottom:2px solid var(--water); }
    .bar.missing { background:transparent; border-bottom:1px dashed var(--muted); }
    .axis { display:flex; justify-content:space-between; gap:12px; color:var(--muted); font-size:14px; }
    .scroll { overflow-x:auto; max-height:240px; scrollbar-color:var(--muted) transparent; }
    table { width:100%; border-collapse:collapse; font-size:14px; font-variant-numeric:tabular-nums; }
    th,td { padding:10px 0; border-bottom:1px solid var(--divider-color,#ddd); text-align:start; }
    th { color:var(--muted); font-weight:400; } th:last-child,td:last-child { text-align:end; padding-inline-start:16px; }
    .empty { margin-top:16px; } .note { margin-top:12px; }
    .comparison { margin-bottom:12px; }
    .calibration { margin-top:12px; } .calibration a { color:var(--water); text-underline-offset:3px; }
    .calibration a:hover { text-decoration-thickness:2px; }
    .calibration.warning { color:var(--error-color,#b3261e); }
    .uncalibrated { margin:12px 0 0; padding:8px 12px; border-left:3px solid var(--water); border-radius:6px;
      background:color-mix(in srgb, var(--water) 12%, transparent); }
    .register { margin-top:16px; color:var(--primary-text-color,#171717); font-variant-numeric:tabular-nums; }
    .register strong { font-size:24px; font-weight:500; }
    .leak { margin-top:12px; display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 8px; }
    .leak-badge { padding:2px 8px; border-radius:4px; font-size:13px; font-weight:500;
      color:var(--primary-text-color,#171717); background:var(--secondary-background-color,var(--divider-color,#eee)); }
    .read-panel { margin-top:20px; padding-top:20px; border-top:1px solid var(--divider-color,#ddd); }
    .read-now { padding:12px; color:var(--primary-text-color,#171717);
      background:color-mix(in srgb,var(--water) 18%,var(--ha-card-background,var(--card-background-color,#fff)));
      border-left:4px solid var(--water); margin-bottom:12px; }
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
    @container (max-width:480px) {
      ha-card { padding:16px; } dl { gap:16px; grid-template-columns:repeat(2,minmax(0,1fr)); }
      dd { font-size:24px; } dl div:last-child { grid-column:1/-1; display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
      dl div:last-child dd { margin-top:0; white-space:nowrap; }
    }
  `;

  class TaggleCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({mode: 'open'});
      this._registry = [];
      this._seenMeters = new WeakSet();
      this._drafts = new WeakMap();
    }
    setConfig(config) {
      const meters = config.meters || [config];
      if (!Array.isArray(meters) || !meters.length || meters.some(m => !m.entities && !m.device)) {
        throw new Error('Configure entities or a device for each Taggle meter.');
      }
      this._config = {...config, meters};
      this._registryRequested = false;
      this._lastMarkup = '';
      this.render();
    }
    connectedCallback() {
      clearInterval(this._timer);
      this._timer = setInterval(() => this.render(), 60000);
      this.render();
    }
    disconnectedCallback() { clearInterval(this._timer); }
    getCardSize() { return 4 * (this._config?.meters.length || 1); }
    getGridOptions() { return {columns: 12, min_columns: 6}; }
    set hass(hass) {
      this._hass = hass;
      if (this._config && !this._registryRequested && hass.callWS) {
        this._registryRequested = true;
        hass.callWS({type: 'config/entity_registry/list'}).then(registry => {
          this._registry = registry;
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
      if (!meter.device) for (const key of ['calibration_status', 'meter_reading', 'last_hour_litres', 'today_litres', 'total_litres', 'read_dial_now', ...Object.keys(CONTROLS)]) {
        const found = device && registry.find(e => e.device_id === device && (e.unique_id || '').endsWith('_' + key));
        const fallback = (CONTROLS[key] || (key === 'read_dial_now' ? 'binary_sensor' : 'sensor')) + '.' + base + key;
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
      if (!average && !median && !counted) return '';
      const avg = number(average), med = number(median), homes = number(counted);
      if (avg === null || homes === null || homes < 3) {
        return '<p class="note comparison">Neighbourhood comparison unknown · waiting for enough qualifying homes.</p>';
      }
      const neighbourUnit = average.attributes?.unit_of_measurement || 'pulses';
      const own = number(today);
      const ratio = own !== null && avg > 0 && unit === neighbourUnit ? (own / avg - 1) * 100 : null;
      const difference = ratio === null ? '' : Math.round(Math.abs(ratio)) === 0 ? ' · Same as average'
        : ` · ${this.format(Math.round(Math.abs(ratio)))}% ${ratio < 0 ? 'below' : 'above'}`;
      return `<p class="note comparison">Today ${esc(this.format(own))} ${esc(unit)} · Neighbourhood avg ${esc(this.format(avg))} ${esc(neighbourUnit)}${esc(difference)}<br>
        ${med === null ? '' : `Median ${esc(this.format(med))} ${esc(neighbourUnit)} · `}${esc(this.format(homes))} homes</p>`;
    }
    time(value, full = false) {
      const date = new Date(value);
      if (!Number.isFinite(date.getTime())) return 'No reading yet';
      return new Intl.DateTimeFormat(this._hass?.locale?.language || undefined, {
        timeZone: this._hass?.config?.time_zone || 'UTC',
        ...(full ? {month: 'short', day: 'numeric'} : {}), hour: '2-digit', minute: '2-digit'
      }).format(date);
    }
    history(entity, factor, index) {
      const rows = entity?.attributes?.history;
      if (!Array.isArray(rows) || !rows.length) return '';
      const valid = rows.filter(r => Number.isFinite(Date.parse(r.end)) && Number.isFinite(r.counts) && r.counts >= 0)
        .slice(-48).sort((a, b) => Date.parse(a.end) - Date.parse(b.end));
      if (!valid.length) return '';
      const end = Date.parse(valid[valid.length-1].end);
      const slots = new Map(valid.map(r => [Math.round((end-Date.parse(r.end))/3600000), r]));
      const max = Math.max(1, ...valid.map(r => r.counts * factor));
      const unit = entity.attributes.unit_of_measurement || 'pulses';
      const bars = Array.from({length:48}, (_, i) => {
        const row = slots.get(47-i), value = row ? row.counts * factor : null;
        const label = `${this.time(end-(47-i)*3600000, true)}: ${row ? this.format(value)+' '+unit : 'No observation'}`;
        return `<span class="bar ${!row ? 'missing' : value === 0 ? 'zero' : ''}" style="--height:${row ? Math.max(2,value/max*100) : 2}%" title="${esc(label)}"></span>`;
      }).join('');
      return `<details data-disclosure="history-${index}"><summary data-focus="history-${index}">Hourly history · ${valid.length} observations</summary>
        <div class="plot" role="img" aria-label="48 hourly intervals. Missing readings appear as dashed marks; values are in the table below.">${bars}</div>
        <div class="axis"><span>${esc(this.time(end-47*3600000,true))}</span><span>${esc(this.time(end,true))}</span></div>
        <div class="scroll"><table><thead><tr><th scope="col">Interval ending</th><th scope="col">${esc(unit)}</th></tr></thead>
        <tbody>${valid.slice().reverse().map(r => `<tr><td>${esc(this.time(r.end,true))}</td><td>${esc(this.format(r.counts*factor))}</td></tr>`).join('')}</tbody></table></div>
        <p class="note">Intervals follow the transmitter’s hourly cycle. Gaps are missing observations.</p></details>`;
    }
    meter(meter, index) {
      const ids = this.resolve(meter), states = this._hass.states;
      const get = key => states[ids[key]];
      const hasLitres = !!get('last_hour_litres');
      const hour = get(hasLitres ? 'last_hour_litres' : 'last_hour');
      const today = get(hasLitres ? 'today_litres' : 'today');
      const total = get(hasLitres ? 'total_litres' : 'meter_count');
      const seen = get('last_seen');
      const stamp = Date.parse(seen?.state);
      const stale = Number.isFinite(stamp) && Date.now()-stamp > 3*3600000;
      const unavailable = hour?.state === 'unavailable';
      const attrs = hour?.attributes || {};
      // HA can mark last_seen unavailable too. Retained frame attributes and
      // observations in this session still distinguish an outage from first use.
      if (Number.isFinite(stamp) || [hour, today, total, get('snr'), get('signal_level')]
          .some(entity => number(entity) !== null) || typeof attrs.encrypted === 'boolean'
          || attrs.history?.length) this._seenMeters.add(meter);
      const waiting = !this._seenMeters.has(meter);
      const unit = hour?.attributes?.unit_of_measurement || (hasLitres ? 'L' : 'pulses');
      const name = meter.name || 'Water meter';
      if (!Object.values(ids).some(id => states[id])) {
        return `<section><h3>${esc(name)}</h3><p class="empty">${this._registryError ? 'Device lookup failed. Configure entity IDs to continue.' : 'Waiting for MQTT entities. Check the configured entities or device and receiver configuration.'}</p></section>`;
      }
      const absolute = number(get('meter_reading'));
      const {calibrated, warning} = this.calibrationState(ids);
      const metrics = [[hour, 'Last hour'], [today, 'Today · observed'], [total, hasLitres ? 'Total · calibrated' : 'Meter count']];
      const leak = get('possible_leak');
      return `<section><div class="heading"><h3>${esc(name)}</h3>
        <span class="status ${!waiting && (stale || unavailable) ? 'stale' : ''}">${waiting ? 'Waiting for first reading (can take up to an hour)' : stale ? 'No recent signal' : unavailable ? 'Usage unavailable' : Number.isFinite(stamp) ? 'Last seen '+esc(this.time(seen.state)) : 'Waiting for a reading'}</span></div>
        ${calibrated && !warning ? this.calibration(meter, ids) : ''}
        ${absolute !== null ? `<p class="register">Meter reading <strong>${esc(new Intl.NumberFormat(this._hass?.locale?.language || undefined, {maximumFractionDigits:0}).format(absolute))}</strong> L</p>` : ''}
        ${leak?.state === 'on' ? `<p class="leak" role="status"><span class="leak-badge">Possible leak</span>${esc(leak.attributes?.reason)}</p>` : ''}
        ${!attrs.encrypted && !hasLitres ? '<p class="uncalibrated" role="note"><strong>Not litres yet.</strong> These are raw pulses from the transmitter. Calibrate with the dial readings below.</p>' : ''}
        <dl>${metrics.map(([entity,label]) => `<div><dt>${label}</dt><dd>${esc(this.format(number(entity)))} <small>${esc(unit)}</small></dd></div>`).join('')}</dl>
        ${this.comparison(meter, today, unit)}
        <div class="diagnostics"><span>SNR ${esc(this.format(number(get('snr'))))} dB</span>
        <span>Signal ${esc(this.format(number(get('signal_level'))))} dBFS</span>
        ${Number.isFinite(attrs.hours_observed) ? `<span>${attrs.hours_observed} hourly intervals today</span>` : ''}</div>
        ${attrs.encrypted || hasLitres ? `<p class="note">${attrs.encrypted ? 'Encrypted transmitter. Only identity and signal diagnostics are available.' : 'Today includes observed intervals only; missed intervals are not estimated.'}</p>` : ''}
        ${this.readPanel(meter, ids, index)}
        ${!unavailable ? this.history(hour, hasLitres && Number.isFinite(attrs.litres_per_count) ? attrs.litres_per_count : 1, index) : ''}</section>`;
    }
    render() {
      if (!this._config || !this._hass) return;
      const markup = `<style>${css}</style><ha-card><h2>${esc(this._config.title || 'Water usage')}</h2>
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

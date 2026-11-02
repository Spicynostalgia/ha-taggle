/* Taggle card 0.2.1. MIT. Home Assistant states only; no external requests. */
(() => {
  'use strict';
  const KEYS = ['last_hour_litres', 'today_litres', 'total_litres', 'last_hour',
    'today', 'meter_count', 'snr', 'signal_level', 'last_seen'];
  KEYS.push('possible_leak');
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
    summary:focus-visible,button:focus-visible { outline:2px solid var(--water); outline-offset:3px; }
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
    .leak { margin-top:12px; display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 8px; }
    .leak-badge { padding:2px 8px; border-radius:4px; font-size:13px; font-weight:500;
      color:var(--primary-text-color,#171717); background:var(--secondary-background-color,var(--divider-color,#eee)); }
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
      if ((this._config?.meters.some(m => m.device || m.neighbourhood?.device)
          || this._config?.neighbourhood?.device) && !this._registryRequested && hass.callWS) {
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
      if (meter.entities && !Array.isArray(meter.entities)) return {...meter.entities};
      const registry = this.entityRegistry();
      const selected = meter.device ? registry.filter(e => e.device_id === meter.device) : [];
      const ids = Array.isArray(meter.entities) ? meter.entities : selected.map(e => e.entity_id);
      for (const id of ids) {
        const entry = registry.find(e => e.entity_id === id);
        const uniqueKey = entry?.unique_id?.match(/^.+_\d+_(.+)$/)?.[1];
        const entityKey = id.match(/^(?:sensor|binary_sensor)\.taggle_\d+_(?:water_)?(.+)$/)?.[1];
        const key = KEYS.includes(uniqueKey) ? uniqueKey : entityKey;
        if (KEYS.includes(key)) result[key] = id;
      }
      return result;
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
    history(entity, factor) {
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
      return `<details><summary>Hourly history · ${valid.length} observations</summary>
        <div class="plot" role="img" aria-label="48 hourly intervals. Missing readings appear as dashed marks; values are in the table below.">${bars}</div>
        <div class="axis"><span>${esc(this.time(end-47*3600000,true))}</span><span>${esc(this.time(end,true))}</span></div>
        <div class="scroll"><table><thead><tr><th scope="col">Interval ending</th><th scope="col">${esc(unit)}</th></tr></thead>
        <tbody>${valid.slice().reverse().map(r => `<tr><td>${esc(this.time(r.end,true))}</td><td>${esc(this.format(r.counts*factor))}</td></tr>`).join('')}</tbody></table></div>
        <p class="note">Intervals follow the transmitter’s hourly cycle. Gaps are missing observations.</p></details>`;
    }
    meter(meter) {
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
      const metrics = [[hour, 'Last hour'], [today, 'Today · observed'], [total, hasLitres ? 'Total · calibrated' : 'Meter count']];
      const leak = get('possible_leak');
      return `<section><div class="heading"><h3>${esc(name)}</h3>
        <span class="status ${!waiting && (stale || unavailable) ? 'stale' : ''}">${waiting ? 'Waiting for first reading (can take up to an hour)' : stale ? 'No recent signal' : unavailable ? 'Usage unavailable' : Number.isFinite(stamp) ? 'Last seen '+esc(this.time(seen.state)) : 'Waiting for a reading'}</span></div>
        ${leak?.state === 'on' ? `<p class="leak" role="status"><span class="leak-badge">Possible leak</span>${esc(leak.attributes?.reason)}</p>` : ''}
        <dl>${metrics.map(([entity,label]) => `<div><dt>${label}</dt><dd>${esc(this.format(number(entity)))} <small>${esc(unit)}</small></dd></div>`).join('')}</dl>
        ${this.comparison(meter, today, unit)}
        <div class="diagnostics"><span>SNR ${esc(this.format(number(get('snr'))))} dB</span>
        <span>Signal ${esc(this.format(number(get('signal_level'))))} dBFS</span>
        ${Number.isFinite(attrs.hours_observed) ? `<span>${attrs.hours_observed} hourly intervals today</span>` : ''}</div>
        <p class="note">${attrs.encrypted ? 'Encrypted transmitter. Only identity and signal diagnostics are available.' : hasLitres ? 'Today includes observed intervals only; missed intervals are not estimated.' : 'Raw pulses. Configure a calibrated litres-per-count scale to display litres.'}</p>
        ${!unavailable ? this.history(hour, hasLitres && Number.isFinite(attrs.litres_per_count) ? attrs.litres_per_count : 1) : ''}</section>`;
    }
    render() {
      if (!this._config || !this._hass) return;
      const markup = `<style>${css}</style><ha-card><h2>${esc(this._config.title || 'Water usage')}</h2>
        ${this._config.meters.map(m => this.meter(m)).join('')}</ha-card>`;
      if (markup === this._lastMarkup) return;
      const opened = [...this.shadowRoot.querySelectorAll('details')].map(d => d.open);
      this.shadowRoot.innerHTML = markup;
      this.shadowRoot.querySelectorAll('details').forEach((d,i) => { d.open = !!opened[i]; });
      this._lastMarkup = markup;
    }
  }
  if (!customElements.get('taggle-card')) customElements.define('taggle-card', TaggleCard);
  window.customCards = window.customCards || [];
  window.customCards.push({type: 'taggle-card', name: 'Taggle water meter',
    description: 'Hourly usage and signal diagnostics from MQTT-discovered Taggle meters.'});
})();

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let Card;
class HTMLElement {
  attachShadow() {
    this.shadowRoot = { innerHTML: '', querySelectorAll: () => [] };
  }
}
vm.runInNewContext(fs.readFileSync('card/taggle-card.js', 'utf8'), {
  HTMLElement, customElements: {get: () => false, define: (_, value) => { Card = value; }},
  window: {}, Intl, Date, Number, setInterval, clearInterval,
});
const state = (value, attributes = {}) => ({state: String(value), attributes});
const hass = () => ({locale: {language: 'en'}, config: {time_zone: 'UTC'}, states: {
  'sensor.taggle_123456_last_hour': state(10, {unit_of_measurement:'pulses', hours_observed: 2,
    history:[{end:'2026-01-01T01:00:00Z',counts:10}]}),
  'sensor.taggle_123456_today': state(16),
  'sensor.taggle_123456_meter_count': state(16),
  'sensor.taggle_123456_last_seen': state(new Date().toISOString()),
}});

test('entity list renders only the configured meter, escaped title and history', () => {
  const card = new Card();
  card.setConfig({title:'<img src=x>', entities:Object.keys(hass().states)});
  card.hass = hass();
  assert.match(card.shadowRoot.innerHTML, /&lt;img src=x&gt;/);
  assert.match(card.shadowRoot.innerHTML, /Hourly history/);
  assert.match(card.shadowRoot.innerHTML, /16/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<img/);
});
test('renamed entities resolve by device registry unique ID', () => {
  const card = new Card();
  card.setConfig({device:'fake-device'});
  const ha = hass();
  ha.entities = { 'sensor.renamed': {entity_id:'sensor.renamed',device_id:'fake-device',
    unique_id:'taggle_123456_last_hour'}};
  ha.states['sensor.renamed'] = state(20);
  card.hass = ha;
  assert.equal(card.resolve(card._config.meters[0]).last_hour, 'sensor.renamed');
  assert.match(card.shadowRoot.innerHTML, /20/);
});
test('unavailable and missing entities do not display fabricated zeros', () => {
  const card = new Card();
  card.setConfig({entities:{last_hour:'sensor.missing'}});
  card.hass = hass();
  assert.match(card.shadowRoot.innerHTML, /Waiting for MQTT entities/);
  const ha = hass();
  ha.states['sensor.missing'] = state('unavailable');
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /Waiting for first reading \(can take up to an hour\)/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /class="status stale"|Usage unavailable/);
  assert.match(card.shadowRoot.innerHTML, /—/);
});
test('fresh unknown or unavailable states and no last_seen show a neutral first-reading status', () => {
  for (const value of ['unknown', 'unavailable']) {
    for (const seen of [undefined, value]) {
      const card = new Card();
      card.setConfig({entities:Object.keys(hass().states)});
      const ha = hass();
      for (const id of Object.keys(ha.states)) ha.states[id] = state(value);
      if (seen === undefined) delete ha.states['sensor.taggle_123456_last_seen'];
      card.hass = ha;
      assert.match(card.shadowRoot.innerHTML, /Waiting for first reading \(can take up to an hour\)/);
      assert.doesNotMatch(card.shadowRoot.innerHTML, /class="status stale"|Usage unavailable/);
    }
  }
});
test('a previously seen meter keeps its warning when usage becomes unavailable', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states)});
  const ha = hass();
  card.hass = ha;
  ha.states['sensor.taggle_123456_last_hour'] = state('unavailable');
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /class="status stale">Usage unavailable/);
  ha.states['sensor.taggle_123456_last_seen'] = state(new Date(Date.now()-4*3600000).toISOString());
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /class="status stale">No recent signal/);
  for (const id of Object.keys(ha.states)) ha.states[id] = state('unavailable');
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /class="status stale">Usage unavailable/);
});
test('retained frame attributes distinguish an outage from first use even after card reload', () => {
  for (const attributes of [{encrypted:true}, {encrypted:false}, {history:[{counts:10}]}]) {
    const card = new Card();
    card.setConfig({entities:Object.keys(hass().states)});
    const ha = hass();
    for (const id of Object.keys(ha.states)) ha.states[id] = state('unavailable');
    ha.states['sensor.taggle_123456_last_hour'].attributes = attributes;
    card.hass = ha;
    assert.match(card.shadowRoot.innerHTML, /class="status stale">Usage unavailable/);
    assert.doesNotMatch(card.shadowRoot.innerHTML, /Waiting for first reading/);
  }
});
test('each meter has its own first-reading status and a first frame clears waiting', () => {
  const card = new Card();
  card.setConfig({meters:[{name:'Seen', entities:Object.keys(hass().states)},
    {name:'Fresh', entities:{last_hour:'sensor.fresh'}}]});
  const ha = hass();
  ha.states['sensor.fresh'] = state('unknown');
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /Waiting for first reading/);
  ha.states['sensor.fresh'] = state(0);
  card.hass = ha;
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Waiting for first reading/);
});
test('invalid configuration has an actionable error', () => {
  assert.throws(() => new Card().setConfig({}), /Configure entities or a device/);
});
test('distribution matches the editable source', () => {
  assert.equal(fs.readFileSync('dist/taggle-card.js','utf8'),fs.readFileSync('card/taggle-card.js','utf8'));
});

const withNeighbourhood = (ha = hass(), unit = 'pulses') => {
  for (const [key, value] of Object.entries({average_today:20, median_today:18, meters_counted:14})) {
    ha.states['sensor.taggle_neighbourhood_'+key] = state(value, {unit_of_measurement:unit});
  }
  return ha;
};
test('default neighbourhood row shows average, median, homes and percentage below', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states)});
  card.hass = withNeighbourhood();
  assert.match(card.shadowRoot.innerHTML, /Today 16 pulses · Neighbourhood avg 20 pulses · 20% below/);
  assert.match(card.shadowRoot.innerHTML, /Median 18 pulses · 14 homes/);
});
test('explicit renamed neighbourhood entities are escaped and support above and zero', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states), neighbourhood:{
    average_today:'sensor.average', median_today:'sensor.median', meters_counted:'sensor.homes'}});
  const ha = hass();
  ha.states['sensor.average'] = state(10, {unit_of_measurement:'<pulses>'});
  ha.states['sensor.median'] = state(8);
  ha.states['sensor.homes'] = state(4);
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /&lt;pulses&gt;/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /% above/); // Units differ.
  ha.states['sensor.average'].attributes.unit_of_measurement = 'pulses';
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /60% above/);
  ha.states['sensor.average'] = state(0);
  card.hass = ha;
  assert.doesNotMatch(card.shadowRoot.innerHTML, /% (above|below)|Infinity|NaN/);
});
test('unknown, below-floor and absent neighbourhood states never fabricate comparisons', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states)});
  const ha = withNeighbourhood();
  ha.states['sensor.taggle_neighbourhood_average_today'].state = 'unknown';
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /comparison unknown/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /% below/);
  ha.states['sensor.taggle_neighbourhood_average_today'].state = '20';
  ha.states['sensor.taggle_neighbourhood_meters_counted'].state = '2';
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /comparison unknown/);
  card.hass = hass();
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Neighbourhood/);
});
test('neighbourhood device resolves renamed registry entities and per-meter options override', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states), neighbourhood:{device:'neighbours'}});
  const ha = hass();
  ha.entities = {};
  for (const [key, value] of Object.entries({average_today:20, median_today:18, meters_counted:3})) {
    const id = 'sensor.renamed_'+key;
    ha.entities[id] = {entity_id:id, device_id:'neighbours', unique_id:'taggle_neighbourhood_'+key};
    ha.states[id] = state(value, {unit_of_measurement:'pulses'});
  }
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /20% below/);
  card.setConfig({meters:[{entities:Object.keys(hass().states), neighbourhood:false}],
    neighbourhood:{device:'neighbours'}});
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Neighbourhood/);
});
test('explicit neighbourhood device does not fall back to a different receiver', () => {
  const card = new Card();
  card.setConfig({entities:Object.keys(hass().states), neighbourhood:{device:'missing-device'}});
  card.hass = withNeighbourhood();
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Neighbourhood avg/);
});

test('device lookup matches today exactly even when comparison is listed first or last', () => {
  for (const keys of [['vs_neighbourhood_today', 'today'], ['today', 'vs_neighbourhood_today'],
                      ['vs_neighbourhood_today']]) {
    const card = new Card();
    card.setConfig({device:'meter'});
    const ha = hass();
    ha.entities = Object.fromEntries(keys.map(key => {
      const id = 'sensor.taggle_123456_' + key;
      ha.states[id] = state(key === 'today' ? 16 : 80);
      return [id, {entity_id:id, device_id:'meter', unique_id:'taggle_123456_' + key}];
    }));
    card.hass = ha;
    const ids = card.resolve(card._config.meters[0]);
    assert.equal(ids.today, keys.includes('today') ? 'sensor.taggle_123456_today' : undefined);
    assert.equal(ids.last_hour, undefined);
  }
});

test('entity list fallback supports default and HA name-derived water IDs without suffix collisions', () => {
  const card = new Card();
  const keys = ['last_hour', 'today', 'last_hour_litres', 'today_litres', 'total_litres'];
  for (const prefix of ['', 'water_']) {
    const entities = keys.map(key => 'sensor.taggle_123456_' + prefix + key);
    entities.push('sensor.taggle_123456_vs_neighbourhood_today', 'sensor.unrelated_today');
    card.setConfig({entities});
    card.hass = hass();
    const ids = card.resolve(card._config.meters[0]);
    for (const key of keys) assert.equal(ids[key], 'sensor.taggle_123456_' + prefix + key);
  }
});

test('device lookup fetches stable unique IDs even when frontend entity map is present', async () => {
  const card = new Card();
  card.setConfig({device:'meter'});
  const ha = hass();
  const records = ['last_hour', 'today', 'last_hour_litres', 'today_litres', 'total_litres'].map(key => ({
    entity_id:'sensor.taggle_123456_water_' + key, device_id:'meter',
    unique_id:'custom/prefix_123456_' + key,
  }));
  // A user rename cannot be resolved from its entity ID alone.
  records[1].entity_id = 'sensor.kitchen_water';
  records.push({entity_id:'sensor.taggle_123456_vs_neighbourhood_today', device_id:'meter',
    unique_id:'custom/prefix_123456_vs_neighbourhood_today'});
  ha.entities = Object.fromEntries(records.map(({unique_id, ...entry}) => [entry.entity_id, entry]));
  let calls = 0;
  ha.callWS = async message => {
    assert.equal(message.type, 'config/entity_registry/list');
    calls++;
    return records;
  };
  card.hass = ha;
  await Promise.resolve();
  const ids = card.resolve(card._config.meters[0]);
  assert.equal(ids.today, 'sensor.kitchen_water');
  assert.equal(ids.last_hour, 'sensor.taggle_123456_water_last_hour');
  assert.equal(ids.total_litres, 'sensor.taggle_123456_water_total_litres');
  card.hass = ha;
  assert.equal(calls, 1);
});

test('manual calibration prompt includes the local expected transmission and device link', () => {
  const card = new Card();
  card.setConfig({device:'meter-device'});
  const ha = hass();
  ha.config.time_zone = 'Australia/Brisbane';
  ha.entities = Object.fromEntries(['last_hour', 'calibration_status'].map(key => {
    const id = 'sensor.taggle_123456_' + key;
    return [id, {entity_id:id, device_id:'meter-device', unique_id:'taggle_123456_' + key}];
  }));
  ha.states['sensor.taggle_123456_calibration_status'] = state('Needs 2 readings — enter your dial reading', {
    next_transmission:'2026-11-02T08:41:00+00:00', chosen_k:null
  });
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /Next transmission expected ≈ 18:41/);
  assert.match(card.shadowRoot.innerHTML, /within 10 minutes, before water use/);
  assert.match(card.shadowRoot.innerHTML, /href="\/config\/devices\/device\/meter-device"/);
  assert.match(card.shadowRoot.innerHTML, /enter your dial reading/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /class="register"/);
});

test('old pulse mappings acquire automatic litre entities and whole-litre absolute reading', () => {
  const card = new Card();
  card.setConfig({entities:{last_hour:'sensor.taggle_123456_last_hour'}});
  const ha = hass();
  ha.states['sensor.taggle_123456_calibration_status'] = state('Calibrated: 5 L per pulse — standard value', {chosen_k:5});
  ha.states['sensor.taggle_123456_meter_reading'] = state(1597861.23, {unit_of_measurement:'L'});
  ha.states['sensor.taggle_123456_last_hour_litres'] = state(50, {unit_of_measurement:'L'});
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /Calibrated: 5 L per pulse/);
  assert.match(card.shadowRoot.innerHTML, /Meter reading <strong>1,597,861<\/strong> L/);
  assert.match(card.shadowRoot.innerHTML, />50 <small>L/);
  ha.states['sensor.taggle_123456_meter_reading'].state = 'unavailable';
  card.hass = ha;
  assert.doesNotMatch(card.shadowRoot.innerHTML, /class="register"/);
});

test('calibration disagreement is visible and hostile text is escaped', () => {
  const card = new Card();
  card.setConfig({entities:{calibration_status:'sensor.check'}});
  const ha = hass();
  ha.states['sensor.check'] = state('Readings disagree — check <img src=x>', {chosen_k:5,
    next_transmission:'bad time'});
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /class="calibration warning"/);
  assert.match(card.shadowRoot.innerHTML, /&lt;img src=x&gt;/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<img|Invalid Date|Next transmission/);
});

test('renamed explicit pulse mapping discovers new calibration entities on the same device', () => {
  const card = new Card();
  card.setConfig({entities:{last_hour:'sensor.kitchen_pulses'}});
  const ha = hass();
  ha.entities = {
    pulse: {entity_id:'sensor.kitchen_pulses', device_id:'meter', unique_id:'taggle_123456_last_hour'},
    absolute: {entity_id:'sensor.kitchen_register', device_id:'meter', unique_id:'taggle_123456_meter_reading'},
    calibration: {entity_id:'sensor.kitchen_check', device_id:'meter', unique_id:'taggle_123456_calibration_status'},
    other: {entity_id:'sensor.other_register', device_id:'other', unique_id:'taggle_234567_meter_reading'},
  };
  ha.states['sensor.kitchen_pulses'] = state(10);
  ha.states['sensor.kitchen_register'] = state(1234567);
  ha.states['sensor.kitchen_check'] = state('Calibrated: 5 L per pulse', {chosen_k:5});
  card.hass = ha;
  assert.equal(card.resolve(card._config.meters[0]).meter_reading, 'sensor.kitchen_register');
  assert.match(card.shadowRoot.innerHTML, /1,234,567/);
  assert.match(card.shadowRoot.innerHTML, /Calibrated: 5 L per pulse/);
});

test('possible leak badge renders only ON states with an escaped reason and clears on recovery', () => {
  const id = 'binary_sensor.taggle_123456_possible_leak';
  const card = new Card();
  card.setConfig({entities:[...Object.keys(hass().states), id]});
  const ha = hass();
  for (const value of ['off', 'unknown', 'unavailable', 'ON']) {
    ha.states[id] = state(value, {reason:'night flow'});
    card.hass = ha;
    assert.doesNotMatch(card.shadowRoot.innerHTML, /Possible leak/);
  }
  ha.states[id] = state('on', {reason:'night flow <img src=x>'});
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /class="leak-badge">Possible leak/);
  assert.match(card.shadowRoot.innerHTML, /night flow &lt;img src=x&gt;/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<img/);
  ha.states[id].state = 'off';
  card.hass = ha;
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Possible leak/);
});

test('renamed possible leak resolves by device registry and explicit mapping', () => {
  const card = new Card();
  const ha = hass();
  ha.entities = {'binary_sensor.renamed': {entity_id:'binary_sensor.renamed',
    device_id:'meter', unique_id:'house/taggle_123456_possible_leak'}};
  ha.states['binary_sensor.renamed'] = state('on', {reason:'continuous flow for 24 h'});
  for (const config of [{device:'meter'}, {entities:{possible_leak:'binary_sensor.renamed'}}]) {
    card.setConfig(config);
    card.hass = ha;
    assert.equal(card.resolve(card._config.meters[0]).possible_leak, 'binary_sensor.renamed');
    assert.match(card.shadowRoot.innerHTML, /Possible leak<\/span>continuous flow for 24 h/);
  }
});

test('possible leak badge is scoped to the selected meter and tolerates missing reasons', () => {
  const card = new Card();
  const ha = hass();
  ha.states['binary_sensor.taggle_123456_possible_leak'] = state('on');
  ha.states['binary_sensor.taggle_234567_possible_leak'] = state('off');
  card.setConfig({meters:[
    {name:'House', entities:['binary_sensor.taggle_123456_possible_leak']},
    {name:'Flat', entities:['binary_sensor.taggle_234567_possible_leak']},
  ]});
  card.hass = ha;
  assert.equal((card.shadowRoot.innerHTML.match(/Possible leak/g) || []).length, 1);
  const flat = card.shadowRoot.innerHTML.split('<h3>Flat</h3>')[1];
  assert.doesNotMatch(flat, /Possible leak/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /undefined|null/);
});

const calibrationCard = (attributes = {}, message = 'Needs 2 readings') => {
  const card = new Card(), ha = hass(), calls = [];
  ha.states['sensor.taggle_123456_calibration_status'] = state(message, {chosen_k:null, ...attributes});
  for (const [key, domain, value] of [['dial_unit', 'select', 'm³'], ['dial_reading', 'text', 'unknown']]) ha.states[`${domain}.taggle_123456_${key}`] = state(value);
  ha.callService = async (...args) => { calls.push(args); };
  card.setConfig({entities:{last_hour:'sensor.taggle_123456_last_hour'}});
  card.hass = ha;
  return {card, ha, calls, meter:card._config.meters[0]};
};

test('uncalibrated panel teaches the register, other meters and the unit before entry', () => {
  for (const chosen_k of [null, undefined, '5', NaN, Infinity]) {
    const {card} = calibrationCard({chosen_k});
    const html = card.shadowRoot.innerHTML;
    assert.match(html, /<div class="read-panel"><h4>Read your dial/);
    assert.match(html, /Your meter's dial is the only source of real litres\. Calibrate in about one hour:/);
    assert.match(html, /01597 black wheels and 765 red wheels/);
    assert.match(html, /black = whole m³ \(kL\)/);
    assert.match(html, /red = litres/);
    assert.match(html, /1597\.765<\/strong>, unit <strong>m³/);
    assert.match(html, /<summary[^>]*>Other meters<\/summary>/);
    assert.match(html, /1597 \+ 0\.7 \+ 0\.06 \+ 0\.005 = 1597\.765 m³/);
    assert.match(html, /Digital\/LCD display/);
    assert.match(html, /star\/triangle spinner/);
    assert.match(html, /Always check the unit printed on the face/);
    assert.match(html, /type="text" inputmode="decimal"/);
    assert.match(html, /type="time" step="60"/);
    assert.match(html, /No dial readings entered yet/);
    assert.ok(html.indexOf('</form>') < html.indexOf('Needs 2 readings'));
    assert.doesNotMatch(html, /Add a check reading/);
  }
});

test('calibrated panel collapses to a check reading disclosure; warnings expand it', () => {
  const {card, ha} = calibrationCard({chosen_k:5}, 'Calibrated: 5 L per pulse');
  assert.match(card.shadowRoot.innerHTML, /<details class="read-panel" data-disclosure="check-0"><summary[^>]*>Add a check reading<\/summary>/);
  for (const message of ['Readings disagree — check the last one', 'Reading is about 1000× off',
    'Counter sequence changed', 'Counter gap may hide wraps', 'Enter a finite, nonnegative dial reading',
    'Use HH:MM for today, or ISO-8601 with a UTC offset']) {
    ha.states['sensor.taggle_123456_calibration_status'].state = message;
    card.hass = ha;
    assert.match(card.shadowRoot.innerHTML, /<div class="read-panel"><h4>Read your dial/);
    assert.match(card.shadowRoot.innerHTML, /class="calibration warning"/);
    assert.doesNotMatch(card.shadowRoot.innerHTML, /Add a check reading/);
  }
});

test('reading history shows the last ten values, local times, used, pending and exclusion reasons safely', () => {
  const readings = Array.from({length:12}, (_, i) => ({time:`2026-11-02T${String(i).padStart(2,'0')}:00:00Z`,
    value:1597 + i / 1000, litres:1597000 + i, unit:'m³', used:i === 9, base_interval:i === 10 ? [10,20] : null,
    reason:i === 10 ? '<img src=x> wrong unit' : i === 11 ? 'Waiting for next transmission' : undefined}));
  const {card, ha} = calibrationCard({readings});
  ha.config.time_zone = 'Australia/Brisbane';
  card.hass = ha;
  const list = card.shadowRoot.innerHTML.split('<ul class="reading-list"')[1];
  assert.equal((list.match(/<time /g) || []).length, 10);
  assert.doesNotMatch(list, /2026-11-02T0[01]:00:00Z/);
  assert.match(list, /1597\.009 m³<\/strong>\s*<br>Used/);
  assert.match(list, /Excluded · Less precise — &lt;img src=x&gt; wrong unit/);
  assert.match(list, /Pending · Less precise — Waiting for next transmission/);
  assert.match(list, /09:00 PM/);
  assert.doesNotMatch(list, /<img/);
});

test('control resolution handles lists, renamed device registries, explicit overrides and old mappings', async () => {
  const {card, ha} = calibrationCard();
  const domains = {dial_unit:'select', dial_reading:'text'};
  card.setConfig({entities:Object.keys(ha.states)});
  for (const [key, domain] of Object.entries(domains)) {
    assert.equal(card.resolve(card._config.meters[0])[key], `${domain}.taggle_123456_${key}`);
  }
  const entries = Object.entries(domains).map(([key,domain]) => ({entity_id:`${domain}.renamed_${key}`,
    device_id:'meter', unique_id:`house/taggle_123456_${key}`}));
  ha.callWS = async () => entries;
  for (const entry of entries) ha.states[entry.entity_id] = state(entry.entity_id.startsWith('select') ? 'L' : 'unknown');
  card.setConfig({device:'meter'});
  card.hass = ha;
  await Promise.resolve();
  for (const entry of entries) assert.equal(card.resolve(card._config.meters[0])[entry.unique_id.split('123456_')[1]], entry.entity_id);
  ha.entities = Object.fromEntries([...entries, {entity_id:'sensor.kitchen', device_id:'meter',
    unique_id:'house/taggle_123456_last_hour'}].map(e => [e.entity_id,e]));
  card.setConfig({entities:{last_hour:'sensor.kitchen', dial_unit:'select.override',
    dial_reading:'text.override'}});
  const resolved = card.resolve(card._config.meters[0]);
  for (const [key,domain] of Object.entries(domains)) assert.equal(resolved[key], `${domain}.override`);
  card.setConfig({entities:{last_hour:'sensor.kitchen'}});
  for (const entry of entries) assert.equal(card.resolve(card._config.meters[0])[entry.unique_id.split('123456_')[1]], entry.entity_id);
});

test('save awaits unit then sends reading and photo time together, clears inputs, and never resubmits a previous entity value', async () => {
  for (const time of ['18:03', '']) {
    const {card, ha, meter, calls} = calibrationCard();
    assert.equal(card.draft(meter, card.resolve(meter)).reading, '');
    Object.assign(card._drafts.get(meter), {reading:'1597.765', time, unit:'kL'});
    let release;
    ha.callService = (...args) => { calls.push(args); return new Promise(resolve => { release = resolve; }); };
    const saving = card.saveReading(meter);
    assert.equal(calls.length, 1);
    assert.match(card.shadowRoot.innerHTML, /aria-busy="true"/);
    assert.match(card.shadowRoot.innerHTML, />Sending…<\/button>/);
    await card.saveReading(meter); // A second Enter/click cannot duplicate an in-flight entry.
    assert.equal(calls.length, 1);
    release(); await new Promise(setImmediate);
    assert.equal(calls.length, 2);
    release(); await saving;
    assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
      ['select', 'select_option', {entity_id:'select.taggle_123456_dial_unit', option:'kL'}],
      ['text', 'set_value', {entity_id:'text.taggle_123456_dial_reading', value:'1597.765' + (time ? ' ' + time : '')}],
    ]);
    assert.equal(card._drafts.get(meter).reading, '');
    assert.equal(card._drafts.get(meter).time, '');
    assert.match(card.shadowRoot.innerHTML, /Reading sent/);
  }
});

test('invalid readings give inline guidance without making service calls', async () => {
  for (const [reading, message] of [['', /Enter the complete reading/], ['  ', /Enter the complete reading/],
    ['-1', /cannot be negative/], ['NaN', /Type a number/], ['Infinity', /Type a number/],
    ['1,597.765', /without grouping separators/], ['abc', /Type a number/], ['0x10', /Type a number/],
    ['1597.765 L', /without grouping separators/], ['1000000000001', /too large/]]) {
    const {card, meter, calls} = calibrationCard();
    Object.assign(card._drafts.get(meter), {reading});
    await card.saveReading(meter);
    assert.equal(calls.length, 0);
    assert.match(card.shadowRoot.innerHTML, message);
    assert.match(card.shadowRoot.innerHTML, /aria-invalid="true"/);
  }
  for (const ratio of [1000, .001]) {
    const {card, meter, calls} = calibrationCard({readings:[{litres:1597765, used:true}]});
    Object.assign(card._drafts.get(meter), {reading:String(1597.765 * ratio)});
    await card.saveReading(meter);
    assert.equal(calls.length, 0);
    assert.match(card.shadowRoot.innerHTML, /1000× different from the last reading/);
  }
});

test('unit conversions compare litres, valid zero and decimals save, and malformed times stop submission', async () => {
  for (const [reading, unit] of [['1597765', 'L'], ['1597.765', 'm³'], ['1597.765', 'kL'], ['0', 'L'], ['.5', 'L']]) {
    const {card, meter, calls} = calibrationCard({readings:[{litres:1597765, used:true}]});
    Object.assign(card._drafts.get(meter), {reading, unit});
    await card.saveReading(meter);
    assert.equal(calls.length, 2);
  }
  const {card, meter, calls} = calibrationCard();
  Object.assign(card._drafts.get(meter), {reading:'1597.765', time:'25:10'});
  await card.saveReading(meter);
  assert.equal(calls.length, 0);
  assert.match(card.shadowRoot.innerHTML, /Use a photo time in HH:MM/);
  Object.assign(card._drafts.get(meter), {time:'', reading:'', badInput:true});
  await card.saveReading(meter);
  assert.match(card.shadowRoot.innerHTML, /Type a number with a decimal point/);
});

test('1000× validation can use the absolute reading and ignores an excluded typo', async () => {
  const {card, ha, meter, calls} = calibrationCard({readings:[{litres:1597765000, used:false,
    base_interval:[10,20], reason:'Wrong unit'}]});
  ha.states['sensor.taggle_123456_meter_reading'] = state(1597765);
  Object.assign(card._drafts.get(meter), {reading:'1597765'});
  await card.saveReading(meter);
  assert.equal(calls.length, 0);
  assert.match(card.shadowRoot.innerHTML, /1000× different from the last reading/);
  Object.assign(card._drafts.get(meter), {reading:'1597.765'});
  await card.saveReading(meter);
  assert.equal(calls.length, 2);
});

test('missing or unavailable controls prevent saving and a failed service stops the sequence', async () => {
  for (const failure of ['missing', 'unavailable', 'unit', 'reading']) {
    const {card, ha, meter, calls} = calibrationCard();
    Object.assign(card._drafts.get(meter), {reading:'1597.765', time:'18:03'});
    if (failure === 'missing') delete ha.states['text.taggle_123456_dial_reading'];
    else if (failure === 'unavailable') ha.states['select.taggle_123456_dial_unit'] = state('unavailable');
    else ha.callService = async (...args) => {
      calls.push(args);
      if (args[0] === {unit:'select', reading:'text'}[failure]) throw new Error('offline');
    };
    card.hass = ha;
    await card.saveReading(meter);
    assert.equal(calls.length, {missing:0, unavailable:0, unit:1, reading:2}[failure]);
    assert.match(card.shadowRoot.innerHTML, /unavailable|Could not send the reading/);
    assert.equal(card._drafts.get(meter).reading, '1597.765');
    assert.equal(card._drafts.get(meter).busy, false);
  }
});

test('drafts survive HA updates and saving uses only the chosen meter and its explicit control IDs', async () => {
  const {card, ha, calls} = calibrationCard();
  ha.states['select.flat'] = state('L');
  ha.states['text.flat'] = state('');
  card.setConfig({meters:[{name:'House', entities:{last_hour:'sensor.taggle_123456_last_hour'}},
    {name:'Flat', entities:{dial_unit:'select.flat', dial_reading:'text.flat'}}]});
  const [house, flat] = card._config.meters;
  Object.assign(card._drafts.get(house), {reading:'1597.765', time:'18:03'});
  Object.assign(card._drafts.get(flat), {reading:'12345'});
  ha.states['sensor.taggle_123456_last_hour'].state = '11';
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /value="1597\.765"/);
  assert.match(card.shadowRoot.innerHTML, /value="18:03"/);
  await card.saveReading(flat);
  assert.deepEqual(calls.map(args => args[2].entity_id), ['select.flat', 'text.flat']);
  assert.equal(calls[0][2].option, 'L');
  assert.equal(card._drafts.get(house).reading, '1597.765');
});

test('read-now state shows an accessible countdown, three-step guidance and expiry', () => {
  const now = Date.now();
  const {card, ha} = calibrationCard({read_dial_now:{state:'ON',
    since:new Date(now - 2 * 60000).toISOString(), until:new Date(now + 8 * 60000).toISOString()}});
  assert.match(card.shadowRoot.innerHTML, /class="read-now" role="status"><strong>Read now<\/strong> · 8 min left/);
  assert.match(card.shadowRoot.innerHTML, /Step 1 of 3/);
  assert.match(card.shadowRoot.innerHTML, /20–50 L; reuse it/);
  assert.match(card.shadowRoot.innerHTML, /NEXT transmission/);
  assert.match(card.shadowRoot.innerHTML, /Outside the window is less precise/);
  ha.states['sensor.taggle_123456_calibration_status'].attributes.readings = [
    {time:new Date(now - 65 * 60000).toISOString(), value:1597.765, unit:'m³', used:true, exact:true}];
  card.hass = ha;
  assert.match(card.shadowRoot.innerHTML, /Step 3 of 3/);
  assert.match(card.shadowRoot.innerHTML, /Used · Exact/);
  ha.states['sensor.taggle_123456_calibration_status'].attributes.read_dial_now.until = new Date(now - 1000).toISOString();
  card.hass = ha;
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<strong>Read now/);
  assert.match(card.shadowRoot.innerHTML, /Step 2 of 3/);
});

test('comma decimals and typed trailing zeros reach the text command intact', async () => {
  for (const reading of ['1597,765', '1597.760']) {
    const {card, meter, calls} = calibrationCard();
    Object.assign(card._drafts.get(meter), {reading, time:'18:00'});
    await card.saveReading(meter);
    assert.equal(calls.length, 2);
    assert.equal(calls[1][0], 'text');
    assert.equal(calls[1][2].value, reading + ' 18:00');
  }
});

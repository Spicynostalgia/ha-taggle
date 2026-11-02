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
  assert.match(card.shadowRoot.innerHTML, /within a few minutes after it/);
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

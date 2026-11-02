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
  assert.match(card.shadowRoot.innerHTML, /Usage unavailable/);
  assert.match(card.shadowRoot.innerHTML, /—/);
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

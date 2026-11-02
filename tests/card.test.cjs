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

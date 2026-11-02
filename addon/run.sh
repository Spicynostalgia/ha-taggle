#!/usr/bin/with-contenv bashio
set -euo pipefail
# The service credentials stay in a private runtime file, never in argv or logs.
export TAGGLE_MQTT_HOST="$(bashio::services mqtt host)"
export TAGGLE_MQTT_PORT="$(bashio::services mqtt port)"
export TAGGLE_MQTT_USERNAME="$(bashio::services mqtt username)"
export TAGGLE_MQTT_PASSWORD="$(bashio::services mqtt password)"
umask 077
python3 - <<'PY'
import json
import os
from pathlib import Path
options = json.loads(Path('/data/options.json').read_text())
options.pop('scan_minutes', None)
options['data_dir'] = '/data/receiver'
options['mqtt'] = {
    'host': os.environ['TAGGLE_MQTT_HOST'],
    'port': int(os.environ['TAGGLE_MQTT_PORT']),
    'username': os.environ['TAGGLE_MQTT_USERNAME'],
    'password': os.environ['TAGGLE_MQTT_PASSWORD'],
}
Path('/run/taggle-options.json').write_text(json.dumps(options))
PY
unset TAGGLE_MQTT_HOST TAGGLE_MQTT_PORT TAGGLE_MQTT_USERNAME TAGGLE_MQTT_PASSWORD
scan_minutes="$(bashio::config scan_minutes)"
if [ "$scan_minutes" -gt 0 ]; then
    exec taggle-rx --config /run/taggle-options.json --scan "$scan_minutes"
fi
exec taggle-rx --config /run/taggle-options.json

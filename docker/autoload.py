"""Attach the pinned Muse model once the local dashboard is listening."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

url = 'http://127.0.0.1:8767'
for attempt in range(120):
    try:
        with urllib.request.urlopen(url + '/api/live/status', timeout=2):
            break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(1)
else:
    raise SystemExit('Dashboard did not start; Muse was not loaded.')
profile = json.loads(Path('configs/muse-smoke.json').read_text())
request = urllib.request.Request(url + '/api/live/load',
    data=json.dumps(profile['load']).encode(),
    headers={'Content-Type': 'application/json', 'Origin': url})
with urllib.request.urlopen(request, timeout=10) as response:
    print('Automatic Muse load requested:', response.read().decode(), flush=True)

#!/usr/bin/env python3
"""Render fictional README screenshots with Chromium (Python stdlib only).

From the repository root, run:
    CHROME=/absolute/path/to/chromium python3 scripts/screenshots.py

Starts `python3 -m http.server` on a free loopback port at the repository root.
Measures each rendered card with --dump-dom, then saves a tightly sized PNG at 2x.
Use the same Chromium version and installed fonts for pixel-identical reruns.
Manual preview: python3 -m http.server 8000 --bind 127.0.0.1
Then open /docs/screenshots/harness.html?theme=light&width=520&scenario=raw.
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SHOTS = (
    ('card-light.png', 'light', 520, 'calibrated'),
    ('card-dark.png', 'dark', 520, 'calibrated'),
    ('card-mobile.png', 'light', 380, 'calibrated'),
    ('card-multi.png', 'light', 520, 'multi'),
    ('card-calibration.png', 'light', 520, 'uncalibrated'),
    ('card-calibration-dark.png', 'dark', 520, 'uncalibrated'),
    ('card-calibration-mobile.png', 'light', 328, 'uncalibrated'),  # 360px viewport including gutters.
)


def main():
    chrome = shutil.which(os.environ.get('CHROME', 'chromium'))
    if not chrome:
        raise SystemExit('Chromium not found. Set CHROME=/absolute/path/to/chromium and rerun.')
    output = ROOT / 'docs/images'
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='taggle-screenshots-') as temporary:
        with open(Path(temporary) / 'server.log', 'w+') as log:
            server = subprocess.Popen(
                [sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1',
                 '--directory', str(ROOT)], cwd=ROOT, stdout=log, stderr=log)
            try:
                base = f'http://127.0.0.1:{port}'
                deadline = time.monotonic() + 10
                while True:
                    if server.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(f'HTTP server failed: {log.read()}')
                    try:
                        with urlopen(f'{base}/dist/taggle-card.js', timeout=1):
                            break
                    except (URLError, TimeoutError):
                        if time.monotonic() > deadline:
                            raise RuntimeError('HTTP server did not become ready') from None
                        time.sleep(0.1)
                common = [chrome, '--headless', '--disable-gpu', '--hide-scrollbars',
                          '--force-device-scale-factor=2', '--virtual-time-budget=2000',
                          '--run-all-compositor-stages-before-draw', '--no-first-run',
                          '--no-default-browser-check', f'--user-data-dir={temporary}/profile']
                if hasattr(os, 'geteuid') and os.geteuid() == 0:
                    common.append('--no-sandbox')  # Only the local, synthetic fixture is loaded.
                for filename, theme, width, scenario in SHOTS:
                    url = (f'{base}/docs/screenshots/harness.html?theme={theme}'
                           f'&width={width}&scenario={scenario}')
                    for _attempt in range(3):  # Headless Chromium occasionally exits before the module runs.
                        measured = subprocess.run(
                            [*common, f'--window-size={width + 32},1800', '--dump-dom', url],
                            check=True, capture_output=True, text=True, timeout=45)
                        if 'data-screenshot-ready="true"' in measured.stdout:
                            break
                    else:
                        raise RuntimeError(f'Fixture did not render for {filename}: {measured.stderr}')
                    height = int(re.search(r'data-screenshot-height="(\d+)"', measured.stdout)[1])
                    target = output / filename
                    # Write to a fresh temporary path, so failed runs cannot reuse old PNGs.
                    pending = Path(temporary) / filename
                    for _attempt in range(3):  # Headless Chromium occasionally exits without writing.
                        subprocess.run(
                            [*common, f'--window-size={width + 32},{height}', f'--screenshot={pending}', url],
                            check=True, capture_output=True, text=True, timeout=45)
                        if pending.is_file():
                            break
                    if not pending.is_file() or not pending.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                        raise RuntimeError(f'Chromium did not write a PNG for {filename}')
                    shutil.copyfile(pending, target)
                    print(f'{target.relative_to(ROOT)} ({width}px card, 2x pixels)')
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'Chromium failed ({error.returncode}):\n{error.stderr}') from error
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error

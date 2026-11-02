"""Command-line acquisition from rtl_sdr, stdin or a cu8 file."""
import argparse
import json
import logging
import queue
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

from .config import Config
from .mqtt import Publisher
from .receiver import Detector, InputPump, Receiver
from .store import Store

LOG = logging.getLogger(__name__)


def parse_time(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise argparse.ArgumentTypeError('timestamp must include a UTC offset')
    return stamp.astimezone(timezone.utc)


def rtl_command(config):
    return ['rtl_sdr', '-d', config.device, '-f', str(config.frequency),
            '-s', str(config.sample_rate), '-g', str(config.gain), '-']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='JSON configuration file')
    parser.add_argument('--input', help='cu8 file, or - for stdin; default launches rtl_sdr')
    parser.add_argument('--start-utc', type=parse_time, help='time of first file sample')
    parser.add_argument('--scan', type=float, metavar='MINUTES', help='print IDs and SNR without MQTT or disk writes')
    args = parser.parse_args(argv)
    if args.input and args.input != '-' and not args.start_utc:
        parser.error('--start-utc is required for file input')
    if args.scan is not None and not 0 < args.scan <= 1440:
        parser.error('--scan must be between 0 and 1440 minutes')
    try:
        config = Config.load(args.config, scan=args.scan is not None)
    except (ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    publisher = None if args.scan is not None else Publisher(config)
    store = Store(config, publisher, scan=(lambda row: print(json.dumps(row), flush=True))
                  if args.scan is not None else None)
    rx = Receiver(store, args.start_utc or datetime.now(timezone.utc),
                  Detector(carrier=921_995_000 - config.frequency))
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    old_handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    deadline = time.monotonic() + args.scan * 60 if args.scan is not None else float('inf')
    producer = None
    source = None
    pump = None
    failed = False
    refresh = time.monotonic()
    try:
        if publisher:
            publisher.start()
            store.refresh(datetime.now(timezone.utc))
        while not stopping and time.monotonic() < deadline:
            if source is None:
                if args.input:
                    source = sys.stdin.buffer if args.input == '-' else open(args.input, 'rb', buffering=0)
                else:
                    producer = subprocess.Popen(rtl_command(config), stdout=subprocess.PIPE)
                    source = producer.stdout
                pump = InputPump(source, follow=False)
                pump.thread.start()
                first = True
            try:
                kind, raw, arrival = pump.items.get(timeout=.25)
            except queue.Empty:
                kind = None
            if time.monotonic() - refresh >= 60:
                store.refresh(datetime.now(timezone.utc))
                refresh = time.monotonic()
            if kind == 'error':
                raise raw
            if kind == 'eof':
                rx.flush()
                if args.input:
                    break
                pump.close()
                source.close()
                producer.wait(timeout=5)
                producer = source = pump = None
                LOG.warning('SDR stopped; reconnecting in 2 seconds')
                retry = time.monotonic() + 2
                while not stopping and time.monotonic() < min(retry, deadline):
                    time.sleep(.1)
                continue
            if kind != 'data':
                continue
            if first:
                if not args.start_utc:
                    rx.discontinuity(arrival)
                first = False
            if len(raw) % 2:
                raise ValueError('truncated IQ input: odd trailing byte')
            rx.feed(raw)
        rx.flush()
        if publisher:
            store.refresh(datetime.now(timezone.utc))
    except (OSError, ValueError) as error:
        LOG.error('%s', error)
        failed = True
    finally:
        if producer and producer.poll() is None:
            producer.terminate()
            try:
                producer.wait(timeout=3)
            except subprocess.TimeoutExpired:
                producer.kill()
                producer.wait()
        if pump:
            pump.close()
        if source and source is not sys.stdin.buffer:
            source.close()
        if publisher:
            publisher.close()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
    return int(failed)

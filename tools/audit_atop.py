"""Audit bake-off stage windows against atop records.

Parses stage start/done markers (and the engine keys within each stage)
from tmp/bench/bakeoff.log, replays the 1 s atop recording for every
window, and flags stages where processes outside the benchmark itself
held at least half a CPU core - those stages must be rerun.

Usage: python tmp/bench/audit_atop.py [atop_copy_path]
"""
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRIVER_LOG = REPO / 'tmp' / 'bench' / 'bakeoff.log'
ATOP_LOG = sys.argv[1] if len(sys.argv) > 1 else '/var/log/atop/atop_bench_1s'

ALLOWED = {'python', 'llama-server', 'poetry', 'atop', 'zcode-cli',
           'zcode-node-rep', 'opencode', 'MainThread', 'dockerd',
           'containerd', 'docker', 'Xorg', 'kded6', 'sonicshell',
           'sonic-win', 'ps', '<docker>'}
CONTAMINATED_SECONDS = 10   # at least this many contaminated samples
CONTAMINATED_SHARE = 0.05   # ...or this share of the window

STAGE_RE = re.compile(r'=== stage (\S+) (start|done) (\S+) ===')
ENGINE_RE = re.compile(r'INFO === engine (\S+) ===')


def parse_stages():
    stages = []
    current = None
    for line in DRIVER_LOG.read_text().splitlines():
        match = STAGE_RE.search(line)
        if match:
            name, kind, iso = match.groups()
            moment = datetime.fromisoformat(iso)
            if kind == 'start':
                current = {'name': name, 'start': moment,
                           'engines': [], 'done': None}
                stages.append(current)
            elif current is not None and current['name'] == name:
                current['done'] = moment
                current = None
            continue
        match = ENGINE_RE.search(line)
        if match and current is not None:
            current['engines'].append(match.group(1))
    return stages


def parse_samples(window_start, window_end):
    """(timestamp, external_cpu_cores) per atop sample inside the window."""
    output = subprocess.run(
        ['atop', '-r', ATOP_LOG, '-b', window_start.strftime('%H:%M:%S'),
         '-e', window_end.strftime('%H:%M:%S')],
        capture_output=True, text=True, check=True).stdout
    samples = []
    header = re.compile(r'ATOP.*?(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})')
    process_re = re.compile(
        r'^\s*(\d+)\s+(\d+\.\d+)s\s+(\d+\.\d+)s\s+\S+\s+\S+\s+\S+\s+'
        r'\S+\s+\S+\s+(\d+)%\s+(\S+)\s*$')
    timestamp = None
    external = 0.0
    for line in output.splitlines():
        if line.startswith('ATOP '):
            if timestamp is not None:
                samples.append((timestamp, external))
            timestamp = datetime.strptime(header.search(line).group(1),
                                          '%Y/%m/%d %H:%M:%S')
            external = 0.0
            continue
        match = process_re.match(line)
        if match and timestamp is not None:
            _pid, _sys, _user, cpu_percent, cmd = match.groups()
            if cmd not in ALLOWED and int(cpu_percent) >= 50:
                external += int(cpu_percent) / 100
    if timestamp is not None:
        samples.append((timestamp, external))
    return samples


def main():
    stages = parse_stages()
    print(f'{"stage":38} {"engine":20} {"window":16} '
          f'{"ext.core-s":>10} {"share":>7} verdict')
    for stage in stages:
        if stage['done'] is None:
            continue
        samples = parse_samples(stage['start'], stage['done'])
        contaminated = sum(1 for _timestamp, external in samples
                           if external >= 0.5)
        worst = max((external for _timestamp, external in samples),
                    default=0.0)
        total_external = sum(external for _timestamp, external in samples)
        share = contaminated / len(samples) if samples else 0
        bad = (samples and (contaminated >= CONTAMINATED_SECONDS
                            or share >= CONTAMINATED_SHARE))
        verdict = 'CONTAMINATED' if bad else 'clean'
        engines = ','.join(stage['engines']) or '-'
        window = stage['start'].strftime('%H:%M') + '-' \
            + stage['done'].strftime('%H:%M')
        print(f'{stage["name"]:38} {engines:20} {window:16} '
              f'{total_external:10.1f} {share:7.1%} {verdict}')
        if bad:
            print(f'    -> {contaminated} contaminated samples '
                  f'of {len(samples)}, peak {worst:.2f} cores')


if __name__ == '__main__':
    main()

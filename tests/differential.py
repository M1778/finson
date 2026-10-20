"""Differential tests for a built Finson test_lib executable (Python stdlib only).
Run: python3 -I tests/differential.py ./test_finson
"""
import json
import math
import os
import random
import struct
import subprocess
import sys
import time

rng = random.Random(0xF1750)


def same(a, b):
    if isinstance(a, float) and isinstance(b, (float, int)):
        return struct.pack('>d', a) == struct.pack('>d', float(b))
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(map(lambda p: same(*p), zip(a, b)))
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def value(depth=0):
    choices = 5 if depth >= 4 else 7
    kind = rng.randrange(choices)
    if kind == 0:
        return None
    if kind == 1:
        return bool(rng.randrange(2))
    if kind == 2:
        return rng.randrange(-(2**53), 2**53)
    if kind == 3:
        while True:
            n = struct.unpack('>d', rng.randbytes(8))[0]
            if math.isfinite(n):
                return n
    if kind == 4:
        return ''.join(rng.choice('abcé中😀\n\t\r\b\f"\\\x01\x1f') for _ in range(rng.randrange(25)))
    if kind == 5:
        return [value(depth + 1) for _ in range(rng.randrange(7))]
    return {f'k{i}é': value(depth + 1) for i in range(rng.randrange(7))}


valid = [json.dumps(value(), ensure_ascii=bool(i % 2), separators=(',', ':')).encode() for i in range(2500)]
valid += [s.encode() for s in ['1000001', '0.12345678901234567', '5e-324', '1e-309',
                                 '1.7976931348623157e308', '-0.0', '0e309', '1e-9999999999999999999999']]
# Broad binary64 round-trip corpus, including negative zero and finite extremes.
for _ in range(5000):
    n = struct.unpack('>d', rng.randbytes(8))[0]
    if math.isfinite(n):
        valid.append(repr(n).encode())
invalid = [b'', b' ', b'01', b'-01', b'1.', b'.1', b'1e', b'1e+', b'+1', b'--1',
           b'[1,]', b'{"a":1,}', b'{}{}', b'null true', b'"\\q"', b'"\\u12"',
           b'"\\ud800"', b'"\\udc00"', b'"\\ud800\\u0041"', b'"\\u0000"',
           b'{"exp":1,"exp":2}', b'{"iss":1,"i\\u0073s":2}', b'{"aud":1,"aud":2}',
           b'1e309', b'-1e309', b'1e2147483647', b'1e4294967296', b'NaN', b'Infinity',
           b'[' * 129 + b'0' + b']' * 129]
for bad in [b'\xff', b'\x80', b'\xc0\xaf', b'\xe0\x80\x80', b'\xed\xa0\x80',
            b'\xf0\x80\x80\x80', b'\xf4\x90\x80\x80', b'\xf5\x80\x80\x80', b'\xe2\x82']:
    invalid.extend([b'"' + bad + b'"', b'{"' + bad + b'":0}'])
# Width and total-node budgets count members even when duplicate replacement is allowed.
invalid += [b'[' + b','.join([b'0'] * 16385) + b']']
valid += [b'[' * 128 + b'0' + b']' * 128]
# Raw node budget counts duplicate replacements; nested compact arrays stay under
# the per-container budget and input-byte budget while exceeding 65,536 values.
invalid += [b'[' + b','.join([b'[' + b','.join([b'0'] * 16383) + b']'] * 4) + b']']
inputs = valid + invalid
started = time.monotonic()
result = subprocess.run([os.path.abspath(sys.argv[1])], input=b'\n'.join(inputs) + b'\n',
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
                        env=dict(os.environ, FINSON_DIFFERENTIAL='1'))
assert result.returncode == 0, result.stderr.decode(errors='replace')
outputs = result.stdout.splitlines()
assert len(outputs) == len(inputs), (len(outputs), len(inputs), result.stderr)
for source, output in zip(valid, outputs):
    assert output != b'!ERROR', source
    expected = json.loads(source)
    actual = json.loads(output, parse_int=lambda text: -0.0 if text == '-0' else int(text))
    assert same(expected, actual), (source, output, expected, actual)
for source, output in zip(invalid, outputs[len(valid):]):
    assert output == b'!ERROR', (source, output)
print(f'finson differential: {len(valid)} valid and {len(invalid)} invalid cases passed in {time.monotonic()-started:.3f}s')

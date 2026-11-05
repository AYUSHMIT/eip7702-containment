"""Check the delivered file manifest; does not authenticate its publisher."""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parent
for line in (root/'SHA256SUMS.txt').read_text().splitlines():
    expected, name = line.split('  ', 1)
    p = root / name
    if p.resolve().parent != root and root not in p.resolve().parents:
        raise ValueError('Unexpected path')
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'FAIL: {name}')
print('PASS: every manifest hash matches')

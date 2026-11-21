"""Собирает plan/index.html из template.html + data.js + сканов-подложек."""
import base64, json, pathlib
here = pathlib.Path(__file__).parent; root = here.parent
t = (here / 'template.html').read_text(encoding='utf-8')
d = (here / 'data.js').read_text(encoding='utf-8')
sc = {i: 'data:image/jpeg;base64,' + base64.b64encode((root / 'scans' / f'f{i}_rect.jpg').read_bytes()).decode() for i in (1, 2, 3)}
(root / 'plan' / 'index.html').write_text(t.replace('__DATA__', d).replace('__SCANS__', json.dumps(sc)), encoding='utf-8')
print('plan/index.html готов')

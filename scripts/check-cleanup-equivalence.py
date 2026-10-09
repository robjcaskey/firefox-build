#!/usr/bin/env python3
"""Compare final compositor content with archived pre-refactor captures."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image
root = Path(__file__).resolve().parents[1]
old = root / 'artifacts/pre-harmony-minimal'
records = {}
for mode in ['gray', 'subpixel']:
    for suffix in ['', '-advanced']:
        name = f'1.5-{mode}-gpu{suffix}'
        before, after = old / name, root / 'artifacts' / name
        a = json.loads((before / 'metrics.json').read_text())
        b = json.loads((after / 'metrics.json').read_text())
        top = math.ceil(1440 - a['height'] * a['dpr'])
        assert top == math.ceil(1440 - b['height'] * b['dpr'])
        x = np.array(Image.open(before / 'screen.png').convert('RGB'))[top:]
        y = np.array(Image.open(after / 'screen.png').convert('RGB'))[top:]
        delta = np.abs(x.astype(int) - y.astype(int))
        result = {'content_top': top,
                  'changed_pixels': int(np.count_nonzero(np.any(delta, axis=2))),
                  'max_channel_difference': int(delta.max()), 'dpr': b['dpr']}
        if suffix:
            result.update(before_canvas=a['pathChecks'], after_canvas=b['pathChecks'],
                          scrollRoundtripEqual=b['scrollRoundtripEqual'])
        assert not delta.any(), (name, result)
        records[name] = result
        print(name, result['changed_pixels'], result['max_channel_difference'])
(root / 'artifacts/harmony-minimal-equivalence.json').write_text(json.dumps(records, indent=2) + '\n')

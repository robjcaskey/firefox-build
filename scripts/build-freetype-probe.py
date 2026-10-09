#!/usr/bin/env python3
"""Compile the exact vendored FreeType sources for direct raster validation."""
import ast
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
src=root/'firefox-157.0.1/modules/freetype2'
units=[]
for node in ast.walk(ast.parse((src/'moz.build').read_text())):
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='SOURCES':
        units.extend(ast.literal_eval(node.value))
out=root/'obj-freetype';out.mkdir(exist_ok=True)
subprocess.run(['cc','-shared','-fPIC','-O2','-DFT2_BUILD_LIBRARY','-I'+str(src/'include'),*[str(src/p) for p in units],'-o',str(out/'libfreetype-qd.so'),'-lz'],check=True)

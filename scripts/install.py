#!/usr/bin/env python3
"""Install the packaged browser alongside system Firefox."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,struct,subprocess,tempfile,time
parser=argparse.ArgumentParser()
parser.add_argument('--keep-previous',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
version=json.loads((root/'source.json').read_text())['version']
archive=root/f'obj-qd/dist/firefox-{version}.en-US.linux-x86_64.tar.xz'
source=root/'obj-qd/dist/bin/libxul.so'
if archive.stat().st_mtime < source.stat().st_mtime:
    raise SystemExit('Package is stale; run mach package after the successful build.')
def allocated_sections(path):
    data=path.read_bytes()
    assert data[:6]==b'\x7fELF\x02\x01', 'expected ELF64 little endian'
    offset=struct.unpack_from('<Q',data,40)[0]
    size,count,names_index=struct.unpack_from('<HHH',data,58)
    headers=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
    names_header=headers[names_index];names=data[names_header[4]:names_header[4]+names_header[5]]
    result={}
    for name,kind,flags,address,start,length,link,info,align,entsize in headers:
        if flags & 2:
            label=names[name:names.index(b'\0',name)].decode()
            contents=b'' if kind==8 else data[start:start+length]
            result[label]=(kind,flags,address,length,hashlib.sha256(contents).hexdigest())
    return result

parent=Path.home()/'.local/opt';parent.mkdir(parents=True,exist_ok=True)
target=parent/'firefox-qd'
with tempfile.TemporaryDirectory(prefix='firefox-qd-install-',dir=parent) as tmp:
    stage=Path(tmp)/'browser';stage.mkdir()
    subprocess.run(['tar','-xf',str(archive),'--strip-components=1','-C',str(stage)],check=True)
    assert allocated_sections(stage/'libxul.so')==allocated_sections(source), 'packaged loadable sections differ from tested build'
    version=subprocess.check_output([str(stage/'firefox'),'--version'],text=True).strip()
    backup=None
    if target.exists():
        backup=parent/('firefox-qd-backup-'+str(time.time_ns()));target.rename(backup)
    try:stage.rename(target)
    except Exception:
        if backup:backup.rename(target)
        raise
    if backup and not args.keep_previous:shutil.rmtree(backup)
launcher=Path.home()/'.local/bin/firefox-qd';launcher.parent.mkdir(parents=True,exist_ok=True)
if launcher.is_symlink():launcher.unlink()
if launcher.exists():raise SystemExit('Existing non-symlink launcher needs review: '+str(launcher))
launcher.symlink_to(root/'scripts/firefox-qd')
apps=Path.home()/'.local/share/applications';apps.mkdir(parents=True,exist_ok=True)
(apps/'firefox-qd.desktop').write_text(f'''[Desktop Entry]
Type=Application
Name=Firefox QD
Comment=Firefox with QD-OLED text rendering and native Wayland scaling
Exec={launcher} %u
Icon={target}/browser/chrome/icons/default/default128.png
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;
StartupNotify=true

''')
if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(apps)],check=True)
record={'allocated_sections_match_build':True,'version':version,'prefix':str(target),'libxul_sha256':hashlib.file_digest((target/'libxul.so').open('rb'),'sha256').hexdigest(),'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()}
if backup and args.keep_previous:record['previous_prefix']=str(backup)
(root/'artifacts/install.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

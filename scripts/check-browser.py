#!/usr/bin/env python3
"""Capture actual Wayland compositor output in an isolated Sway session."""
import argparse,json,os,signal,socket,subprocess,tempfile,time,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

class Marionette:
    def __init__(self,port):
        self.socket=socket.create_connection(('127.0.0.1',port),timeout=20)
        self.serial=0; self.receive()
    def receive(self):
        header=b''
        while not header.endswith(b':'):
            b=self.socket.recv(1)
            if not b:raise EOFError('Marionette disconnected')
            header+=b
        size=int(header[:-1]);data=b''
        while len(data)<size:
            part=self.socket.recv(size-len(data))
            if not part:raise EOFError('Marionette disconnected')
            data+=part
        return json.loads(data)
    def command(self,name,params=None):
        self.serial+=1;data=json.dumps([0,self.serial,name,params or {}]).encode()
        self.socket.sendall(str(len(data)).encode()+b':'+data)
        response=self.receive()
        assert response[0:2]==[1,self.serial],response
        if response[2]:raise RuntimeError(response[2])
        return response[3]
    def script(self,script):
        result=self.command('WebDriver:ExecuteScript',{'script':script,'args':[],'newSandbox':True,'sandbox':'default','line':1,'filename':'qd-test'})
        return result.get('value',result)

def wait(fn,proc,timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if proc.poll() is not None:raise RuntimeError(f'process exited: {proc.returncode}')
        result=fn()
        if result:return result
        time.sleep(.2)
    raise TimeoutError('readiness timeout')

def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()

def nodes(tree):
    result=[tree] if tree.get('app_id') else []
    for node in tree.get('nodes',[])+tree.get('floating_nodes',[]):result+=nodes(node)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scale',type=float,default=1.5);parser.add_argument('--gpu',action='store_true');parser.add_argument('--advanced',action='store_true');parser.add_argument('--installed',action='store_true');parser.add_argument('--stock',action='store_true');parser.add_argument('--native-stock',action='store_true');parser.add_argument('--mode',choices=['gray','subpixel'],default='subpixel');args=parser.parse_args()
    if args.stock and args.native_stock:parser.error('choose one baseline')
    if args.stock:args.mode='stock'
    if args.native_stock:args.mode='native'
    out=ROOT/'artifacts'/(f'{args.scale}-{args.mode}'+('-gpu' if args.gpu else '')+('-advanced' if args.advanced else ''));out.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/('tests/advanced.html' if args.advanced else 'tests/text.html'),out/'text.html')
    if args.advanced:shutil.copy2(Path.home()/'.local/share/fonts/attention-manager/NotoSansCham-wght.ttf',out/'Variable.ttf')
    shutil.copy2(Path.home()/'caskey-fonts/fonts/caskey-mono/CaskeyMono-Regular.ttf',out/'CaskeyMono-Regular.ttf')
    with tempfile.TemporaryDirectory(prefix='firefox-qd-test-') as temp:
        runtime=Path(temp);runtime.chmod(0o700)
        swayconf=runtime/'sway.conf';swayconf.write_text(f'output HEADLESS-1 mode 1920x1440\noutput HEADLESS-1 scale {args.scale}\nseat seat0 fallback true\nxwayland disable\ndefault_border none\nfocus_follows_mouse no\n')
        env=dict(os.environ,XDG_RUNTIME_DIR=str(runtime),WLR_BACKENDS='headless',WLR_RENDERER='pixman',WLR_LIBINPUT_NO_DEVICES='1',LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/50_mesa.json',MOZ_ENABLE_WAYLAND='1',FIREFOX_QD_MODE=args.mode,FONTCONFIG_FILE=str(ROOT/'config'/f'fonts-{args.mode}.conf'))
        if args.stock or args.native_stock:
            env.pop('FIREFOX_QD_MODE',None);env.pop('FONTCONFIG_FILE',None)
        for key in ['WAYLAND_DISPLAY','DISPLAY','SWAYSOCK','DBUS_SESSION_BUS_ADDRESS']:env.pop(key,None)
        if args.gpu:
            for key in ['LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER','__EGL_VENDOR_LIBRARY_FILENAMES']:env.pop(key,None)
            env.update(WLR_RENDERER='gles2',WLR_RENDER_DRM_DEVICE='/dev/dri/renderD128')
        with (out/'sway.log').open('w') as slog,(out/'firefox.log').open('w') as flog:
            sway=subprocess.Popen(['sway','-c',str(swayconf)],env=env,stdout=slog,stderr=slog,start_new_session=True)
            try:
                ipc=wait(lambda:next(iter(runtime.glob('sway-ipc*.sock')),None),sway)
                display=next(p for p in runtime.glob('wayland-*') if not p.name.endswith('.lock'))
                env.update(SWAYSOCK=str(ipc),WAYLAND_DISPLAY=display.name)
                def swaymsg(*cmd):return json.loads(subprocess.check_output(['swaymsg','-s',str(ipc),'-r',*cmd],env=env))
                profile=runtime/'profile';profile.mkdir()
                with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
                prefs={'marionette.port':port,'marionette.enabled':True,'browser.aboutwelcome.enabled':False,'browser.shell.checkDefaultBrowser':False,'browser.startup.homepage_override.mstone':'ignore','browser.startup.page':0,'datareporting.policy.dataSubmissionPolicyBypassNotification':True,'remote.screenshot.use_readback':True,'gfx.webrender.all':True}
                if args.gpu:prefs.pop('gfx.webrender.all')
                (profile/'user.js').write_text(('user_pref("widget.wayland.fractional-scale.enabled", true);\n' if args.native_stock else '' if args.stock else (ROOT/'config'/f'user-{args.mode}.js').read_text())+''.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k,v in prefs.items()))
                binary=Path.home()/'.local/opt/firefox-qd/firefox' if args.installed else ROOT/'obj-qd/dist/bin/firefox'
                if args.stock:binary=Path('/usr/bin/firefox')
                if args.native_stock:binary=ROOT/'obj-native/firefox/firefox'
                browser=subprocess.Popen(['dbus-run-session','--',str(binary),'-no-remote','-profile',str(profile),'-marionette','--remote-allow-system-access','about:blank'],env=env,stdout=flog,stderr=flog,start_new_session=True)
                try:
                    win=wait(lambda:next(iter(nodes(swaymsg('-t','get_tree'))),None),browser)
                    swaymsg(f'[con_id={win["id"]}] fullscreen enable')
                    def connect():
                        try:return Marionette(port)
                        except (ConnectionRefusedError,socket.timeout):return None
                    m=wait(connect,browser)
                    m.command('WebDriver:NewSession',{'capabilities':{'alwaysMatch':{}}})
                    m.command('WebDriver:Navigate',{'url':(out/'text.html').as_uri()})
                    wait(lambda:m.script('return document.documentElement.dataset.ready === "true"'),browser)
                    metrics=m.script('return {dpr:devicePixelRatio,width:innerWidth,height:innerHeight,fonts:document.fonts.check("16px DownloadedCaskey"),canvas:document.querySelector("canvas").getBoundingClientRect().toJSON()}')
                    if not args.stock:assert metrics['dpr']==args.scale,metrics
                    m.command('Marionette:SetContext',{'value':'chrome'})
                    metrics['graphics']=m.script('const g=Cc["@mozilla.org/gfx/info;1"].getService(Ci.nsIGfxInfo); return {features:g.getFeatures(),adapter:g.adapterDescription,protocol:g.windowProtocol,details:g.getInfo()};')
                    if args.gpu:
                        assert metrics['graphics']['features']['compositor']=='webrender',metrics['graphics']
                        assert metrics['graphics']['features']['openglCompositing']['status']=='available',metrics['graphics']
                        assert 'NVIDIA' in metrics['graphics']['adapter'],metrics['graphics']
                    m.command('Marionette:SetContext',{'value':'content'})
                    time.sleep(1)
                    subprocess.run(['grim','-o','HEADLESS-1','-s',str(args.scale),str(out/'screen.png')],env=env,check=True)
                    assert Image.open(out/'screen.png').size==(1920,1440)
                    if args.advanced:
                        checks=m.script('return JSON.parse(document.documentElement.dataset.pathChecks)')
                        assert checks['variableLoaded'] and all(checks[k]['ink']>0 for k in ['opaque','transparent']) and checks['transparent']['chromatic']==0 and (checks['opaque']['chromatic']>0 if args.mode=='subpixel' else checks['opaque']['chromatic']==0),checks
                        metrics['pathChecks']=checks
                        m.script('window.scrollTo(0,1000);return true');time.sleep(.5)
                        m.script('window.scrollTo(0,0);return true');time.sleep(.5)
                        subprocess.run(['grim','-o','HEADLESS-1','-s',str(args.scale),str(out/'after-scroll.png')],env=env,check=True)
                        from PIL import ImageChops
                        assert not ImageChops.difference(Image.open(out/'screen.png'),Image.open(out/'after-scroll.png')).getbbox(),'scroll roundtrip changed pixels'
                        metrics['scrollRoundtripEqual']=True
                    (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
                    print(json.dumps(metrics,indent=2))
                    m.socket.close()
                finally:stop(browser)
            finally:stop(sway)
if __name__=='__main__':main()

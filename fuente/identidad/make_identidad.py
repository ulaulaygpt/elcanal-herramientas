"""Genera los recursos de identidad △ (PNG, ICO) a partir de triangulo.svg, y las imágenes para compartir.
Uso: python3 make_identidad.py <carpeta_salida>
Requiere: Python 3, Pillow y Playwright con Chromium (o CHROME_PATH apuntando a Chrome/Chromium). No usa recursos externos."""
import sys, os, io, pathlib
from playwright.sync_api import sync_playwright
from PIL import Image
AQUI=pathlib.Path(__file__).parent
OUT=pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True,exist_ok=True)
svg=(AQUI/'triangulo.svg').read_text(encoding='utf8')
TRI='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{w}" height="{w}"><path d="M32 11 L53.5 49 H10.5 Z" fill="none" stroke="#C8A84B" stroke-width="6" stroke-linejoin="round"/></svg>'
def og(titulo,sub,linea,fname):
    return f'''<html><body style="margin:0;width:1200px;height:630px;background:#0C0B0A;position:relative;overflow:hidden;font-family:'Inter','DejaVu Sans',sans-serif">
<div style="position:absolute;left:0;top:0;width:1200px;height:8px;background:#C8A84B"></div>
<div style="position:absolute;left:90px;top:150px">{TRI.format(w=210)}</div>
<div style="position:absolute;left:350px;top:140px;width:760px">
<div style="font:700 112px 'GFS Baskerville','Libre Baskerville',Georgia,'DejaVu Serif',serif;color:#EFE6D2;letter-spacing:2px;line-height:1">{titulo}</div>
<div style="margin-top:26px;font:500 38px/1.3 'Inter','DejaVu Sans',sans-serif;color:#D8C28F">{sub}</div>
</div>
<div style="position:absolute;left:90px;bottom:54px;right:90px;display:flex;justify-content:space-between;font:500 26px 'Inter','DejaVu Sans',sans-serif;color:#B9A57A">
<span>△ El Canal · elcanal.es</span><span>{linea}</span></div></body></html>'''
with sync_playwright() as p:
    b=p.chromium.launch(**({'executable_path':os.environ['CHROME_PATH']} if os.environ.get('CHROME_PATH') else {}))
    for n in (16,32,48,64,180,192,512):
        pg=b.new_page(viewport={'width':n,'height':n},device_scale_factor=1)
        pg.set_content('<html><body style="margin:0;background:transparent">'+svg.replace('viewBox="0 0 64 64"','viewBox="0 0 64 64" width="%d" height="%d"'%(n,n),1)+'</body></html>')
        pg.screenshot(path=str(OUT/f'tmp-{n}.png'),omit_background=True,clip={'x':0,'y':0,'width':n,'height':n}); pg.close()
    for key,t,s,l in (('senda','SENDA','Su punto de partida: recursos y enlaces de la administración, en una sola página','Gratuito · Sin registro'),
                      ('cauce','CAUCE','Guía de consulta de los procedimientos de contratación pública (LCSP)','Gratuito · Sin registro')):
        pg=b.new_page(viewport={'width':1200,'height':630}); pg.set_content(og(t,s,l,key)); pg.screenshot(path=str(OUT/f'og-{key}.png')); pg.close()
    b.close()
def ld(n): return Image.open(OUT/f'tmp-{n}.png').convert('RGBA')
ld(32).save(OUT/'favicon-32x32.png'); ld(16).save(OUT/'favicon-16x16.png'); ld(48).save(OUT/'favicon-48x48.png')
# apple-touch-icon: fondo opaco (iOS no admite transparencia)
for n,name in ((180,'apple-touch-icon.png'),(192,'icon-192.png'),(512,'icon-512.png')):
    im=ld(n); bg=Image.new('RGBA',im.size,(12,11,10,255)); bg.alpha_composite(im); bg.convert('RGB').save(OUT/name)
big=ld(64); big.save(OUT/'favicon.ico',sizes=[(16,16),(32,32),(48,48),(64,64)])
for n in (16,32,48,64,180,192,512): (OUT/f'tmp-{n}.png').unlink()
(OUT/'favicon.svg').write_text(svg,encoding='utf8')
(OUT/'triangulo-marca.svg').write_text((AQUI/'triangulo-marca.svg').read_text(encoding='utf8'),encoding='utf8')
print(sorted(os.listdir(OUT)))

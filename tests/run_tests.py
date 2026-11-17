#!/usr/bin/env python3
"""Pruebas de regresión de las ediciones públicas (automáticas, Chromium headless de Playwright).
Genera informes/PRUEBAS_RESULTADOS.json y .md. Las comprobaciones en navegador real
(Chrome/Edge de escritorio con permisos persistentes, HTTPS real, lectores de pantalla) NO se simulan aquí."""
import json, re, sys, os, threading, http.server, socketserver, functools, subprocess, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SHOT = ROOT / "informes" / "capturas"; SHOT.mkdir(parents=True, exist_ok=True)
RES = []

def rec(grupo, nombre, ok, detalle=""):
    RES.append({"grupo": grupo, "prueba": nombre, "ok": bool(ok), "detalle": str(detalle)[:400]})
    print(("PASS " if ok else "FAIL ") + f"[{grupo}] {nombre}" + (f" — {detalle}" if (detalle and not ok) else ""))

# ---------------- servidor local (raíz = dist/web) ----------------
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
handler = functools.partial(Q, directory=str(DIST / "web"))
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 8799), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
WEB = "http://127.0.0.1:8799"

# ---------------- A. análisis estático ----------------
# Lista de patrones prohibidos: no se versiona en el repositorio. Cada mantenedor puede aportar la suya
# (una expresión regular por línea) con la variable de entorno PROHIBIDOS_FILE.
PROHIB = []
if os.environ.get("PROHIBIDOS_FILE"):
    PROHIB = [l.strip() for l in open(os.environ["PROHIBIDOS_FILE"], encoding="utf8") if l.strip() and not l.startswith("#")]
def prohibido(texto):
    return [pat for pat in PROHIB if re.search(pat, texto)]
htmls = [p for p in DIST.rglob("*.html")]
for p in htmls:
    t = p.read_text(encoding="utf8")
    hits = prohibido(t)
    rec("A.privacidad", f"sin términos de la lista prohibida · {p.relative_to(DIST)}", not hits, hits)
for p in htmls:
    t = p.read_text(encoding="utf8")
    ext = re.findall(r'<script[^>]+src="https?://|<link[^>]+href="https?://[^"]*\.css|<img[^>]+src="https?://', t)
    rec("A.privacidad", f"sin recursos externos cargados · {p.relative_to(DIST)}", not ext, ext)
    trk = re.findall(r"google-analytics|googletagmanager|gtag\(|plausible|matomo|hotjar|facebook\.net|doubleclick|fbq\(|analytics\.js", t, re.I)
    rec("A.privacidad", f"sin rastreadores/analítica · {p.relative_to(DIST)}", not trk, trk)

# enlaces relativos
def resolve(base: Path, href: str):
    href = href.split("#")[0].split("?")[0]
    if not href: return base
    tgt = (base.parent / href)
    if tgt.is_dir() or href.endswith("/"): tgt = tgt / "index.html"
    return tgt
for dist_dir in ["senda-individual", "cauce-individual", "senda-cauce-paquete", "web"]:
    broken = []
    for p in (DIST / dist_dir).rglob("*.html"):
        t = p.read_text(encoding="utf8")
        for h in re.findall(r'(?:href|src)="([^"#][^"]*)"', t):
            if re.match(r"(https?:|mailto:|data:|javascript:)", h) or "${" in h: continue
            if h == "recursos.js": continue   # copia de lectura opcional de SENDA: no se distribuye (ver README)
            if h.startswith("/"):
                tgt = (DIST / "web" / h.lstrip("/")) if dist_dir == "web" else None
                if tgt is None: broken.append((p.name, h)); continue
            else:
                tgt = resolve(p, h)
            if not tgt.exists(): broken.append((str(p.relative_to(DIST)), h))
    rec("B.enlaces", f"sin enlaces rotos · {dist_dir}", not broken, broken[:6])
# apps ausentes
for dist_dir, prohibidos in [("senda-individual", ["CAUCE.html", "../cauce"]), ("cauce-individual", ["SENDA.html", "../senda"])]:
    t = " ".join(p.read_text(encoding="utf8") for p in (DIST / dist_dir).glob("*.html"))
    bad = [x for x in prohibidos if f'href="{x}' in t]
    rec("B.enlaces", f"{dist_dir} no enlaza a apps ausentes", not bad, bad)

# integridad SHA-256
for dist_dir in ["senda-individual", "cauce-individual", "senda-cauce-paquete", "web"]:
    r = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=DIST / dist_dir, capture_output=True, text=True)
    rec("C.integridad", f"SHA256SUMS válido · {dist_dir}", r.returncode == 0, r.stdout[-200:] + r.stderr[-200:])

# identidad
from PIL import Image
for f, size in [("favicon-16x16.png", (16, 16)), ("favicon-32x32.png", (32, 32)), ("favicon-48x48.png", (48, 48)), ("apple-touch-icon.png", (180, 180)), ("icon-192.png", (192, 192)), ("icon-512.png", (512, 512))]:
    im = Image.open(DIST / "web" / f)
    rec("D.identidad", f"icono {f} {size}", im.size == size, im.size)
for app in ("senda", "cauce"):
    im = Image.open(DIST / "web" / "contratacion" / app / "assets" / f"og-{app}.png")
    rec("D.identidad", f"imagen social og-{app}.png 1200×630", im.size == (1200, 630), im.size)
ico = Image.open(DIST / "web" / "favicon.ico"); rec("D.identidad", "favicon.ico multi-tamaño", len(ico.info.get("sizes", [])) >= 3, ico.info.get("sizes"))
svg = (DIST / "web" / "favicon.svg").read_text()
rec("D.identidad", "favicon.svg contiene △ dibujado (path) sin depender de fuentes", "<path" in svg and "<text" not in svg)
for p in [DIST / "senda-individual/SENDA.html", DIST / "cauce-individual/CAUCE.html", DIST / "senda-cauce-paquete/SENDA.html", DIST / "web/contratacion/senda/index.html", DIST / "web/contratacion/cauce/index.html"]:
    t = p.read_text(encoding="utf8")
    rec("D.identidad", f"icono incrustado y △ visible en pie · {p.relative_to(DIST)}", 'rel="icon" type="image/svg+xml" href="data:image/svg+xml' in t and 'class="tri"' in t and "ORCID" in t)

# ---------------- E. SEO web ----------------
descs, titles = set(), set()
for p in sorted((DIST / "web").rglob("index.html")):
    t = p.read_text(encoding="utf8")
    rel = p.relative_to(DIST / "web")
    can = re.search(r'<link rel="canonical" href="([^"]+)"', t)
    exp = "https://elcanal.es/" + (str(rel.parent) + "/").replace("./", "") if str(rel.parent) != "." else None
    rec("E.seo", f"canonical correcto · {rel}", bool(can) and can.group(1) == exp, (can.group(1) if can else None, exp))
    ti = re.search(r"<title>(.*?)</title>", t); de = re.search(r'name="description" content="([^"]+)"', t)
    rec("E.seo", f"title y description presentes y únicos · {rel}", bool(ti and de) and ti.group(1) not in titles and de.group(1) not in descs and 70 <= len(de.group(1)) <= 330, (len(de.group(1)) if de else 0))
    titles.add(ti.group(1)); descs.add(de.group(1))
    rec("E.seo", f"Open Graph + Twitter + robots · {rel}", all(k in t for k in ['og:title', 'og:description', 'og:image"', 'og:url', 'twitter:card', 'twitter:image', 'name="robots"']))
    lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    okld = bool(lds)
    for l in lds:
        try: json.loads(l)
        except Exception: okld = False
    rec("E.seo", f"JSON-LD válido · {rel}", okld)
    if "procedimientos" in str(rel):
        words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)[^>]*>.*?</\1>", "", t, flags=re.S)).split())
        rec("E.seo", f"página de procedimiento con contenido sustancial (≥400 palabras) · {rel.parent.name}", words >= 400, words)
        rec("E.seo", f"un solo H1 y enlace profundo a CAUCE · {rel.parent.name}", t.count("<h1>") == 1 and "?proc=" in t)
for p in (DIST / "web" / "contratacion").rglob("*.html"):
    t = p.read_text(encoding="utf8")
    if "ld+json" in t and '"SoftwareApplication"' in t:
        rec("E.seo", f"SoftwareApplication sin valoraciones inventadas · {p.relative_to(DIST/'web')}", "aggregateRating" not in t and "review" not in t.lower().replace("revisión", ""))

# ---------------- F. navegador ----------------
OPFS = """
window.__pickName='carpeta_prueba';
// Chromium headless (este entorno) se cuelga al deserializar un handle OPFS desde IndexedDB: no se almacenan handles en las pruebas web.
const _put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,k){if(typeof FileSystemHandle!=='undefined'&&v instanceof FileSystemHandle){return _put.call(this,null,k)}return _put.apply(this,arguments)};
window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle(window.__pickName,{create:true}); };
"""
def disk(page, name='carpeta_prueba'):
    return page.evaluate("""async(name)=>{const root=await navigator.storage.getDirectory();const d=await root.getDirectoryHandle(name,{create:true});const out={files:[],vers:[]};for await(const [n] of d.entries())out.files.push(n);try{const v=await d.getDirectoryHandle('versiones');for await(const [n] of v.entries())out.vers.push(n)}catch{};try{out.json=JSON.parse(await(await(await d.getFileHandle('recursos.json')).getFile()).text())}catch{};try{out.js=await(await(await d.getFileHandle('recursos.js')).getFile()).text()}catch{};return out}""", name)
def seed(page, files, name='carpeta_prueba', wipe=True):
    page.evaluate("""async([name,files,wipe])=>{const root=await navigator.storage.getDirectory();if(wipe){try{await root.removeEntry(name,{recursive:true})}catch{}};const d=await root.getDirectoryHandle(name,{create:true});for(const [n,c] of Object.entries(files)){const f=await d.getFileHandle(n,{create:true});const w=await f.createWritable();await w.write(c);await w.close()}}""", [name, files, wipe])


FAKE = """
(()=>{
class FF{constructor(n,d){this.kind='file';this.name=n;this.d=d}
 async getFile(){const t=this.d.t;return {text:async()=>t,size:t.length,name:this.name}}
 async createWritable(){const self=this;let buf='';return {write:async x=>{buf+=x},close:async()=>{self.d.t=buf;window.__save&&window.__save()}}}}
class FD{static FF=FF;constructor(n){this.kind='directory';this.name=n;this.f=new Map();this.dd=new Map()}
 async *keys(){for(const k of this.f.keys())yield k;for(const k of this.dd.keys())yield k}
 async *entries(){for(const [k,v] of this.f)yield [k,v];for(const [k,v] of this.dd)yield [k,v]}
 async getFileHandle(n,o){if(!this.f.has(n)){if(o&&o.create)this.f.set(n,new FF(n,{t:''}));else throw Object.assign(new Error('nf'),{name:'NotFoundError'})}return this.f.get(n)}
 async getDirectoryHandle(n,o){if(!this.dd.has(n)){if(o&&o.create)this.dd.set(n,new FD(n));else throw Object.assign(new Error('nf'),{name:'NotFoundError'})}return this.dd.get(n)}
 async queryPermission(){return 'granted'} async requestPermission(){return 'granted'}}
window.__fake=new FD('carpeta_prueba');
const dump=(d)=>({f:[...d.f].map(([k,v])=>[k,v.d.t]),d:[...d.dd].map(([k,v])=>[k,dump(v)])});
const load=(d,o)=>{for(const [k,t] of o.f)d.f.set(k,new FF(k,{t}));for(const [k,x] of o.d){const n=new FD(k);load(n,x);d.dd.set(k,n)}};
try{if(window.name&&window.name.startsWith('__FAKE:'))load(window.__fake,JSON.parse(window.name.slice(7)))}catch(e){}
window.__save=()=>{window.name='__FAKE:'+JSON.stringify(dump(window.__fake))};
indexedDB.open=()=>{throw new Error('stub')};
window.showDirectoryPicker=async()=>window.__fake;
})();
"""
def fdisk(page):
    return page.evaluate("""async()=>{const d=window.__fake;const out={files:[...d.f.keys()],vers:[]};const v=d.dd.get('versiones');if(v)out.vers=[...v.f.keys()];const j=d.f.get('recursos.json');if(j&&j.d.t)out.json=JSON.parse(j.d.t);const m=d.f.get('recursos.js');if(m)out.js=m.d.t;return out}""")
def fseed(page, files):
    page.evaluate("""(files)=>{const d=window.__fake;d.f.clear();d.dd.clear();for(const [n,c] of Object.entries(files)){d.f.set(n,new d.constructor.FF(n,{t:c}))}}""", files)

def open_conn(pg):
    pg.wait_for_timeout(250)
    if not pg.locator("#connDlg[open]").count():
        pg.click("#connect2"); pg.wait_for_timeout(250)

def new_page(ctx, errs, fake=False):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("PAGEERR " + e.message))
    pg.on("console", lambda m: errs.append("CONSOLE " + m.text) if m.type == "error" else None)
    pg.add_init_script(FAKE if fake else OPFS)
    return pg

def real_errs(errs):  # el 404/ERR_FILE_NOT_FOUND de recursos.js ausente es esperado y cosmético en la edición local
    return [e for e in errs if "recursos.js" not in e and "ERR_FILE_NOT_FOUND" not in e and "Failed to load resource" not in e]

with sync_playwright() as pw:
    br = pw.chromium.launch(**({"executable_path": os.environ["CHROME_PATH"]} if os.environ.get("CHROME_PATH") else {}))
    ctx = br.new_context(viewport={"width": 1366, "height": 860}, locale="es-ES")

    # ---- SENDA individual (file://) ----
    errs = []; pg = new_page(ctx, errs, fake=True)
    pg.goto((DIST / "senda-individual/SENDA.html").as_uri())
    pg.wait_for_timeout(300)
    n = pg.locator(".res").count()
    rec("F.SENDA-local", "carga con 13 enlaces de ejemplo públicos", n == 13, n)
    txt = pg.inner_text("body")
    rec("F.SENDA-local", "sin rutas preconfiguradas ni referencias internas en pantalla", not prohibido(txt) and not re.search(r"O:\\", txt))
    rec("F.SENDA-local", "lema de gratuidad visible", "Uso gratuito. Sin registro. Sin suscripción." in txt)
    rec("F.SENDA-local", "sin selector de familia (no hay otras apps)", pg.locator("nav.fam").count() == 0)
    pg.screenshot(path=str(SHOT / "senda_local_inicio.png"), full_page=True)
    pg.fill("#search", "boe"); pg.wait_for_timeout(150)
    rec("F.SENDA-local", "búsqueda «boe» filtra", 0 < pg.locator(".res").count() < 13, pg.locator(".res").count())
    pg.fill("#search", "")
    pg.click("#helpBtn"); pg.wait_for_timeout(150)
    rec("F.SENDA-local", "diálogo de ayuda abre con ORCID, El Canal y △", pg.locator("#helpDlg[open]").count() == 1 and "0009-0000-8891-7021" in pg.inner_text("#helpDlg") and pg.locator("#helpDlg svg.tri").count() >= 1)
    pg.screenshot(path=str(SHOT / "senda_ayuda.png"))
    pg.click("#helpClose")
    # enlaces del autor
    hrefs = pg.eval_on_selector_all("#helpDlg a", "els=>els.map(e=>e.href)")
    rec("F.SENDA-local", "ORCID y elcanal.es enlazados", any("orcid.org/0009-0000-8891-7021" in h for h in hrefs) and any("elcanal.es" in h for h in hrefs), hrefs)
    # edición (carpeta sin SENDA.html -> se rechaza en modo local)
    fseed(pg, {})
    pg.click("#edit"); open_conn(pg)
    rec("F.SENDA-local", "diálogo de conexión local muestra ruta de carpeta", pg.locator("#connBox").is_visible())
    pg.click("#connGo"); pg.wait_for_timeout(500)
    st = pg.inner_text("#status") + pg.inner_text("#saveText")
    rec("F.SENDA-local", "modo local exige carpeta que contenga SENDA.html (comportamiento original conservado)", "no es la carpeta de SENDA" in (st + pg.inner_text("body")).lower() or "esa no es la carpeta" in (st + pg.inner_text("body")).lower(), st[:160])
    fseed(pg, {"SENDA.html": "x"})
    open_conn(pg); pg.click("#connGo")
    pg.wait_for_timeout(600)
    rec("F.SENDA-local", "conecta con carpeta válida", pg.inner_text("#connectLabel") == "Carpeta conectada", pg.inner_text("#connectLabel"))
    # editar: borrar un ejemplo, añadir uno propio, guardar
    nombre0 = pg.locator(".rname").first.inner_text()
    pg.locator("[data-act=delete]").first.click(); pg.wait_for_timeout(120); pg.click("#askOk"); pg.wait_for_timeout(200)
    pg.click("#add"); pg.fill("#itemName", "Mi enlace propio"); pg.fill("#itemUrl", "https://example.org/mio"); pg.click("#itemForm button[type=submit]"); pg.wait_for_timeout(600)
    d = fdisk(pg)
    rec("F.SENDA-local", "guardado crea recursos.json (revisión ≥2) + recursos.js espejo", d.get("json", {}).get("revision", 0) >= 2 and "recursos.js" in d["files"] and "SENDA_RECURSOS" in d.get("js", ""), d["files"])
    rec("F.SENDA-local", "el enlace propio está en disco y el ejemplo borrado no", any(r["name"] == "Mi enlace propio" for r in d["json"]["resources"]) and all(r["name"] != nombre0 for r in d["json"]["resources"]) and len(d["json"]["resources"]) == 13)
    pg.screenshot(path=str(SHOT / "senda_local_edicion.png"), full_page=True)
    # recargar y reconectar: no se vuelve a ofrecer el ejemplo borrado
    pg.reload(); pg.wait_for_timeout(300)
    pg.click("#edit"); pg.wait_for_timeout(500)
    if pg.locator("#connDlg[open]").count(): pg.click("#connGo"); pg.wait_for_timeout(600)
    dlg_abierto = pg.locator("dialog[open]").count()
    nombres = pg.locator(".rname").all_inner_texts()
    rec("F.SENDA-local", "tras recargar y reconectar: enlaces propios intactos y ejemplo borrado NO reaparece ni se pregunta", "Mi enlace propio" in nombres and nombre0 not in nombres and dlg_abierto == 0, (len(nombres), dlg_abierto))
    # recuperar enlaces iniciales (explícito) devuelve el ejemplo sin tocar los propios
    pg.click("#backupMenu summary"); pg.click("#restoreStarter"); pg.wait_for_timeout(300); pg.click("#askOk"); pg.wait_for_timeout(600)
    d = fdisk(pg); noms = [r["name"] for r in d["json"]["resources"]]
    rec("F.SENDA-local", "«Recuperar enlaces iniciales» repone el ejemplo sin borrar el propio", nombre0 in noms and "Mi enlace propio" in noms, len(noms))
    rec("F.SENDA-local", "sin errores JS (salvo recursos.js ausente, cosmético)", not real_errs(errs), real_errs(errs)[:3])
    # móvil
    pm = ctx.new_page(); pm.set_viewport_size({"width": 390, "height": 844}); pm.goto((DIST / "senda-individual/SENDA.html").as_uri()); pm.wait_for_timeout(250)
    sw = pm.evaluate("document.documentElement.scrollWidth"); rec("G.móvil", "SENDA sin desbordamiento horizontal a 390 px", sw <= 392, sw)
    pm.screenshot(path=str(SHOT / "senda_movil.png"), full_page=True); pm.close()
    pg.close()

    # ---- SENDA web (http) ----
    errs = []; pg = new_page(ctx, errs)
    pg.goto(WEB + "/contratacion/senda/"); pg.wait_for_timeout(300)
    rec("F.SENDA-web", "carga con 13 enlaces de ejemplo", pg.locator(".res").count() == 13, pg.locator(".res").count())
    nav = pg.eval_on_selector_all("nav.fam a", "els=>els.map(e=>[e.textContent,e.getAttribute('href')])")
    rec("F.SENDA-web", "selector muestra solo apps publicadas (SENDA, CAUCE)", nav == [["SENDA", "../senda/"], ["CAUCE", "../cauce/"]], nav)
    rec("F.SENDA-web", "no se carga recursos.js (sin etiqueta script)", 'src="recursos.js"' not in pg.content())
    seed(pg, {})   # carpeta vacía cualquiera: admitida en edición web
    pg.click("#edit"); open_conn(pg)
    rec("F.SENDA-web", "diálogo de conexión web sin ruta corporativa ni 'copiar ruta'", not pg.locator("#connBox").is_visible() and "recursos.json" in pg.inner_text("#connLead"))
    pg.screenshot(path=str(SHOT / "senda_web_conectar.png"))
    pg.click("#connGo"); pg.wait_for_timeout(600)
    rec("F.SENDA-web", "admite cualquier carpeta propia (no exige SENDA.html)", pg.inner_text("#connectLabel") == "Carpeta conectada", pg.inner_text("#status"))
    pg.click("#add"); pg.fill("#itemName", "Propio web"); pg.fill("#itemUrl", "https://example.org/web"); pg.click("#itemForm button[type=submit]"); pg.wait_for_timeout(600)
    d = disk(pg)
    rec("F.SENDA-web", "guarda recursos.json con el enlace propio", any(r["name"] == "Propio web" for r in d.get("json", {}).get("resources", [])), d["files"])
    # sin permiso persistente: la caché del navegador muestra los enlaces propios
    pg.reload(); pg.wait_for_timeout(700)
    nombres = pg.locator(".rname").all_inner_texts()
    rec("F.SENDA-web", "sin carpeta/permiso recordados, se muestran igualmente los enlaces propios (copia en el navegador)", "Propio web" in nombres, len(nombres))
    rec("F.SENDA-web", "sin errores JS", not real_errs(errs), real_errs(errs)[:3])
    pg.close()

    # ---- CAUCE ----
    for etiqueta, url in [("individual", (DIST / "cauce-individual/CAUCE.html").as_uri()), ("web", WEB + "/contratacion/cauce/")]:
        errs = []; pg = new_page(ctx, errs)
        pg.goto(url); pg.wait_for_timeout(400)
        tabs = pg.locator("#nav button, #nav a").count()
        rec(f"F.CAUCE-{etiqueta}", "6 procedimientos disponibles", tabs == 6, tabs)
        body = pg.inner_text("body")
        rec(f"F.CAUCE-{etiqueta}", "sin referencias internas", not prohibido(body))
        rec(f"F.CAUCE-{etiqueta}", "lema de gratuidad y autoría en el pie", "Uso gratuito. Sin registro. Sin suscripción." in body and "Manuel Barrera Anglada" in body)
        if etiqueta == "individual":
            rec(f"F.CAUCE-{etiqueta}", "sin selector de familia", pg.locator("nav.fam").count() == 0)
        pg.screenshot(path=str(SHOT / f"cauce_{etiqueta}_inicio.png"), full_page=True)
        pg.fill("#search", "mesa"); pg.wait_for_timeout(200)
        rec(f"F.CAUCE-{etiqueta}", "búsqueda «mesa» devuelve resultados", len(pg.inner_text("#pbody")) > 300)
        pg.fill("#search", "")
        pg.click("#btnCmp"); pg.wait_for_timeout(200)
        rec(f"F.CAUCE-{etiqueta}", "comparador funciona", "Comparar" in pg.inner_text("#btnCmp") and len(pg.inner_text("#pbody")) > 300)
        pg.screenshot(path=str(SHOT / f"cauce_{etiqueta}_comparador.png"))
        pg.click("#btnCmp")
        pg.click("#btnAlc"); pg.wait_for_timeout(200)
        al = pg.inner_text("#alcance")
        rec(f"F.CAUCE-{etiqueta}", "«Alcance y fuentes»: ORCID, El Canal, licencia MIT, PTC pendiente, no validado", all(k in al for k in ["0009-0000-8891-7021", "El Canal", "licencia MIT", "pendiente de emitir", "ha sido validada"]) and pg.locator("#alcance svg.tri").count() >= 1)
        rec(f"F.CAUCE-{etiqueta}", "distingue norma contrastada / orientativa / práctica particular / pendiente", all(k in al for k in ["Norma contrastada", "Explicación orientativa", "Práctica particular de cada entidad", "pendiente de validación jurídica"]))
        pg.screenshot(path=str(SHOT / f"cauce_{etiqueta}_alcance.png"))
        pg.keyboard.press("Escape")
        # pestaña de normativa: umbral con fuente BOE
        pg.goto(url + ("&" if "?" in url else "?") + "proc=simplificado&tab=nor"); pg.wait_for_timeout(300)
        rec(f"F.CAUCE-{etiqueta}", "enlace profundo ?proc=simplificado&tab=nor abre la pestaña de normativa", "Umbrales vigentes" in pg.inner_text("#pbody") and "fuente secundaria" not in pg.inner_text("#pbody"))
        rec(f"F.CAUCE-{etiqueta}", "sin errores JS", not real_errs(errs), real_errs(errs)[:3])
        pm = ctx.new_page(); pm.set_viewport_size({"width": 390, "height": 844}); pm.goto(url); pm.wait_for_timeout(300)
        sw = pm.evaluate("document.documentElement.scrollWidth"); rec("G.móvil", f"CAUCE {etiqueta} sin desbordamiento horizontal a 390 px", sw <= 392, sw)
        pm.screenshot(path=str(SHOT / f"cauce_{etiqueta}_movil.png"), full_page=True); pm.close()
        pg.close()

    # ---- páginas estáticas: enlace profundo y legibilidad ----
    errs = []; pg = new_page(ctx, errs)
    for slug, pid in [("contrato-menor", "menor"), ("procedimiento-abierto-ordinario", "abierto"), ("procedimiento-abierto-simplificado", "simplificado"), ("procedimiento-simplificado-abreviado", "abreviado"), ("procedimiento-restringido", "restringido"), ("procedimiento-negociado-sin-publicidad", "negociado")]:
        pg.goto(f"{WEB}/contratacion/cauce/procedimientos/{slug}/"); pg.wait_for_timeout(100)
        rec("F.páginas", f"{slug}: H1 y descripción", pg.locator("h1").count() == 1 and len(pg.inner_text("h1")) > 20)
        pg.click("a.cta"); pg.wait_for_timeout(350)
        act = pg.evaluate("new URLSearchParams(location.search).get('proc')")
        marcado = pg.locator('#nav [aria-selected="true"], #nav [aria-current="true"], #nav .on, #nav .act').count()
        rec("F.páginas", f"{slug}: enlace profundo abre CAUCE en el procedimiento", act == pid and "/contratacion/cauce/" in pg.url, (act, pg.url))
    pg.goto(f"{WEB}/contratacion/cauce/procedimientos/procedimiento-abierto-simplificado/"); pg.screenshot(path=str(SHOT / "pagina_simplificado.png"), full_page=True)
    pg.set_viewport_size({"width": 390, "height": 844}); pg.reload()
    rec("G.móvil", "página estática sin desbordamiento a 390 px", pg.evaluate("document.documentElement.scrollWidth") <= 392, pg.evaluate("document.documentElement.scrollWidth"))
    pg.goto(WEB + "/contratacion/"); pg.screenshot(path=str(SHOT / "hub.png"), full_page=True)
    rec("F.páginas", "portada de Contratación enlaza a SENDA, CAUCE y 6 procedimientos", pg.locator("a[href='senda/']").count() == 1 and pg.locator("a[href='cauce/']").count() == 1 and pg.locator("a[href^='cauce/procedimientos/']").count() == 6)
    pg.close()

    # ---- paquete combinado, sin conexión ----
    off = br.new_context(viewport={"width": 1366, "height": 860}, offline=True)
    errs = []; pg = off.new_page(); pg.on("pageerror", lambda e: errs.append(e.message))
    pg.goto((DIST / "senda-cauce-paquete/SENDA.html").as_uri()); pg.wait_for_timeout(300)
    nav = pg.eval_on_selector_all("nav.fam a", "els=>els.map(e=>[e.textContent,e.getAttribute('href')])")
    rec("F.paquete-offline", "SENDA muestra selector SENDA/CAUCE", nav == [["SENDA", "SENDA.html"], ["CAUCE", "CAUCE.html"]], nav)
    pg.click("nav.fam a:has-text('CAUCE')"); pg.wait_for_timeout(400)
    rec("F.paquete-offline", "SENDA → CAUCE sin conexión", "CAUCE.html" in pg.url and pg.locator("#nav button, #nav a").count() == 6, pg.url)
    pg.click("nav.fam a:has-text('SENDA')"); pg.wait_for_timeout(300)
    rec("F.paquete-offline", "CAUCE → SENDA sin conexión", "SENDA.html" in pg.url and pg.locator(".res").count() == 13, pg.url)
    rec("F.paquete-offline", "sin errores JS", not errs, errs[:3])
    pg.screenshot(path=str(SHOT / "paquete_senda.png"))
    pg.close(); off.close()
    br.close()

httpd.shutdown()
tot = len(RES); ok = sum(r["ok"] for r in RES)
(ROOT / "informes").mkdir(exist_ok=True)
(ROOT / "informes" / "PRUEBAS_RESULTADOS.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf8")
print(f"\n{ok}/{tot} correctas")
sys.exit(0 if ok == tot else 1)

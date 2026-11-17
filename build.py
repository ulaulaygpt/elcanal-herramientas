#!/usr/bin/env python3
"""Generador único de las ediciones públicas de SENDA y CAUCE (El Canal).

Una sola fuente de mantenimiento por aplicación:
  fuente/senda/SENDA_base.html + catalogo_publico.json
  fuente/cauce/CAUCE_base.html + datos.json
El generador aplica parches con aserción (cada cadena a sustituir debe aparecer
exactamente las veces esperadas; si no, el build falla) para producir las cuatro distribuciones.

Salidas (dist/):
  senda-individual/   cauce-individual/   senda-cauce-paquete/   web/
Uso:  python3 build.py            (genera todo)
"""
import json, re, sys, shutil, hashlib, subprocess, base64, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "fuente"
DIST = ROOT / "dist"
IDENT = DIST / "_identidad"

# ---------------------------------------------------------------- metadatos
EDICION = "Primera edición pública · v0.1.0"
V_SENDA = "0.1.0"
V_CAUCE = "0.1.0"
FECHA = "2026-11-15"
BASE = "https://elcanal.es/contratacion/"          # URL canónica PLANIFICADA (no desplegada)
URL = {"senda": BASE + "senda/", "cauce": BASE + "cauce/", "hub": BASE}
AUTOR = "Manuel Barrera Anglada"
ORCID = "https://orcid.org/0009-0000-8891-7021"
PROYECTO = "https://elcanal.es/"
GRATIS = "Uso gratuito. Sin registro. Sin suscripción."

SLUG = {
    "menor": "contrato-menor",
    "abierto": "procedimiento-abierto-ordinario",
    "simplificado": "procedimiento-abierto-simplificado",
    "abreviado": "procedimiento-simplificado-abreviado",
    "restringido": "procedimiento-restringido",
    "negociado": "procedimiento-negociado-sin-publicidad",
}
TITULO_PROC = {
    "menor": "Contrato menor (art. 118 LCSP)",
    "abierto": "Procedimiento abierto ordinario (arts. 156–158 LCSP)",
    "simplificado": "Procedimiento abierto simplificado (art. 159.1–5 LCSP)",
    "abreviado": "Procedimiento abierto simplificado abreviado (art. 159.6 LCSP)",
    "restringido": "Procedimiento restringido (arts. 160–165 LCSP)",
    "negociado": "Procedimiento negociado sin publicidad (arts. 168–170 LCSP)",
}

TRI_SVG = ('<svg class="tri" viewBox="0 0 64 64" width="14" height="14" aria-hidden="true" focusable="false">'
           '<path d="M32 11 L53.5 49 H10.5 Z" fill="none" stroke="currentColor" stroke-width="7" stroke-linejoin="round"/></svg>')


def favicon_datauri():
    svg = (IDENT / "favicon.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def sub(s, old, new, n=1, label=""):
    c = s.count(old)
    if c != n:
        raise SystemExit(f"[PARCHE] '{label or old[:60]}' aparece {c} veces (esperadas {n})")
    return s.replace(old, new)


def sub_re(s, pat, new, label="", flags=re.S):
    r = re.compile(pat, flags)
    if len(r.findall(s)) != 1:
        raise SystemExit(f"[PARCHE-RE] '{label}' no coincide exactamente una vez")
    return r.sub(lambda m: new, s)


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------- navegación de familia
def nav_html(actual, disponibles, aria="Herramientas de El Canal para contratación pública"):
    """Selector SENDA / CAUCE. Solo muestra destinos disponibles."""
    if len(disponibles) < 2:
        return ""
    items = []
    for nombre, href in disponibles:
        cur = ' aria-current="page"' if nombre == actual else ""
        items.append(f'<a href="{href}"{cur}>{nombre}</a>')
    return f'<nav class="fam" aria-label="{aria}">' + "".join(items) + "</nav>"


# ---------------------------------------------------------------- cabecera <head>
DESC = {
    "senda": ("SENDA: panel gratuito y sin registro para organizar en un solo sitio los enlaces que usa cada día "
              "en contratación pública (plataformas, normativa, sedes). Funciona en su navegador y guarda sus enlaces en su carpeta."),
    "cauce": ("CAUCE: guía gratuita y sin registro de los procedimientos de contratación pública (LCSP) para entidades locales: "
              "plazos, mesa, documentos y artículos, con búsqueda y comparador."),
    "hub": ("SENDA y CAUCE: dos herramientas gratuitas y sin registro de El Canal para la contratación pública en España "
            "(acceso a recursos y guía de procedimientos de la LCSP)."),
}
TITLE = {
    "senda": "SENDA · Centro de acceso a recursos de contratación pública",
    "cauce": "CAUCE · Guía de procedimientos de contratación pública (LCSP)",
    "hub": "SENDA y CAUCE · Herramientas gratuitas de contratación pública · El Canal",
}


def jsonld_app(app):
    nombre = "SENDA" if app == "senda" else "CAUCE"
    cat = "BusinessApplication"
    d = {
        "@context": "https://schema.org", "@type": "SoftwareApplication", "name": nombre,
        "applicationCategory": cat, "operatingSystem": "Cualquier sistema con navegador web moderno",
        "inLanguage": "es", "url": URL[app], "description": DESC[app],
        "softwareVersion": V_SENDA if app == "senda" else V_CAUCE,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "author": {"@type": "Person", "name": AUTOR, "identifier": ORCID, "sameAs": [ORCID]},
        "publisher": {"@type": "Organization", "name": "El Canal", "url": PROYECTO},
        "isAccessibleForFree": True,
    }
    return json.dumps(d, ensure_ascii=False)


def head_block(app, mode, extra_ld=None):
    """mode: individual | paquete | web."""
    t = TITLE[app]
    parts = [f"<title>{esc(t)}</title>",
             f'<meta name="description" content="{esc(DESC[app])}">',
             f'<meta name="author" content="{esc(AUTOR)}">',
             '<meta name="generator" content="El Canal · build.py ' + (V_SENDA if app == 'senda' else V_CAUCE) + '">',
             f'<link rel="icon" type="image/svg+xml" href="{favicon_datauri()}">']
    if mode == "web":
        parts += [
            '<meta name="robots" content="index,follow">',
            f'<link rel="canonical" href="{URL[app]}">',
            '<link rel="icon" href="/favicon.ico" sizes="any">',
            '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
            '<meta name="theme-color" content="#0C0B0A">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="El Canal">',
            '<meta property="og:locale" content="es_ES">',
            f'<meta property="og:title" content="{esc(t)}">',
            f'<meta property="og:description" content="{esc(DESC[app])}">',
            f'<meta property="og:url" content="{URL[app]}">',
            f'<meta property="og:image" content="{URL[app]}assets/og-{app}.png">',
            '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{"SENDA" if app=="senda" else "CAUCE"} · △ El Canal · Gratuito, sin registro">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{esc(t)}">',
            f'<meta name="twitter:description" content="{esc(DESC[app])}">',
            f'<meta name="twitter:image" content="{URL[app]}assets/og-{app}.png">',
            f'<script type="application/ld+json">{jsonld_app(app)}</script>',
        ]
        if extra_ld:
            parts.append(f'<script type="application/ld+json">{extra_ld}</script>')
    return "\n".join(parts)


# ---------------------------------------------------------------- Acerca de (común)
ACERCA_HTML = f"""<div class="acerca">
<p><b>{{NOMBRE}}</b> · {EDICION} · versión {{VERSION}} · {FECHA}</p>
<p>{GRATIS} Funciona en su navegador: no hay cuentas, publicidad ni analítica, y sus datos no se envían a ningún sitio.</p>
<h3>Autoría y procedencia</h3>
<ul>
<li><b>Autor y dirección del proyecto:</b> {AUTOR} · <a href="{ORCID}" target="_blank" rel="noopener noreferrer">ORCID 0009-0000-8891-7021</a></li>
<li><b>Proyecto:</b> {TRI_SVG} <a href="{PROYECTO}" target="_blank" rel="noopener noreferrer">El Canal · elcanal.es</a></li>
<li><b>Apoyo de IA:</b> el desarrollo se ha realizado con asistencia de sistemas de IA (Claude, de Anthropic, y ChatGPT, de OpenAI). La dirección, las decisiones y la responsabilidad son humanas.</li>
<li><b>Naturaleza:</b> proyecto de El Canal. No es una herramienta oficial de ninguna administración ni ha sido validada por ningún órgano o servicio jurídico.</li>
<li><b>Declaración PTC:</b> pendiente de emitir para esta edición; no se afirma ninguna verificación PTC.</li>
<li><b>Licencia:</b> software libre bajo licencia MIT (archivo LICENSE). Puede usarlo, copiarlo, modificarlo y redistribuirlo conservando el aviso de copyright. Se ofrece «tal cual», sin garantía.</li>
</ul>
</div>"""


def acerca(nombre, version):
    return ACERCA_HTML.replace("{NOMBRE}", nombre).replace("{VERSION}", version)


# ---------------------------------------------------------------- SENDA
HELP_SENDA = """<div class="help">
<h3>Para empezar</h3>
<p>Pulse un recurso para abrirlo. Use el buscador (o la tecla «/») para encontrarlo por nombre.</p>
<h3>Añadir, modificar o borrar enlaces</h3>
<ol>
<li>Pulse <b>Editar</b> y después <b>Conectar</b>: elija una carpeta de su ordenador donde SENDA guardará sus enlaces. El navegador le pedirá permiso.</li>
<li>Use <b>Añadir recurso</b>, el lápiz de cada enlace o la papelera. Puede cambiar el orden y renombrar módulos.</li>
<li>Pulse <b>Guardar</b>. Se crea el archivo <code>recursos.json</code> en su carpeta, con copias anteriores en la subcarpeta <code>versiones</code>.</li>
</ol>
<h3>Copias y recuperación</h3>
<ul>
<li><b>Copias y enlaces → Exportar copia de seguridad</b> descarga un archivo con todos sus enlaces; <b>Importar</b> lo recupera.</li>
<li><b>Recuperar enlaces iniciales</b> añade los enlaces de ejemplo que falten, sin borrar ninguno de los suyos.</li>
<li>Los enlaces de ejemplo son editables y borrables: son solo un punto de partida.</li>
</ul>
<h3>Actualizaciones</h3>
<p>Para actualizar SENDA basta con sustituir este archivo por la versión nueva. Sus enlaces están en su carpeta (<code>recursos.json</code>) y <b>no se tocan</b>.</p>
<h3>Navegadores</h3>
<p>Guardar en una carpeta requiere un navegador basado en Chromium (Chrome, Edge…). En otros navegadores puede consultar los enlaces y usar la exportación/importación de copias.
Si abre SENDA desde un archivo local, el navegador puede pedir el permiso de la carpeta en cada sesión; desde la versión web, algunos navegadores permiten recordarlo.</p>
</div>"""

SENDA_CSS = """
.tri{vertical-align:-1px;margin-right:3px}
.footer a{color:inherit}
.help h3,.acerca h3{font:700 .95rem/1.3 var(--font);margin:16px 0 4px}
.help p,.help li,.acerca p,.acerca li{font-size:.9rem;line-height:1.55}
.help code{background:#EEF1F4;padding:1px 5px;border-radius:5px;font-size:.85em}
#helpDlg .dlg-body{max-height:70vh;overflow:auto}
"""


def build_senda(mode, disponibles):
    s = (SRC / "senda" / "SENDA_base.html").read_text(encoding="utf8")
    cat = json.loads((SRC / "senda" / "catalogo_publico.json").read_text(encoding="utf8"))
    L = "SENDA"
    s = sub(s, "<title>SENDA · Contratación</title>", head_block("senda", mode), label="title")
    s = sub(s, "<p>Contratación · Centro de acceso a recursos</p>", "<p>Centro de acceso a recursos · contratación pública</p>", label="subtitulo")
    nav_old = re.search(r'   <nav class="fam"[^\n]*</nav>\n', s)
    if not nav_old:
        raise SystemExit("nav SENDA no encontrado")
    s = s.replace(nav_old.group(0), ("   " + nav_html("SENDA", disponibles) + "\n") if nav_html("SENDA", disponibles) else "")
    # botón de ayuda
    s = sub(s, '    <button id="edit" class="btn ghost"',
            '    <button id="helpBtn" class="btn ghost" type="button" title="Ayuda y acerca de SENDA"><span>Ayuda</span></button>\n    <button id="edit" class="btn ghost"', label="boton ayuda")
    # pie
    foot_new = (f'<div class="footer"><span>{TRI_SVG} SENDA · {EDICION}</span><span>·</span><span>{GRATIS}</span><span>·</span>'
                f'<span>Funciona en su navegador, sin enviar datos</span><span>·</span>'
                f'<a href="#" id="aboutLink">Acerca de</a><span>·</span>'
                f'<a href="{PROYECTO}" target="_blank" rel="noopener noreferrer">El Canal</a></div>')
    s = sub(s, '<div class="footer"><span>SENDA · Contratación · Beta 0.5</span><span>·</span><span>Funciona sin conexión a Internet</span></div>', foot_new, label="footer")
    # diálogos de ayuda / acerca
    dlg = ('<dialog id="helpDlg" class="dlg-md" aria-labelledby="helpTitle">\n'
           ' <div class="dlg-head"><h2 id="helpTitle">Ayuda y acerca de SENDA</h2></div>\n <div class="dlg-body">\n'
           + HELP_SENDA + "\n" + acerca("SENDA", V_SENDA) +
           '\n  <div class="dlg-actions"><button id="helpClose" class="btn primary" type="button">Cerrar</button></div>\n </div>\n</dialog>\n\n')
    s = sub(s, '<dialog id="askDlg"', dlg + '<dialog id="askDlg"', label="dlg ayuda")
    s = sub(s, "</style>", SENDA_CSS + "</style>", label="css")
    # diálogo de conexión genérico
    s = sub_re(s, r'<h2 id="connTitle">.*?</p>\n  <div class="dlg-actions"><button id="connNo"',
               '<h2 id="connTitle">Para editar, elija una carpeta</h2></div>\n <div class="dlg-body">\n'
               '  <p class="conn-lead" id="connLead"></p>\n'
               '  <div class="pathbox" id="connBox"><div id="connPath" class="pathcode"></div><button id="connCopy" class="btn" type="button">Copiar ruta</button></div>\n'
               '  <p class="conn-hint" id="connHint"></p>\n'
               '  <div class="dlg-actions"><button id="connNo"', "connDlg")
    s = sub(s, "const dlg=$('connDlg'),path=folderPath();let answer=false;",
            "const dlg=$('connDlg'),path=folderPath();let answer=false;\n"
            " const isFile=location.protocol==='file:'&&!!path;\n"
            " $('connBox').classList.toggle('hide',!isFile);\n"
            " $('connLead').textContent=isFile?'La carpeta de SENDA es esta:':'SENDA guardará sus enlaces en un archivo (recursos.json) dentro de la carpeta que elija. Se queda en su ordenador: no se envía a ningún sitio.';\n"
            " $('connHint').textContent=isFile?'Pulse «Seleccionar carpeta», pegue la ruta en la barra de direcciones de la ventana que se abre (Ctrl+V y Intro) y confirme.':'Pulse «Seleccionar carpeta» y elija o cree una carpeta propia (por ejemplo, «SENDA enlaces»). Si ya la usó antes, elija la misma para recuperar sus enlaces.';",
            label="connectDialog js")
    # edición web: cualquier carpeta propia vale (no hace falta que contenga SENDA.html)
    s = sub(s, "async function checkFolder(handle){\n await probe(handle);\n",
            "async function checkFolder(handle){\n await probe(handle);\n if(location.protocol!=='file:')return; // edición web: se admite cualquier carpeta propia\n", label="checkFolder")
    s = sub(s, "offerRecovery&&missing.length&&db.revision<=2&&", "false&&offerRecovery&&missing.length&&", label="no-reofrecer ejemplos")
    s = sub(s, "notice('Los 14 enlaces iniciales ya están presentes.','ok')", "notice('Los enlaces iniciales ya están presentes.','ok')", label="14 enlaces")
    s = sub(s, "Para guardar cambios, indica dónde está la carpeta de SENDA.", "Para guardar cambios, elige una carpeta donde guardar tus enlaces.", n=2, label="saveText")
    s = s.replace("Conectar con la carpeta de SENDA", "Conectar con tu carpeta de enlaces")
    s = sub_re(s, r"const DEFAULT=\{.*?\};\n", "const DEFAULT=" + json.dumps(cat, ensure_ascii=False, separators=(",", ":")) + ";\n", label="DEFAULT")
    s = sub(s, "const VERSION='0.5.0-beta';", f"const VERSION='{V_SENDA}';", label="VERSION")
    # copia de lectura local: solo en archivo local; en web se omite la etiqueta <script src="recursos.js">
    if mode == "web":
        s = sub(s, '<script src="recursos.js"></script>\n', "", label="recursos.js tag")
    # caché del catálogo en el navegador (solo origen web) para mostrar los enlaces propios sin reconectar
    s = sub(s, "async function writeMirror(obj){const f=", "async function writeMirror(obj){cacheCatalog(obj);const f=", label="writeMirror")
    s = sub(s, "try{if(!dir||lastLoaded===null)return;const obj=JSON.parse(lastLoaded),want=mirrorText(obj);",
            "try{if(!dir||lastLoaded===null)return;const obj=JSON.parse(lastLoaded),want=mirrorText(obj);cacheCatalog(obj);", label="syncMirror")
    extra = r"""
/* ---------- Copia de lectura en el navegador (solo cuando SENDA se abre desde una página web) ---------- */
const WEB_CACHE=location.protocol!=='file:';
async function cacheCatalog(o){
 if(!WEB_CACHE)return;
 try{const d=await openLocalDb();await new Promise((res,rej)=>{const t=d.transaction('estado','readwrite');t.objectStore('estado').put(JSON.stringify(o),'catalogo');t.oncomplete=()=>{d.close();res()};t.onerror=()=>{d.close();rej(t.error)}})}catch(e){}
}
async function loadCachedCatalog(){
 if(!WEB_CACHE||window.SENDA_RECURSOS||dir)return;
 try{const d=await openLocalDb();const txt=await new Promise((res,rej)=>{const t=d.transaction('estado','readonly');const q=t.objectStore('estado').get('catalogo');q.onsuccess=()=>{d.close();res(q.result)};q.onerror=()=>{d.close();rej(q.error)}});
  if(!txt||dir)return;db=validate(JSON.parse(txt));source='espejo';render()}catch(e){}
}
/* ---------- Ayuda y acerca de ---------- */
$('helpBtn').onclick=()=>$('helpDlg').showModal();
$('aboutLink').onclick=e=>{e.preventDefault();$('helpDlg').showModal()};
$('helpClose').onclick=()=>$('helpDlg').close();

/* ===================== Arranque ===================== */"""
    s = sub(s, "\n/* ===================== Arranque ===================== */", extra, label="arranque marcador")
    s = sub(s, "clean();render();restoreFolder();", "clean();render();loadCachedCatalog().then(()=>restoreFolder());", label="arranque")
    return s


# ---------------------------------------------------------------- CAUCE
ALCANCE_JS = r"""  a.appendChild(h('p',{class:'meta',text:'__EDICION__ · versión __VERSION__ · contenido derivado de la revisión jurídica de 05/11/2026 y contrastado de nuevo con el BOE el 15/11/2026.'}));
  D.alcance.forEach(function(t){var p=h('p');p.innerHTML=t;a.appendChild(p)});
  a.appendChild(h('h3',{text:'Cómo leer los contenidos'}));
  a.appendChild(h('ul',null,[
    h('li',null,[h('b',{text:'Norma contrastada: '}),'artículos y cifras cotejados con el texto consolidado del BOE (etiqueta «Obligación legal», «Requisito condicionado» o «Previsión de pliegos»).']),
    h('li',null,[h('b',{text:'Explicación orientativa: '}),'síntesis operativa revisable; no es una transcripción de la ley ni asesoramiento jurídico.']),
    h('li',null,[h('b',{text:'Práctica particular de cada entidad: '}),'depende de la organización interna de cada entidad; no se presume ni es de aplicación general.']),
    h('li',null,[h('b',{text:'Demostrativo o pendiente de validación jurídica: '}),'borradores de documentos (todos los procedimientos salvo el abierto simplificado) y cuestiones aún no validadas por ningún órgano o servicio jurídico.'])
  ]));
  a.appendChild(h('h3',{text:'Estado de esta edición'}));
  a.appendChild(h('ul',null,[
    h('li',null,['Las respuestas de las fichas y las referencias normativas proceden de la guía original; las cuestiones jurídicas abiertas se mantienen como pendientes de validación.']),
    h('li',null,['Documentos: el abierto simplificado es el ejemplo desarrollado; los otros cinco procedimientos son borradores demostrativos.']),
    h('li',null,['Normativa: solo los artículos con texto literal contrastado en el texto consolidado del BOE llevan cita literal. El resto se marca «sin texto literal verificado».']),
    h('li',null,['No hay conexión con ningún sistema ni datos de ninguna entidad: no se recoge ni se envía información.'])
  ]));
  a.appendChild(h('h3',{text:'Autoría y procedencia'}));
  var pr=h('div');pr.innerHTML=__ACERCA__;a.appendChild(pr);
}
"""


def build_cauce(mode, disponibles, extra_ld=None):
    s = (SRC / "cauce" / "CAUCE_base.html").read_text(encoding="utf8")
    datos = json.loads((SRC / "cauce" / "datos.json").read_text(encoding="utf8"))
    datos["meta"]["version"] = EDICION
    s = sub(s, "<title>CAUCE · Guía jurídica y operativa de contratación · Beta 0.6</title>", head_block("cauce", mode, extra_ld), label="title")
    s = sub(s, '<h1>CAUCE</h1><p>Guía jurídica y operativa de contratación</p><span class="ver">Beta 0.6</span>',
            '<h1>CAUCE</h1><p>Guía de procedimientos de contratación pública</p><span class="ver">Primera edición pública · v0.1.0</span>', label="brand")
    nav_old = re.search(r'    <nav class="fam"[^\n]*</nav>\n', s)
    if not nav_old:
        raise SystemExit("nav CAUCE no encontrado")
    nv = nav_html("CAUCE", disponibles)
    s = s.replace(nav_old.group(0), ("    " + nv + "\n") if nv else "")
    s = sub(s, "<b>Herramienta de apoyo, no instrucción oficial.</b> Revisión jurídica: 05/11/2026 · Importes: valor estimado sin IVA · Los contenidos marcados «pendiente» no están validados.",
            "<b>Herramienta de apoyo, no instrucción oficial ni asesoramiento jurídico.</b> Contraste con el BOE: 15/11/2026 · Importes: valor estimado sin IVA · Los contenidos marcados «pendiente de validación jurídica» no están validados.", label="strip")
    # datos
    blob = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    m = re.search(r'(<script id="datos" type="application/json">).*?(</script>)', s, re.S)
    if not m or len(re.findall(r'<script id="datos"', s)) != 1:
        raise SystemExit("bloque datos no encontrado")
    s = s[:m.start()] + m.group(1) + blob + m.group(2) + s[m.end():]
    # textos JS
    s = sub(s, "local:{t:'Práctica local · pendiente de verificar',i:'local'}", "local:{t:'Práctica particular de cada entidad',i:'local'}", label="tipo local")
    s = sub(s, "local:'Práctica local · sin verificar'", "local:'Práctica particular · no general'", label="tipo doc local")
    s = sub(s, " · Etiqueta original (beta 0.4.1): '+f.st", " · Etiqueta de la ficha: '+f.st", label="etiqueta orig")
    s = sub(s, "text:'Interpretación operativa (beta 0.4.1)'", "text:'Interpretación operativa'", label="badge")
    s = sub(s, "'No consta fundamento legal: depende de práctica local pendiente de verificar.'", "'No consta fundamento legal: depende de la práctica particular de cada entidad.'", label="sin fundamento")
    s = sub(s, "Los documentos de práctica local no se presumen.", "Las prácticas particulares de cada entidad no se presumen.", label="demo")
    s = sub(s, "document.title='CAUCE · Guía jurídica y operativa de contratación · Beta 0.6';", "document.title=" + json.dumps(TITLE["cauce"], ensure_ascii=False) + ";", label="document.title")
    acerca_js = json.dumps(acerca("CAUCE", V_CAUCE), ensure_ascii=False).replace("</", "<\\/")
    block = ALCANCE_JS.replace("__EDICION__", EDICION).replace("__VERSION__", V_CAUCE).replace("__ACERCA__", acerca_js)
    s = sub(s, "  /*__ALCANCE__*/\n}\n", block, label="alcance")
    # pie con procedencia
    enlaces_proc = ""
    if mode == "web":
        enlaces_proc = ('<nav class="pf-proc" aria-label="Páginas por procedimiento">' + "".join(
            f'<a href="procedimientos/{SLUG[p["id"]]}/">{esc(p["n"])}</a>' for p in datos["procs"]) + "</nav>")
    pie = (f'<footer class="pubfoot">{enlaces_proc}<p>{TRI_SVG} <b>CAUCE</b> · {EDICION} · {GRATIS} · '
           f'Por <a href="{ORCID}" target="_blank" rel="noopener noreferrer">{AUTOR}</a> · '
           f'<a href="{PROYECTO}" target="_blank" rel="noopener noreferrer">El Canal</a> · Procesa todo en su navegador; sin cuentas ni analítica.</p></footer>\n')
    s = sub(s, '<section id="alcance" role="region"', pie + '<section id="alcance" role="region"', label="pie")
    css = (".tri{vertical-align:-1px;margin-right:3px}"
           ".pubfoot{margin-top:auto;padding:18px 32px 26px;font-size:.82rem;color:var(--mut2);border-top:1px solid var(--line)}"
           ".pubfoot p{margin:6px 0 0}.pubfoot a{color:var(--pri-d)}"
           ".pf-proc{display:flex;flex-wrap:wrap;gap:6px 16px;margin-bottom:6px}"
           "#alcance .acerca h3{margin:12px 0 4px;font-size:.95rem}"
           "@media (max-width:760px){.pubfoot{padding:16px 14px 22px}}"
           "@media print{.pubfoot{border:0;padding:6px 0}.pf-proc{display:none}}\n")
    s = sub(s, "</style>", css + "</style>", label="css cauce")
    return s, datos


# ---------------------------------------------------------------- páginas estáticas de CAUCE (web)
PAGE_CSS = """
:root{--ink:#14283B;--mut:#44586B;--bg:#F5F3EE;--surf:#fff;--line:#DAE2EA;--pri:#1F6F78;--pri-d:#14565D;--gold:#B08D3C;--navy:#12263F;color-scheme:light;
--font:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;--font-d:Georgia,Cambria,"Liberation Serif","Times New Roman",serif}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--font);-webkit-font-smoothing:antialiased}
a{color:var(--pri-d)}header,main,footer{max-width:900px;margin:0 auto;padding:0 18px}
.top{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid var(--line)}
.top b{font:400 1.25rem/1 var(--font-d);letter-spacing:.2em;color:var(--pri)}.top a{text-decoration:none}
.crumb{font-size:.85rem;color:var(--mut);margin:14px 0 0}
h1{font:400 1.9rem/1.25 var(--font-d);margin:.4em 0 .3em;color:var(--navy)}
h2{font:700 1.25rem/1.3 var(--font);margin:1.8em 0 .5em;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:.25em}
h3{font:700 1.02rem/1.35 var(--font);margin:1.3em 0 .3em}
.lede{font-size:1.08rem;color:var(--mut)}
.cta{display:inline-block;background:var(--pri);color:#fff;text-decoration:none;font-weight:700;padding:11px 22px;border-radius:999px;margin:10px 0}
.cta:hover{background:var(--pri-d)}
.aviso{background:#FBF6E8;border:1px solid #EADFC0;border-radius:10px;padding:10px 14px;font-size:.9rem;color:#5C4410;margin:16px 0}
.card{background:var(--surf);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:10px 0}
.card h3{margin-top:0}.card p{margin:.3em 0}.tag{font-size:.78rem;font-weight:700;color:var(--pri-d)}.pend{color:#7A2E45}
body{overflow-wrap:anywhere}.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}table{min-width:560px;width:100%;border-collapse:collapse;font-size:.92rem;background:var(--surf)}th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:#EEF1F4}
ul.norm{padding-left:1.1em}ul.norm li{margin:.3em 0}
footer{padding:22px 18px 40px;margin-top:30px;border-top:1px solid var(--line);font-size:.85rem;color:var(--mut)}
.tri{vertical-align:-1px;margin-right:3px}nav.otros{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.9rem}
@media (max-width:600px){h1{font-size:1.5rem}th,td{padding:6px}}
@media print{.cta,nav.otros{display:none}}
"""


def strip_html(t):
    return re.sub(r"<[^>]+>", "", t or "")


def tag_label(t):
    return {"legal": "Obligación legal", "cond": "Requisito condicionado", "pliegos": "Previsión de pliegos",
            "local": "Práctica particular de cada entidad"}.get(t, t)


def match_tok(k, t):
    # Réplica de matchTok de CAUCE: coincide si son iguales o si uno es prefijo del otro por apartado.
    return k == t or k.startswith(t + ".") or t.startswith(k + ".")


def pagina_proc(datos, p):
    pid = p["id"]
    nombre = TITULO_PROC[pid]
    url = f'{URL["cauce"]}procedimientos/{SLUG[pid]}/'
    f = datos["fichas"][pid]
    amb = f["ambito"]
    cats = {c["id"]: c for c in datos["cats"]}
    docs = [d for d in datos["docs"] if d["p"] == pid]
    toks = {t for c in f.values() for t in c.get("tk", [])} | {t for d in docs for t in d.get("tk", [])}
    normas = [n for n in datos["normas"] if any(match_tok(n["k"], t) for t in toks)]
    desc = f'{nombre}: {strip_html(amb["s"])} Plazos, mesa, documentos y normativa para entidades locales. Gratis y sin registro.'
    if len(desc) > 165:
        desc = desc[:162].rsplit(" ", 1)[0] + "…"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": nombre + " · guía de tramitación", "description": desc, "inLanguage": "es",
         "isPartOf": {"@type": "WebSite", "name": "El Canal", "url": PROYECTO},
         "author": {"@type": "Person", "name": AUTOR, "identifier": ORCID},
         "about": {"@type": "Legislation", "name": "Ley 9/2017, de Contratos del Sector Público", "sameAs": "https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Contratación", "item": URL["hub"]},
            {"@type": "ListItem", "position": 2, "name": "CAUCE", "item": URL["cauce"]},
            {"@type": "ListItem", "position": 3, "name": nombre, "item": url}]}]}
    out = [f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           f"<title>{esc(nombre)} · guía de tramitación · CAUCE</title>",
           f'<meta name="description" content="{esc(desc)}">',
           f'<meta name="author" content="{esc(AUTOR)}"><meta name="robots" content="index,follow">',
           f'<link rel="canonical" href="{url}">',
           '<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">',
           '<meta name="theme-color" content="#0C0B0A">',
           '<meta property="og:type" content="article"><meta property="og:site_name" content="El Canal"><meta property="og:locale" content="es_ES">',
           f'<meta property="og:title" content="{esc(nombre)} · CAUCE"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}">',
           f'<meta property="og:image" content="{URL["cauce"]}assets/og-cauce.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
           f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(nombre)} · CAUCE"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{URL["cauce"]}assets/og-cauce.png">',
           f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>',
           f"<style>{PAGE_CSS}</style></head><body>",
           f'<header><div class="top"><b>CAUCE</b><a href="../../">Abrir la guía interactiva</a><a href="{URL["hub"]}">SENDA y CAUCE</a></div>'
           f'<p class="crumb"><a href="{URL["hub"]}">Contratación</a> › <a href="../../">CAUCE</a> › {esc(nombre)}</p></header><main>',
           f"<h1>{esc(nombre)}: guía de tramitación</h1>",
           f'<p class="lede">{esc(strip_html(amb["s"]))} {esc(strip_html(amb["d"]))}</p>',
           f'<a class="cta" href="../../?proc={pid}&amp;tab=car">Abrir {esc(p["n"])} en CAUCE</a>',
           '<p class="aviso"><b>Herramienta de apoyo, no instrucción oficial ni asesoramiento jurídico.</b> Contenido contrastado con el texto consolidado de la LCSP en el BOE el 15/11/2026; lo marcado «pendiente de validación jurídica» no ha sido validado por ningún órgano o servicio jurídico. Importes: valor estimado sin IVA.</p>']
    out.append("<h2>Qué conviene saber, paso a paso</h2>")
    for g in datos["grupos"]:
        out.append(f"<h3>{esc(g['n'])}</h3>")
        for cid in g["cats"]:
            x = f.get(cid)
            if not x:
                continue
            nt = ""
            if x.get("nt") and x["nt"].get("texto"):
                nt = f'<p class="pend"><b>Pendiente de validación jurídica:</b> {esc(strip_html(x["nt"]["texto"]))}</p>'
            out.append(f'<div class="card"><h3>{esc(cats[cid]["n"])}</h3><p>{esc(strip_html(x["s"]))}</p>'
                       f'<p>{esc(strip_html(x["d"]))}</p><p class="tag">{esc(tag_label(x["t"]))} · Art. {esc(x["r"])}</p>{nt}</div>')
    if docs:
        out.append("<h2>Documentos del expediente</h2>")
        if any(d.get("demo") for d in docs):
            out.append('<p class="aviso"><b>Borrador demostrativo.</b> Inventario parcial construido solo con preceptos revisados o marcado como pendiente. Las prácticas particulares de cada entidad no se presumen.</p>')
        out.append("<div class=\"tw\"><table><thead><tr><th>Documento</th><th>Quién</th><th>Qué comprobar</th><th>Tipo</th></tr></thead><tbody>")
        for d in docs:
            out.append(f'<tr><td>{esc(strip_html(d["n"]))}</td><td>{esc(d["q"])}</td><td>{esc(strip_html(d["ck"]))}</td><td>{esc(tag_label(d["t"]))}</td></tr>')
        out.append("</tbody></table></div>")
    if normas:
        out.append("<h2>Normativa de referencia</h2><ul class=\"norm\">")
        for n in normas:
            out.append(f'<li><b>{esc(n["titulo"])}</b>. {esc(strip_html(n["breve"]))}</li>')
        out.append("</ul>")
        out.append('<p>Texto consolidado de la ley: <a href="https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902" rel="noopener noreferrer">LCSP · BOE</a>.</p>')
    otros = "".join(f'<a href="../{SLUG[q["id"]]}/">{esc(TITULO_PROC[q["id"]])}</a>' for q in datos["procs"] if q["id"] != pid)
    out.append(f'<h2>Otros procedimientos</h2><nav class="otros" aria-label="Otros procedimientos">{otros}</nav></main>')
    out.append(f'<footer>{TRI_SVG} <b>CAUCE</b> · {EDICION} · {GRATIS} · Por <a href="{ORCID}" rel="noopener noreferrer">{AUTOR}</a> · '
               f'<a href="{PROYECTO}" rel="noopener noreferrer">El Canal</a>. No es una herramienta oficial de ninguna administración. Sin cuentas, publicidad ni analítica.</footer></body></html>')
    return "\n".join(out), url


def pagina_hub():
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "url": URL["hub"], "name": TITLE["hub"], "description": DESC["hub"], "inLanguage": "es",
          "author": {"@type": "Person", "name": AUTOR, "identifier": ORCID}, "isPartOf": {"@type": "WebSite", "name": "El Canal", "url": PROYECTO}}
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(TITLE['hub'])}</title><meta name="description" content="{esc(DESC['hub'])}"><meta name="author" content="{esc(AUTOR)}"><meta name="robots" content="index,follow">
<link rel="canonical" href="{URL['hub']}"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><meta name="theme-color" content="#0C0B0A">
<meta property="og:type" content="website"><meta property="og:site_name" content="El Canal"><meta property="og:locale" content="es_ES"><meta property="og:title" content="{esc(TITLE['hub'])}"><meta property="og:description" content="{esc(DESC['hub'])}"><meta property="og:url" content="{URL['hub']}">
<meta property="og:image" content="{URL['cauce']}assets/og-cauce.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(TITLE['hub'])}"><meta name="twitter:description" content="{esc(DESC['hub'])}"><meta name="twitter:image" content="{URL['cauce']}assets/og-cauce.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script><style>{PAGE_CSS}</style></head><body>
<header><div class="top"><b>{TRI_SVG}EL CANAL</b><span>Contratación pública</span></div></header>
<main><h1>SENDA y CAUCE</h1><p class="lede">Dos herramientas gratuitas para quien trabaja con contratación pública en España. {GRATIS} Funcionan en su navegador y no envían sus datos a ningún sitio.</p>
<div class="card"><h3><a href="senda/">SENDA · Centro de acceso a recursos</a></h3><p>Un panel para tener en un solo sitio los enlaces que usa cada día: plataformas, sedes, normativa, modelos. Usted los añade, los cambia y los guarda en su propia carpeta.</p></div>
<div class="card"><h3><a href="cauce/">CAUCE · Guía de procedimientos de contratación pública</a></h3><p>Los procedimientos de la Ley 9/2017 (LCSP) explicados para entidades locales: plazos, mesa de contratación, documentos y artículos, con búsqueda y comparador.</p>
<nav class="otros" aria-label="Procedimientos">{''.join(f'<a href="cauce/procedimientos/{SLUG[k]}/">{esc(v)}</a>' for k, v in TITULO_PROC.items())}</nav></div>
<p class="aviso">Proyecto de El Canal. No son herramientas oficiales de ninguna administración. CAUCE no es asesoramiento jurídico y no ha sido validado por ningún órgano o servicio jurídico.</p></main>
<footer>{TRI_SVG} <a href="{PROYECTO}" rel="noopener noreferrer">El Canal</a> · {AUTOR} · <a href="{ORCID}" rel="noopener noreferrer">ORCID</a> · {EDICION}</footer></body></html>"""


# ---------------------------------------------------------------- documentación por distribución
def sha_lista(carpeta: Path):
    lineas = []
    for f in sorted(carpeta.rglob("*")):
        if f.is_file() and f.name != "SHA256SUMS.txt":
            lineas.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(carpeta).as_posix()}")
    (carpeta / "SHA256SUMS.txt").write_text("\n".join(lineas) + "\n", encoding="utf8")


def docs_comunes(carpeta: Path, titulo, contenido, version, extra=""):
    shutil.copy2(ROOT / "LICENSE", carpeta / "LICENSE")
    shutil.copy2(ROOT / "AVISO_LEGAL.md", carpeta / "AVISO_LEGAL.md")
    (carpeta / "VERSION.txt").write_text(f"{titulo}\n{EDICION}\nVersión {version}\nFecha de generación: {FECHA}\n", encoding="utf8")
    (carpeta / "LEEME.md").write_text(f"""# {titulo} · {EDICION}

{GRATIS}

{contenido}

## Cómo se usa
Abra el archivo HTML con su navegador (doble clic). No necesita instalar nada, ni conexión a Internet (salvo para abrir los enlaces externos).
Funciona en su navegador: no se envían datos, no hay cuentas, publicidad ni analítica.

{extra}
## Autoría y procedencia
- Autor y dirección del proyecto: {AUTOR} · ORCID {ORCID}
- Proyecto: El Canal · {PROYECTO}
- Apoyo de IA: Claude (Anthropic) y ChatGPT (OpenAI). Dirección, decisiones y responsabilidad humanas.
- No es una herramienta oficial de ninguna administración. Sin logotipos institucionales.
- Declaración PTC: pendiente de emitir; no se afirma ninguna verificación PTC.
- Licencia: MIT (archivo `LICENSE` incluido). Software «tal cual», sin garantía; ver `AVISO_LEGAL.md`.

## Navegadores
Consultar los enlaces y usar CAUCE funciona en cualquier navegador moderno. Guardar los enlaces propios de SENDA en una carpeta requiere Chrome o Edge de escritorio; en otros navegadores use Exportar/Importar copia. Detalle en el repositorio: `docs/COMPATIBILIDAD_NAVEGADORES.md`.

## Aviso legal
No es una herramienta oficial ni asesoramiento jurídico; software «tal cual». Ver `AVISO_LEGAL.md`.

## Integridad
`SHA256SUMS.txt` lista el SHA-256 de cada archivo de esta distribución. Verificación: `sha256sum -c SHA256SUMS.txt`.
""", encoding="utf8")
    (carpeta / "CHANGELOG.md").write_text(f"""# Registro de cambios

## {version} · {FECHA} · {EDICION}
- Primera edición pública (v0.1.0), con licencia MIT.
- Identidad △ de El Canal: icono, imágenes para redes e información de procedencia en la propia herramienta.
- Contenido generalizado para uso público por entidades locales; sin referencias a ninguna organización concreta.
""", encoding="utf8")


def copia_identidad(dest: Path, incluir_og=None):
    dest.mkdir(parents=True, exist_ok=True)
    for f in IDENT.iterdir():
        if f.name.startswith("og-") and incluir_og and f.name not in incluir_og:
            continue
        shutil.copy2(f, dest / f.name)


# ---------------------------------------------------------------- orquestación
def main():
    if not (IDENT / "favicon.svg").exists():
        raise SystemExit("Faltan los recursos de identidad: ejecute fuente/identidad/make_identidad.py dist/_identidad")
    for d in ["senda-individual", "cauce-individual", "senda-cauce-paquete", "web"]:
        if (DIST / d).exists():
            shutil.rmtree(DIST / d)
    # 1 individuales (sin enlaces a apps ausentes)
    d = DIST / "senda-individual"; d.mkdir(parents=True)
    (d / "SENDA.html").write_text(build_senda("individual", [("SENDA", "SENDA.html")]), encoding="utf8")
    copia_identidad(d / "identidad", {"og-senda.png"})
    docs_comunes(d, "SENDA", "Centro de acceso a recursos para contratación pública: sus enlaces, en un solo sitio, editables y guardados en su carpeta.", V_SENDA,
                 "## Personalización\nSENDA → Editar → Conectar → elegir carpeta → Añadir/Modificar/Borrar → Guardar. Sus enlaces quedan en `recursos.json` (y una copia de lectura `recursos.js`) en su carpeta; actualizar SENDA sustituyendo `SENDA.html` no los modifica.\n\n")
    cs, datos = build_cauce("individual", [("CAUCE", "CAUCE.html")])
    d = DIST / "cauce-individual"; d.mkdir(parents=True)
    (d / "CAUCE.html").write_text(cs, encoding="utf8")
    copia_identidad(d / "identidad", {"og-cauce.png"})
    docs_comunes(d, "CAUCE", "Guía de procedimientos de contratación pública (LCSP) para entidades locales, con búsqueda y comparador.", V_CAUCE,
                 "## Contenido\nLos contenidos jurídicos se actualizan por solicitud escrita al autor (no se editan dentro de la aplicación). Lo marcado «pendiente de validación jurídica» no ha sido validado por ningún órgano o servicio jurídico.\n\n")
    # 2 paquete conjunto (enlaces relativos bidireccionales)
    d = DIST / "senda-cauce-paquete"; d.mkdir(parents=True)
    nav = [("SENDA", "SENDA.html"), ("CAUCE", "CAUCE.html")]
    (d / "SENDA.html").write_text(build_senda("paquete", nav), encoding="utf8")
    (d / "CAUCE.html").write_text(build_cauce("paquete", nav)[0], encoding="utf8")
    copia_identidad(d / "identidad", {"og-senda.png", "og-cauce.png"})
    docs_comunes(d, "SENDA + CAUCE", "Paquete conjunto: SENDA (acceso a recursos) y CAUCE (guía de procedimientos) enlazadas entre sí. Funciona sin conexión a Internet.", V_SENDA,
                 "Guarde ambos archivos en la misma carpeta. El selector de la cabecera pasa de una herramienta a la otra.\n\n")
    # 3 edición web (navegación solo entre apps publicadas)
    w = DIST / "web"; w.mkdir(parents=True)
    ct = w / "contratacion"
    navw = [("SENDA", "../senda/"), ("CAUCE", "../cauce/")]
    (ct / "senda").mkdir(parents=True); (ct / "cauce").mkdir(parents=True)
    (ct / "senda" / "index.html").write_text(build_senda("web", navw), encoding="utf8")
    cs, datos = build_cauce("web", navw)
    (ct / "cauce" / "index.html").write_text(cs, encoding="utf8")
    (ct / "index.html").write_text(pagina_hub(), encoding="utf8")
    urls = [URL["hub"], URL["senda"], URL["cauce"]]
    for p in datos["procs"]:
        html, url = pagina_proc(datos, p)
        (ct / "cauce" / "procedimientos" / SLUG[p["id"]]).mkdir(parents=True)
        (ct / "cauce" / "procedimientos" / SLUG[p["id"]] / "index.html").write_text(html, encoding="utf8")
        urls.append(url)
    for f in IDENT.iterdir():
        if f.name.startswith("og-"):
            continue
        shutil.copy2(f, w / f.name)           # favicon único a nivel de dominio (raíz)
    for app in ("senda", "cauce"):
        (ct / app / "assets").mkdir()
        shutil.copy2(IDENT / f"og-{app}.png", ct / app / "assets" / f"og-{app}.png")
    prop = w / "_propuestas_no_desplegar"; prop.mkdir()
    (prop / "sitemap_contratacion.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{FECHA}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf8")
    (prop / "robots_propuesta.txt").write_text(
        "# PROPUESTA — no sustituye al robots.txt de producción. Añadir, si procede, tras revisar el existente.\n"
        "User-agent: *\nAllow: /contratacion/\n\nSitemap: https://elcanal.es/sitemap.xml\n"
        "# (e incluir en ese sitemap las URL de sitemap_contratacion.xml)\n", encoding="utf8")
    docs_comunes(w, "SENDA y CAUCE · edición web", "Estructura lista para publicar bajo `elcanal.es/contratacion/` (no desplegada).", V_SENDA,
                 "## Estructura\n`contratacion/` (portada), `contratacion/senda/`, `contratacion/cauce/` y `contratacion/cauce/procedimientos/<procedimiento>/` (6 páginas indexables generadas de los mismos datos que la guía). Icono único a nivel de dominio en la raíz (`/favicon.ico`, `/favicon.svg`, `/apple-touch-icon.png`). La carpeta `_propuestas_no_desplegar` contiene solo propuestas de sitemap y robots: no deben copiarse tal cual a producción.\n\n")
    for dd in ["senda-individual", "cauce-individual", "senda-cauce-paquete", "web"]:
        sha_lista(DIST / dd)
    print("OK build", FECHA)


if __name__ == "__main__":
    main()

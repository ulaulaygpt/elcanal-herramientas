from pathlib import Path
from html import escape
import hashlib, shutil, re, zipfile, json, datetime, textwrap, os

HERE=Path(__file__).resolve().parent
DIST=HERE/'dist'
BASE=HERE/'base'
WEB=HERE/'web'
OUT=HERE/'release_site'
assert BASE.is_dir() and WEB.is_dir()
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(BASE,OUT)
for p in (WEB/'contratacion').rglob('*'):
    if p.is_file():
        target=OUT/p.relative_to(WEB)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
(OUT/'herramientas').mkdir(exist_ok=True)
(OUT/'normaliza').mkdir(exist_ok=True)
shutil.copy2(HERE/'source/LICENSE',OUT/'normaliza/LICENSE.txt')
(OUT/'descargas').mkdir(exist_ok=True)
DIST.mkdir(exist_ok=True)

ROOT='https://elcanal.es'
ORCID='https://orcid.org/0009-0000-8891-7021'
DATE='2026-11-16'
TRI='△'
STYLE='''
:root{color-scheme:dark;--bg:#101111;--surface:#191b1b;--line:#383936;--ink:#f5f1e6;--mut:#c6c5bd;--gold:#e3bc6e;--sage:#9cd9bb;--blue:#badce8;--warn:#fae6ac}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif}a{color:var(--gold);text-underline-offset:3px}a:hover{color:#ffdb96}a:focus-visible,button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid var(--sage);outline-offset:3px}
.layout{width:min(1100px,calc(100% - 36px));margin:0 auto}.skip{position:absolute;transform:translateY(-120%);background:var(--ink);color:var(--bg);padding:9px;z-index:50}.skip:focus{transform:none}.nav{border-bottom:1px solid var(--line);background:#121414}.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px;flex-wrap:wrap}.brand{color:var(--ink);font-size:.92rem;letter-spacing:.12em;font-weight:800;text-decoration:none}.brand b{color:var(--gold);font-size:1.35rem}.links{display:flex;gap:20px;flex-wrap:wrap}.links a{color:var(--ink);text-decoration:none;font-size:.88rem}.links a:hover{text-decoration:underline}
.kicker{font-size:.76rem;text-transform:uppercase;letter-spacing:.17em;font-weight:700;color:var(--gold)}h1,h2,h3,p{overflow-wrap:anywhere}h1{font-size:clamp(2.1rem,5.5vw,3.55rem);line-height:1.13;letter-spacing:-.045em;margin:12px 0 18px;max-width:850px}h2{font-size:1.6rem;line-height:1.3;margin:10px 0}h3{font-size:1.15rem;margin:8px 0}.lead{font-size:1.13rem;color:var(--mut);max-width:810px}.hero{padding:70px 0 45px}.pill{display:inline-flex;gap:6px;align-items:center;border:1px solid #706044;border-radius:99px;padding:4px 11px;font-size:.79rem;color:#f4d7a3}.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 18px;border-radius:10px;min-height:45px;border:1px solid #8f7951;color:var(--ink);font:inherit;font-weight:700;text-decoration:none;background:transparent;cursor:pointer}.btn.primary{background:var(--gold);border-color:var(--gold);color:#161616}.btn.primary:hover{background:#ffd68e;border-color:#ffd68e;color:#121212}.btn:hover{background:#272722;color:#fff}.btn[disabled]{opacity:.5;cursor:default}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin:24px 0 35px}.tile{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:27px}.tile.spotlight{border-color:#aa843d;background:linear-gradient(145deg,#252016,#141515 85%);box-shadow:0 0 0 1px #4a3b22,0 0 35px rgba(236,183,76,.09)}.tile .eyebrow{font-size:.78rem;font-weight:800;letter-spacing:.1em;color:var(--sage);text-transform:uppercase}.tile h2{margin:10px 0}.tile p{color:var(--mut);margin:12px 0}.tile .btn{margin-top:8px}.muted{color:var(--mut)}.small{font-size:.88rem}.notice{border-left:3px solid var(--gold);padding:10px 16px;background:#25231c;color:var(--ink);margin:24px 0}.row{display:flex;align-items:center;flex-wrap:wrap;gap:12px}.footer{border-top:1px solid var(--line);color:var(--mut);padding:23px 0 55px;font-size:.84rem}.footer a{color:var(--mut)}.fine{font-size:.82rem;color:var(--mut)}
@media (max-width:700px){.grid{grid-template-columns:1fr}.hero{padding-top:45px}.nav-inner{padding:12px 0}.links{gap:12px}.tile{padding:20px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''

def head(title,description,canonical,extra=''):
    safe_title=escape(title,quote=True);safe_desc=escape(description,quote=True)
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe_title}</title><meta name="description" content="{safe_desc}"><meta name="author" content="Manuel Barrera Anglada"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta property="og:title" content="{safe_title}"><meta property="og:description" content="{safe_desc}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="El Canal"><meta name="theme-color" content="#101111">{extra}<style>{STYLE}</style></head><body><a class="skip" href="#contenido">Ir al contenido</a><nav class="nav" aria-label="Navegación"><div class="layout nav-inner"><a class="brand" href="/"><b>△</b> EL CANAL</a><div class="links"><a href="/herramientas/">Herramientas</a><a href="/normaliza/">Normaliza</a><a href="/contratacion/cauce/">Cauce</a><a href="/contratacion/senda/">Senda</a></div></div></nav>'''

foot='''<footer class="footer"><div class="layout">△ El Canal · Proyecto independiente de Manuel Barrera Anglada · <a href="https://orcid.org/0009-0000-8891-7021" rel="noopener noreferrer">ORCID</a>. Aplicaciones gratuitas, sin registro ni publicidad. Sin vinculación ni respaldo institucional. <a href="/">Volver a El Canal</a></div></footer></body></html>'''

PORTAL_DESC='Herramientas gratuitas de El Canal: NORMALIZA para limpiar textos, CAUCE para consultar contratación pública, SENDA para gestionar accesos de trabajo y PASOS próximamente.'
PORTAL=head('Herramientas gratuitas · NORMALIZA, CAUCE, SENDA · El Canal',PORTAL_DESC,ROOT+'/herramientas/')+'''
<main id="contenido" class="layout">
<section class="hero"><p class="kicker">Herramientas gratuitas · El Canal</p><h1>Un problema concreto. Una herramienta que funciona.</h1><p class="lead">Sin registro, publicidad ni suscripciones. Algunas se utilizan aquí mismo y otras puedes descargarlas para adaptarlas a tu trabajo.</p><p class="fine">Elige por lo que necesitas hacer, no por el nombre de la aplicación.</p></section>
<div class="grid" aria-label="Herramientas disponibles">
<article class="tile spotlight"><span class="eyebrow">Usar ahora · En línea</span><h2>¿El formato de tu texto es un desastre?</h2><p><strong>NORMALIZA</strong> quita formatos extraños, espacios repetidos y sangrías no deseadas. Pega desde un PDF, Word, la web o una IA. Revisa el resultado y vuelve a copiarlo.</p><div class="actions"><a class="btn primary" href="/normaliza/">Limpiar un texto</a></div><p class="fine">Todo el procesamiento ocurre en tu navegador. No tienes que subir el documento.</p></article>
<article class="tile"><span class="eyebrow">Consultar ahora · En línea</span><h2>¿Qué exige un procedimiento de contratación?</h2><p><strong>CAUCE</strong> organiza seis procedimientos de la LCSP: requisitos, plazos, documentos, mesa y artículos. Incluye búsqueda y comparador; referencia de consulta para cualquier interesado.</p><div class="actions"><a class="btn primary" href="/contratacion/cauce/">Consultar CAUCE</a><a class="btn" href="/contratacion/">Ver procedimientos</a></div><p class="fine">Contenido de apoyo sujeto a revisión. Fechas de actualización y contraste visibles; comprueba siempre la norma aplicable.</p></article>
<article class="tile"><span class="eyebrow">Descargar · Demostración disponible</span><h2>¿Buscas siempre los mismos recursos?</h2><p><strong>SENDA</strong> crea un único punto de acceso a aplicaciones, enlaces de confianza, documentos, carpetas y recursos de red. El catálogo puede adaptarse a una persona o un equipo.</p><div class="actions"><a class="btn primary" href="/descargas/senda-individual-v0.1.0.zip" download>Descargar SENDA</a><a class="btn" href="/contratacion/senda/">Explorar la demo</a></div><p class="fine">La demo usa recursos de ejemplo. Los accesos locales o de red dependen del navegador y de los permisos del sistema.</p></article>
<article class="tile"><span class="eyebrow">En preparación · No disponible</span><h2>¿Necesitas seguir tus expedientes?</h2><p><strong>PASOS</strong> será una herramienta local y descargable para organizar el seguimiento de expedientes. Aún no se publica ni se ofrece como servicio activo.</p><p class="fine">No es necesaria ninguna inscripción ni lista de espera.</p></article>
</div>
<section class="notice"><h2 style="font-size:1.1rem">Acceso libre y responsabilidad clara</h2><p>Las herramientas son iniciativas independientes de El Canal. No son aplicaciones oficiales de ninguna administración. El uso no requiere una cuenta; consulta los límites y las advertencias propias de cada herramienta.</p></section>
<section style="margin:34px 0 60px"><h2>También puedes llevarte las aplicaciones</h2><p>Además de utilizar CAUCE en línea o explorar SENDA, hay paquetes para utilizarlas sin conexión, sujetos a las posibilidades de tu navegador.</p><div class="actions"><a class="btn" href="/descargas/cauce-individual-v0.1.0.zip" download>CAUCE sin conexión</a><a class="btn" href="/descargas/senda-cauce-paquete-v0.1.0.zip" download>SENDA + CAUCE</a></div><p class="fine">En las descargas se incluye la información de versión y licencia de la edición. PASOS no está incluido.</p></section>
</main>'''+foot
(OUT/'herramientas/index.html').write_text(PORTAL,encoding='utf-8')

# CONTRATACION: from landing for parallel identical tools to complementary use types.
con_path=OUT/'contratacion/index.html'
s=con_path.read_text(encoding='utf-8')
s=s.replace('<span>Contratación pública</span>','<span>Herramientas · <a href="/herramientas/">Todas las herramientas</a></span>')
s=s.replace('<main><h1>SENDA y CAUCE</h1><p class="lede">Dos herramientas gratuitas para quien trabaja con contratación pública en España. Uso gratuito. Sin registro. Sin suscripción. Funcionan en su navegador y no envían sus datos a ningún sitio.</p>',
'''<main><h1>SENDA y CAUCE</h1><p class="lede">Dos soluciones distintas y gratuitas: <strong>CAUCE es una guía de consulta que puedes usar aquí mismo</strong>. <strong>SENDA es una herramienta descargable para organizar los accesos de trabajo de una persona o un equipo</strong>; esta versión web es una demostración con recursos de ejemplo.</p>''')
s=s.replace('<h3><a href="senda/">SENDA · Centro de acceso a recursos</a></h3><p>Un panel para tener en un solo sitio los enlaces que usa cada día: plataformas, sedes, normativa, modelos. Usted los añade, los cambia y los guarda en su propia carpeta.</p>',
'''<p class="tag">APLICACIÓN DESCARGABLE · DEMO EN LÍNEA</p><h3>SENDA · Accesos de confianza en un clic</h3><p>Crea un punto de acceso a tus aplicaciones, documentos, carpetas, sitios web y recursos de red. El catálogo de ejemplo solo permite descubrir cómo funciona. Su utilidad real empieza cuando lo configuras para tus recursos o los de tu equipo.</p><p><a class="cta" href="/descargas/senda-individual-v0.1.0.zip" download>Descargar SENDA</a> <a href="senda/">Explorar demostración</a></p>''')
s=s.replace('<h3><a href="cauce/">CAUCE · Guía de procedimientos de contratación pública</a></h3><p>Los procedimientos de la Ley 9/2017 (LCSP) explicados para entidades locales: plazos, mesa de contratación, documentos y artículos, con búsqueda y comparador.</p>',
'''<p class="tag">HERRAMIENTA EN LÍNEA · CONSULTA DIRECTA</p><h3>CAUCE · Guía de procedimientos de contratación pública</h3><p>Consulta seis procedimientos de la Ley 9/2017 (LCSP): requisitos, plazos, mesa, documentos y artículos. Útil para empleados públicos, empresas, profesionales y estudiantes. Consulta su fecha de revisión y contrasta los preceptos aplicables.</p><p><a class="cta" href="cauce/">Consultar CAUCE</a> <a href="/descargas/cauce-individual-v0.1.0.zip" download>Descargar copia</a></p>''')
s=s.replace('<p class="aviso">Proyecto de El Canal.', '<p><a href="/descargas/senda-cauce-paquete-v0.1.0.zip" download>Descargar SENDA y CAUCE juntas (ZIP)</a> · <a href="/herramientas/">Ver todas las herramientas gratuitas</a></p><p class="aviso">Proyecto de El Canal.')
con_path.write_text(s,encoding='utf-8')

# SENDA: no change to the JS engine or bundled example links.
sp=OUT/'contratacion/senda/index.html'; s=sp.read_text(encoding='utf-8')
banner='''<aside class="senda-public-demo" role="note" aria-label="Demostración de SENDA"><div><strong>DEMOSTRACIÓN INTERACTIVA</strong><p>Estos recursos son ejemplos, no tu catálogo de trabajo. SENDA está pensada para descargarse y configurar accesos web, locales y de red para ti o tu equipo. La demo no es un espacio de almacenamiento permanente.</p></div><div class="senda-public-actions"><a href="/descargas/senda-individual-v0.1.0.zip" download>Descargar SENDA</a><a href="/herramientas/">Todas las herramientas</a></div></aside>'''
css='''<style>.senda-public-demo{padding:14px max(16px,calc((100% - 1220px)/2));background:#fff5da;color:#382b11;border-bottom:2px solid #bf9041;font:15px/1.5 system-ui,sans-serif;display:flex;gap:24px;align-items:center;justify-content:space-between}.senda-public-demo strong{font-size:.8rem;letter-spacing:.11em}.senda-public-demo p{margin:4px 0;max-width:850px}.senda-public-actions{display:flex;gap:9px;flex-wrap:wrap;flex-shrink:0}.senda-public-actions a{display:inline-block;background:#44351a;color:#fff;padding:9px 13px;border-radius:6px;font-weight:700;text-decoration:none}.senda-public-actions a:nth-child(2){background:transparent;color:#44351a;border:1px solid #a98646}@media(max-width:800px){.senda-public-demo{flex-direction:column;align-items:stretch}.senda-public-actions{flex-shrink:1}}</style>'''
s=s.replace('</head>',css+'</head>',1)
s=s.replace('<body>','<body>\n'+banner,1)
s=s.replace('Centro de acceso a recursos · contratación pública','Punto de acceso a recursos · demostración pública',1)
s=s.replace('aria-label="Herramientas de El Canal para contratación pública"','aria-label="Herramientas de El Canal"',1)
sp.write_text(s,encoding='utf-8')

# CAUCE: visible, distinct content revision and legal comparison dates, without claiming verification today.
cp=OUT/'contratacion/cauce/index.html';s=cp.read_text(encoding='utf-8')
s=s.replace('Contraste con el BOE: 15/11/2026 · Importes:', 'Contenidos actualizados: 05/11/2026 · Último contraste normativo documentado: 15/11/2026 · Importes:',1)
s=s.replace('aria-label="Herramientas de El Canal para contratación pública"','aria-label="Herramientas de El Canal"',1)
cp.write_text(s,encoding='utf-8')

# Remove concrete public-employer identifying name while keeping generic statutory idea accurate enough for derived summary.
for p in (OUT/'contratacion').rglob('*.html'):
  s=p.read_text(encoding='utf-8')
  s=re.sub(r'Puede integrarse personal de las [A-Z][a-z]+ en mesas de municipios, mancomunidades y consorcios\.', 'Puede integrarse personal procedente de administraciones provinciales en las mesas de determinados entes locales.', s)
  p.write_text(s,encoding='utf-8')

# NORMALIZA: source code engine lifted from reviewed v0.3, presentation and defaults adapted without network services.
norm_source=Path('/mnt/data/NORMALIZA_DECRETA_v0.3.html').read_text(encoding='utf-8')
script=norm_source[norm_source.find('<script>'):norm_source.rfind('</script>')+len('</script>')]
css_extra='''
.normalize-shell{display:grid;grid-template-columns:minmax(250px,310px) minmax(0,1fr);gap:20px;margin:24px 0 38px;align-items:start}.normalize-shell input,.normalize-shell select,.normalize-shell textarea{background:#f9fafb;color:#1a2223;border:1px solid #95a1a4;border-radius:8px;width:100%;font:inherit;padding:9px}.normalize-shell label{display:block;font-size:.88rem;margin:12px 0 5px;font-weight:600}.normalize-shell .card{background:#f5f5f2;color:#182124;border-radius:15px;padding:19px;border:1px solid #ddd}.normalize-shell h2{font-size:1.2rem}.normalize-shell .row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}.normalize-shell .chk{display:flex;gap:8px;align-items:flex-start;font-weight:400;margin:9px 0}.normalize-shell .chk input{width:auto;margin-top:5px}.normalize-shell details{border-top:1px solid #c5cccb;margin-top:14px;padding-top:10px}.normalize-shell summary{cursor:pointer;font-weight:700}.normalize-shell .btn{color:#222;border:1px solid #aaa;cursor:pointer}.normalize-shell .btn.primary{background:#4a735e;color:#fff;border-color:#4a735e}.normalize-shell .btn:disabled{opacity:.5;cursor:not-allowed}.normalize-shell .bar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:15px 0}.normalize-shell .panel{border:1px solid #a7acaa;background:#f5f5f2;color:#172326;border-radius:12px;padding:20px}.normalize-shell #drop{border:2px dashed #658d7f;text-align:center;border-radius:12px;padding:24px;outline:none;background:#f8faf9;cursor:text}.normalize-shell #drop:focus{border-color:#286850;box-shadow:0 0 0 3px #d5eee0}.normalize-shell #drop strong{display:block;font-size:1.15rem;margin-bottom:8px}.normalize-shell #manualPaste{min-height:94px;resize:vertical;margin-top:11px}.normalize-shell .chips{display:flex;flex-wrap:wrap;gap:6px}.normalize-shell .chip{background:#e6eae6;border-radius:99px;padding:2px 9px;font-size:.79rem}.normalize-shell .warn{background:#fff1d9;padding:9px;color:#5a3910;border-radius:7px;margin-top:6px}.normalize-shell .tabs{display:flex;gap:4px;margin-top:19px}.normalize-shell .tab{border:1px solid #9ba6a3;border-radius:8px 8px 0 0;background:#e4e7e4;color:#1a2927;padding:8px 16px;cursor:pointer}.normalize-shell .tab[aria-selected=true]{background:#315f50;color:#fff}.normalize-shell .view{background:#fff;color:#141414;min-height:170px;max-height:65vh;overflow:auto;padding:20px;border:1px solid #9ba6a3;border-radius:0 9px 9px 9px}.normalize-shell #code{width:100%;min-height:180px;max-height:65vh;resize:vertical;background:#fff;color:#121212;border-radius:0 9px 9px 9px;font:12px/1.4 ui-monospace,monospace;padding:15px}.normalize-shell #toast{position:fixed;z-index:60;bottom:20px;left:50%;transform:translateX(-50%);background:#111;color:#fff;padding:10px 18px;border-radius:9px;opacity:0;pointer-events:none;transition:opacity .2s}.normalize-shell #toast.show{opacity:1}.normalize-shell #clear{color:#172b25}.normalize-shell .note{font-size:.86rem;color:#495552}.normalize-shell .stepper{color:#454f4a;font-size:.9rem}
@media(max-width:850px){.normalize-shell{grid-template-columns:1fr}.normalize-shell .panel{padding:14px}}
@media(prefers-reduced-motion:reduce){.normalize-shell #toast{transition:none}}
'''
CSP="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'"
extra='<meta http-equiv="Content-Security-Policy" content="'+escape(CSP,quote=True)+'">'
normal=head('NORMALIZA · Limpiar texto copiado en línea gratis · El Canal','Pega textos de Word, PDF, páginas web, ChatGPT o Claude y elimina formatos extraños, espacios dobles y sangrías. Normaliza en tu navegador sin subir documentos.',ROOT+'/normaliza/',extra=extra)
normal=normal.replace('</style></head>',css_extra+'</style></head>')
normal+='''
<main id="contenido" class="layout">
<section class="hero" style="padding-bottom:5px"><p class="kicker">Herramienta en línea · El Canal</p><h1>NORMALIZA</h1><p class="lead">Tu texto, limpio y con un formato uniforme. <strong>Pega, revisa y copia.</strong> Así de sencillo.</p><p>Útil para textos de Word, PDF, páginas web y asistentes de IA. No reescribe las ideas; modifica la presentación y puede omitir elementos no textuales.</p><span class="pill">Gratuita · Sin registro · Procesamiento en tu navegador</span></section>
<section class="normalize-shell" aria-label="Normalizador de texto">
<aside class="card" aria-label="Configuración del formato"><h2>Cómo quieres el texto</h2>
<label for="preset">Tipo de resultado</label><select id="preset"><option value="general" selected>Limpieza general (recomendado)</option><option value="documento">Documento uniforme</option><option value="decreta">Compatible con Decret@</option><option value="personalizado">Personalizado</option></select><p class="note">Decret@ es solo un ajuste opcional, no hace falta utilizar esa aplicación.</p>
<details id="advanced"><summary>Personalizar formato</summary>
<label for="font">Fuente</label><select id="font"><option>Arial</option><option>Times New Roman</option><option>Verdana</option><option>Tahoma</option><option>Courier New</option><option>Comic Sans MS</option><option>Gill Sans MT</option></select>
<div class="row2"><div><label for="size">Tamaño (pt)</label><select id="size"><option>8</option><option>10</option><option selected>12</option><option>14</option><option>16</option><option>18</option><option>20</option><option>22</option><option>24</option></select></div><div><label for="lh">Interlineado</label><select id="lh"><option value="1">Sencillo</option><option value="1.15">1,15</option><option value="1.5" selected>1,5</option><option value="2">Doble</option></select></div></div>
<div class="row2"><div><label for="align">Alineación</label><select id="align"><option value="left" selected>Izquierda</option><option value="justify">Justificado</option></select></div><div><label for="indent">Sangría 1.ª línea (cm)</label><input id="indent" type="number" min="0" max="5" step="0.25" value="0"></div></div>
<div class="row2"><div><label for="mb">Espacio tras párrafo (pt)</label><input id="mb" type="number" min="0" max="48" step="1" value="0"></div><div><label for="tsize">Tamaño de tablas (pt)</label><select id="tsize"><option>8</option><option>10</option><option selected>11</option><option>12</option><option>14</option></select></div></div>
<label class="chk"><input id="respect" type="checkbox" checked> Respetar textos centrados o a la derecha</label>
<label class="chk"><input id="dropEmpty" type="checkbox" checked> Eliminar párrafos vacíos</label>
<label class="chk"><input id="nbsp" type="checkbox" checked> Normalizar espacios dobles y espacios inseparables</label>
<label class="chk"><input id="colors" type="checkbox"> Conservar colores</label>
<label class="chk"><input id="keepML" type="checkbox"> Conservar sangrías izquierda</label>
<label class="chk"><input id="keepMerge" type="checkbox" checked> Mantener celdas combinadas en tablas</label>
<label for="widths">Anchos de tabla</label><select id="widths"><option value="prop" selected>Proporcionales</option><option value="equal">Iguales</option><option value="auto">Automáticos</option></select>
<label class="chk"><input id="trailP" type="checkbox"> Añadir un párrafo si termina con tabla</label>
</details>
<div class="actions"><button class="btn" id="reset" type="button">Restablecer</button></div>
<p class="note">El texto no se envía a un servidor. Se guarda únicamente la preferencia de formato en este navegador.</p>
</aside>
<div class="panel"><h2 style="margin-top:0">Pega aquí el texto</h2>
<div id="drop" tabindex="0" role="textbox" aria-label="Zona donde pegar el texto" aria-multiline="true"><strong>Haz clic y pega con Ctrl+V</strong><span id="dropMsg">Pega un fragmento desde un documento o página web. También puedes usar el cuadro inferior, incluso desde un móvil.</span></div>
<label for="manualPaste">O escribe / pega directamente aquí</label><textarea id="manualPaste" rows="4" placeholder="Tu texto aparece aquí al pegarlo..."></textarea>
<div class="bar"><button id="copy" class="btn primary" type="button" disabled>Copiar con formato uniforme</button><button id="copyPlain" class="btn" type="button" disabled>Copiar texto limpio</button><button id="clear" class="btn" type="button" disabled>Limpiar</button><button id="tryExample" class="btn" type="button">Probar con ejemplo</button></div>
<div id="chips" class="chips" role="status" aria-live="polite"></div><div id="warns" aria-live="polite"></div>
<div class="tabs" role="tablist" aria-label="Resultado"><button class="tab" id="tabPrev" role="tab" aria-selected="true" type="button">Vista previa</button><button class="tab" id="tabCode" role="tab" aria-selected="false" type="button">Código HTML</button></div>
<div id="preview" class="view" role="tabpanel"><span>El resultado aparecerá aquí.</span></div><textarea id="code" aria-label="Código HTML normalizado" readonly hidden spellcheck="false"></textarea>
<p class="note">Revisa siempre tablas, listas, imágenes y expresiones especiales antes de usar el resultado. Las imágenes se omiten y ciertos formatos pueden cambiar.</p>
<div id="toast" role="status" aria-live="polite"></div>
</div>
</section>
<section class="notice" style="margin-bottom:55px"><h2 style="font-size:1.2rem">¿También sirve para Decret@?</h2><p>Sí. Selecciona el ajuste «Compatible con Decret@» si necesitas pegar el resultado en ese editor. Es una compatibilidad orientativa basada en las pruebas disponibles, no una garantía para todas las versiones o documentos.</p><p class="fine">Herramienta independiente, sin relación institucional ni soporte oficial. Autor: Manuel Barrera Anglada · <a href="https://orcid.org/0009-0000-8891-7021">ORCID</a> · <a href="LICENSE.txt">Licencia MIT</a>.</p></section>
</main>'''

# Adapt original proven normalization engine and copy path with explicit copy-plain, preset and mobile input.
script=script.replace("var DEFAULTS = {font:'Arial', size:'12', lh:'1.5', align:'justify', indent:'1', mb:'6', tsize:'11',", "var DEFAULTS = {font:'Arial', size:'12', lh:'1.5', align:'left', indent:'0', mb:'0', tsize:'11',")
script=script.replace("localStorage.setItem('decreta-norm-cfg'", "localStorage.setItem('elcanal-normaliza-config-v1'")
script=script.replace("localStorage.getItem('decreta-norm-cfg'", "localStorage.getItem('elcanal-normaliza-config-v1'")
script=script.replace("$('copy').disabled = !has; $('clear').disabled = !has;", "$('copy').disabled = !has; $('copyPlain').disabled = !has; $('clear').disabled = !has;")
script=script.replace("toast(ok ? 'Copiado. Ahora pega con Ctrl+V en el editor de Decret@' : 'No se pudo copiar. Selecciona la vista previa y pulsa Ctrl+C');", "toast(ok ? 'Copiado con formato. Pégalo donde lo necesites.' : 'No se pudo copiar. Selecciona la vista previa y pulsa Ctrl+C');")
script=script.replace("$('copy').disabled = true; $('clear').disabled = true;", "$('copy').disabled = true; $('copyPlain').disabled = true; $('clear').disabled = true;")
script=script.replace("$('dropMsg').textContent = 'Texto con formato de Word, LibreOffice u OpenOffice, incluidas las tablas.';", "$('dropMsg').textContent = 'Pega texto de cualquier aplicación, documento o página web.';")
script=script.replace("$('manualPaste').value = '';", "$('manualPaste').value = '';")
# Insert functions before loadCfg call, give paste-input precedence and avoid deleting copy effects.
insert='''
var PRESETS = {
 general:{font:'Arial',size:'12',lh:'1.5',align:'left',indent:'0',mb:'0',tsize:'11',respect:true,dropEmpty:true,nbsp:true,colors:false,keepML:false,keepMerge:true,widths:'prop',trailP:false},
 documento:{font:'Arial',size:'12',lh:'1.5',align:'justify',indent:'0',mb:'6',tsize:'11',respect:true,dropEmpty:true,nbsp:true,colors:false,keepML:false,keepMerge:true,widths:'prop',trailP:false},
 decreta:{font:'Arial',size:'12',lh:'1.5',align:'justify',indent:'1',mb:'6',tsize:'11',respect:true,dropEmpty:true,nbsp:true,colors:false,keepML:false,keepMerge:true,widths:'prop',trailP:false}
};
function pasteAsPlain(text){ state.raw='';state.text=String(text||'');$('dropMsg').textContent='Contenido recibido; revisa el resultado.';render(); }
$('manualPaste').addEventListener('input',function(){pasteAsPlain(this.value)});
$('preset').addEventListener('change',function(){
 var p=this.value;
 if(PRESETS[p]){applyCfg(PRESETS[p]);saveCfg();render();}
 if(p==='personalizado')$('advanced').open=true;
});
$('copyPlain').addEventListener('click',async function(){
 if(!state.plain)return;
 var ok=false;
 try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(state.plain);ok=true}}catch(e){}
 if(!ok){try{
 var t=document.createElement('textarea');t.value=state.plain;t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);t.select();ok=document.execCommand('copy');t.remove();
 }catch(e){}}
 toast(ok?'Texto limpio copiado.':'No se pudo copiar automáticamente; selecciona el resultado.');
});
$('tryExample').addEventListener('click',function(){
 var ex='Texto   copiado  con     espacios   repetidos.\\nOtra línea    con   formato inconsistente.\\n\\nUn tercer párrafo que necesita unificación.';
 $('manualPaste').value=ex;pasteAsPlain(ex);$('manualPaste').focus();
});
$('reset').addEventListener('click',function(){ $('preset').value='general'; });
$('clear').addEventListener('click',function(){ $('manualPaste').value=''; });
var cfgStart={}; try{cfgStart=JSON.parse(localStorage.getItem('elcanal-normaliza-config-v1')||'{}')}catch(e){}
if(!Object.keys(cfgStart).length) $('preset').value='general';else $('preset').value='personalizado';
'''
script=script.replace("loadCfg();\n$('drop').focus();", "loadCfg();\n"+insert+"\n$('drop').focus();")
# NOTE: legacy script registers reset and clear handlers prior to additional listeners; post-handlers correct extra state.
normal+=script+foot
np=OUT/'normaliza/index.html';np.write_text(normal,encoding='utf-8')

# Offline standalone normalizer: same byte content except canonical absolute links; source is self-contained.
(DIST/'NORMALIZA_v1.0.0.html').write_text(normal,encoding='utf-8')

# Repackage v0.2.0 offline distributions with the same engine and a strict neutral-public check.
# Always refresh internal SHA256SUMS when a byte is changed.
def distribute_offline(srcfilename,dstfilename):
    with zipfile.ZipFile(Path('/mnt/data')/srcfilename) as z:
        items={name:z.read(name) for name in z.namelist() if not name.endswith('/')}
    fixed={}
    for name,bytes_ in items.items():
        if name=='SHA256SUMS.txt':continue
        if name.lower().endswith(('.html','.md','.txt','.json')):
            txt=bytes_.decode('utf-8')
            txt=re.sub(r'Puede integrarse personal de las [A-Z][a-z]+ en mesas de municipios, mancomunidades y consorcios\.',
                       'Puede integrarse personal procedente de administraciones provinciales en las mesas de determinados entes locales.',txt)
            txt=txt.replace('v0.1.0','v0.2.0').replace('Versión 0.1.0','Versión 0.2.0')
            if name=='VERSION.txt':txt=txt.replace('2026-11-15','2026-11-16')
            if name=='CHANGELOG.md':txt+='\n## v0.2.0 · 2026-11-16\nEdición pública neutral y accesos de distribución; sin cambios sustantivos en el motor.\n'
            fixed[name]=txt.encode('utf-8')
        else:fixed[name]=bytes_
    if 'LICENSE' not in fixed: fixed['LICENSE']=(HERE/'source/LICENSE').read_bytes()
    fixed['SHA256SUMS.txt']=('\n'.join(hashlib.sha256(content).hexdigest()+'  '+name for name,content in sorted(fixed.items()))+'\n').encode('utf-8')
    dest=OUT/'descargas'/dstfilename
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for name,blob in sorted(fixed.items()):z.writestr(name,blob)
    return dest

for src,dst in [('senda-individual-v0.1.0.zip','senda-individual-v0.2.0.zip'),('cauce-individual-v0.1.0.zip','cauce-individual-v0.2.0.zip'),('senda-cauce-paquete-v0.1.0.zip','senda-cauce-paquete-v0.2.0.zip')]:
    distribute_offline(src,dst)

# Web labels are for the revised candidate, the normative dates remain those actually recorded.
for p in (OUT/'contratacion').rglob('*.html'):
    t=p.read_text(encoding='utf-8').replace('v0.1.0','v0.2.0').replace('versión 0.1.0','versión 0.2.0')
    p.write_text(t,encoding='utf-8')
for p in [OUT/'herramientas/index.html',OUT/'index.html']:
    t=p.read_text(encoding='utf-8').replace('v0.1.0.zip','v0.2.0.zip')
    p.write_text(t,encoding='utf-8')
# Root link and an editorial callout: never replace existing content.
rootp=OUT/'index.html';s=rootp.read_text(encoding='utf-8')
needle='<a href="legal.html" class="nav-link">Legal</a>'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n        <a href="herramientas/" class="nav-link" style="font-weight:700">Herramientas gratuitas</a>')
marker='    <div class="operador">'
assert s.count(marker)==1
callout='''<section aria-label="Herramientas gratuitas" style="margin:0 0 2.5rem;padding:1.4rem 1.7rem;border:1px solid var(--rule);background:var(--surface)"><p style="font-family:var(--mono);font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-mid);margin:0 0 .7rem">Herramientas gratuitas · Uso abierto</p><h2 style="font-family:var(--serif);font-size:1.35rem;font-weight:400;margin:0 0 .5rem">Soluciones sencillas para problemas cotidianos</h2><p style="font-size:.9rem;line-height:1.7">Limpiar el formato de un texto con <a href="normaliza/">NORMALIZA</a>, consultar contratación pública con <a href="contratacion/cauce/">CAUCE</a> o descargar <a href="descargas/senda-individual-v0.2.0.zip">SENDA</a> para organizar accesos de trabajo. Sin registro ni suscripción.</p><a href="herramientas/" style="font-family:var(--mono);font-size:.85rem;font-weight:700">Explorar todas las herramientas →</a></section>\n\n'''
s=s.replace(marker,callout+marker)
# v0.2.1: estilo propio para los enlaces del recuadro (sin esto salen con el azul del navegador)
LINKCSS='<style id="herramientas-links">section[aria-label="Herramientas gratuitas"] a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink-mid);padding-bottom:1px;transition:color .15s,border-color .15s}section[aria-label="Herramientas gratuitas"] a:hover,section[aria-label="Herramientas gratuitas"] a:focus-visible{color:var(--ink-light);border-bottom-color:var(--ink-light)}section[aria-label="Herramientas gratuitas"] a:focus-visible{outline:1px solid var(--ink-mid);outline-offset:3px}section[aria-label="Herramientas gratuitas"] a[href="herramientas/"]{border-bottom:none;letter-spacing:.04em}</style>\n'
assert s.count('</head>')==1
s=s.replace('</head>',LINKCSS+'</head>')
rootp.write_text(s,encoding='utf-8')

# Fix absent favicons for new pages while preserving original favicon.svg as byte-identical.
for f in ['favicon.ico','apple-touch-icon.png','favicon-16x16.png','favicon-32x32.png']:
    shutil.copy2(WEB/f,OUT/f)

# Sitemap: add new canonical pages but preserve existing entries.
sm=OUT/'sitemap.xml';s=sm.read_text(encoding='utf-8')
new_urls=[('/herramientas/','0.9','weekly'),('/normaliza/','0.9','monthly'),('/contratacion/','0.8','monthly'),('/contratacion/senda/','0.7','monthly'),('/contratacion/cauce/','0.9','monthly')]
new_urls += [(f'/contratacion/cauce/procedimientos/{x}/','0.7','monthly') for x in ['contrato-menor','procedimiento-abierto-ordinario','procedimiento-abierto-simplificado','procedimiento-simplificado-abreviado','procedimiento-restringido','procedimiento-negociado-sin-publicidad']]
block='\n'.join(f'  <url><loc>{ROOT}{p}</loc><lastmod>{DATE}</lastmod><changefreq>{freq}</changefreq><priority>{pri}</priority></url>' for p,pri,freq in new_urls)
assert '</urlset>' in s
s=s.replace('</urlset>',block+'\n</urlset>')
sm.write_text(s,encoding='utf-8')

# PREVIEW copies use root _headers; PRODUCTION zip MUST NEVER include a noindex header.
NOINDEX='/*\n  X-Robots-Tag: noindex, nofollow\n'

# Review bundle: instructions and integrity.
report=HERE/'INFORME_EJECUCION_v0.2.0.md'
report.write_text('''# El Canal · Herramientas gratuitas · Release candidata 0.2.0

Fecha: 16-11-2026. Preparada localmente por ChatGPT, a partir de los archivos facilitados por el autor y el release público limpio v0.1.0.

## Objetivo

Publicar cuatro puertas claramente distintas: NORMALIZA (utilización online directa), CAUCE (consulta online con fecha de mantenimiento), SENDA (descarga + demo), PASOS (anuncio no activo).

## Cambios implementados

- Nueva página `/herramientas/` con cuatro puertas orientadas a problemas reales.
- Nueva aplicación `/normaliza/` basada en NORMALIZA_DECRETA_v0.3, con presentación universal, tres perfiles, entrada móvil y dos copias (texto limpio y formato uniforme).
- SENDA: banner inequívoco de demo y botón de descarga. Se conserva su motor y catálogo de ejemplo.
- CAUCE: fechas diferenciadas de última revisión del contenido (05/11/2026) y contraste BOE (15/11/2026), derivadas del código original. No se da a entender que toda la ley esté exhaustivamente contrastada.
- Página de Contratación revisada para diferenciar demostración y consulta real y ofrecer los tres ZIP oficiales originales.
- Acceso visible en el inicio español de El Canal sin reemplazar ni eliminar sus contenidos existentes.
- Iconos raíz añadidos; sitemap ampliado; avisos, accesibilidad y metadatos de nuevas páginas.
- PASOS no se publica.

## Control editorial y jurídico

- No se ha incorporado código corporativo: la web procede de distribuciones públicas limpias.
- Ningún contenido nuevo identifica al empleador o servicios internos.
- CAUCE no es instrucción oficial ni asesoramiento jurídico. Su contenido necesita control periódico del BOE.
- SENDA no garantiza la apertura de enlaces locales desde HTTPS ni que todos los documentos se abran en solo lectura; depende del navegador y permisos.
- NORMALIZA procesa en navegador, sin API ni conexión declarada. No conserva imágenes del texto original y puede transformar tablas y listas.
- NORMALIZA mantiene compatibilidad orientativa con el editor mencionado, no oficialmente certificada.

## Dependencias para lanzamiento efectivo

1. Desplegar `ELCANAL_PREVIEW_HERRAMIENTAS_v0.2.0.zip` como PREVIEW en Cloudflare Pages, en rama distinta a producción; verificar que no toca `elcanal.es`.
2. Pruebas visuales y funcionales en el dominio Preview (Windows/Edge especialmente para SENDA, móvil para NORMALIZA).
3. Contrastar fuentes de CAUCE con normativa vigente antes de declarar edición estable.
4. Crear repositorio público para código fuente en GitHub; por ahora la fuente local está empaquetada.
5. Desplegar el ZIP de producción SIN `_headers` de noindex solo una vez contrastado el estado actual de la web y con copia de seguridad reciente.

La creación de archivos no constituye un despliegue público. La autorización de lanzar es del autor; la verificación del medio y del destino sigue siendo obligatoria.
''',encoding='utf-8')

# Source provenance: copy explicit clean source and new script, excluding original old candidate corporate code.
shutil.copy2(HERE/'source/README.md',DIST/'README_ORIGEN_SENDA_CAUCE.md')
shutil.copy2(HERE/'source/LICENSE',DIST/'LICENSE_SENDA_CAUCE')
shutil.copy2(Path('/mnt/data/NORMALIZA_DECRETA_v0.3.html'),DIST/'ORIGEN_NORMALIZA_DECRETA_v0.3.html')
shutil.copy2(Path(__file__),DIST/'build_release_v020.py')
shutil.copy2(report,DIST/'INFORME_EJECUCION_v0.2.0.md')

# Build archive preserving site tree and manifest.
def zipdir(dest,work):
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
      for p in sorted(work.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(work).as_posix())

zipdir(Path('/mnt/data/ELCANAL_PRODUCCION_HERRAMIENTAS_v0.2.0.zip'),OUT)
preview=HERE/'release_preview'
if preview.exists():shutil.rmtree(preview)
shutil.copytree(OUT,preview)
(preview/'_headers').write_text(NOINDEX,encoding='utf-8')
zipdir(Path('/mnt/data/ELCANAL_PREVIEW_HERRAMIENTAS_v0.2.0.zip'),preview)

# Separate source project (public clean source v0.1.0 + new standalone app, patch recipe, report)
source_dist=HERE/'release_fuente'
if source_dist.exists():shutil.rmtree(source_dist)
shutil.copytree(HERE/'source',source_dist)
(source_dist/'normaliza').mkdir()
shutil.copy2(DIST/'NORMALIZA_v1.0.0.html',source_dist/'normaliza/index.html')
# Remove even generic province-body mentions from the distributable source. Keep legal context in neutral terms.
source_json=source_dist/'fuente/cauce/datos.json'
raw=source_json.read_text(encoding='utf-8')
raw=re.sub(r'Puede integrarse personal de las [A-Z][a-z]+ en mesas de municipios, mancomunidades y consorcios\.', 'Puede integrarse personal procedente de administraciones provinciales en las mesas de determinados entes locales.',raw)
source_json.write_text(raw,encoding='utf-8')
(source_dist/'integration').mkdir()
shutil.copy2(Path(__file__),source_dist/'integration/build_release_v020.py')
(source_dist/'integration'/'README.md').write_text('''# Edición 0.2.0 · Integración de herramientas

Para reconstruir el paquete web de esta edición, es necesario disponer de las distribuciones públicas v0.1.0 y una copia exacta del sitio existente, que no se incluye aquí. `integration/build_release_v020.py` contiene las modificaciones de presentación reproducibles cuando se ubica en el directorio de trabajo indicado en el informe. No incluye código ni datos institucionales.

La copia autónoma `normaliza/index.html` puede usarse independientemente.
''',encoding='utf-8')
zipdir(Path('/mnt/data/ELCANAL_FUENTE_PUBLICA_HERRAMIENTAS_v0.2.0.zip'),source_dist)

# SHA manifest in /mnt/data with final package hashes.
files=[p for p in Path('/mnt/data').glob('*v0.2.0.zip') if p.is_file()]+[DIST/'NORMALIZA_v1.0.0.html']
lines=[f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in sorted(files,key=lambda x:x.name)]
(Path('/mnt/data')/'SHA256SUMS_HERRAMIENTAS_v0.2.0.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('CREATED')
for p in files:print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
print('total files prod',len([p for p in OUT.rglob('*') if p.is_file()]))

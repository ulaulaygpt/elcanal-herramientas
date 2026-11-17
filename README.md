# SENDA y CAUCE · El Canal

Dos herramientas **gratuitas y de código abierto (MIT)** para quien trabaja con contratación pública en España. Funcionan en el navegador, sin cuentas, publicidad ni analítica, y sin enviar datos a ningún servidor.

- **SENDA** · centro de acceso a recursos: sus enlaces (plataformas, sedes, normativa, modelos) en un solo sitio, editables y guardados en su propia carpeta.
- **CAUCE** · guía de procedimientos de contratación pública (Ley 9/2017, LCSP) para entidades locales: plazos, mesa, documentos y artículos, con búsqueda y comparador.

> Proyecto de El Canal (https://elcanal.es/). **No son herramientas oficiales** de ninguna administración. CAUCE **no es asesoramiento jurídico**; lo marcado «pendiente de validación jurídica» no ha sido validado. Véase [AVISO_LEGAL.md](AVISO_LEGAL.md).

## Uso
Descargue una distribución de la sección *Releases* y abra el HTML con su navegador:
`senda-individual`, `cauce-individual`, `senda-cauce-paquete` (ambas enlazadas) o `web` (estructura para publicar en `/contratacion/`). Cada una incluye `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt`).

Guardar enlaces en una carpeta requiere Chrome o Edge de escritorio; ver [compatibilidad](docs/COMPATIBILIDAD_NAVEGADORES.md).

## Reproducir las distribuciones
Requisitos: Python 3.10+, Pillow y Playwright con Chromium (solo para identidad y pruebas).
```
python3 fuente/identidad/make_identidad.py dist/_identidad   # iconos e imágenes sociales
python3 build.py                                             # genera dist/
python3 tests/run_tests.py                                   # 177 pruebas automáticas
```
Estructura: `fuente/senda` (plantilla + catálogo de ejemplo), `fuente/cauce` (plantilla + `datos.json`), `fuente/identidad`, `build.py`, `tests/`, `docs/`.

## Contenido jurídico de CAUCE
El contenido se mantiene en `fuente/cauce/datos.json`. Los preceptos contrastados con el BOE (15/11/2026) son los arts. 20, 21, 22, 159 y 326 y las disposiciones adicionales 2ª y 3ª; el resto figura como pendiente de contraste. Las correcciones son bienvenidas mediante *issues*, citando el precepto y la fuente.

## Autoría y licencia
Manuel Barrera Anglada · ORCID [0009-0000-8891-7021](https://orcid.org/0009-0000-8891-7021). Desarrollado con asistencia de IA (Claude y ChatGPT); la dirección, las decisiones y la responsabilidad son humanas. Licencia [MIT](LICENSE).

# Compatibilidad de navegadores · v0.1.0

| Función | Chrome / Edge (escritorio) | Firefox / Safari |
|---|---|---|
| Consultar SENDA (enlaces, búsqueda, ayuda) | Sí | Sí |
| Guardar enlaces propios en una carpeta (`recursos.json`) | **Sí** (File System Access API) | **No** (el navegador no ofrece selector de carpeta) |
| Exportar / importar copia de seguridad de SENDA | Sí | Sí (alternativa a la carpeta) |
| CAUCE completo (fichas, búsqueda, comparador, enlaces profundos) | Sí | Sí |
| Páginas estáticas por procedimiento | Sí | Sí |
| Uso sin conexión (archivos locales / paquete) | Sí | Sí |

## Estado de las pruebas
- **Automáticas** (Playwright, Chromium headless): 177 pruebas, todas correctas (`python3 tests/run_tests.py`).
- **Firefox** (Playwright, motor Gecko): 37 comprobaciones correctas en la edición candidata anterior; el guion no forma parte de este repositorio y no se ha repetido sobre v0.1.0.
- **No comprobado**: Microsoft Edge real, Safari, lectores de pantalla, HTTPS real en producción, permisos persistentes de carpeta en navegadores reales. Las pruebas automáticas no los sustituyen.

## Notas
- Abierto desde un archivo local (`file://`), Chrome/Edge pueden pedir de nuevo el permiso de la carpeta en cada sesión; desde la edición web algunos navegadores permiten recordarlo.
- En navegadores sin selector de carpeta, SENDA muestra un mensaje claro y mantiene la exportación/importación de copias.

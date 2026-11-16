# Centro de control EPP · Streamlit + Google Sheets (V5)

**Cambios:** no se modifica n8n ni se reentrenan los modelos. Solo se conecta la pestaña de Inspecciones directamente con la hoja donde n8n escribe sus resultados. Pronósticos y Transformer siguen mostrando CSV de experimentos sintéticos.

## Instalación rápida con hoja compartida en modo lectura

> IMPORTANTE: esta ruta es sencilla, pero permite que cualquier persona con el enlace pueda leer **toda la hoja de cálculo compartida**, no solamente las columnas visibles en Streamlit. No la utilices con correos, identidades o datos sensibles sin autorización. Si prefieres mantener la hoja privada, consulta la sección siguiente.

1. Abre la hoja **Historial de Inspecciones EPP - Certamen 2**, la misma que usa el nodo `Registrar inspección en Sheets` de n8n. Confirma que su primera pestaña sea **Inspecciones** (gid `0`).
2. Haz clic en **Compartir → Acceso general → Cualquier persona con el enlace → Lector**. Copia la dirección del documento.
3. En **Streamlit Community Cloud**, entra a tu aplicación → **Manage app → Settings → Secrets**. Agrega (reemplaza `PEGA_AQUI_URL` por el enlace completo):

```toml
[connections.gsheets]
spreadsheet = "PEGA_AQUI_URL"
```

4. En GitHub reemplaza solo `app.py`, `requirements.txt` y este `README.md`. Mantén la carpeta `data/` con los tres CSV como respaldo. No subas ningún `secrets.toml` real a GitHub.
5. Comprueba que la barra lateral indique **Google Sheets (directo)**. Envía una inspección de prueba de `zona_2` desde el formulario n8n; comprueba que aparezca en la pestaña de Operación (usa **Actualizar datos ahora** si necesitas ver la prueba inmediatamente).

**Actualización:** mientras el tablero está abierto, se recarga cada cinco minutos y consulta la hoja con una caché de cuatro minutos. No se rehace la predicción ni la clasificación de textos automáticamente.

**Si algo falla**, no se rompe la demostración: Streamlit usa `data/inspecciones.csv` y muestra **CSV de respaldo** en la barra lateral. Ten en cuenta que este respaldo fue elaborado a partir de datos anteriores y puede tener transformaciones que no estén verificadas contra la hoja original.

## Alternativa: mantener Google Sheets privada

Streamlit soporta una cuenta de servicio de Google Cloud sin publicar la hoja. Activa Google Sheets API en tu proyecto de Google Cloud, crea una cuenta de servicio de solo lectura, comparte la hoja con el correo de esa cuenta como **Lector**, y copia los campos de la clave JSON (incluido `private_key`) en **Secrets** bajo `[connections.gsheets]`, junto con `spreadsheet` (URL). No subas la clave al repositorio. El código de `app.py` funciona con ambos métodos. Revisa la guía oficial: https://docs.streamlit.io/develop/tutorials/databases/private-gsheet

## Estructura del repositorio

```text
app.py
requirements.txt
README.md
data/
  inspecciones.csv
  pronosticos.csv
  transformer.csv
```

## Precisión de resultados

- El contenido de la pestaña **Inspecciones** se consulta directamente desde Google Sheets; la aplicación no inventa `zona_id` ni supone qué zona corresponde a textos antiguos.
- Si el historial viejo carece de `zona_id`, aparece **Histórico sin zona homologada**. Para reclasificarlo debe verificarse el origen en la hoja original.
- La suma de trabajadores detectados cuenta observaciones de inspecciones, no necesariamente personas únicas.
- Las revisiones potenciales **no son infracciones confirmadas**.
- Pronósticos (LSTM / Holt-Winters) y Transformer son **resultados académicos simulados**, con sus CSV ya generados. Solo cambian si vuelves a generar y sustituir esos archivos.
- El dashboard no valida ni cierra las revisiones humanas pendientes; el control definitivo debe realizarlo el supervisor.


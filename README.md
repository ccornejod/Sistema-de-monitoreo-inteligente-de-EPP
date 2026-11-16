# Centro de Supervisión EPP · Dashboard Streamlit

Dashboard académico basado en los resultados guardados en Google Sheets por el sistema n8n.

## Archivos

- `app.py`: aplicación Streamlit, usa Pandas y Plotly Express.
- `requirements.txt`: dependencias para Streamlit Community Cloud.
- `data/inspecciones.csv`: 44 inspecciones de prueba, con nombres de supervisores (sin correos, chats, imágenes ni credenciales).
- `data/pronosticos.csv`: 60 filas de pronósticos de prueba LSTM / Holt-Winters.
- `data/transformer.csv`: 220 clasificaciones de texto simuladas.

## Actualizar en GitHub

En tu repositorio existente, reemplaza `app.py` y `data/inspecciones.csv` con los incluidos aquí. `requirements.txt`, `data/pronosticos.csv` y `data/transformer.csv` no cambiaron; no necesitas volver a subirlos si ya están publicados. Streamlit Community Cloud suele detectar automáticamente el nuevo commit.

## Seguridad y alcance

El sitio público mostrará los nombres de los supervisores. Confirma que puedan aparecer en un dashboard publicado antes de compartir la URL; si no, conserva la versión anonimizada. No se publican datos de correos, imágenes, Telegram ni claves API.

Este dashboard usa una instantánea de las hojas de Google Sheets, no datos en vivo. Para actualizar, sube nuevos CSV a GitHub o utiliza el cargador temporal del menú lateral. Para la hoja Inspecciones, acepta tanto el CSV procesado incluido en este ZIP como las columnas habituales de la hoja n8n.

Todos los datos pertenecen a una demostración académica. Las predicciones y clasificaciones son simuladas y los resultados de imágenes requieren validación humana.

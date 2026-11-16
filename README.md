# Centro de Supervisión EPP · Dashboard Streamlit

Tablero académico de monitoreo de EPP con una **instantánea de tres hojas de Google Sheets** utilizadas por el sistema n8n. **No consulta datos en tiempo real**, no ejecuta los modelos desde Streamlit y no requiere claves API.

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

- `app.py`: aplicación Streamlit con pandas y Plotly.
- `requirements.txt`: dependencias de Streamlit Community Cloud.
- `data/inspecciones.csv`: **44 registros** de inspecciones de prueba, con los nombres tal como figuran en la fuente; sin correos, chats ni imágenes.
- `data/pronosticos.csv`: **60 registros** de pronósticos de prueba (LSTM, zona 1; Holt-Winters, zona 2).
- `data/transformer.csv`: **220 clasificaciones** de textos de ejemplo simulados.

## Publicar o actualizar en GitHub

1. Copia `app.py`, `requirements.txt` y `README.md` a la raíz de tu repositorio.
2. Dentro de la carpeta **`data/`**, ubica los CSV con sus nombres exactos: `inspecciones.csv`, `pronosticos.csv` y `transformer.csv` (sin `(1)` ni otros sufijos).
3. Confirma los cambios (*Commit changes*). Si tu aplicación está vinculada a Streamlit Community Cloud, el servicio normalmente reconstruye la app después del commit.
4. Abre la URL publicada y comprueba las cuatro pestañas: Operación, Pronósticos, Transformer y Gemini.

**Actualización:** los archivos CSV solo cambian cuando los reemplazas en GitHub. El tablero **no tiene un cargador de archivos desde el navegador**. Para ver nuevos registros de n8n, primero debes exportar una nueva instantánea de las hojas y actualizar los CSV del repositorio.

## Cómo interpretar los resultados

- Las inspecciones anteriores sin `zona_id` homologado permanecen como **«Histórico sin zona homologada»**; no se asignan a Zona 1 o Zona 2 por su descripción. En esta instantánea son **43 de 44** registros; el restante corresponde a Zona 1.
- Los nombres de los supervisores se muestran tal cual aparecen en el CSV; el código **no asigna alias** del tipo «Supervisor A» a personas específicas.
- **«Revisiones potenciales»** es la suma, por inspección, de trabajadores para quienes YOLO no confirmó visualmente algún EPP requerido. No es el número de equipos faltantes, de infracciones confirmadas ni necesariamente de personas distintas.
- La sección Pronósticos muestra inicialmente **el día siguiente según la zona horaria America/Santiago** si hay datos; de lo contrario selecciona el siguiente día disponible o, si no hay futuros, la última fecha registrada. El usuario puede elegir cualquier fecha disponible.
- LSTM y Holt-Winters se aplican a zonas distintas: sus valores **no permiten** comparar directamente riesgo entre zonas.
- Los pronósticos y las clasificaciones de texto utilizan **datos simulados**. Las clasificaciones Transformer no indican incidentes reales de la jornada.
- El historial de Gemini muestra recomendaciones registradas en las inspecciones. Toda decisión operativa requiere **revisión humana**; el estado «pendiente» no equivale a una aprobación o verificación final.
- **Advertencia sobre identificadores:** el CSV de inspecciones contiene 44 filas, pero solo 33 valores distintos de `id_inspeccion`. Las filas se conservan tal como fueron exportadas: **no se deduplican ni se asume** que sean eventos independientes hasta verificar el origen de esos IDs.

## Seguridad y limitaciones

El sitio público exhibe los nombres de los supervisores. Confirma que exista autorización para mostrarlos antes de compartir la URL; de lo contrario, utiliza una copia anonimizada del CSV. No se incluyen correos, imágenes, chats, tokens ni credenciales de API en estos archivos.

Este es un prototipo académico. Los resultados del detector de imágenes **no certifican cumplimiento de EPP**, y el estado de revisión humana del flujo no acredita la resolución de cada alerta.

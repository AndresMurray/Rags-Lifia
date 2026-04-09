# Guia completa del RAG y estructura de carpetas - Lifia-Rag

## 1. Que es este proyecto

Lifia-Rag es un stack local de IA que combina:

- Inferencia de modelos con Ollama.
- Interfaz de chat con Open WebUI.
- Un pipeline RAG personalizado para Seven Wonders.
- Persistencia de embeddings y busqueda semantica en pgvector.

La idea central del proyecto es que el modelo no responda solo por conocimiento general, sino usando contexto recuperado desde una base vectorial construida con datos reales.

---

## 2. Como funciona el RAG en este proyecto

El pipeline real esta en [appdata/pipelines/seven_wonders_rag.py](appdata/pipelines/seven_wonders_rag.py).

### 2.1 Flujo end-to-end

1. El usuario escribe una pregunta en Open WebUI.
2. Open WebUI envia la consulta al modelo Seven Wonders RAG (proveedor Pipelines).
3. El pipeline sincroniza datos reales desde Hugging Face (dataset Seven Wonders).
4. El pipeline transforma contenido y consulta en embeddings con Ollama (`nomic-embed-text`).
5. Los embeddings se guardan y consultan en pgvector (`vdb`).
6. Se recuperan los chunks mas relevantes por similitud coseno.
7. Se construye un prompt con ese contexto.
8. Ollama (`llama3`) genera la respuesta final.
9. Se devuelve la respuesta al chat junto con fuentes usadas.

### 2.2 Ingestion de datos reales (sin fallback local)

El pipeline usa el endpoint de datasets-server de Hugging Face para traer filas del dataset:

- Dataset: `bilgeyucel/seven-wonders`
- Split: `train`

No depende de un txt local de ejemplo para funcionar.

### 2.3 Indexacion en base vectorial

El pipeline crea/usa en `vdb`:

- `sw_knowledge`: contenido, metadatos y vector embedding.
- `sw_ingestion_state`: checksum del dataset para saber si hay que reindexar.

Si el checksum no cambia, evita reprocesar. Si cambia, vuelve a indexar.

### 2.4 Recuperacion semantica

Cuando llega una pregunta:

- Se genera embedding de la consulta.
- Se ejecuta busqueda vectorial en `sw_knowledge`.
- Se recupera Top-K por distancia coseno.
- Esos fragmentos se inyectan como contexto al prompt.

### 2.5 Generacion de respuesta

El modelo generador (`llama3`) responde en base al contexto recuperado. Por eso el resultado es RAG real y no solo respuesta general del LLM.

---

## 3. Arquitectura de servicios Docker

Definida en [docker-compose.yaml](docker-compose.yaml).

- `ollama`: motor de embeddings y generacion.
- `open-webui`: interfaz web y backend del chat.
- `pipelines`: runtime de pipelines Open WebUI (donde corre `seven_wonders_rag.py`).
- `db`: PostgreSQL relacional auxiliar.
- `vdb`: PostgreSQL con extension pgvector para embeddings.

Puertos principales:

- Open WebUI: `localhost:8180`
- Ollama: `localhost:11434`
- Pipelines: `localhost:9099`
- DB: `localhost:5432`
- VDB: `localhost:5433`

---

## 4. Explicacion de cada carpeta del repositorio

## 4.1 Carpeta raiz

- [README.md](README.md): guia de instalacion, arranque y uso.
- [docker-compose.yaml](docker-compose.yaml): define todos los servicios.
- [explicacion_proyecto.md](explicacion_proyecto.md): explicacion general del sistema.
- [explicacion_docker_compose.md](explicacion_docker_compose.md): detalle tecnico de compose.
- [explicacion_seven_wonders.md](explicacion_seven_wonders.md): contexto del caso Seven Wonders.

## 4.2 Carpeta env

Contiene configuracion por servicio.

- [env/ollama.env](env/ollama.env): vars de Ollama.
- [env/openwebui.env](env/openwebui.env): vars de Open WebUI y proveedor OpenAI-compatible hacia Pipelines.
- [env/pipelines.env](env/pipelines.env): vars del servicio Pipelines y conexion a vdb.
- [env/db.env](env/db.env): credenciales de db relacional.
- [env/vdb.env](env/vdb.env): credenciales de db vectorial.
- Archivos `.example`: plantillas para crear los `.env` reales.

## 4.3 Carpeta appdata

Persistencia real de datos (bind mounts desde Docker).

- [appdata/ollama](appdata/ollama): modelos descargados de Ollama.
- [appdata/owui](appdata/owui): estado/datos de Open WebUI (usuarios, configuracion, chats).
- [appdata/pipelines](appdata/pipelines): scripts de pipelines y metadata de valves.
- [appdata/rawdata](appdata/rawdata): insumos documentales opcionales para otros pipelines.
- [appdata/postgress](appdata/postgress): datos de PostgreSQL relacional.
- [appdata/postgress_vector](appdata/postgress_vector): datos de PostgreSQL con pgvector.

## 4.4 Carpeta examples

Ejemplos de scripts fuera del runtime productivo de Pipelines.

- [examples/SevenWonders/seven_wonders_ollama.py](examples/SevenWonders/seven_wonders_ollama.py): ejemplo Haystack standalone.
- [examples/SevenWonders/requirements.txt](examples/SevenWonders/requirements.txt): dependencias de ejemplo.

Nota: para chat en Open WebUI con RAG real, el flujo actual usa [appdata/pipelines/seven_wonders_rag.py](appdata/pipelines/seven_wonders_rag.py), no el script de ejemplo.

---

## 5. Persistencia y datos: que se guarda y donde

- Si borras `appdata/ollama`, perdes modelos descargados.
- Si borras `appdata/owui`, reseteas estado de Open WebUI.
- Si borras `appdata/postgress_vector`, perdes embeddings indexados.
- Si borras `appdata/postgress`, perdes datos de la DB relacional.

En general, `docker compose down` no borra estos datos, pero eliminar carpetas en `appdata` si.

---

## 6. Validaciones utiles

### 6.1 Ver servicios

```bash
docker compose ps
```

### 6.2 Ver cantidad de chunks indexados en pgvector

```bash
docker exec lifia-rag-vdb-1 psql -U postgres -d postgres -c "SELECT COUNT(*) FROM sw_knowledge;"
```

### 6.3 Ver modelos en Pipelines

```bash
curl -H "Authorization: Bearer 0p3n-w3bu!" http://localhost:9099/v1/models
```

---

## 7. Resumen operativo rapido

1. Levantar stack.
2. Verificar Ollama con modelos (`llama3` y `nomic-embed-text`).
3. Verificar que aparezca `Seven Wonders RAG` en modelos.
4. Elegir ese modelo en Open WebUI y chatear.
5. Confirmar indexacion en `sw_knowledge` para validar RAG real.

Con esto, el proyecto queda operando con RAG real sobre datos externos y recuperacion vectorial persistente.

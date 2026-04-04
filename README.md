# 🤖 Lifia-RAG — Stack de IA Local con RAG

Sistema de chat con modelos de IA locales que pueden leer y responder sobre tus propios documentos, usando **Retrieval Augmented Generation (RAG)**.

Todo corre en Docker. No se envían datos a servicios externos.

---

## 📋 Requisitos previos

Antes de empezar, asegurate de tener instalado:

| Herramienta | Versión mínima | Cómo verificar | Descarga |
|---|---|---|---|
| **Docker Desktop** | 4.x+ | `docker --version` | [docker.com/get-docker](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | v2+ (viene incluido en Docker Desktop) | `docker compose version` | Ya incluido |
| **Git** | cualquiera | `git --version` | [git-scm.com](https://git-scm.com/) |

> [!IMPORTANT]
> **Docker Desktop debe estar corriendo** antes de ejecutar cualquier comando. Abrilo y esperá a que el ícono deje de parpadear.

### Recursos de hardware recomendados

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 8 GB | 16 GB+ |
| Disco libre | 10 GB | 20 GB+ (los modelos de IA pesan varios GB) |
| CPU | 4 cores | 8 cores+ |
| GPU (opcional) | — | NVIDIA con 6GB+ VRAM (acelera muchísimo la IA) |

---

## 🚀 Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPO>
cd Lifia-Rag
```

### 2. Crear los archivos de variables de entorno

El proyecto necesita archivos `.env` con passwords y configuración. No vienen en el repo por seguridad, pero hay archivos `.env.example` como referencia.

**En Windows (PowerShell):**
```powershell
Copy-Item env\ollama.env.example env\ollama.env
Copy-Item env\db.env.example env\db.env
Copy-Item env\vdb.env.example env\vdb.env
Copy-Item env\openwebui.env.example env\openwebui.env
Copy-Item env\pipelines.env.example env\pipelines.env
```

**En Linux/Mac:**
```bash
cp env/ollama.env.example env/ollama.env
cp env/db.env.example env/db.env
cp env/vdb.env.example env/vdb.env
cp env/openwebui.env.example env/openwebui.env
cp env/pipelines.env.example env/pipelines.env
```

### 3. Configurar los passwords

Abrí los archivos `.env` que acabás de crear y cambiá los valores de ejemplo por los tuyos:

| Archivo | Variable a editar | Qué poner |
|---|---|---|
| `env/db.env` | `POSTGRES_PASSWORD=` | Un password para la base de datos principal |
| `env/vdb.env` | `POSTGRES_PASSWORD=` | Un password para la base de datos vectorial |
| `env/openwebui.env` | `WEBUI_SECRET_KEY=` | Una clave secreta cualquiera (para tokens de sesión) |

> [!NOTE]
> Los demás archivos (`ollama.env`, `pipelines.env`) ya vienen con valores por defecto que no necesitás cambiar.

### 4. Levantar todos los servicios

```bash
docker compose up -d
```

La primera vez va a **descargar las imágenes de Docker** (~3-5 GB en total). Esto puede tardar varios minutos dependiendo de tu conexión a internet.

Podés ver el progreso con:
```bash
docker compose logs -f
```

*(Presioná `Ctrl+C` para salir de los logs sin apagar los servicios)*

### 5. Verificar que todo esté corriendo

```bash
docker compose ps
```

Deberías ver los 5 servicios con estado `Up`:

```
NAME                    STATUS
lifia-rag-ollama-1      Up
lifia-rag-db-1          Up
lifia-rag-vdb-1         Up
lifia-rag-open-webui-1  Up
lifia-rag-pipelines-1   Up
```

### 6. Descargar un modelo de IA

Ollama arranca **sin modelos**. Tenés que descargar al menos uno:

```bash
# Modelo recomendado para empezar (~4.7 GB)
docker exec -it lifia-rag-ollama-1 ollama pull llama3

# Alternativa más liviana (~2 GB)
docker exec -it lifia-rag-ollama-1 ollama pull phi3
```

> [!TIP]
> Podés ver todos los modelos disponibles en [ollama.com/library](https://ollama.com/library). Modelos más grandes = mejores respuestas pero más lentos y más RAM.

### 7. Abrir la interfaz web

Abrí tu navegador y andá a:

### 👉 [http://localhost:8180](http://localhost:8180)

La primera vez te va a pedir **crear una cuenta de administrador**. Esa cuenta es local (se guarda en tu máquina, no se envía a ningún lado).

---

## ✅ ¡Listo!

Ya podés chatear con la IA. Para usar RAG (que la IA lea tus documentos):

1. Poné tus documentos (PDFs, TXTs, etc.) en la carpeta `appdata/rawdata/`
2. Configurá un pipeline de RAG desde la interfaz de Open WebUI
3. Hacé preguntas sobre el contenido de tus documentos

---

## 🛑 Cómo apagar todo

```bash
# Parar los servicios (los datos se mantienen)
docker compose down

# Parar sin eliminar los contenedores (arranque más rápido después)
docker compose stop
```

## 🔄 Cómo volver a encender

```bash
docker compose up -d
```

No necesitás repetir la configuración ni re-descargar modelos. Todo se mantiene en `appdata/`.

---

## 📁 Estructura del proyecto

```
Lifia-Rag/
├── docker-compose.yaml           ← Define los 5 servicios
├── .gitignore                    ← Qué archivos NO van al repo
├── README.md                     ← Este archivo
├── explicacion_proyecto.md       ← Explicación general del proyecto
├── explicacion_docker_compose.md ← Explicación detallada del docker-compose
├── env/                          ← Variables de entorno
│   ├── ollama.env.example        ← Referencia (en el repo)
│   ├── ollama.env                ← Tu config real (NO en el repo)
│   ├── db.env.example
│   ├── db.env
│   ├── vdb.env.example
│   ├── vdb.env
│   ├── openwebui.env.example
│   ├── openwebui.env
│   ├── pipelines.env.example
│   └── pipelines.env
└── appdata/                      ← Datos persistentes (NO en el repo)
    ├── ollama/                   ← Modelos de IA descargados
    ├── owui/                     ← DB y config de Open WebUI
    ├── postgress/                ← Base de datos PostgreSQL
    ├── postgress_vector/         ← Base de datos vectorial (embeddings)
    ├── pipelines/                ← Scripts de pipelines RAG
    └── rawdata/                  ← Tus documentos para RAG
```

---

## 🌐 Puertos y servicios

| Servicio | URL / Puerto | Descripción |
|---|---|---|
| **Open WebUI** | [localhost:8180](http://localhost:8180) | Interfaz de chat (lo que usás) |
| **Ollama** | localhost:11434 | Motor de IA (no tiene interfaz visual) |
| **PostgreSQL** | localhost:5432 | Base de datos relacional |
| **pgvector** | localhost:5433 | Base de datos vectorial |
| **Pipelines** | localhost:9099 | Motor de procesamiento RAG |

---

## 🔧 Troubleshooting

### "No puedo acceder a localhost:8180"
1. Verificá que Docker Desktop esté corriendo
2. Ejecutá `docker compose ps` y fijate que `open-webui` esté `Up`
3. Revisá los logs: `docker compose logs open-webui`

### "Ollama no aparece en Open WebUI"
Verificá que `env/openwebui.env` tenga esta línea:
```
OLLAMA_BASE_URL=http://ollama:11434
```

### "No hay modelos disponibles"
Descargá uno: `docker exec -it lifia-rag-ollama-1 ollama pull llama3`

### "Las respuestas son muy lentas"
- Sin GPU, los modelos grandes tardan. Probá un modelo más chico: `ollama pull phi3`
- Cerrá otras aplicaciones pesadas para liberar RAM

### "Error de puerto ocupado"
Otro programa está usando el mismo puerto. Podés cambiar los puertos editando `docker-compose.yaml`:
```yaml
# Ejemplo: cambiar Open WebUI del puerto 8180 al 3000
ports:
    - "3000:8080"
```
Después reiniciá: `docker compose down && docker compose up -d`

### Quiero empezar de cero
```bash
docker compose down
# Borrá los datos que quieras resetear:
# rm -rf appdata/owui/*        ← Resetea Open WebUI (usuarios, chats)
# rm -rf appdata/postgress/*   ← Resetea la DB
docker compose up -d
```

---

## 📖 Documentación adicional

- [`explicacion_proyecto.md`](explicacion_proyecto.md) — Qué es este proyecto y qué hace cada parte
- [`explicacion_docker_compose.md`](explicacion_docker_compose.md) — Análisis línea por línea del docker-compose.yaml

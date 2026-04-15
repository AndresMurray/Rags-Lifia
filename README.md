# Infraestructura Básica para RAGs
Este es un repositorio con ejemplos de infraestructura básica para RAGs.
Incluye
- **OpenWebUI**: es una interfaz web de código abierto, autohosteada y extensible diseñada para interactuar con grandes modelos de lenguaje (LLM) locales o en la nube, ofreciendo una experiencia similar a ChatGPT pero con control total sobre los datos. Funciona como un centro de mando que permite conectar con Ollama, APIs compatibles con OpenAI (como vLLM, LocalAI o proveedores en la nube) y gestionar flujos de trabajo de IA privados sin conexión a internet.
- **Ollama**: Ollama es una plataforma de código abierto que permite descargar, ejecutar y gestionar modelos de lenguaje grandes (LLM) directamente en el ordenador local, sin depender de servicios en la nube. Fue lanzado en julio de 2023 por Jeffrey Morgan y está diseñado para ejecutarse en sistemas Windows, macOS y Linux, funcionando principalmente a través de la terminal o mediante una API para integraciones.
- **pgvector**: es una extensión de código abierto para PostgreSQL que añade soporte nativo para el almacenamiento, indexación y búsqueda de similitud de vectores de alta dimensión, permitiendo integrar capacidades avanzadas de inteligencia artificial directamente en bases de datos relacionales existentes.
- 

## Startup
```
git clone
cd infrastructure
docker compose pull
docker compose run
```
And a bit of luck.

## Creando tu propio RAG
El código de tu RAG puede vivir en cualquier carpeta fuera de infrastructure e incluso fuera del repositorio. La carpeta `seven_wonders` tiene un ejemplo de RAG sencillo usando HayStack pero pueden crearse RAGs usando cualquier otra librería como LlamaIndex o LangChain. Sigue por el camino de tu arcoiris 🌈.

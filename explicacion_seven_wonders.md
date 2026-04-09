# Explicación del funcionamiento de `seven_wonders_ollama.py`

Este documento explica paso a paso cómo funciona el script independiente de ejemplos RAG utilizando **Haystack** y conectándose a los modelos locales ejecutados en **Ollama**.

---

## 1. Fase de Preparación (Base de datos y Textos)

```python
document_store = InMemoryDocumentStore()
dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
docs = [Document(content=doc["content"], meta=doc["meta"]) for doc in dataset]
```

En lugar de requerir que subas un PDF manualmente, el código se conecta a internet a través de HuggingFace y descarga un paquete de textos cortos llamado `"seven-wonders"`. Luego inicializa una "Base de datos en la memoria RAM" (`InMemoryDocumentStore`) y estructura y guarda esos textos convertidos a formato estándar `Document`.

## 2. Fase de Indexación (Creación de Embeddings)

```python
doc_embedder = OllamaDocumentEmbedder(
        model = EMBEDDING_MODEL_NAME, # nomic-embed-text
        url = OLLAMA_BASE_URL,
        batch_size=32
    )
docs_with_embeddings = doc_embedder.run(docs)
document_store.write_documents(docs_with_embeddings["documents"])
```

Para poder "buscar" texto por su significado, necesitamos vectorizarlo. El documento envía los textos a Ollama usando el modelo `nomic-embed-text` para traducirlos a vectores (arrays de números). Todo este texto vectorizado se escribe en la base de datos en memoria y queda listo para buscarse.

## 3. Construcción de los Elementos del Pipeline

El RAG consta de piezas que cumplen un rol único, casi como piezas de Lego:

```python
# 1. El Embedder de Preguntas
text_embedder = OllamaTextEmbedder(model=EMBEDDING_MODEL_NAME...) 

# 2. El Buscador (Retriever)
retriever = InMemoryEmbeddingRetriever(document_store)

# 3. La Plantilla (Prompt Builder)
prompt_builder = PromptBuilder(template=template) 

# 4. El Generador (LLM)
generator = OllamaGenerator(model=MODEL_NAME...) # llama3
```

- **text_embedder**: Transforma la pregunta literal textual del usuario a un formato de vector que la base de datos pueda entender.
- **retriever**: Compara el vector de la pregunta con los vectores del texto, extrae y recupera los fragmentos de texto que "mejor responden" a la consulta.
- **prompt_builder**: Toma el texto recuperado por el *retriever* y lo inyecta en una *plantilla*, de manera de decirle a la IA textual: *"Dado este texto sobre Maravillas del mundo, respondeme a esta pregunta"*.
- **generator**: El modelo de Lenguaje LLM real (`llama3`) que formula la respuesta escrita natural.

## 4. Ensamblaje del Pipeline

```python
basic_rag_pipeline = Pipeline()
basic_rag_pipeline.add_component(...)

basic_rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
basic_rag_pipeline.connect("retriever", "prompt_builder.documents")
basic_rag_pipeline.connect("prompt_builder", "llm")
```

El pipeline ensambla todas las piezas para que encajen estrictamente una atrás de la otra conectadas mediante sus variables de entrada y salida (como si fuese una tubería de agua). El esquema es: 
**Pregunta vectorizada ➡ Buscador de similitud ➡ Se envían textos a la Platilla ➡ Se envía la plantilla al Modelo LLM**.

## 5. Ejecución del Pipeline

```python
question = "Make a short description of the Lighthouse of Alexandria in a hundred words."

results = basic_rag_pipeline.run({
    "text_embedder": {"text": question},
    "prompt_builder": {"question": question}
})

print(results["llm"]["replies"][0])
```

Se introduce la consulta inicial y comienza a circular de forma automatizada por la cadena hasta terminar y obtener el resultado final por parte del modelo inteligente, que luego se muestra por pantalla usando `print()`.

---

## 💡 ¿Cómo chatear con estos o nuevos datos desde Open WebUI?

El repositorio principal soporta nativamente RAG utilizando el entorno visual de la página web mediante Open WebUI. Podés usar cualquiera de los enfoques:

### A) La forma recomendada y fácil (RAG Nativo WebUI)

Open WebUI corre con un servicio vectorial propio persistente (con `pgvector` en este proyecto), lo cual es ideal para los usuarios finales. No necesitas código ni pipelines.

1. Guardá el texto de forma local que querés consultar o tu propio PDF. 
2. Abrí la interfaz web en tu navegador (`http://localhost:8180`).
3. En el cuadro de texto del Nuevo Chat, tocá el ícono del **`+`** a la izquierda y subí el documento de texto o PDF, o ingresá al símbolo de perfil 👉 "Workspace" 👉 "Documents" para guardarlos en tu entorno.
4. Para chatear referenciando el documento, ingresá `#` y seleccioná el archivo en la lista, hacé una pregunta (ej. *"Resumime sobre el faro de alejandría"*) y WebUI manejará todo el RAG visualmente con el modelo configurado.

### B) Desde Pipelines Avanzados (Para Desarrolladores)

Ese script pertenece al entorno de una librería programática de automatización (*Haystack*). En tu `docker-compose`, tienes corriendo un servicio llamado **Pipelines**. Ese servicio soporta inyectarle estos scripts directamente a WebUI para que tengas total control de cómo WebUI hace RAG sobre distintas bases de dato como por ejemplo el InMemory provisto aquí. Si lo programás, funciona perfecto. Para la inmensa carga de usos, el RAG nativo (el del punto *A*) es todo lo que uno necesita.

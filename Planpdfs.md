1. Crear la carpeta del proyecto
  examples/MiRAG/

  2. Instalar dependencias
  pip install markitdown langchain-community psycopg2-binary ollama

  3. Convertir el PDF a Markdown
  from markitdown import MarkItDown
  md = MarkItDown()
  result = md.convert("mi_documento.pdf")
  text = result.text_content

  4. Chunkear el texto
  Dividirlo en fragmentos de ~500 tokens con overlap, para no perder contexto entre chunks.

  5. Generar embeddings con Ollama
  Llamar a http://localhost:11434/api/embeddings con modelo nomic-embed-text (768 dims) o bge-m3 (1024 dims).

  6. Guardar en pgvector
  Crear la tabla con el schema del CLAUDE.md y hacer el INSERT con los embeddings.

  7. Pipeline de consulta
  - Embed la pregunta del usuario
  - Cosine similarity search en pgvector (TOP_K=4)
  - Armar el prompt con el contexto
  - Llamar a Ollama para generar la respuesta

  8. Opcional: integrar como Pipeline en OpenWebUI
  Implementar la interfaz Pipeline y dropearlo en infrastructure/appdata/pipelines/.
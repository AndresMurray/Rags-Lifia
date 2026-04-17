from pathlib import Path

from haystack import Pipeline
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.converters.markitdown import MarkItDownConverter
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack_integrations.components.embedders.ollama import OllamaTextEmbedder
from haystack_integrations.components.embedders.ollama import OllamaDocumentEmbedder
from haystack_integrations.components.generators.ollama import OllamaGenerator


DOCS_DIR = Path(__file__).parent / "docs"

document_store = InMemoryDocumentStore()

# --- Indexing pipeline ---
indexing_pipeline = Pipeline()
indexing_pipeline.add_component("converter", MarkItDownConverter())
indexing_pipeline.add_component(
    "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=40)
)
indexing_pipeline.add_component(
    "embedder",
    OllamaDocumentEmbedder(model="bge-m3", url="http://localhost:11434", batch_size=32),
)
indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store))

indexing_pipeline.connect("converter", "splitter")
indexing_pipeline.connect("splitter", "embedder")
indexing_pipeline.connect("embedder", "writer")

pdf_files = list(DOCS_DIR.glob("*.pdf"))
indexing_pipeline.run({"converter": {"sources": pdf_files}})

EMBEDDING_MODEL_NAME = "bge-m3"
MODEL_NAME = "ministral-3:3b"
OLLAMA_BASE_URL = "http://localhost:11434"

text_embedder = OllamaTextEmbedder(model=EMBEDDING_MODEL_NAME, url=OLLAMA_BASE_URL)

retriever = InMemoryEmbeddingRetriever(document_store)
template = """
        Given the following information, answer the question.

        Context:
        {% for document in documents %}
            {{ document.content }}
        {% endfor %}

        Question: {{question}}
        Answer:
        """


prompt_builder = PromptBuilder(
    template=template,
    required_variables=["documents", "question"],
)

# generator = OpenAIGenerator(model="gpt-3.5-turbo")
generator = OllamaGenerator(
    model=MODEL_NAME,
    url=OLLAMA_BASE_URL,
    generation_kwargs={
        "num_predict": 1000,
        "temperature": 0.5,
    },
    timeout=450,
)

basic_rag_pipeline = Pipeline()
# Add components to your pipeline
basic_rag_pipeline.add_component("text_embedder", text_embedder)
basic_rag_pipeline.add_component("retriever", retriever)
basic_rag_pipeline.add_component("prompt_builder", prompt_builder)
basic_rag_pipeline.add_component("llm", generator)

# Now, connect the components to each other
basic_rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
basic_rag_pipeline.connect("retriever", "prompt_builder.documents")
basic_rag_pipeline.connect("prompt_builder", "llm")

question = "Que sabes sobre la Reforma Constitucional de 1994"

results = basic_rag_pipeline.run(
    {"text_embedder": {"text": question}, "prompt_builder": {"question": question}}
)

print(results["llm"]["replies"][0])

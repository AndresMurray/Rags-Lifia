import os


from haystack import Pipeline, Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.embedders.ollama import OllamaTextEmbedder
from haystack_integrations.components.embedders.ollama import OllamaDocumentEmbedder
from haystack_integrations.components.generators.ollama import OllamaGenerator

from datasets import load_dataset


document_store = InMemoryDocumentStore()
dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
docs = [Document(content=doc["content"], meta=doc["meta"]) for doc in dataset]

EMBEDDING_MODEL_NAME="nomic-embed-text"
MODEL_NAME="llama3"
OLLAMA_BASE_URL="http://localhost:11434"

doc_embedder = OllamaDocumentEmbedder(
        model = EMBEDDING_MODEL_NAME,
        url = OLLAMA_BASE_URL,
        batch_size=32
    )

docs_with_embeddings = doc_embedder.run(docs)
document_store.write_documents(docs_with_embeddings["documents"])

text_embedder = OllamaTextEmbedder(
    model = EMBEDDING_MODEL_NAME,
    url = OLLAMA_BASE_URL
)

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


prompt_builder = PromptBuilder(template=template)

# generator = OpenAIGenerator(model="gpt-3.5-turbo")
generator = OllamaGenerator(model=MODEL_NAME,
                            url = OLLAMA_BASE_URL,
                            generation_kwargs={
                                "num_predict": 1000,
                                "temperature": 0.5,
                                },
                            timeout=450
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

question = "Make a short description of the Lighthouse of Alexandria in a hundred words."

results = basic_rag_pipeline.run({
    "text_embedder": {"text": question},
    "prompt_builder": {"question": question}
})

print(results["llm"]["replies"][0])
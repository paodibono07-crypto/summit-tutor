from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from resource_index import DOC_TYPES

DOCS_DIR = Path(__file__).parent / "docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_vectorstore: FAISS | None = None


def _build_vectorstore() -> FAISS:
    pdf_paths = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(
            f"No PDFs found in {DOCS_DIR}. Add PDFs to the docs/ folder first."
        )

    print(f"[RAG] Found {len(pdf_paths)} PDF(s) in {DOCS_DIR}:")
    docs = []
    for path in pdf_paths:
        doc_type = DOC_TYPES.get(path.name, "unknown")
        if doc_type == "placeholder":
            print(f"  Skipping (placeholder): {path.name}")
            continue
        print(f"  Loading [{doc_type}]: {path.name}")
        try:
            loader = PyPDFLoader(str(path))
            pages = loader.load()
            if pages:
                for page in pages:
                    page.metadata["doc_type"] = doc_type
                    page.metadata["filename"] = path.name
                docs.extend(pages)
                print(f"    OK — {len(pages)} page(s)")
            else:
                print(f"    WARNING — 0 pages extracted (file may be empty or image-only)")
        except Exception as e:
            print(f"    ERROR — skipping ({e})")

    if not docs:
        raise ValueError("No text could be extracted from any PDF in docs/.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Built index: {len(docs)} pages → {len(chunks)} chunks\n")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return FAISS.from_documents(chunks, embeddings)


def _get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _build_vectorstore()
    return _vectorstore


def retrieve_context(query: str, k: int = 3) -> str:
    try:
        results = _get_vectorstore().similarity_search(query, k=k)
        if not results:
            return ""

        print(f"[RAG] Retrieved {len(results)} chunk(s) for: {query[:60]!r}")
        parts = []
        for doc in results:
            doc_type = doc.metadata.get("doc_type", "unknown")
            filename = doc.metadata.get(
                "filename",
                Path(doc.metadata.get("source", "unknown")).name,
            )
            print(f"  <- [{doc_type}] {filename}")
            tag = f"[{doc_type.upper()}]" if doc_type in ("teaching", "activity") else "[REF]"
            parts.append(f"{tag} {filename}\n{doc.page_content}")

        return "\n\n".join(parts)
    except FileNotFoundError:
        return ""

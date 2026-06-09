"""
RAG Pipeline for ORYA static knowledge base.
Chunks PDFs and Text files → Embeds → Stores in ChromaDB.
Run build_vector_store() once (or on document update).
"""

import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# ── Config ────────────────────────────────────────────────────
DOCS_DIR         = Path(__file__).parent.parent / 'static' / 'docs'
CHROMA_DIR       = Path(__file__).parent.parent / 'chroma_db'
KNOWLEDGE_COL    = 'orya_knowledge'
PRODUCTS_COL     = 'orya_products'

# Chunking settings
CHUNK_SIZE    = 1000   # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks (important for context)

# Search settings — adjust these to tune result quality
TOP_K        = 30     # number of results to return (more = wider coverage)
MAX_DISTANCE = 0.2   # minimum similarity score (lower = more permissive)

# ── Build / Rebuild Vector Store ──────────────────────────────
def build_vector_store():
    """
    Load all PDFs and TXT files from DOCS_DIR, chunk them with overlap,
    embed with OpenAI, and persist to ChromaDB.
    Call this once at startup or when documents change.
    """
    all_documents = []

    # Handle PDFs
    for pdf_path in DOCS_DIR.glob('*.pdf'):
        loader = PyPDFLoader(str(pdf_path))
        pages  = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = CHUNK_SIZE,
            chunk_overlap = CHUNK_OVERLAP,
            separators    = ['\n\n', '\n', '، ', '. ', ' ', '']
        )
        chunks = splitter.split_documents(pages)

        # Tag each chunk with its source file
        for chunk in chunks:
            chunk.metadata['source_file'] = pdf_path.name

        all_documents.extend(chunks)

    # Handle Text files (if any)
    for txt_path in DOCS_DIR.glob('*.txt'):
        loader = TextLoader(str(txt_path), encoding='utf-8')
        docs   = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = CHUNK_SIZE,
            chunk_overlap = CHUNK_OVERLAP,
            separators    = ['\n\n', '\n', '، ', '. ', ' ', '']
        )
        chunks = splitter.split_documents(docs)

        for chunk in chunks:
            chunk.metadata['source_file'] = txt_path.name

        all_documents.extend(chunks)

    if not all_documents:
        print('[RAG] No documents found in', DOCS_DIR)
        return None

    embeddings = OpenAIEmbeddings(
        model='text-embedding-3-small'
    )

    vectorstore = Chroma.from_documents(
        documents       = all_documents,
        embedding       = embeddings,
        collection_name = KNOWLEDGE_COL,
        persist_directory = str(CHROMA_DIR)
    )

    print(f'[RAG] Built knowledge store: {len(all_documents)} chunks')
    return vectorstore

def build_product_index():
    """
    Parse products_catalog.txt and index each product as a Document with metadata.
    Ensures 'Guaranteed Search' from file while keeping UI functionality.
    """
    import re
    from langchain.schema import Document
    
    catalog_path = DOCS_DIR / 'products_catalog.txt'
    if not catalog_path.exists():
        print(f'[RAG] Catalog file not found: {catalog_path}')
        return None

    with open(catalog_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the separator
    blocks = content.split('-' * 40)
    docs = []
    
    for block in blocks:
        block = block.strip()
        if "PRODUCT ID:" not in block: continue
        
        # 1. Extract Metadata using Regex
        m_id    = re.search(r'PRODUCT ID: (\d+)', block)
        m_ar    = re.search(r'NAME \(AR\): (.*)', block)
        m_en    = re.search(r'NAME \(EN\): (.*)', block)
        m_price = re.search(r'PRICE: ([\d.]+) JOD', block)
        m_sale  = re.search(r'SALE PRICE: ([\d.]+) JOD', block)
        m_img   = re.search(r'IMAGE URL: (.*)', block)
        
        if not m_id: continue
        
        product_id = int(m_id.group(1))
        name_ar    = m_ar.group(1).strip() if m_ar else "Product"
        name_en    = m_en.group(1).strip() if m_en else name_ar
        price      = float(m_price.group(1)) if m_price else 0.0
        sale_price = float(m_sale.group(1)) if m_sale else price
        is_on_sale = True if m_sale else False
        image      = m_img.group(1).strip() if m_img else ""
        
        metadata = {
            'product_id':     product_id,
            'name_ar':        name_ar,
            'name_en':        name_en,
            'price':          sale_price,
            'original_price': price,
            'is_on_sale':     is_on_sale,
            'image':          image,
            'url':            f'/product/{product_id}'
        }
        
        # 2. Content for Search (The whole block text)
        docs.append(Document(page_content=block, metadata=metadata))

    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    
    # Rebuild collection
    vectorstore = Chroma.from_documents(
        documents       = docs,
        embedding       = embeddings,
        collection_name = PRODUCTS_COL,
        persist_directory = str(CHROMA_DIR)
    )
    print(f'[RAG] Rebuilt product index from catalog file: {len(docs)} products')
    return vectorstore


# ── Load Existing Vector Store ────────────────────────────────
def load_vector_store(collection_name: str = KNOWLEDGE_COL):
    """Load persisted ChromaDB vector store."""
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    return Chroma(
        collection_name   = collection_name,
        embedding_function = embeddings,
        persist_directory  = str(CHROMA_DIR)
    )


# ── Query the RAG ─────────────────────────────────────────────
def query_rag(question: str, k: int = TOP_K) -> str:
    """
    Search vector store for relevant chunks.
    Returns concatenated context string.
    """
    try:
        vs      = load_vector_store()
        results = vs.similarity_search(question, k=k)
        if not results:
            return ''
        context = '\n\n'.join([doc.page_content for doc in results])
        return context
    except Exception as e:
        print(f'[RAG Query Error] {e}')
        return ''

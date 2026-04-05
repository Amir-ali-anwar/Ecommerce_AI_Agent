import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_astradb import AstraDBVectorStore
from langchain_huggingface import HuggingFaceEmbeddings


import logging

load_dotenv()

# Configure logging for direct execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
ASTRA_DB_KEYSPACE = os.getenv("ASTRA_DB_KEYSPACE")


def load_and_chunk_data(csv_path):
    """
    Reads the CSV, aggregates reviews by product, and chunks them.
    This is much better than treating every 5-word review as a separate document!
    """

    logger.info(f'Loading data from {csv_path}')
    df = pd.read_csv(csv_path)
    logger.info(f'Loaded {len(df)} rows')

    # Aggregate reviews by product
    aggregated_data = (
    df.groupby(['product_id', 'product_title'])['review']
      .apply(lambda x: ' '.join(str(v) for v in x))
      .reset_index())
    logger.info(f'Aggregated to {len(aggregated_data)} products')

    # Convert to LangChain Documents
    documents = []
    for _, row in aggregated_data.iterrows():
        doc = Document(
            page_content=row['review'],
            metadata={
                'product_id': row['product_id'],
                'product_title': row['product_title']
            }
        )
        documents.append(doc)
    
    print(f'Created {len(documents)} documents')
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(documents)
    logger.info(f'Split into {len(split_docs)} chunks')
    return split_docs


def ingest_to_astradb(documents):
    """
    Ingests the documents into AstraDB.
    """ 
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    print("Connecting to AstraDB...")   
    vstore = AstraDBVectorStore(
        embedding=embedding,
        collection_name="advanced_ecomm",
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_APPLICATION_TOKEN,
        namespace=ASTRA_DB_KEYSPACE,
    )
    print("Inserting documents (this might take a minute)...")
    inserted_ids = vstore.add_documents(documents=documents)
    print(f"Successfully inserted {len(inserted_ids)} documents.")
    return vstore

if __name__ == '__main__':
    # Map back to the original data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "flipkart_product_review.csv")
    csv_path = os.path.abspath(csv_path)
    
    # 1. Load and process
    documents = load_and_chunk_data(csv_path)
    
    # 2. Ingest
    if ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN:
        ingest_to_astradb(documents)
    else:
        logger.error("AstraDB API Connection details are missing! Make sure to fill out the .env file.")

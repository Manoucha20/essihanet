# database_utils.py
import os
import re
from neo4j import GraphDatabase

# --- إعدادات Pinecone ---
index = None
model = None
try:
    from pinecone import Pinecone, ServerlessSpec
    from sentence_transformers import SentenceTransformer

    PINECONE_KEY = os.getenv("PINECONE_KEY")
    INDEX_NAME = os.getenv("INDEX_NAME", "default_index")

    if PINECONE_KEY:
        pc = Pinecone(api_key=PINECONE_KEY)
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if INDEX_NAME not in existing_indexes:
            pc.create_index(
                name=INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        index = pc.Index(INDEX_NAME)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Pinecone initialized.")
except Exception as e:
    print(f"⚠️ Pinecone Error: {e}")

# --- إعدادات Neo4j ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = None
if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("✅ Neo4j connected.")
    except Exception as e:
        print(f"⚠️ Neo4j Connection Failed: {e}")

def save_to_pinecone(text, file_id):
    if index and text and model:
        try:
            vector = model.encode(text).tolist()
            index.upsert([{"id": file_id, "values": vector, "metadata": {"analysis_text": text}}])
            print(f"✅ Saved to Pinecone: {file_id}")
        except Exception as e:
            print(f"❌ Pinecone Error: {e}")

def save_to_neo4j(name, analysis):
    if driver:
        try:
            with driver.session() as session:
                session.execute_write(lambda tx: tx.run(
                    "MERGE (p:Patient {name: $name}) CREATE (a:Analysis {result: $analysis, timestamp: datetime()}) MERGE (p)-[:HAS]->(a)",
                    name=name, analysis=analysis
                ))
            print("✔️ Saved to Neo4j")
        except Exception as e:
            print(f"❌ Neo4j Error: {e}")
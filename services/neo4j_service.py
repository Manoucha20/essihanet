import os
import json
import time
import threading
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

QUEUE_FILE = "neo4j_queue.json"

driver = None


# =========================
# CONNECT
# =========================
def connect_neo4j():
    global driver
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        print("✅ Neo4j connected successfully!")
    except Exception as e:
        print("⚠️ Neo4j connection failed:", e)
        driver = None


connect_neo4j()


# =========================
# SAVE TO LOCAL FILE
# =========================
def save_locally(data):
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
        else:
            queue = []

        queue.append(data)

        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f)

        print("💾 Saved locally (offline mode)")

    except Exception as e:
        print("❌ Local save failed:", e)


# =========================
# REAL NEO4J SAVE
# =========================
def send_to_neo4j(patient_id, text, analysis):
    global driver

    if not driver:
        connect_neo4j()

    with driver.session() as session:
        session.execute_write(lambda tx: tx.run(
            """
            MERGE (p:Patient {id: $patient_id})
            CREATE (a:Analysis {
                text: $text,
                result: $analysis,
                timestamp: datetime()
            })
            MERGE (p)-[:HAS]->(a)
            """,
            patient_id=patient_id,
            text=text,
            analysis=analysis
        ))


# =========================
# MAIN SAVE FUNCTION
# =========================
def save_to_neo4j(patient_id, text, analysis=None):

    data = {
        "patient_id": patient_id,
        "text": text,
        "analysis": analysis,
        "timestamp": str(datetime.utcnow())
    }

    try:
        send_to_neo4j(patient_id, text, analysis)
        print("✔️ Saved to Neo4j")

    except Exception:
        print("⚠️ Neo4j down → saving locally")
        save_locally(data)


# =========================
# AUTO SYNC BACKGROUND
# =========================
def auto_sync():
    while True:
        try:
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, "r") as f:
                    queue = json.load(f)

                if queue:
                    print("🔄 Syncing queued data...")

                new_queue = []

                for item in queue:
                    try:
                        send_to_neo4j(
                            item["patient_id"],
                            item["text"],
                            item["analysis"]
                        )
                        print("✅ Synced item")
                    except:
                        new_queue.append(item)

                with open(QUEUE_FILE, "w") as f:
                    json.dump(new_queue, f)

        except Exception as e:
            print("⚠️ Sync error:", e)

        time.sleep(20)  # كل 20 ثانية


# =========================
# START SYNC THREAD
# =========================
threading.Thread(target=auto_sync, daemon=True).start()
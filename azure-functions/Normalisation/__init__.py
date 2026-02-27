import logging
import os
from azure.cosmos import CosmosClient

from .normalizer import normalize_trace


def main(documents):

    if not documents:
        logging.info("No documents received.")
        return

    logging.info(f"Processing {len(documents)} raw traces...")

    cosmos = CosmosClient.from_connection_string(
        os.environ["COSMOS_CONN_WRITE"]
    )

    db = cosmos.get_database_client("llmops-data")
    container = db.get_container_client("traces")

    for raw in documents:
        try:
            canonical = normalize_trace(raw)
            container.upsert_item(canonical.model_dump())
            logging.info(f"Normalized trace {canonical.trace_id}")
        except Exception as e:
            logging.error(f"Normalization failed: {str(e)}")
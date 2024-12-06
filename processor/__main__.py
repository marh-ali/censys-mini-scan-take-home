"""Main entry point for the processor package."""

import os
import logging

from processor.processor import MessageProcessor
from processor.pubsub_client import PubSubClient

def main():
    """Initialize and run the processor service."""
    # Get configuration from environment variables
    project_id = os.getenv("PUBSUB_PROJECT_ID")
    subscription_id = os.getenv("PUBSUB_SUBSCRIPTION_ID")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if not project_id or not subscription_id:
        raise ValueError(
            "Missing required environment variables: "
            "PUBSUB_PROJECT_ID, PUBSUB_SUBSCRIPTION_ID"
        )

    logging.info(f"Starting processor with project_id={project_id}, "
                f"subscription_id={subscription_id}")

    # Initialize processor and client
    processor = MessageProcessor()
    client = PubSubClient(project_id, subscription_id)

    logging.info("Starting message processing service...")
    client.start_listening(processor.process_message)

if __name__ == "__main__":
    main()
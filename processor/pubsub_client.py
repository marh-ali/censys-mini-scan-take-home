import logging
from google.cloud import pubsub_v1


class PubSubClient:
    """Handles Google Cloud Pub/Sub connectivity and subscription."""

    def __init__(self, project_id: str, subscription_id: str):
        """
        Initialize Pub/Sub client.

        Args:
            project_id: GCP project ID
            subscription_id: Pub/Sub subscription ID
        """
        self.project_id = project_id
        self.subscription_id = subscription_id
        self._setup_client()

    def _setup_client(self) -> None:
        """Configure Pub/Sub client and subscription path."""
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            self.project_id, self.subscription_id
        )

    def _get_flow_control(self) -> pubsub_v1.types.FlowControl:
        """Configure message flow control settings."""
        return pubsub_v1.types.FlowControl(
            max_messages=10,
            max_bytes=1024 * 1024,
        )

    def start_listening(self, callback) -> None:
        """
        Start listening for messages.

        Args:
            callback: Function to process received messages
        """
        flow_control = self._get_flow_control()

        future = self.subscriber.subscribe(
            self.subscription_path,
            callback=callback,
            flow_control=flow_control,
        )

        try:
            future.result()
        except KeyboardInterrupt:
            logging.info("Initiating graceful shutdown...")
            future.cancel()  # Trigger shutdown on Ctrl+C
            self.subscriber.close()
            logging.info("Shutdown complete")

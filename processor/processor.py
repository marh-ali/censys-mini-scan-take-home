"""Network scan result processor module."""

import base64
import ipaddress
import json
import logging
import time

from processor.db import Database

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MessageProcessor:
    """Process messages from Pub/Sub containing scan results."""

    MAX_RETRIES = 3  # Can be made configurable via env var
    BASE_DELAY = 1  # Base delay in seconds

    def __init__(self):
        """Initialize the message processor with database connection."""
        self.db = Database()

    def process_message(self, message, retry_count: int = 0) -> None:
        """
        Process a scan result message from Pub/Sub with retries.

        :param message: A Pub/Sub message object containing scan result data
        :param retry_count: Current retry attempt number, defaults to 0
        :type message: google.cloud.pubsub_v1.subscriber.message.Message
        :type retry_count: int
        :raises json.JSONDecodeError: If message contains invalid JSON - no retry
        :raises ValueError: If message data fails validation and attempts a retry
        :raises Exception: For other processing errors
        :return: None
        """
        try:
            data = json.loads(message.data.decode("utf-8"))
            logging.info(f"Processing message: {data}")

            ip, port, service, timestamp = self._extract_scan_data(data)
            response = self._parse_response(data)

            self.db.upsert_scan(
                ip=ip,
                port=port,
                service=service,
                timestamp=timestamp,
                response=response,
            )
            logging.info(f"Successfully stored scan for {ip}:{port} ({service})")
            message.ack()

        except json.JSONDecodeError as e:
            # Don't retry for malformed data
            logging.error(f"Invalid JSON in message: {e}")
            message.nack()

        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                # Calculate exponential backoff delay
                delay = (2 ** retry_count) * self.BASE_DELAY
                logging.warning(
                    f"Attempt {retry_count + 1}/{self.MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
                self.process_message(message, retry_count + 1)
            else:
                logging.error(
                    f"Failed after {self.MAX_RETRIES} attempts: {e}", exc_info=True
                )
                message.nack()

    def _validate_scan_data(self, ip: str, port: int, timestamp: int) -> None:
        """
        Validate the format and ranges of scan data fields.

        :param ip: IPv4 or IPv6 address string
        :param port: Network port number (0-65535)
        :param timestamp: Unix timestamp (positive integer)
        :type ip: str
        :type port: int
        :type timestamp: int
        :raises ValueError: If any field fails validation with specific error message
        :return: None
        """
        if not isinstance(port, int) or not (0 <= port <= 65535):
            raise ValueError(f"Invalid port number: {port}")
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError(f"Invalid timestamp: {timestamp}")
        try:
            ipaddress.ip_address(ip)
        except ValueError as err:
            raise ValueError(f"Invalid IP address: {ip}") from err

    def _extract_scan_data(self, data: dict) -> tuple[str, int, str, int]:
        """
        Extract and validate required fields from scan data dictionary.

        :param data: Dictionary containing scan result data.
        :type data: dict
        :return: tuple containing (ip_address, port_number, service_name, timestamp)
        :rtype: tuple[str, int, str, int]
        :raises ValueError: If required fields are missing or invalid
        """
        try:
            ip = str(data["ip"])
            port = int(data["port"])
            service = str(data["service"])
            timestamp = int(data["timestamp"])

            self._validate_scan_data(ip, port, timestamp)
            return (ip, port, service, timestamp)
        except (ValueError, KeyError) as err:
            raise ValueError(f"Data validation failed: {err}") from err

    def _parse_response(self, data: dict) -> str:
        """
        Parse service response based on data version format.

        :param data: Dictionary containing scan response data. Required keys:
                    'data_version', 'data'.
                    For version 1: data.response_bytes_utf8 (base64 encoded)
                    For version 2: data.response_str (plain text)
        :type data: dict
        :return: Decoded service response string
        :rtype: str
        :raises ValueError: If data version is unknown or required fields are missing
        """
        try:
            version = data["data_version"]

            if version == 1:
                return base64.b64decode(data["data"]["response_bytes_utf8"]).decode(
                    "utf-8"
                )
            elif version == 2:
                return data["data"]["response_str"]
            else:
                raise ValueError(f"Unknown data version: {version}")
        except KeyError as err:
            raise ValueError(f"Missing required field: {err}") from err

"""Unit tests for the MessageProcessor class."""

import base64
import json
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from processor.processor import MessageProcessor


@pytest.fixture
def mock_message():
    """Create a base mock message with ack/nack methods."""
    message = Mock()
    message.ack = Mock()
    message.nack = Mock()
    return message


@pytest.fixture
def valid_scan_data_v1():
    """Create valid version 1 scan data."""
    return {
        "ip": "192.168.1.1",
        "port": 80,
        "service": "http",
        "timestamp": 1234567890,
        "data_version": 1,
        "data": {
            "response_bytes_utf8": base64.b64encode(b"Hello World").decode()
        },
    }


@pytest.fixture
def valid_scan_data_v2():
    """Create valid version 2 scan data."""
    return {
        "ip": "192.168.1.1",
        "port": 80,
        "service": "http",
        "timestamp": 1234567890,
        "data_version": 2,
        "data": {"response_str": "Hello World"},
    }


class TestMessageProcessor:
    """Test cases for MessageProcessor class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        with patch("processor.processor.Database") as mock_db, patch(
            "time.sleep"
        ) as _:  # Mock sleep for all tests
            self.processor = MessageProcessor()
            self.mock_db = mock_db.return_value
            yield

    def test_process_valid_v1_message(self, mock_message, valid_scan_data_v1):
        """Test processing a valid version 1 message."""
        # Arrange
        mock_message.data = json.dumps(valid_scan_data_v1).encode()

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_called_once_with(
            ip="192.168.1.1",
            port=80,
            service="http",
            timestamp=1234567890,
            response="Hello World",
        )
        mock_message.ack.assert_called_once()
        mock_message.nack.assert_not_called()

    def test_process_valid_v2_message(self, mock_message, valid_scan_data_v2):
        """Test processing a valid version 2 message."""
        # Arrange
        mock_message.data = json.dumps(valid_scan_data_v2).encode()

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_called_once_with(
            ip="192.168.1.1",
            port=80,
            service="http",
            timestamp=1234567890,
            response="Hello World",
        )
        mock_message.ack.assert_called_once()
        mock_message.nack.assert_not_called()

    def test_invalid_json_message(self, mock_message):
        """Test handling invalid JSON message."""
        # Arrange
        mock_message.data = b"invalid json"

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_not_called()
        mock_message.nack.assert_called_once()
        mock_message.ack.assert_not_called()

    @pytest.mark.parametrize(
        "field,invalid_value,error_pattern",
        [
            ("ip", "invalid-ip", "Invalid IP address"),
            ("port", -1, "Invalid port number"),
            ("port", 65536, "Invalid port number"),
            ("timestamp", -1, "Invalid timestamp"),
        ],
    )
    def test_invalid_field_values(
        self, mock_message, valid_scan_data_v1, field, invalid_value, error_pattern
    ):
        """Test handling of invalid field values."""
        # Arrange
        valid_scan_data_v1[field] = invalid_value
        mock_message.data = json.dumps(valid_scan_data_v1).encode()

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_not_called()
        mock_message.nack.assert_called_once()
        mock_message.ack.assert_not_called()

    def test_missing_required_fields(self, mock_message):
        """Test handling missing required fields."""
        # Arrange
        incomplete_data = {"ip": "192.168.1.1"}  # Missing required fields
        mock_message.data = json.dumps(incomplete_data).encode()

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_not_called()
        mock_message.nack.assert_called_once()
        mock_message.ack.assert_not_called()

    def test_unknown_data_version(self, mock_message, valid_scan_data_v1):
        """Test handling unknown data version."""
        # Arrange
        valid_scan_data_v1["data_version"] = 999
        mock_message.data = json.dumps(valid_scan_data_v1).encode()

        # Act
        self.processor.process_message(mock_message)

        # Assert
        self.mock_db.upsert_scan.assert_not_called()
        mock_message.nack.assert_called_once()
        mock_message.ack.assert_not_called()

    @pytest.mark.parametrize(
        "ip,port,timestamp",
        [
            ("192.168.1.1", 80, 1234567890),
            ("2001:db8::1", 443, 1234567890),
            ("10.0.0.1", 1, 0),
            ("172.16.0.1", 65535, 1),
        ],
    )
    def test_valid_data_validation(self, ip, port, timestamp):
        """Test validation of valid data combinations."""
        self.processor._validate_scan_data(ip, port, timestamp)  # Should not raise

    def test_database_error_retry(self, mock_message, valid_scan_data_v1):
        """Test database error triggers retry mechanism."""
        # Arrange
        mock_message.data = json.dumps(valid_scan_data_v1).encode()
        self.mock_db.upsert_scan.side_effect = [
            Exception("DB Error"),
            None,
        ]  # Fail once, then succeed

        # Act
        with patch("time.sleep") as mock_sleep:  # Prevent actual sleep in tests
            self.processor.process_message(mock_message)

        # Assert
        assert (
            self.mock_db.upsert_scan.call_count == 2
        )  # Called twice (initial + 1 retry)
        mock_sleep.assert_called_once()  # Verify backoff was attempted
        mock_message.ack.assert_called_once()  # Should succeed on retry
        mock_message.nack.assert_not_called()

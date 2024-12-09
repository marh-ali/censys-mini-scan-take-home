"""Database operations for scan results."""

import os

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from processor.models import Base, ServiceScan


class Database:
    """
    Thread-safe database manager for network scan results.
    """

    def __init__(self):
        """Initialize database connection."""

        db_path = os.path.join("/app/data", "scan_results.db")

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={
                "timeout": 30,
                "check_same_thread": False,
                "isolation_level": "IMMEDIATE",
            },
        )

        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=DELETE"))
            conn.execute(text("PRAGMA busy_timeout=30000"))
            conn.commit()

        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """
        Provide a transactional scope around operations.

        :return: SQLAlchemy session with automatic commit/rollback
        :rtype: sqlalchemy.orm.Session
        :raises Exception: If database operations fail
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_scan(
        self, ip: str, port: int, service: str, timestamp: int, response: str
    ) -> None:
        """
        Insert or update a scan record, maintaining the most recent data.

        Updates existing record only if new scan is more recent than stored timestamp.
        Implements atomic updates via transaction management.

        :param ip: IPv4 or IPv6 address of scanned service
        :param port: Port number of service
        :param service: Service identifier (e.g., "HTTP", "SSH")
        :param timestamp: Unix timestamp of scan
        :param response: Service response string
        :type ip: str
        :type port: int
        :type service: str
        :type timestamp: int
        :type response: str
        :raises ValueError: If data validation fails
        :raises Exception: If database operation fails
        """
        with self.get_session() as session:
            scan = (
                session.query(ServiceScan)
                .filter_by(ip=ip, port=port, service=service)
                .first()
            )

            if not scan:
                # Create new record
                scan = ServiceScan(
                    ip=ip,
                    port=port,
                    service=service,
                    last_scan_timestamp=timestamp,
                    service_response=response,
                )
                session.add(scan)
            elif timestamp > scan.last_scan_timestamp:
                # Only update if new timestamp is more recent
                scan.last_scan_timestamp = timestamp
                scan.service_response = response

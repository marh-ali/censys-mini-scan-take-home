"""Database models for storing scan results."""

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ServiceScan(Base):
    """Store scan results with composite primary key.

    Stores scan results with composite primary key of (ip, port, service).
    Tracks when service was last scanned and its response.
    """

    __tablename__ = "service_scans"

    # Composite primary key
    ip = Column(String, primary_key=True)
    port = Column(Integer, primary_key=True)
    service = Column(String, primary_key=True)

    last_scan_timestamp = Column(BigInteger, nullable=False)
    service_response = Column(String)

    # Index on timestamp for potential query optimization
    __table_args__ = (Index("idx_timestamp", last_scan_timestamp),)

    def __repr__(self):
        """Return string representation of ServiceScan object."""
        return f"<ServiceScan(ip={self.ip}, port={self.port}, service={self.service})>"

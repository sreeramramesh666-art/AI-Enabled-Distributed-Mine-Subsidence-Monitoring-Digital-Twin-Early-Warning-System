import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.db.models import SensorNode, NodeBaseline

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Seed baseline node
    node = SensorNode(
        node_id="TEST-NODE-01",
        name="Test Highwall Extensometer",
        latitude=23.7541,
        longitude=86.4215,
        elevation_m=180.0,
        node_type="highwall_extensometer",
        installation_location="Pit Sector Alpha",
        firmware_version="v1.0.0",
        connectivity_status="ONLINE",
        is_enabled=True
    )
    session.add(node)

    baseline = NodeBaseline(node_id="TEST-NODE-01", is_valid=False)
    session.add(baseline)
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def disk_sqlite_client():
    """Provides a TestClient connected to a real temporary disk-backed SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    disk_db_url = f"sqlite:///{temp_db_path}"
    disk_engine = create_engine(disk_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=disk_engine)
    DiskSession = sessionmaker(autocommit=False, autoflush=False, bind=disk_engine)

    # Pre-seed
    seed_db = DiskSession()
    seed_db.add(SensorNode(
        node_id="DISK-NODE-01",
        name="Disk-Backed Inclinometer",
        latitude=23.7500,
        longitude=86.4200,
        elevation_m=190.0,
        node_type="inclinometer",
        connectivity_status="ONLINE",
        is_enabled=True
    ))
    seed_db.commit()
    seed_db.close()

    def override_disk_get_db():
        db = DiskSession()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_disk_get_db
    with TestClient(app) as c:
        yield c, temp_db_path
    app.dependency_overrides.clear()

    # Cleanup disk database file
    disk_engine.dispose()
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

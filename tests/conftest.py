import pytest
import os
import sys
from pathlib import Path
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models import User, Symbol, Price, Portfolio, UserRole
from backend.app.core.security import get_password_hash, create_access_token

# Use portfolix.db for testing so all 83k price records and symbols are present
TEST_DATABASE_URL = settings.DATABASE_URL

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    
    # Ensure test user
    test_user = db.query(User).filter(User.email == "test_trader@portfolix.com").first()
    if not test_user:
        test_user = User(
            email="test_trader@portfolix.com",
            hashed_password=get_password_hash("password123"),
            full_name="Test Trader",
            role=UserRole.TRADER.value,
            is_active=True
        )
        db.add(test_user)
        db.flush()

    test_portfolio = db.query(Portfolio).filter(Portfolio.user_id == test_user.id).first()
    if not test_portfolio:
        test_portfolio = Portfolio(
            user_id=test_user.id,
            name="Test Portfolio",
            initial_cash=Decimal("1000000.00"),
            cash_balance=Decimal("1000000.00"),
            currency="INR"
        )
        db.add(test_portfolio)
        db.commit()

    db.close()
    yield

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(db_session):
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    token = create_access_token(subject=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}

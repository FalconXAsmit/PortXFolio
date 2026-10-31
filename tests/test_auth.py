import pytest
import uuid
from backend.app.core.security import verify_password, get_password_hash, create_access_token, decode_token

def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_generation():
    token = create_access_token(subject=42, role="trader")
    assert isinstance(token, str)
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["role"] == "trader"
    assert decoded["type"] == "access"

def test_auth_api_flow(client):
    unique_email = f"quant_{uuid.uuid4().hex[:8]}@test.com"
    # 1. Register new user
    reg_res = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "StrongPassword123!",
        "full_name": "Alex Quant"
    })
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == unique_email

    # 2. Login
    login_res = client.post("/api/v1/auth/login/json", json={
        "email": unique_email,
        "password": "StrongPassword123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # 3. Access protected /me endpoint
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email

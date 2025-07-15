# tests/test_recommendation.py

import pytest
from fastapi.testclient import TestClient
from main import app  # Убедись, что у тебя есть main.py, где FastAPI(app) зарегистрирован с router

client = TestClient(app)

sample_draft = {
    "user_hero": "invoker",
    "user_role": "mid",
    "aspect": "magic",
    "enemy_heroes": ["phantom_assassin", "zeus"],
    "ally_heroes": ["lina", "crystal_maiden"]
}

def test_recommend_with_openai():
    response = client.post("/api/recommend?use_openai=true", json=sample_draft)
    assert response.status_code == 200
    data = response.json()
    assert "recommended_aspect" in data
    assert "source" in data
    assert data["source"] in ["openai", "meta", "fallback"]

def test_recommend_without_openai():
    response = client.post("/api/recommend?use_openai=false", json=sample_draft)
    assert response.status_code == 200
    data = response.json()
    assert "builds" in data
    assert "suggested_heroes" in data
    assert data["source"] == "meta" or data["source"] == "fallback"

def test_recommend_invalid_data():
    invalid_draft = {
        "user_hero": "invalid_hero",
        "user_role": "mid",
        "aspect": "magic",
        "enemy_heroes": ["phantom_assassin", "zeus"],
        "ally_heroes": ["lina", "crystal_maiden"]
    }
    response = client.post("/api/recommend", json=invalid_draft)
    assert response.status_code == 200  # даже с неверным героем — fallback работает
    assert "warnings" in response.json()

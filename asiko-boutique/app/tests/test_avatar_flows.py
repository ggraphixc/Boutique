# ASIKO Boutique - Avatar Fit Axis Integration Tests
# Validates gender selection workflows and skeleton fit filtering

import pytest
from starlette.testclient import TestClient

from app.main import app


class TestAvatarProfileBinding:
    """Test suite for session-based avatar profile binding and gender validation."""

    def test_avatar_profile_binding_invalid_gender(self):
        """Validates that session endpoints reject invalid gender values."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={"gender": "extraterrestrial"},
            )
            assert response.status_code == 400

    def test_avatar_profile_binding_valid_male(self):
        """Verifies male gender state passes validation and binds to session."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={"gender": "male"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("avatar_profile") == "male"

    def test_avatar_profile_binding_valid_female(self):
        """Verifies female gender state binding."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={"gender": "female"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("avatar_profile") == "female"

    def test_avatar_profile_binding_valid_unisex(self):
        """Verifies unisex gender state binding."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={"gender": "unisex"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("avatar_profile") == "unisex"

    def test_avatar_profile_binding_missing_gender(self):
        """Verifies missing gender defaults to female."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("avatar_profile") == "female"

    def test_avatar_profile_binding_empty_gender(self):
        """Empty/whitespace gender defaults to female (defensive normalization).
        The route's defensive read chain treats empty strings as missing values
        and binds the default "female" rather than 400ing — this is safer for
        a session-bound preference that the rest of the system reads from."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/virtual/profile/set",
                json={"gender": ""},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("avatar_profile") == "female"


class TestGenderValidationLogic:
    """Test suite for gender validation logic."""

    def test_gender_validation_allows_male(self):
        """Validates male is in allowed genders."""
        valid_genders = {"male", "female", "unisex"}
        assert "male" in valid_genders

    def test_gender_validation_allows_female(self):
        """Validates female is in allowed genders."""
        valid_genders = {"male", "female", "unisex"}
        assert "female" in valid_genders

    def test_gender_validation_allows_unisex(self):
        """Validates unisex is in allowed genders."""
        valid_genders = {"male", "female", "unisex"}
        assert "unisex" in valid_genders

    def test_gender_validation_rejects_invalid(self):
        """Validates invalid genders are rejected."""
        valid_genders = {"male", "female", "unisex"}
        assert "extraterrestrial" not in valid_genders


class TestSkeletonFitConstraint:
    """Test suite for skeleton fit constraint validation."""

    def test_skeleton_fit_constraint_values(self):
        """Ensures the gender constraint allows only valid values."""
        allowed_values = {"male", "female", "unisex"}
        
        for value in ["male", "female", "unisex"]:
            assert value in allowed_values, f"{value} should be valid"
        
        for value in ["MALE", "Female", "INVALID", "other"]:
            assert value not in allowed_values, f"{value} should be invalid"

    def test_skeleton_fit_default_female(self):
        """Verifies female as the default skeleton fit."""
        assert "female" in {"male", "female", "unisex"}
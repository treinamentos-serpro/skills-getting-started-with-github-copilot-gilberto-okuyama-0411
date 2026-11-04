"""Tests for the Mergington High School FastAPI backend.

All tests follow the AAA (Arrange-Act-Assert) pattern.
"""

import copy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    """Snapshot the in-memory activities database and restore it after each test."""
    snapshot = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(snapshot)


class TestRoot:
    def test_root_redirects_to_static_index(self):
        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code in (302, 307)
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    def test_returns_all_activities(self):
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == activities
        assert "Chess Club" in data

    def test_activity_has_expected_fields(self):
        # Arrange
        expected_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        data = client.get("/activities").json()

        # Assert
        chess = data["Chess Club"]
        assert set(chess) == expected_fields
        assert isinstance(chess["participants"], list)

    def test_cache_control_header_is_no_store(self):
        # Act
        response = client.get("/activities")

        # Assert
        assert response.headers["cache-control"] == "no-store"


class TestSignup:
    def test_signup_success(self):
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Soccer Team"

        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})

        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": f"Signed up {email} for {activity}"}
        assert email in activities[activity]["participants"]

    def test_signup_unknown_activity_returns_404(self):
        # Arrange
        email = "someone@mergington.edu"

        # Act
        response = client.post("/activities/Nonexistent Club/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_returns_400(self):
        # Arrange
        email = "michael@mergington.edu"  # already a Chess Club participant
        assert email in activities["Chess Club"]["participants"]

        # Act
        response = client.post("/activities/Chess Club/signup", params={"email": email})

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"

    def test_signup_requires_email_param(self):
        # Act
        response = client.post("/activities/Chess Club/signup")

        # Assert
        assert response.status_code == 422


class TestUnregister:
    def test_unregister_success(self):
        # Arrange
        email = "michael@mergington.edu"  # already a Chess Club participant
        assert email in activities["Chess Club"]["participants"]

        # Act
        response = client.delete("/activities/Chess Club/signup", params={"email": email})

        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
        assert email not in activities["Chess Club"]["participants"]

    def test_unregister_unknown_activity_returns_404(self):
        # Arrange
        email = "someone@mergington.edu"

        # Act
        response = client.delete("/activities/Nonexistent Club/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up_returns_404(self):
        # Arrange
        email = "notsignedup@mergington.edu"
        assert email not in activities["Chess Club"]["participants"]

        # Act
        response = client.delete("/activities/Chess Club/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not signed up for this activity"


class TestSignupUnregisterFlow:
    def test_full_signup_then_unregister_cycle(self):
        # Arrange
        email = "cycle@mergington.edu"
        activity = "Art Club"

        # Act
        signup_response = client.post(f"/activities/{activity}/signup", params={"email": email})
        unregister_response = client.delete(f"/activities/{activity}/signup", params={"email": email})

        # Assert
        assert signup_response.status_code == 200
        assert unregister_response.status_code == 200
        assert email not in activities[activity]["participants"]

"""
Tests for the Mergington High School Activities API

Tests cover:
- GET /activities: Retrieving all activities
- POST /activities/{activity_name}/signup: Signing up for activities
- DELETE /activities/{activity_name}/participants/{email}: Removing participants
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """
    Create a TestClient with a fresh copy of activities data.
    This ensures each test starts with a known state and tests don't affect each other.
    """
    # Save original activities with deep copy to preserve nested structure
    original_activities = copy.deepcopy(activities)
    
    # Create test client
    test_client = TestClient(app)
    
    yield test_client
    
    # Restore original activities after test - clear and update with deep copy
    activities.clear()
    for key, value in original_activities.items():
        activities[key] = copy.deepcopy(value)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns list of all activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 9 activities
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_returns_correct_structure(self, client):
        """Test that activity objects have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of first activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
    
    def test_get_activities_initial_participants(self, client):
        """Test that initial participant lists match expected data"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have 2 initial participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
        
        # Programming Class should have 2 initial participants
        assert len(data["Programming Class"]["participants"]) == 2


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "newstudent@mergington.edu" in response.json()["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that participant is added to activity's participant list"""
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()["Chess Club"]["participants"])
        
        # Sign up
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        # Get updated list
        response = client.get("/activities")
        updated_count = len(response.json()["Chess Club"]["participants"])
        
        assert updated_count == initial_count + 1
        assert "newstudent@mergington.edu" in response.json()["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test error when signing up for non-existent activity"""
        response = client.post(
            "/activities/Fake Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_duplicate_email_same_activity(self, client):
        """Test error when same student signs up twice for same activity"""
        # First signup succeeds
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Second signup fails
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_same_email_different_activities(self, client):
        """Test that same student can sign up for different activities"""
        email = "student@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class (should succeed)
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify in both activities
        response = client.get("/activities")
        activities_data = response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]
    
    def test_signup_multiple_students_same_activity(self, client):
        """Test that multiple different students can sign up for same activity"""
        # Sign up first student
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Sign up second student
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        assert response2.status_code == 200
        
        # Verify both in activity
        response = client.get("/activities")
        participants = response.json()["Chess Club"]["participants"]
        assert "student1@mergington.edu" in participants
        assert "student2@mergington.edu" in participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_successful(self, client):
        """Test successful removal of participant"""
        # Sign up first
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        # Remove
        response = client.delete(
            "/activities/Chess Club/participants/student@mergington.edu"
        )
        
        assert response.status_code == 200
        assert "Removed" in response.json()["message"]
    
    def test_remove_participant_from_list(self, client):
        """Test that participant is removed from activity's list"""
        email = "student@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Verify they're in the list
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Remove
        client.delete(
            "/activities/Chess Club/participants/student@mergington.edu"
        )
        
        # Verify they're removed
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]
    
    def test_remove_participant_not_found(self, client):
        """Test error when removing non-existent participant"""
        response = client.delete(
            "/activities/Chess Club/participants/nonexistent@mergington.edu"
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_remove_participant_activity_not_found(self, client):
        """Test error when activity doesn't exist"""
        response = client.delete(
            "/activities/Fake Activity/participants/student@mergington.edu"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_remove_participant_twice_fails(self, client):
        """Test error when trying to remove same participant twice"""
        email = "student@mergington.edu"
        
        # Sign up and remove
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        response1 = client.delete(
            "/activities/Chess Club/participants/student@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Try to remove again
        response2 = client.delete(
            "/activities/Chess Club/participants/student@mergington.edu"
        )
        assert response2.status_code == 400
        assert "not signed up" in response2.json()["detail"].lower()
    
    def test_remove_participant_doesnt_affect_others(self, client):
        """Test that removing one participant doesn't affect others"""
        # Sign up two students
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        
        # Remove first student
        client.delete(
            "/activities/Chess Club/participants/student1@mergington.edu"
        )
        
        # Verify second student still there
        response = client.get("/activities")
        participants = response.json()["Chess Club"]["participants"]
        assert "student1@mergington.edu" not in participants
        assert "student2@mergington.edu" in participants


class TestIntegration:
    """Integration tests combining multiple operations"""
    
    def test_signup_then_view_then_remove(self, client):
        """Test complete flow: signup, view, remove"""
        email = "student@mergington.edu"
        activity = "Chess Club"
        
        # Initially not in activity
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # View and confirm added
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Remove
        response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert response.status_code == 200
        
        # View and confirm removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signup_and_remove_operations(self, client):
        """Test multiple signup and remove operations in sequence"""
        activity = "Chess Club"
        students = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu"
        ]
        
        # Sign up all students
        for student in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": student}
            )
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        for student in students:
            assert student in response.json()[activity]["participants"]
        
        # Remove second student
        response = client.delete(
            f"/activities/{activity}/participants/{students[1]}"
        )
        assert response.status_code == 200
        
        # Verify correct state
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert students[0] in participants
        assert students[1] not in participants
        assert students[2] in participants

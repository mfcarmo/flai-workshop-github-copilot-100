"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_html(self, client):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        
    def test_get_activities_structure(self, client, reset_activities):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
        

class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup with non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_already_registered(self, client, reset_activities):
        """Test signup when student is already registered"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_activity_full(self, client, reset_activities):
        """Test signup when activity is full"""
        # Fill up Math Olympiad (max_participants: 10)
        for i in range(8):  # Already has 2 participants
            response = client.post(
                f"/activities/Math%20Olympiad/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Try to add one more (11th participant)
        response = client.post(
            "/activities/Math%20Olympiad/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        assert "Activity is full" in response.json()["detail"]
    
    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test.user%2Bspecial@mergington.edu"
        )
        assert response.status_code == 200
        

class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        # First verify the student is registered
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        
        # Unregister the student
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregister with non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_student_not_registered(self, client, reset_activities):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_allows_new_signup(self, client, reset_activities):
        """Test that unregistering frees up a spot for new signup"""
        # Fill up Math Olympiad
        for i in range(8):
            response = client.post(
                f"/activities/Math%20Olympiad/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Verify it's full
        response = client.post(
            "/activities/Math%20Olympiad/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        
        # Unregister one student
        response = client.delete(
            "/activities/Math%20Olympiad/unregister?email=student0@mergington.edu"
        )
        assert response.status_code == 200
        
        # Now the new signup should succeed
        response = client.post(
            "/activities/Math%20Olympiad/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for complete user flows"""
    
    def test_complete_signup_and_unregister_flow(self, client, reset_activities):
        """Test complete flow of signup and unregister"""
        email = "testflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant was added
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity]["participants"])
        assert after_signup_count == initial_count + 1
        assert email in after_signup.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify participant was removed
        after_unregister = client.get("/activities")
        after_unregister_count = len(after_unregister.json()[activity]["participants"])
        assert after_unregister_count == initial_count
        assert email not in after_unregister.json()[activity]["participants"]
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "multitask@mergington.edu"
        
        activities = ["Chess Club", "Programming Class", "Art Club"]
        
        for activity in activities:
            response = client.post(
                f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities:
            assert email in all_activities[activity]["participants"]

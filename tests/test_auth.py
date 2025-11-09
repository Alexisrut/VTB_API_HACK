"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient


class TestRegistration:
    """Test user registration"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "phone_number": "+79991234568",
                "first_name": "New",
                "last_name": "User",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["phone_number"] == "+79991234568"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["is_active"] is True
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email"""
        response = await client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "phone_number": "+79991234569",
                "first_name": "Another",
                "last_name": "User",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 409
        assert "уже зарегистрирован" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_phone(self, client: AsyncClient, test_user):
        """Test registration with duplicate phone number"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "different@example.com",
                "phone_number": test_user.phone_number,
                "first_name": "Another",
                "last_name": "User",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 409
        assert "уже зарегистрирован" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "phone_number": "+79991234570",
                "first_name": "Test",
                "last_name": "User",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_invalid_phone(self, client: AsyncClient):
        """Test registration with invalid phone number"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "phone_number": "1234567890",  # Missing +7 prefix
                "first_name": "Test",
                "last_name": "User",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "phone_number": "+79991234571",
                "first_name": "Test",
                "last_name": "User",
                "password": "weak"  # Too short, no uppercase, no digit
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        response = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                # Missing other required fields
            }
        )
        assert response.status_code == 422


class TestLogin:
    """Test user login"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login"""
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with non-existent email"""
        response = await client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPass123"
            }
        )
        assert response.status_code == 401
        assert "неверный" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with wrong password"""
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123"
            }
        )
        assert response.status_code == 401
        assert "неверный" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session, test_user):
        """Test login with inactive user"""
        test_user.is_active = False
        await db_session.commit()
        
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"
            }
        )
        assert response.status_code == 403
        assert "неактивен" in response.json()["detail"].lower()


class TestRefreshToken:
    """Test token refresh"""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh the token
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token"""
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid_token"
            }
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """Test getting current user info"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client: AsyncClient, test_user):
        """Test getting current user info with valid token"""
        # Login first
        login_response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"
            }
        )
        access_token = login_response.json()["access_token"]
        
        # Get user info
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting user info without token"""
        response = await client.get("/users/me")
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting user info with invalid token"""
        response = await client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


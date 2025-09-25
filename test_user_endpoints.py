"""Quick test of the new user management endpoints."""

from uuid import uuid4

import httpx


async def test_endpoints():
    base_url = "http://localhost:8000"

    # You would need to adjust these with valid JWT tokens and tenant IDs from your system
    headers = {"Authorization": "Bearer YOUR_JWT_TOKEN_HERE", "Content-Type": "application/json"}

    tenant_id = str(uuid4())  # Replace with actual tenant ID

    async with httpx.AsyncClient() as client:
        # Test 1: List users
        print("Testing GET /tenants/{tenant_id}/users")
        response = await client.get(
            f"{base_url}/tenants/{tenant_id}/users",
            headers=headers,
            params={"page": 1, "limit": 10},
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Test 2: List users with filters
        print("Testing GET /tenants/{tenant_id}/users with filters")
        response = await client.get(
            f"{base_url}/tenants/{tenant_id}/users",
            headers=headers,
            params={"page": 1, "limit": 5, "role": "admin", "search": "test"},
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Test 3: Remove membership (replace user_id with actual ID)
        user_id = str(uuid4())  # Replace with actual user ID
        print(f"Testing DELETE /tenants/{tenant_id}/users/{user_id}/membership")
        response = await client.delete(
            f"{base_url}/tenants/{tenant_id}/users/{user_id}/membership",
            headers=headers,
            json={"reason": "User requested removal"},
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    print("This is a template test file. You need to:")
    print("1. Start your FastAPI server")
    print("2. Get valid JWT tokens and tenant/user IDs")
    print("3. Replace the placeholder values in this script")
    print("4. Run this script to test the endpoints")
    print()
    print("Example usage:")
    print("python -m uvicorn src.interfaces.http.main:app --reload")
    print("# Then in another terminal:")
    print("python test_user_endpoints.py")

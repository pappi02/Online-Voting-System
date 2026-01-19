#!/usr/bin/env python
"""
Test script for authentication API endpoints
Tests registration, login, OTP, and profile management
"""
import requests
import json
import sys

BASE_URL = 'http://localhost:8000/api/v1/accounts'
TEST_USER = {
    'email': 'testvoter@example.com',
    'password': 'SecurePass123!',
    'first_name': 'Test',
    'last_name': 'Voter',
    'phone_number': '+254712345678',
    'national_id': 'ID123456789',
    'institution': 'Test University',
    'department': 'Computer Science'
}

def print_response(title, response):
    """Print formatted API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_registration():
    """Test user registration endpoint"""
    url = f"{BASE_URL}/auth/register/"
    data = {
        **TEST_USER,
        'password_confirm': TEST_USER['password']
    }
    response = requests.post(url, json=data)
    print_response("1. USER REGISTRATION", response)
    return response.status_code == 201

def test_login():
    """Test login endpoint"""
    url = f"{BASE_URL}/auth/login/"
    data = {
        'email': 'admin@ivotesystems.com',
        'password': 'Admin@12345'
    }
    response = requests.post(url, json=data)
    print_response("2. USER LOGIN (Admin)", response)
    
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('access'), tokens.get('refresh')
    return None, None

def test_profile(access_token):
    """Test profile endpoint"""
    url = f"{BASE_URL}/profile/me/"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    print_response("3. GET USER PROFILE", response)
    return response.status_code == 200

def test_send_otp(access_token):
    """Test OTP sending endpoint"""
    url = f"{BASE_URL}/otp/send/"
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {
        'method': 'email',
        'purpose': 'login'
    }
    response = requests.post(url, json=data, headers=headers)
    print_response("4. SEND OTP", response)
    return response.status_code == 200

def test_token_refresh(refresh_token):
    """Test token refresh endpoint"""
    url = f"{BASE_URL}/auth/refresh/"
    data = {'refresh': refresh_token}
    response = requests.post(url, json=data)
    print_response("5. REFRESH TOKEN", response)
    return response.status_code == 200

def test_invalid_login():
    """Test login with invalid credentials"""
    url = f"{BASE_URL}/auth/login/"
    data = {
        'email': 'nonexistent@example.com',
        'password': 'WrongPassword123'
    }
    response = requests.post(url, json=data)
    print_response("6. INVALID LOGIN (Should Fail)", response)
    return response.status_code == 401 or response.status_code == 400

def main():
    """Run all tests"""
    print("=" * 60)
    print("iVote Systems - Authentication API Tests")
    print("=" * 60)
    print("\nMake sure the Django server is running on http://localhost:8000")
    print("Press Enter to start tests...")
    input()
    
    results = []
    
    # Test 1: Registration
    print("\n\n" + "="*60)
    print("TESTING AUTHENTICATION FLOW")
    print("="*60)
    
    results.append(("Registration", test_registration()))
    
    # Test 2: Login
    access_token, refresh_token = test_login()
    results.append(("Login", access_token is not None))
    
    if access_token:
        # Test 3: Profile
        results.append(("Get Profile", test_profile(access_token)))
        
        # Test 4: Send OTP
        results.append(("Send OTP", test_send_otp(access_token)))
        
        # Test 5: Token Refresh
        if refresh_token:
            results.append(("Token Refresh", test_token_refresh(refresh_token)))
    
    # Test 6: Invalid Login
    results.append(("Invalid Login", test_invalid_login()))
    
    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    print("="*60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n\n✗ ERROR: Could not connect to Django server")
        print("Make sure the server is running: python manage.py runserver")
        sys.exit(1)

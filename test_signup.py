import requests

url = "http://localhost:8000/api/v1/auth/signup"
data = {
    "name": "홍길동",
    "email": "testuser_api@example.com",
    "password": "password123!",
    "gender": "male",
    "birthday": "1990-01-01",
    "phone_number": "010-1234-5678"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")

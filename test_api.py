import requests
import json

url = "http://127.0.0.1:8000/route/comprehensive"
payload = {
    "origin": [28.6139, 77.2090],
    "destination": [28.5355, 77.3910],
    "city_name": "Delhi",
    "weather": "Rain"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

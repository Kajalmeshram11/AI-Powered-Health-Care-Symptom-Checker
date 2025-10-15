import requests
import json

# Test the symptom analysis API
def test_symptom_api():
    url = "http://localhost:5000/api/analyze"
    data = {
        "symptoms": "I have a high fever of 102°F, headache, and body aches for the past 2 days",
        "age": "25",
        "gender": "male",
        "duration": "1-3days",
        "severity": "moderate",
        "session_id": "test_session"
    }

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_symptom_api()

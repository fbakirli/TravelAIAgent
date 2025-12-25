import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get your API key from environment
api_key = os.getenv("SERPAPI_KEY")

if not api_key:
    raise ValueError("❌ SERPAPI_KEY not found in environment variables")

params = {
    "engine": "google_flights",
    "departure_id": "GYD",  # Baku
    "arrival_id": "IST",    # Istanbul
    "departure_date": "2026-01-10",
    "currency": "USD",
    "api_key": api_key
}

res = requests.get("https://serpapi.com/search", params=params)

print("Status:", res.status_code)
print("Response JSON:")
print(res.json())

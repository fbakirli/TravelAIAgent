from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, Tuple

import ollama
import streamlit as st

from agents.travel_agent import TravelAgent
from utils.date_parser import extract_first_date, parse_date

SYSTEM_PROMPT = """
You are a multilingual travel request parser. Given a user's message about a trip (in ANY language), respond with ONLY a JSON object using this exact shape:
{
  "language": "<ISO 639-1 code of the user's message; default to en if unsure>",
  "origin_city": "<city name in English or IATA code; leave empty if unknown>",
  "destinations": ["<city name in English or IATA code>", "..."],
  "num_days": <integer>,
  "num_locations": <integer>,
  "total_budget": <number>,
  "start_date": "<YYYY-MM-DD>" or null,
  "end_date": "<YYYY-MM-DD>" or null
}
Rules:
- Detect the input language first and set the language field (use en when uncertain).
- Input may be in Turkish, Azerbaijani, Italian, or any other language; always parse correctly.
- Recognize month/day expressions in any language; always output ISO YYYY-MM-DD dates.
- You will be given today's date; if the user omits the year, pick the next valid occurrence on or after today using that month/day.
- Prefer IATA airport codes; otherwise use the common English city name so downstream tools work.
- Respond with valid JSON only; no markdown or extra text.
- start_date and end_date must be ISO format YYYY-MM-DD or null.
- If the request is not about travel, respond with {"error":"non_travel","language":"<detected or en>"}.
- If origin_city is missing, keep it empty so the app can default to GYD.
- If any value is unknown, use null (for dates) or 0/[]/"" as appropriate.
- If multiple destinations are mentioned, list them in the order they were mentioned.
- Do not add comments or explanations; output must be valid JSON.
"""

TRANSLATION_PROMPT = """
You are a translation layer for a travel assistant. Translate the assistant's message into the target language while preserving meaning, numbers, currency symbols, airport codes, and markdown formatting. Keep IATA/currency codes unchanged. If the target language is English (code: en) or missing, return the text unchanged.
"""

TRAVEL_KEYWORDS = [
    "travel",
    "trip",
    "vacation",
    "holiday",
    "flight",
    "flights",
    "fly",
    "flying",
    "plane",
    "planes",
    "airfare",
    "airfares",
    "hotel",
    "hotels",
    "stay",
    "staying",
    "lodging",
    "itinerary",
    "destination",
    "destinations",
    "tour",
    "tours",
    "journey",
    "journeys",
    "airport",
    "airports",
    "airline",
    "airlines",
    "visit",
    "visiting",
    "go to",
    "fly to",
    "stay in",
    "city",
    "cities",
    "country",
    "countries",
    "weekend",
    "budget",
    "ticket",
    "tickets",
    "book",
    "booking",
    "days",
    "nights",
    "round trip",
    "one way",
    "morning flight",
    "night flight",
    "red-eye",
    "red eye",
    "departure",
    "arrival",
    "layover",
    "luggage",
    "carry-on",
    "passport",
    "visa",
    "resort",
    "beach",
    "cruise",
    "road trip",
    "car rental",
    "rent a car",
    "drive to",
    "train",
    "rail",
]

MONTH_KEYWORDS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

APP_STYLE = """
<style>
:root {
  --bg: #f6f8fb;
  --panel: #ffffff;
  --panel-2: #eef2fa;
  --text: #0f172a;
  --muted: #475569;
  --accent: #0ea5e9;
  --accent-2: #22c55e;
}
html, body {
  background: var(--bg);
  color: var(--text);
}
.main .block-container {
  padding: 1.5rem 2rem 3rem;
  background: var(--bg);
}
.hero {
  background: linear-gradient(135deg, rgba(14,165,233,0.18), rgba(34,197,94,0.14));
  border: 1px solid rgba(14,165,233,0.12);
  padding: 1.25rem 1.5rem;
  border-radius: 14px;
  margin-bottom: 1rem;
}
.hero h1 {
  margin: 0;
  color: var(--text);
}
.hero p {
  margin: 0.25rem 0 0;
  color: var(--muted);
}
[data-testid="stChatMessage"] {
  border: 1px solid rgba(15,23,42,0.08);
  background: var(--panel);
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
}
[data-testid="stChatMessage"]:hover {
  border-color: rgba(14,165,233,0.35);
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
  margin-bottom: 0.2rem;
}
.chat-subtle {
  color: var(--muted);
  font-size: 0.92rem;
}
hr {
  border: none;
  border-top: 1px solid rgba(15,23,42,0.08);
}
</style>
"""


@st.cache_resource
def get_agent() -> TravelAgent:
    return TravelAgent()


def is_travel_related(text: str) -> bool:
    lower = text.lower()
    has_travel_word = any(keyword in lower for keyword in TRAVEL_KEYWORDS)
    has_month = any(month in lower for month in MONTH_KEYWORDS)
    has_budget = "budget" in lower or "$" in lower or "usd" in lower
    has_flight_term = any(word in lower for word in ["flight", "flights", "fly", "plane", "planes", "airfare", "airfares", "airline", "airlines"])
    has_time_pref = has_flight_term and any(t in lower for t in ["morning", "evening", "night", "late", "overnight", "afternoon", "early"])
    return has_travel_word or has_month or has_budget or has_time_pref


def parse_preferences(user_input: str) -> Tuple[Dict[str, Any], str]:
    language = "en"
    today_iso = date.today().isoformat()
    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {
                "role": "user",
                "content": (
                    f"Today is {today_iso}. Parse this travel request: {user_input}"
                ),
            },
        ],
    )

    content = response.get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("Empty model response.")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        # Try to salvage a JSON object from the response
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                raise ValueError("Model did not return valid JSON.") from exc
        else:
            raise ValueError("Model did not return valid JSON.") from exc

    lang_raw = str(data.get("language") or "").strip().lower()
    if lang_raw:
        language = lang_raw.split("-")[0]
    if len(language) != 2:
        language = "en"

    if data.get("error") == "non_travel":
        err = ValueError("I can only help with travel-related questions.")
        setattr(err, "language", language)
        raise err

    destinations = data.get("destinations") or []
    num_locations = data.get("num_locations")
    if num_locations in (None, "") and destinations:
        num_locations = len(destinations)

    raw_start = data.get("start_date")
    raw_end = data.get("end_date")

    parsed_start = None
    parsed_end = None
    if raw_start not in ("", "null", None):
        parsed_start = parse_date(str(raw_start))
    if raw_end not in ("", "null", None):
        parsed_end = parse_date(str(raw_end))

    # Fallback: detect dates directly from the user's text (handles Turkish/Azerbaijani month names)
    fallback_start = extract_first_date(user_input)
    if fallback_start:
        if parsed_start is None or (
            parsed_start.month != fallback_start.month or parsed_start.day != fallback_start.day
        ):
            parsed_start = fallback_start
            # If the model produced an end date earlier than the inferred start, drop it.
            if parsed_end and parsed_end < parsed_start:
                parsed_end = None

    prefs = {
        "origin_city": data.get("origin_city") or "GYD",
        "destinations": destinations,
        "num_days": data.get("num_days"),
        "num_locations": num_locations,
        "total_budget": data.get("total_budget"),
        "start_date": parsed_start.isoformat() if parsed_start else None,
        "end_date": parsed_end.isoformat() if parsed_end else None,
    }
    return prefs, language


def translate_response(message: str, target_language: str) -> str:
    normalized = (target_language or "en").split("-")[0].lower()
    if normalized == "en" or len(normalized) != 2:
        return message

    try:
        translation = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT.strip()},
                {
                    "role": "user",
                    "content": (
                        f"Target language: {normalized}\n"
                        "Translate the following message without changing markdown structure:\n"
                        f"{message}"
                    ),
                },
            ],
        )
        translated = translation.get("message", {}).get("content", "").strip()
        return translated or message
    except Exception:
        return message


st.set_page_config(page_title="Travel Planner", page_icon="✈️")
st.markdown(APP_STYLE, unsafe_allow_html=True)
st.markdown(
    """
    <div class="hero">
      <h1>Travel Planner Chatbot</h1>
      <p>Plan multi-city trips with real flights, hotels, and daily itineraries. Share your origin, destinations, dates, and budget.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Tell me about your trip (destination, dates, budget), and I'll plan it.",
        }
    ]

for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])

user_prompt = st.chat_input("Describe your trip request")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.chat_message("user").markdown(user_prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Parsing your request and planning your trip..._")
        input_language = "en"
        try:
            prefs_dict, input_language = parse_preferences(user_prompt)
            agent = get_agent()
            result = agent.run(prefs_dict)
            translated_result = translate_response(result, input_language)
            placeholder.markdown(translated_result)
            st.session_state.messages.append({"role": "assistant", "content": translated_result})
        except Exception as exc:
            error_msg = (
                "Sorry, I couldn't process that. Please share travel details like destination, dates, and budget. "
                f"({exc})"
            )
            translated_error = translate_response(error_msg, getattr(exc, "language", input_language))
            placeholder.markdown(translated_error)
            st.session_state.messages.append({"role": "assistant", "content": translated_error})

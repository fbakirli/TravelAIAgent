# utils/airport_codes.py

CITY_TO_AIRPORT = {
    # Azerbaijan
    "Baku": "GYD",

    # Turkey
    "Istanbul": "IST",   # or "SAW" if you prefer
    "Ankara": "ESB",
    "Izmir": "ADB",

    # Georgia
    "Tbilisi": "TBS",

    # UAE
    "Dubai": "DXB",
    "Abu Dhabi": "AUH",

    # Europe
    "Amsterdam": "AMS",
    "Athens": "ATH",
    "Barcelona": "BCN",
    "Berlin": "BER",
    "Brussels": "BRU",
    "Budapest": "BUD",
    "Copenhagen": "CPH",
    "Dublin": "DUB",
    "Frankfurt": "FRA",
    "Helsinki": "HEL",
    "Lisbon": "LIS",
    "London": "LHR",
    "Madrid": "MAD",
    "Munich": "MUC",
    "Oslo": "OSL",
    "Paris": "CDG",
    "Prague": "PRG",
    "Rome": "FCO",
    "Stockholm": "ARN",
    "Vienna": "VIE",
    "Warsaw": "WAW",
    "Zurich": "ZRH",

    # UK extras
    "Manchester": "MAN",

    # Middle East
    "Doha": "DOH",
    "Jeddah": "JED",
    "Kuwait City": "KWI",
    "Muscat": "MCT",
    "Riyadh": "RUH",

    # Asia
    "Bangkok": "BKK",
    "Hong Kong": "HKG",
    "Jakarta": "CGK",
    "Kuala Lumpur": "KUL",
    "Manila": "MNL",
    "Mumbai": "BOM",
    "New Delhi": "DEL",
    "Seoul": "ICN",
    "Shanghai": "PVG",
    "Singapore": "SIN",
    "Taipei": "TPE",
    "Tokyo": "HND",  # or "NRT"

    # North America
    "Atlanta": "ATL",
    "Boston": "BOS",
    "Chicago": "ORD",
    "Dallas": "DFW",
    "Denver": "DEN",
    "Houston": "IAH",
    "Los Angeles": "LAX",
    "New York": "JFK",
    "Miami": "MIA",
    "Montreal": "YUL",
    "San Francisco": "SFO",
    "Seattle": "SEA",
    "Toronto": "YYZ",
    "Vancouver": "YVR",
    "Washington D.C.": "IAD",

    # Latin America
    "Buenos Aires": "EZE",
    "Mexico City": "MEX",
    "Rio de Janeiro": "GIG",
    "Sao Paulo": "GRU",

    # Africa
    "Cairo": "CAI",
    "Cape Town": "CPT",
    "Johannesburg": "JNB",
    "Lagos": "LOS",
    "Nairobi": "NBO",

    # Oceania
    "Auckland": "AKL",
    "Melbourne": "MEL",
    "Sydney": "SYD",
}

IATA_ALIASES = {
    # City codes to primary airports
    "BAK": "GYD",  # Baku city code -> Heydar Aliyev
    "ROM": "FCO",  # Rome city code -> Fiumicino
    "PAR": "CDG",  # Paris city code -> Charles de Gaulle
    "NYC": "JFK",  # NYC metro -> JFK
    "LON": "LHR",  # London metro -> Heathrow
}

def to_airport_code(value: str) -> str:
    v = (value or "").strip()

    # already an IATA code
    if len(v) == 3 and v.isupper():
        return IATA_ALIASES.get(v, v)

    if v in CITY_TO_AIRPORT:
        return CITY_TO_AIRPORT[v]

    titled = v.title()
    if titled in CITY_TO_AIRPORT:
        return CITY_TO_AIRPORT[titled]

    # fail loudly so you immediately know what mapping is missing
    raise ValueError(f"No airport code mapping found for: {v}")

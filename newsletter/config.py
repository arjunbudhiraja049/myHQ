"""
Central configuration for myHQ newsletter regions, areas, and news sources.
"""

# ---------------------------------------------------------------------------
# REGIONS
# Each region maps to a set of search terms (for Google News RSS) and a list
# of micro-markets / sub-areas that subscribers cater to.
# ---------------------------------------------------------------------------
REGIONS = {
    "bangalore": {
        "display": "Bengaluru",
        "search_terms": [
            "office leasing Bangalore real estate",
            "commercial real estate Bengaluru",
            "IT park Whitefield Outer Ring Road",
            "office space Koramangala HSR Hebbal",
        ],
        "areas": [
            "Whitefield",
            "Electronic City",
            "Outer Ring Road",
            "Koramangala",
            "HSR Layout",
            "Hebbal",
            "Marathahalli",
            "MG Road Brigade Road",
            "Sarjapur Road",
            "Bagmane Tech Park",
        ],
    },
    "delhi_ncr": {
        "display": "Delhi NCR",
        "search_terms": [
            "office leasing Delhi NCR commercial real estate",
            "office space Gurgaon Gurugram",
            "commercial real estate Noida Greater Noida",
            "office leasing Aerocity Cyber City",
        ],
        "areas": [
            "Gurgaon Cyber City",
            "Gurgaon Golf Course Road",
            "Noida Sector 62",
            "Noida Expressway",
            "Aerocity",
            "Connaught Place",
            "Nehru Place",
            "Faridabad",
            "Manesar",
            "Greater Noida",
        ],
    },
    "chennai_hyderabad": {
        "display": "Chennai & Hyderabad",
        "search_terms": [
            "office leasing Chennai commercial real estate",
            "OMR Chennai IT corridor office space",
            "office leasing Hyderabad commercial real estate",
            "HITEC City Gachibowli office space",
        ],
        "areas": [
            "HITEC City",
            "Gachibowli",
            "Madhapur",
            "Banjara Hills",
            "Financial District Hyderabad",
            "OMR Sholinganallur",
            "OMR Perungudi",
            "Ambattur Industrial Estate",
            "Chennai CBD Anna Salai",
            "Taramani",
        ],
    },
    "mumbai_pune": {
        "display": "Mumbai & Pune",
        "search_terms": [
            "office leasing Mumbai commercial real estate",
            "BKC Lower Parel Andheri office space",
            "office leasing Pune commercial real estate",
            "Hinjewadi Kharadi Pune IT park",
        ],
        "areas": [
            "BKC Bandra Kurla Complex",
            "Lower Parel",
            "Andheri MIDC",
            "Powai",
            "Nariman Point CBD",
            "Thane",
            "Navi Mumbai",
            "Hinjewadi Pune",
            "Kharadi Pune",
            "Viman Nagar Pune",
        ],
    },
}

# ---------------------------------------------------------------------------
# ADDITIONAL RSS SOURCES (fixed feeds for Indian real estate news)
# ---------------------------------------------------------------------------
FIXED_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/industry/services/property-/-cstruction/rss.cms",
    "https://www.business-standard.com/rss/real-estate.rss",
]

# Google News RSS base URL — region-specific search terms are appended
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

# ---------------------------------------------------------------------------
# NEWSLETTER SETTINGS
# ---------------------------------------------------------------------------
NEWSLETTER_SETTINGS = {
    "max_articles_per_region": 40,   # fetch cap before AI vetting
    "min_articles_per_section": 1,   # at least 1 article per section
    "lookback_days": 14,             # fortnight window
    "edition_name": "myHQ Market Insights",
}

# ---------------------------------------------------------------------------
# SECTION LABELS (used in template rendering)
# ---------------------------------------------------------------------------
SECTIONS = {
    "transactions":       {"icon": "🏢", "label": "Transactions & Deals"},
    "developer_updates":  {"icon": "🏗️", "label": "Developer Updates"},
    "people_movement":    {"icon": "👥", "label": "People on the Move"},
    "market_trends":      {"icon": "📊", "label": "Market Pulse"},
    "quick_bytes":        {"icon": "⚡", "label": "Quick Bytes"},
}

"""
Renders a sample newsletter to preview.html so you can see
exactly what the email will look like — no API key needed.

Run: python3 preview_email.py
Then open preview.html in your browser.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(".env")

from newsletter.email_sender import render_html

SAMPLE_NEWSLETTER = {
    "region_display": "Bengaluru",
    "edition": "Edition #27 | Apr 08 – Apr 22, 2026",
    "intro": "Bengaluru's office market is firing on all cylinders this fortnight. With Flipkart anchoring a landmark ORR deal and Embassy REIT posting 94% occupancy, demand from GCCs and homegrown tech is showing no signs of slowing. HSR and Hebbal are the micro-markets to watch.",
    "market_pulse": "Bengaluru recorded 14.2 mn sq ft of gross absorption in FY26 — the highest in five years. Outer Ring Road led with a 38% share, followed by Whitefield at 22%. Vacancy across Grade-A assets has tightened to 11.4%, keeping upward pressure on rentals. GCC demand now accounts for 44% of all leasing activity, displacing pure-play IT/ITeS as the primary occupier segment.",
    "transactions": [
        {
            "headline": "Flipkart signs 2.5 lakh sq ft lease at Prestige Tech Park, ORR",
            "body": "Flipkart has executed a 9-year lease at Prestige Tech Park on Outer Ring Road for 2.5 lakh sq ft. The deal is valued at approximately ₹180 crore over the tenure. This will consolidate Flipkart's engineering and operations teams currently spread across three Bengaluru locations.",
            "takeaway": "Signals continued consolidation among large tech occupiers seeking quality, campus-style environments on ORR.",
        },
        {
            "headline": "Google pre-leases 3 lakh sq ft at RMZ Nexity, Hebbal",
            "body": "Google India has signed a pre-lease for 3 lakh sq ft at RMZ Nexity in Hebbal — its third major Bengaluru expansion in 24 months. The space will house Google's cloud infrastructure and AI research teams, expected to be operational by Q2 FY27.",
            "takeaway": "Hebbal is cementing its status as a GCC corridor, with Google joining a growing list of global tech giants anchoring the micro-market.",
        },
    ],
    "developer_updates": [
        {
            "headline": "Prestige Tech Cloud, Whitefield — 65% pre-leased ahead of Q3 FY27 delivery",
            "body": "Prestige Group's 1.8 mn sq ft Tech Cloud project in Whitefield is 65% pre-leased with nine months to delivery. The project is targeting LEED Platinum certification and includes a dedicated GCC floor plate configuration.",
            "takeaway": "Strong pre-leasing momentum confirms Whitefield's revival as a preferred Grade-A destination post-metro connectivity.",
        },
    ],
    "people_movement": [
        {
            "headline": "Sattva Group appoints Rajesh Nair as CEO — Commercial Real Estate",
            "body": "Rajesh Nair, formerly Senior Director at CBRE India with 18 years of CRE experience, joins Sattva Group as CEO of its commercial vertical. He will lead a 10 mn sq ft development pipeline across Bengaluru and Hyderabad.",
            "takeaway": "Hiring a CBRE veteran to lead commercial ops signals Sattva's intent to aggressively pursue institutional-grade leasing mandates.",
        },
    ],
    "quick_bytes": [
        "Embassy REIT reports 94% occupancy across Bengaluru assets in Q4 FY26 — strongest quarter in two years.",
        "Koramangala office vacancy drops to 12% from 18% a year ago, driven by D2C and fintech startup demand.",
        "HSR Layout rentals touch ₹90–95/sqft/month, up 8% YoY — tightest supply in the micro-market since 2019.",
        "Bagmane Tech Park completes Phase 4 (4.2 lakh sq ft) — fully leased to a single BFSI GCC.",
        "Bengaluru airport zone (Devanahalli) attracting early-stage interest from aerospace and defence R&D occupiers.",
    ],
    "area_spotlights": {
        "HSR Layout": "HSR Layout is seeing its tightest supply cycle in six years. With vacancy at 7% and rentals at ₹90–95/sqft/month, the micro-market is drawing fintech, SaaS, and consumer tech companies for its unmatched talent density. Expect landlords to hold firm on pricing through H1 FY27.",
        "Whitefield": "Whitefield's fortunes have turned decisively since the metro opened. Prestige Tech Cloud's strong pre-leasing and a pipeline of 3.2 mn sq ft under construction signal that Whitefield is reclaiming its position as Bengaluru's largest office sub-market. Watch for rental rerating in legacy Grade-B stock.",
        "Outer Ring Road": "ORR continues to dominate with 38% of city-wide absorption. The Flipkart deal is the marquee transaction, but a dozen sub-50,000 sq ft GCC deals underpin the broad-based demand. New supply additions are being absorbed within 6–9 months of delivery — keep an eye on Sarjapur Road extension emerging as overflow.",
    },
    "outro": "The next fortnight brings Q1 FY27 earnings from the major REITs — watch for commentary on pre-leasing pipelines and rental guidance. The data suggests Bengaluru's demand cycle has at least 18 more months of runway.",
}

SAMPLE_SUBSCRIBER = {
    "name": "Arjun",
    "area": "HSR Layout",
    "region": "bangalore",
}

if __name__ == "__main__":
    region_arg = sys.argv[1] if len(sys.argv) > 1 else "bangalore"

    html = render_html(SAMPLE_NEWSLETTER, SAMPLE_SUBSCRIBER)
    out = Path("preview.html")
    out.write_text(html, encoding="utf-8")
    print(f"✅ Preview saved to: {out.resolve()}")
    print("   Open preview.html in your browser to see the email design.")

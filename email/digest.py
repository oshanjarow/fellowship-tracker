#!/usr/bin/env python3
"""Generate and send biweekly email digest via Gmail SMTP."""

import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, List

# Load .env file if present
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR.parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# Paths
DATA_DIR = SCRIPT_DIR.parent / "data"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"


def load_opportunities() -> List[dict]:
    """Load opportunities from JSON file."""
    if OPPORTUNITIES_FILE.exists():
        with open(OPPORTUNITIES_FILE) as f:
            return json.load(f)
    return []


def parse_deadline(deadline_str: Optional[str]) -> Optional[datetime]:
    """Try to parse a deadline string into a datetime."""
    if not deadline_str:
        return None
    from dateutil import parser
    try:
        return parser.parse(deadline_str, fuzzy=True)
    except (ValueError, TypeError):
        return None


def get_closing_soon(opportunities: List[dict], days: int = 14) -> List[dict]:
    """Get opportunities closing within the next N days."""
    cutoff = datetime.now() + timedelta(days=days)
    closing = []

    for opp in opportunities:
        deadline = parse_deadline(opp.get("deadline"))
        if deadline and datetime.now() < deadline <= cutoff:
            opp["_parsed_deadline"] = deadline
            closing.append(opp)

    return sorted(closing, key=lambda x: x["_parsed_deadline"])


def get_new_opportunities(opportunities: List[dict], days: int = 14) -> List[dict]:
    """Get opportunities scraped within the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    new_opps = []

    for opp in opportunities:
        scraped_at = opp.get("scraped_at")
        if scraped_at:
            try:
                scraped_date = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
                if scraped_date.replace(tzinfo=None) >= cutoff:
                    new_opps.append(opp)
            except (ValueError, TypeError):
                pass

    return new_opps


def format_opportunity_html(opp: dict, is_closing_soon: bool = False) -> str:
    """Format a single opportunity as HTML."""
    title = opp.get("title", "Untitled")
    url = opp.get("url", "#")
    source = opp.get("source", "Unknown")
    opp_type = opp.get("type", "").upper()
    deadline = opp.get("deadline")
    funding = opp.get("funding_size", "")
    description = opp.get("description", "")[:200]
    if len(opp.get("description", "")) > 200:
        description += "..."
    eligibility = opp.get("eligibility", "")

    # Card background for closing soon items
    card_bg = "#FBF5F2" if is_closing_soon else "#FFFFFF"

    # Build details line
    details_parts = []
    if funding:
        details_parts.append(f'<span style="font-weight: 600; color: #1A1A1A;">{funding}</span>')
    if deadline:
        deadline_color = "#C26E4B" if is_closing_soon else "#6C6863"
        deadline_weight = "500" if is_closing_soon else "400"
        details_parts.append(f'<span style="color: {deadline_color}; font-weight: {deadline_weight};">Deadline: {deadline}</span>')
    details_html = " &nbsp;&middot;&nbsp; ".join(details_parts) if details_parts else ""

    # Badge for closing soon
    badge_html = ""
    if is_closing_soon:
        badge_html = '<span style="display: inline-block; padding: 4px 8px; margin-bottom: 12px; font-size: 10px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; background-color: #C26E4B; color: white; border-radius: 3px;">CLOSING SOON</span><br>'

    # Meta line (source and type)
    meta_parts = [f'<span style="color: #6C6863;">{source}</span>']
    if opp_type:
        meta_parts.append(f'<span>{opp_type}</span>')
    meta_html = " &nbsp;&middot;&nbsp; ".join(meta_parts)

    # Eligibility
    eligibility_html = ""
    if eligibility:
        eligibility_html = f'<p style="margin: 8px 0 0 0; font-size: 13px; line-height: 1.5; color: #9A9590;"><span style="font-weight: 500; color: #6C6863;">Eligibility:</span> {eligibility}</p>'

    return f"""
    <div style="margin-bottom: 8px; padding: 24px; background-color: {card_bg}; border-radius: 3px;">
        {badge_html}
        <h3 style="margin: 0 0 8px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 16px; font-weight: 500; line-height: 1.4;">
            <a href="{url}" style="color: #1A1A1A; text-decoration: none;">{title}</a>
        </h3>
        <p style="margin: 0 0 8px 0; font-size: 14px;">{details_html}</p>
        <p style="margin: 0; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #9A9590;">{meta_html}</p>
        <p style="margin: 12px 0 0 0; font-size: 14px; line-height: 1.6; color: #6C6863;">{description}</p>
        {eligibility_html}
        <p style="margin: 12px 0 0 0;">
            <a href="{url}" style="font-size: 12px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; color: #9A9590; text-decoration: none;">VIEW OPPORTUNITY →</a>
        </p>
    </div>
    """


def generate_digest_html(closing_soon: List[dict], new_opps: List[dict], site_url: str) -> str:
    """Generate the full email digest HTML."""
    today = datetime.now().strftime("%B %d, %Y")

    # Stats line
    stats_parts = []
    if closing_soon:
        stats_parts.append(f"<strong style='color: #1A1A1A;'>{len(closing_soon)}</strong> CLOSING SOON")
    stats_parts.append(f"<strong style='color: #1A1A1A;'>{len(new_opps)}</strong> NEW")
    stats_html = " &nbsp;&nbsp;·&nbsp;&nbsp; ".join(stats_parts)

    closing_html = ""
    if closing_soon:
        closing_html = """
        <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(26, 26, 26, 0.1);">
            <h2 style="margin: 0 0 20px 0; font-family: Georgia, serif; font-size: 18px; font-weight: 600; color: #C26E4B;">Closing Soon</h2>
        """
        for opp in closing_soon:
            closing_html += format_opportunity_html(opp, is_closing_soon=True)
        closing_html += "</div>"
    else:
        closing_html = '<p style="margin-top: 32px; color: #9A9590; font-style: italic;">No opportunities closing in the next 14 days.</p>'

    new_html = ""
    if new_opps:
        new_html = """
        <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(26, 26, 26, 0.1);">
            <h2 style="margin: 0 0 20px 0; font-family: Georgia, serif; font-size: 18px; font-weight: 600; color: #1A1A1A;">New Opportunities</h2>
        """
        for opp in new_opps:
            new_html += format_opportunity_html(opp, is_closing_soon=False)
        new_html += "</div>"
    else:
        new_html = '<p style="margin-top: 32px; color: #9A9590; font-style: italic;">No new opportunities found since last digest.</p>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background-color: #F9F8F6; margin: 0; padding: 0;">
        <div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">
            <!-- Header -->
            <div style="text-align: center; padding-bottom: 32px;">
                <h1 style="margin: 0 0 8px 0; font-family: Georgia, 'Times New Roman', serif; font-size: 28px; font-weight: 600; letter-spacing: -0.025em; color: #1A1A1A;">
                    Fellowship & Grant Tracker
                </h1>
                <p style="margin: 0; font-size: 15px; color: #6C6863;">Biweekly digest for {today}</p>
            </div>

            <!-- Stats -->
            <div style="text-align: center; padding: 16px 0; border-top: 1px solid rgba(26, 26, 26, 0.1); border-bottom: 1px solid rgba(26, 26, 26, 0.1); font-size: 12px; letter-spacing: 0.05em; text-transform: uppercase; color: #9A9590;">
                {stats_html}
            </div>

            {closing_html}

            {new_html}

            <!-- CTA Button -->
            <div style="margin-top: 48px; padding-top: 32px; border-top: 1px solid rgba(26, 26, 26, 0.1); text-align: center;">
                <a href="{site_url}" style="display: inline-block; padding: 14px 28px; background-color: #1A1A1A; color: #FFFFFF; font-size: 12px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; text-decoration: none; border-radius: 3px;">
                    View All Opportunities
                </a>
            </div>

            <!-- Footer -->
            <div style="margin-top: 48px; text-align: center;">
                <p style="margin: 0; font-size: 12px; color: #9A9590; line-height: 1.7;">
                    This digest is automatically generated.<br>
                    Opportunities are scraped from various sources and may not be complete or fully accurate.<br>
                    Always verify details on the original source.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


def send_digest():
    """Send the digest email via Gmail SMTP."""
    # Get environment variables
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    site_url = os.environ.get("SITE_URL", "https://oshanjarow.github.io/fellowship-tracker")

    if not gmail_address:
        print("ERROR: GMAIL_ADDRESS not set")
        return False

    if not gmail_app_password:
        print("ERROR: GMAIL_APP_PASSWORD not set")
        return False

    # Load and process opportunities
    opportunities = load_opportunities()
    print(f"Loaded {len(opportunities)} opportunities")

    closing_soon = get_closing_soon(opportunities)
    new_opps = get_new_opportunities(opportunities)

    print(f"Closing soon: {len(closing_soon)}")
    print(f"New opportunities: {len(new_opps)}")

    # Generate email
    html_content = generate_digest_html(closing_soon, new_opps, site_url)

    # Create message
    today = datetime.now().strftime("%B %d, %Y")
    subject = f"Fellowship & Grant Digest - {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = gmail_address  # Send to yourself

    # Attach HTML content
    msg.attach(MIMEText(html_content, "html"))

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


if __name__ == "__main__":
    send_digest()

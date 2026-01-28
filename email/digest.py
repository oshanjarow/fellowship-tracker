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

# Paths
SCRIPT_DIR = Path(__file__).parent
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


def format_opportunity_html(opp: dict) -> str:
    """Format a single opportunity as HTML."""
    title = opp.get("title", "Untitled")
    url = opp.get("url", "#")
    source = opp.get("source", "Unknown")
    deadline = opp.get("deadline", "No deadline listed")
    description = opp.get("description", "")[:200]
    if len(opp.get("description", "")) > 200:
        description += "..."

    return f"""
    <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h3 style="margin: 0 0 10px 0;">
            <a href="{url}" style="color: #1a73e8; text-decoration: none;">{title}</a>
        </h3>
        <p style="margin: 5px 0; color: #666; font-size: 14px;">
            <strong>Source:</strong> {source} | <strong>Deadline:</strong> {deadline}
        </p>
        <p style="margin: 10px 0 0 0; color: #333; font-size: 14px;">{description}</p>
    </div>
    """


def generate_digest_html(closing_soon: List[dict], new_opps: List[dict], site_url: str) -> str:
    """Generate the full email digest HTML."""
    today = datetime.now().strftime("%B %d, %Y")

    closing_html = ""
    if closing_soon:
        closing_html = "<h2 style='color: #d93025; margin-top: 30px;'>Closing Soon (Next 14 Days)</h2>"
        for opp in closing_soon:
            closing_html += format_opportunity_html(opp)
    else:
        closing_html = "<p><em>No opportunities closing in the next 14 days.</em></p>"

    new_html = ""
    if new_opps:
        new_html = "<h2 style='color: #1a73e8; margin-top: 30px;'>New Opportunities</h2>"
        for opp in new_opps[:10]:  # Limit to 10
            new_html += format_opportunity_html(opp)
        if len(new_opps) > 10:
            new_html += f"<p><em>... and {len(new_opps) - 10} more. <a href='{site_url}'>View all on website</a></em></p>"
    else:
        new_html = "<p><em>No new opportunities found since last digest.</em></p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
        <h1 style="color: #202124; border-bottom: 2px solid #1a73e8; padding-bottom: 10px;">
            Fellowship & Grant Tracker
        </h1>
        <p style="color: #666;">Biweekly digest for {today}</p>

        {closing_html}

        {new_html}

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e0e0e0;">

        <p style="text-align: center;">
            <a href="{site_url}" style="display: inline-block; padding: 12px 24px; background-color: #1a73e8; color: white; text-decoration: none; border-radius: 6px;">
                View All Opportunities
            </a>
        </p>

        <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
            This digest is automatically generated. Opportunities are scraped from various sources and may not be complete or fully accurate.
            Always verify details on the original source.
        </p>
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

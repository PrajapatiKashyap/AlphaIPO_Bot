import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.investorgain.com",
    "Referer": "https://www.investorgain.com/"
}

def fetch_with_retry(url: str) -> requests.Response:
    """
    Fetches a URL with a 10 second timeout and retries once on failure.
    """
    for attempt in range(2):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response
            else:
                print(f"HTTP Error {response.status_code} for URL: {url} (attempt {attempt + 1})")
        except Exception as e:
            print(f"Network error for URL: {url} (attempt {attempt + 1}): {e}")
    return None

def extract_state_params() -> dict:
    """
    Fetches the main report page and parses Next.js state parameters.
    Returns a dictionary of parameters with safe defaults.
    """
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    print("Checking IPO data...")
    response = fetch_with_retry(url)
    
    # Defaults
    params = {
        "version": "17-18",
        "month": 8,
        "year": 2026,
        "financial_year": "2026-27"
    }
    
    if not response:
        print("Failed to load main page, using default state parameters.")
        return params
        
    try:
        # Unescape quotes and backslashes in the push calls to facilitate regex matching
        normalized = response.text.replace('\\"', '"').replace('\\\\', '\\')
        
        # Parse version from resultData
        version_match = re.search(r'"resultData"\s*:\s*\{\s*"msg"\s*:\s*\d+\s*,\s*"version"\s*:\s*"([^"]+)"', normalized)
        if version_match:
            params["version"] = version_match.group(1)
            
        # Parse month
        month_match = re.search(r'"currentMonth"\s*:\s*(\d+)', normalized)
        if month_match:
            params["month"] = int(month_match.group(1))
            
        # Parse year
        year_match = re.search(r'"currentYear"\s*:\s*(\d+)', normalized)
        if year_match:
            params["year"] = int(year_match.group(1))
            
        # Parse financialYear
        fin_match = re.search(r'"financialYear"\s*:\s*"([^"]+)"', normalized)
        if fin_match:
            params["financial_year"] = fin_match.group(1)
            
    except Exception as e:
        print(f"Error parsing page state parameters: {e}")
        
    return params

def clean_html_tags(text: str) -> str:
    """
    Helper to strip HTML tags from a string.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]*>', '', text)
    # Decode common HTML entities
    clean = clean.replace('&nbsp;', ' ').replace('&#8377;', '₹').replace('&amp;', '&')
    return clean.strip()

def extract_allotment_link_from_html(html: str) -> str:
    """
    Parses detailed IPO page HTML to extract the registrar website.
    """
    if not html:
        return None
    try:
        # Search for registrar domains matching http/https URLs
        urls = re.findall(r'https?://[^\s"\'<>]+', html)
        
        # Recognized registrar domains
        registrar_keywords = [
            "linkintime", "kfintech", "bigshareonline", "bigshare", "maashitla", "mufg",
            "cameoindia", "skylinerta", "purvashare", "integratedindia", "beetalfinancial", "masserv"
        ]
        
        for url in urls:
            clean_url = url.replace('\\', '/')
            # Remove duplicate slashes
            clean_url = re.sub(r'(?<!:)/+', '/', clean_url)
            # Trim bounds
            for delim in ['"', "'", '<', '>', '\\', ';', '&', ')', '(', ']', '[']:
                clean_url = clean_url.split(delim)[0]
            clean_url = clean_url.rstrip('/.,;')
            
            if any(kw in clean_url.lower() for kw in registrar_keywords):
                return clean_url
    except Exception as e:
        print(f"Error extracting allotment link: {e}")
        
    return None

def fetch_allotment_link(row: dict) -> str:
    """
    Retrieves the allotment status page URL for an IPO.
    Checks the row Name field first, then queries the details page.
    """
    # 1. Check if the allotment link is already inside the Name field (for closed/allotted IPOs)
    name_html = row.get("Name", "")
    allotment_match = re.search(r'href="([^"]+)"[^>]*title="Check Allotment"', name_html)
    if allotment_match:
        return allotment_match.group(1).replace('\\', '')
        
    # 2. Otherwise, fetch the detailed IPO page to extract the registrar website
    folder_name = row.get("~urlrewrite_folder_name")
    if not folder_name:
        return None
        
    # Convert gmp path to detailed ipo path
    folder_name = folder_name.replace("/gmp/", "/ipo/")
    detail_url = f"https://www.investorgain.com{folder_name}"
    
    print(f"Fetching allotment link details from {detail_url}...")
    response = fetch_with_retry(detail_url)
    if not response:
        return None
        
    return extract_allotment_link_from_html(response.text)

def normalize_percentage(percent: float) -> int:
    """
    Normalizes/rounds the percentage to the closest value in [10, 30, 35, 50].
    """
    if percent is None:
        return None
    allowed = [10, 30, 35, 50]
    closest = min(allowed, key=lambda x: abs(x - percent))
    return closest

def format_amount(amount: float) -> str:
    """
    Formats the quota amount in Cr, stripping trailing .00 or .0 if it's a whole number.
    """
    if amount is None:
        return None
    formatted = f"{amount:.2f}"
    if formatted.endswith(".00"):
        formatted = formatted[:-3]
    elif formatted.endswith("0") and "." in formatted:
        formatted = formatted[:-1]
    return formatted

def parse_issue_size(size_str: str) -> float:
    """
    Parses issue size string (e.g., '₹1,245 Cr') and returns float value in Cr.
    """
    if not size_str or size_str == "N/A":
        return 0.0
    clean_str = size_str.replace(",", "").strip()
    match = re.search(r'(\d+(?:\.\d+)?)', clean_str)
    if not match:
        return 0.0
    val = float(match.group(1))
    if "lakh" in clean_str.lower():
        val = val / 100.0
    return val

def parse_retail_reservation(html: str) -> tuple:
    """
    Parses the HTML to find the retail quota percentage and, if available, the retail reservation amount.
    Returns (percentage, amount_in_cr_or_none).
    """
    if not html:
        return None, None
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Locate row for Retail/RII
    retail_row = None
    rsv_table = soup.find('table', class_='rsv-table')
    if rsv_table:
        for row in rsv_table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                category = cells[0].get_text(strip=True).lower()
                if 'retail' in category or 'rii' in category:
                    retail_row = cells
                    break
    if not retail_row:
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    category = cells[0].get_text(strip=True).lower()
                    if 'retail' in category or 'rii' in category:
                        retail_row = cells
                        break
            if retail_row:
                break
                
    percent = None
    amount = None
    
    if retail_row:
        # Search all cells after the first one for percentage and amount
        for cell in retail_row[1:]:
            text = cell.get_text(strip=True)
            # Find percentage
            if percent is None:
                pct_match = re.search(r'(\d+(?:\.\d+)?)%', text)
                if pct_match:
                    percent = float(pct_match.group(1))
            # Find amount in Cr
            if amount is None:
                amt_match = re.search(r'(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)\s*Cr', text, re.IGNORECASE)
                if amt_match:
                    amount = float(amt_match.group(1))
                    
    # Fallback to entire HTML regex if not found in table cells
    if percent is None:
        matches = re.finditer(r'(?i)retail', html)
        for m in matches:
            start = m.start()
            end = min(len(html), start + 150)
            snippet = html[start:end]
            pct_match = re.search(r'(\d+(?:\.\d+)?)%', snippet)
            if pct_match:
                percent = float(pct_match.group(1))
                # Also check for amount in snippet
                amt_match = re.search(r'(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)\s*Cr', snippet, re.IGNORECASE)
                if amt_match:
                    amount = float(amt_match.group(1))
                break
                
    return percent, amount

def parse_updated_time(date_str: str) -> datetime:
    """
    Cleans ordinal suffixes (e.g. 3rd, 30th) and formats the date string,
    then parses it into a datetime object.
    """
    # Clean ordinal suffixes: 1st, 2nd, 3rd, 4th, 30th etc.
    cleaned = re.sub(r'(\d+)(?:st|nd|rd|th)\b', r'\1', date_str, flags=re.IGNORECASE)
    cleaned = cleaned.replace('-', ' ')
    cleaned = ' '.join(cleaned.split())
    
    formats = [
        "%d %b %Y %H:%M",
        "%d %B %Y %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse date string: {date_str}")

def format_updated_time(dt: datetime) -> str:
    """
    Formats a datetime object as 'DD-Mon | HH:MM AM/PM'.
    """
    return dt.strftime("%d-%b | %I:%M %p")

def clean_sub_value(val: str) -> str:
    """
    Cleans and standardizes the subscription value, ensuring it ends with 'x'.
    """
    val = val.strip()
    if not val or val == "-":
        return "N/A"
    if not val.endswith('x') and not val.endswith('×'):
        val += 'x'
    val = val.replace('×', 'x')
    return val

def parse_daywise_subscription_table(soup: BeautifulSoup) -> tuple:
    """
    Parses the BeautifulSoup object (reconstructed Next.js payload) to extract
    daily RII subscriptions, the latest RII value, and the latest update timestamp.
    Returns (daily_retail_subscription, latest_retail_subscription, subscription_updated_time).
    """
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
        
        header_cells = rows[0].find_all(['th', 'td'])
        headers = [c.get_text(strip=True).lower() for c in header_cells]
        
        # Look for the table having both "day" and "rii" columns
        if "day" in headers and "rii" in headers:
            day_idx = headers.index("day")
            rii_idx = headers.index("rii")
            date_idx = headers.index("date") if "date" in headers else -1
            
            daily_retail_sub = {}
            latest_retail_sub = None
            raw_latest_date = None
            
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= max(day_idx, rii_idx, date_idx):
                    continue
                
                day_text = cells[day_idx].get_text(strip=True)
                rii_text = cells[rii_idx].get_text(strip=True)
                
                if not day_text.lower().startswith("day"):
                    continue
                
                rii_val = clean_sub_value(rii_text)
                if rii_val == "N/A":
                    continue
                
                daily_retail_sub[day_text] = rii_val
                latest_retail_sub = rii_val
                
                if date_idx != -1:
                    raw_latest_date = cells[date_idx].get_text(strip=True)
            
            if daily_retail_sub:
                formatted_date = None
                if raw_latest_date:
                    try:
                        dt = parse_updated_time(raw_latest_date)
                        formatted_date = format_updated_time(dt)
                    except Exception as e:
                        print(f"Error parsing date '{raw_latest_date}': {e}")
                
                return daily_retail_sub, latest_retail_sub, formatted_date
                
    return None, None, None

def fetch_ipos() -> list:
    """
    Fetches, filters, processes, and correlates live Mainboard IPOs from InvestorGain.
    Only returns IPOs with a positive GMP percentage.
    """
    params = extract_state_params()
    
    # 1. Fetch GMP Report (331)
    gmp_url = (
        f"https://webnodejs.investorgain.com/cloud/v2/report/data-read/331/1/"
        f"{params['month']}/{params['year']}/{params['financial_year']}/0/all?search=0&v={params['version']}"
    )
    print("Checking GMP...")
    gmp_response = fetch_with_retry(gmp_url)
    
    # 2. Fetch Subscription Report (333)
    sub_url = (
        f"https://webnodejs.investorgain.com/cloud/v2/report/data-read/333/1/"
        f"{params['month']}/{params['year']}/{params['financial_year']}/0/all?search=0&v={params['version']}"
    )
    print("Checking Retail Subscription...")
    sub_response = fetch_with_retry(sub_url)
    
    if not gmp_response:
        print("Failed to fetch GMP data.")
        return []
        
    try:
        gmp_data = gmp_response.json()
        gmp_rows = gmp_data.get("reportTableData", [])
    except Exception as e:
        print(f"Error parsing GMP JSON: {e}")
        return []
        
    sub_map = {}
    if sub_response:
        try:
            sub_data = sub_response.json()
            for row in sub_data.get("reportTableData", []):
                sub_id = row.get("~id")
                if sub_id:
                    sub_map[sub_id] = row
        except Exception as e:
            print(f"Error parsing Subscription JSON: {e}")
            
    processed_ipos = []
    
    for row in gmp_rows:
        # Ignore SME IPOs: Only monitor Mainboard (Category == "IPO")
        if row.get("~IPO_Category") != "IPO":
            continue
            
        # Parse GMP percent
        gmp_val_str = row.get("~gmp_percent_calc", "0.00")
        try:
            gmp_val = float(gmp_val_str)
        except ValueError:
            gmp_val = 0.0
            
        # Allow negative/zero GMP to support sending initial alert for all Mainboard IPOs
            
        # Correlate with Subscription Report
        ipo_id = row.get("~id")
        sub_row = sub_map.get(ipo_id) if ipo_id else None
        
        # Get Retail Subscription (RII)
        retail_sub = "N/A"
        if sub_row:
            raw_rii = sub_row.get("RII")
            if raw_rii and raw_rii != "-":
                retail_sub = f"{raw_rii}x"
                
        # Parse price and lot size to calculate Minimum Investment
        raw_price = clean_html_tags(row.get("Price (₹)", row.get("Price (\u20b9)", "")))
        # Upper Price Band is usually the price or upper end of the price band (e.g. "53")
        try:
            price = float(raw_price.split("-")[-1].strip()) if raw_price else 0.0
        except ValueError:
            price = 0.0
            
        raw_lot = clean_html_tags(row.get("Lot", ""))
        try:
            lot = int(raw_lot) if raw_lot else 0
        except ValueError:
            lot = 0
            
        min_investment = int(price * lot)
        
        # Clean dates
        open_date = row.get("~Srt_Open", "N/A")
        close_date = row.get("~Srt_Close", "N/A")
        listing_date = row.get("~Str_Listing", "N/A")
        
        # Issue size
        issue_size = clean_html_tags(row.get("IPO Size", "N/A"))
        
        # Formatted GMP percentage
        if gmp_val > 0.0:
            formatted_gmp = f"+{gmp_val}%"
        else:
            formatted_gmp = f"{gmp_val}%"
        
        # Check if allotment link is inside the Name field first (for closed/allotted IPOs)
        name_html = row.get("Name", "")
        allotment_match = re.search(r'href="([^"]+)"[^>]*title="Check Allotment"', name_html)
        allotment_link = allotment_match.group(1).replace('\\', '') if allotment_match else None
        
        # Fetch IPO detailed page to parse retail quota and registrar allotment link
        folder_name = row.get("~urlrewrite_folder_name")
        detail_html = None
        if folder_name:
            folder_name = folder_name.replace("/gmp/", "/ipo/")
            detail_url = f"https://www.investorgain.com{folder_name}"
            print(f"Fetching IPO details from {detail_url}...")
            detail_resp = fetch_with_retry(detail_url)
            if detail_resp:
                detail_html = detail_resp.text
                
        # If allotment link was not in Name, try to extract it from the detailed page
        if detail_html and not allotment_link:
            allotment_link = extract_allotment_link_from_html(detail_html)
            
        # Parse Retail Reservation (Quota) information
        retail_quota_percent = None
        retail_quota_amount = None
        if detail_html:
            raw_percent, raw_amount = parse_retail_reservation(detail_html)
            if raw_percent is not None:
                retail_quota_percent = normalize_percentage(raw_percent)
                if raw_amount is not None:
                    retail_quota_amount = format_amount(raw_amount)
                else:
                    issue_size_val = parse_issue_size(issue_size)
                    if issue_size_val > 0:
                        calculated_amount = issue_size_val * retail_quota_percent / 100.0
                        retail_quota_amount = format_amount(calculated_amount)
                        
        # Parse detailed page for day-wise subscription and latest subscription
        daily_retail_subscription = None
        latest_retail_subscription = None
        subscription_updated_time = None
        
        if detail_html:
            try:
                # 1. Reconstruct Next.js payload
                matches = re.findall(r'self\.__next_f\.push\(\[(?:\d+),\s*"(.*?)"\]\)', detail_html)
                if matches:
                    reconstructed = ""
                    for m in matches:
                        chunk = m.replace('\\"', '"').replace('\\\\', '\\').replace('\\/', '/')
                        try:
                            chunk = chunk.encode().decode('unicode-escape', errors='ignore')
                        except Exception:
                            pass
                        reconstructed += chunk
                    
                    # 2. Parse table
                    detail_soup = BeautifulSoup(reconstructed, 'html.parser')
                    daily_sub, latest_sub, sub_time = parse_daywise_subscription_table(detail_soup)
                    if daily_sub:
                        daily_retail_subscription = daily_sub
                        latest_retail_subscription = latest_sub
                        subscription_updated_time = sub_time
            except Exception as e:
                print(f"Error parsing daywise subscription for {row.get('~ipo_name')}: {e}")
                
        # Override retail_sub if we found the latest subscription in the daywise table
        if latest_retail_subscription:
            retail_sub = latest_retail_subscription
            
        processed_ipos.append({
            "id": ipo_id,
            "ipo_name": row.get("~ipo_name", "N/A"),
            "open_date": open_date,
            "close_date": close_date,
            "allotment_date": row.get("~Srt_BoA_Dt", "N/A"),
            "issue_size": issue_size,
            "price_band": raw_price if raw_price else "N/A",
            "lot_size": lot if lot > 0 else "N/A",
            "min_investment": min_investment,
            "listing_date": listing_date,
            "gmp_percent": formatted_gmp,
            "retail_sub": retail_sub,
            "allotment_link": allotment_link,
            "allotment_status_url": allotment_link,
            "retail_quota_percent": retail_quota_percent,
            "retail_quota_amount": retail_quota_amount,
            "daily_retail_subscription": daily_retail_subscription,
            "subscription_updated_time": subscription_updated_time
        })
        
    return processed_ipos

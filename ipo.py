import re
import requests
from bs4 import BeautifulSoup

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
        
    try:
        # Search for registrar domains matching http/https URLs
        urls = re.findall(r'https?://[^\s"\'<>]+', response.text)
        
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
            
        # Ignore if GMP is 0% or negative
        if gmp_val <= 0.0:
            continue
            
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
        formatted_gmp = f"+{gmp_val}%"
        
        # Fetch Allotment Link
        allotment_link = fetch_allotment_link(row)
        
        processed_ipos.append({
            "id": ipo_id,
            "ipo_name": row.get("~ipo_name", "N/A"),
            "open_date": open_date,
            "close_date": close_date,
            "issue_size": issue_size,
            "price_band": raw_price if raw_price else "N/A",
            "lot_size": lot if lot > 0 else "N/A",
            "min_investment": min_investment,
            "listing_date": listing_date,
            "gmp_percent": formatted_gmp,
            "retail_sub": retail_sub,
            "allotment_link": allotment_link
        })
        
    return processed_ipos

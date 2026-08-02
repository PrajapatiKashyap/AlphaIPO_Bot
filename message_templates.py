from datetime import datetime, timezone, timedelta

def get_ist_time_str() -> str:
    """
    Returns the current time in IST formatted as 'DD-Mon | HH:MM AM/PM'.
    """
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%d-%b | %I:%M %p")

def format_date(date_str: str) -> str:
    """
    Formats a 'YYYY-MM-DD' date string to 'DD-Mon-YYYY'.
    """
    if not date_str or date_str == "N/A":
        return "N/A"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")
    except Exception:
        return date_str

def format_sub(sub_str: str) -> str:
    """
    Formats subscription strings to use the standard multiplication sign '×'.
    """
    if not sub_str or sub_str == "N/A":
        return "N/A"
    # Replace normal 'x' with '×'
    formatted = sub_str.replace("x", "×")
    if not formatted.endswith("×") and formatted != "-":
        formatted += "×"
    return formatted

def build_new_ipo_message(ipo: dict) -> str:
    """
    Builds a beautifully formatted HTML message for a new Mainboard IPO listing.
    """
    open_d = format_date(ipo.get("open_date"))
    close_d = format_date(ipo.get("close_date"))
    retail_s = format_sub(ipo.get("retail_sub"))
    allot_link = ipo.get("allotment_link")
    allot_line = f"🔗 Check Allotment : {allot_link}\n\n" if allot_link else ""
    
    return (
        f"🚀 <b>New IPO ALERT</b>\n\n"
        f"🏢 <b>Company:</b> {ipo.get('ipo_name', 'N/A')}\n\n"
        f"📅 <b>Opens :</b> {open_d}\n"
        f"📅 <b>Closes:</b> {close_d}\n\n"
        f"📦 <b>Issue Size :</b> {ipo.get('issue_size', 'N/A')}\n"
        f"💰 <b>Price Band :</b> {ipo.get('price_band', 'N/A')}\n"
        f"📊 <b>Lot Size   :</b> {ipo.get('lot_size', 'N/A')}\n"
        f"💵 <b>Investment :</b> {ipo.get('min_investment', 'N/A')}\n\n"
        f"📈 <b>GMP        :</b> {ipo.get('gmp_percent', 'N/A')}\n"
        f"👥 <b>Retail Sub :</b> {retail_s}\n\n"
        f"{allot_line}"
        f"🕒 <b>Alert:</b> {get_ist_time_str()}"
    )

def build_gmp_update_message(ipo: dict, old_gmp: str, new_gmp: str) -> str:
    """
    Builds a formatted HTML message when the GMP percentage of an IPO changes.
    """
    open_d = format_date(ipo.get("open_date"))
    close_d = format_date(ipo.get("close_date"))
    
    return (
        f"📈 <b>GMP UPDATE</b>\n\n"
        f"🏢 <b>{ipo.get('ipo_name', 'N/A')}</b>\n\n"
        f"<b>Previous :</b> {old_gmp}\n"
        f"<b>Current  :</b> {new_gmp}\n\n"
        f"📅 <b>Opens :</b> {open_d}\n"
        f"📅 <b>Closes:</b> {close_d}\n\n"
        f"🕒 <b>Updated:</b> {get_ist_time_str()}"
    )

def build_subscription_update_message(ipo: dict, old_sub: str, new_sub: str) -> str:
    """
    Builds a formatted HTML message when the retail subscription of an IPO changes.
    """
    current_sub = format_sub(new_sub)
    return (
        f"🔥 <b>SUBSCRIPTION UPDATE</b>\n\n"
        f"🏢 <b>{ipo.get('ipo_name', 'N/A')}</b>\n\n"
        f"👥 <b>Subscription :</b> {current_sub}\n\n"
        f"📈 <b>GMP :</b> {ipo.get('gmp_percent', 'N/A')}\n\n"
        f"🕒 <b>Updated:</b> {get_ist_time_str()}"
    )

def build_open_today_message(ipo: dict) -> str:
    """
    Builds a formatted HTML message when an IPO opens today.
    """
    close_d = format_date(ipo.get("close_date"))
    allot_link = ipo.get("allotment_link")
    allot_line = f"🔗 Check Allotment : {allot_link}\n\n" if allot_link else ""
    return (
        f"🟢 <b>IPO OPEN TODAY</b>\n\n"
        f"🏢 <b>{ipo.get('ipo_name', 'N/A')}</b>\n\n"
        f"📦 <b>Issue Size :</b> {ipo.get('issue_size', 'N/A')}\n"
        f"💰 <b>Price Band :</b> {ipo.get('price_band', 'N/A')}\n"
        f"📊 <b>Lot Size   :</b> {ipo.get('lot_size', 'N/A')}\n"
        f"💵 <b>Investment :</b> {ipo.get('min_investment', 'N/A')}\n\n"
        f"📈 <b>GMP :</b> {ipo.get('gmp_percent', 'N/A')}\n\n"
        f"{allot_line}"
        f"⏳ <b>Last Date:</b> {close_d}"
    )

def build_closing_today_message(ipo: dict) -> str:
    """
    Builds a formatted HTML message when an IPO is closing today.
    """
    retail_s = format_sub(ipo.get("retail_sub"))
    allot_link = ipo.get("allotment_link")
    allot_line = f"🔗 Check Allotment : {allot_link}\n\n" if allot_link else ""
    return (
        f"🔴 <b>IPO CLOSING TODAY</b>\n\n"
        f"🏢 <b>{ipo.get('ipo_name', 'N/A')}</b>\n\n"
        f"👥 <b>Retail :</b> {retail_s}\n"
        f"📈 <b>GMP    :</b> {ipo.get('gmp_percent', 'N/A')}\n\n"
        f"{allot_line}"
        f"⚠️ <b>Last day to apply.</b>"
    )

def build_listing_today_message(ipo: dict) -> str:
    """
    Builds a formatted HTML message when an IPO is listing today.
    """
    raw_price = ipo.get("price_band", "N/A")
    raw_gmp = ipo.get("gmp_percent", "N/A")
    
    # Try to calculate estimated listing price
    est_listing_str = ""
    try:
        # Extract numeric price from price band string (e.g. "425" or "400-425")
        price_num = float(raw_price.split("-")[-1].strip())
        # Extract numeric GMP percentage (e.g. "+21.80%")
        gmp_num = float(raw_gmp.replace("%", "").replace("+", "").strip())
        est_price = price_num * (1.0 + gmp_num / 100.0)
        est_listing_str = f" (₹{est_price:.2f})"
    except Exception:
        pass
        
    return (
        f"🎉 <b>LISTING TODAY</b>\n\n"
        f"🏢 <b>{ipo.get('ipo_name', 'N/A')}</b>\n\n"
        f"📈 <b>Last GMP :</b> {raw_gmp}{est_listing_str}\n\n"
        f"💰 <b>IPO Price :</b> ₹{raw_price}\n\n"
        f"Good luck to all applicants!"
    )

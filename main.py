import os
import json
from datetime import datetime, timezone, timedelta
import ipo
import telegram_bot
import message_templates
from datetime import datetime

print(f"Bot started at {datetime.now()}")

STATE_FILE = "sent_ipos.json"
MIN_ALERT_GMP = 10.0

def parse_gmp_to_float(gmp_str: str) -> float:
    """
    Parses a GMP string like '+14.15%' or '-2%' or 'N/A' into a float.
    Returns 0.0 or the parsed float value on failure.
    """
    if not gmp_str or gmp_str == "N/A":
        return 0.0
    try:
        clean_str = gmp_str.replace("%", "").replace("+", "").strip()
        return float(clean_str)
    except ValueError:
        return 0.0

def should_send_update_alert(ipo: dict, saved_state: dict, today_ist: str) -> bool:
    """
    Decides whether an IPO is eligible for update notifications.
    Updates the saved_state flags as a side-effect.
    
    This function considers:
    1. Is it a Mainboard IPO? (Assumed true since live_ipos only contains Mainboard IPOs)
    2. Has the IPO closing date passed?
    3. Has the IPO already been permanently disabled?
    4. Has GMP ever crossed 10% while active?
    5. Is current GMP >= 10% if it has not previously qualified?
    6. Has the IPO already qualified?
    """
    # Check if the IPO has already been permanently disabled
    if saved_state.get("update_alerts_permanently_disabled"):
        return False
        
    close_date = ipo.get("close_date") or saved_state.get("close_date")
    current_gmp = parse_gmp_to_float(ipo.get("gmp_percent"))
    
    # Check if the IPO closing date has passed
    if close_date and close_date != "N/A" and today_ist > close_date:
        # If it has never reached the 10% GMP threshold while active, permanently disable it
        if not saved_state.get("update_alerts_enabled") and not saved_state.get("update_alerts_permanently_disabled"):
            saved_state["update_alerts_permanently_disabled"] = True
        return False
        
    # On or before the closing date:
    # Check if already qualified
    if saved_state.get("update_alerts_enabled"):
        return True
        
    # Check if current GMP >= 10.0% if not previously qualified
    if current_gmp >= MIN_ALERT_GMP:
        saved_state["update_alerts_enabled"] = True
        return True
        
    return False

def get_today_ist_str() -> str:
    """
    Returns today's date in IST formatted as YYYY-MM-DD.
    """
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d")

def load_state() -> dict:
    """
    Loads the previous execution state from sent_ipos.json.
    If the file does not exist or fails to parse, returns an empty dictionary.
    """
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading state from {STATE_FILE}: {e}")
        return {}

def save_state(state: dict):
    """
    Saves the execution state back to sent_ipos.json.
    """
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state to {STATE_FILE}: {e}")

def main():
    print("Comparing previous data...")
    state = load_state()
    today_ist = get_today_ist_str()
    
    # Fetch live processed Mainboard IPOs
    live_ipos = ipo.fetch_ipos()
    
    state_updated = False
    
    for item in live_ipos:
        name = item["ipo_name"]
        current_gmp = item["gmp_percent"]
        current_sub = item["retail_sub"]
        open_date = item["open_date"]
        close_date = item["close_date"]
        listing_date = item["listing_date"]
        
        # Check if the IPO exists in our historical state
        if name not in state:
            # Case 1: Brand new IPO detected
            gmp_float = parse_gmp_to_float(current_gmp)
            
            # Send New IPO Alert only if GMP is positive (> 0.0)
            sent = False
            if gmp_float > 0.0:
                message = message_templates.build_new_ipo_message(item)
                sent = telegram_bot.send_message(message)
                
            is_past_close = (close_date and close_date != "N/A" and today_ist > close_date)
            update_alerts_enabled = (gmp_float >= MIN_ALERT_GMP and not is_past_close)
            
            state[name] = {
                "open_date": open_date,
                "close_date": close_date,
                "last_gmp": current_gmp,
                "last_retail_sub": current_sub,
                "new_ipo_alert_sent": sent,
                "open_alert_sent": False,
                "closing_alert_sent": False,
                "listing_alert_sent": False,
                "update_alerts_enabled": update_alerts_enabled,
                "update_alerts_permanently_disabled": (is_past_close and not update_alerts_enabled)
            }
            # Initialize state variables to prevent duplicates on discovery
            if open_date <= today_ist:
                state[name]["open_alert_sent"] = True
            if close_date <= today_ist:
                state[name]["closing_alert_sent"] = True
            if listing_date <= today_ist:
                state[name]["listing_alert_sent"] = True
            state_updated = True
        else:
            # Case 2: Existing IPO. Check for updates
            saved_ipo = state[name]
            
            # Ensure basic fields exist in state structure (migrations for older states)
            if "open_date" not in saved_ipo:
                saved_ipo["open_date"] = open_date
            if "close_date" not in saved_ipo:
                saved_ipo["close_date"] = close_date
            if "open_alert_sent" not in saved_ipo:
                saved_ipo["open_alert_sent"] = False
            if "closing_alert_sent" not in saved_ipo:
                saved_ipo["closing_alert_sent"] = False
            if "listing_alert_sent" not in saved_ipo:
                saved_ipo["listing_alert_sent"] = False
            if "update_alerts_enabled" not in saved_ipo:
                # Backfill based on existing last_gmp or current_gmp
                gmp_val_saved = parse_gmp_to_float(saved_ipo.get("last_gmp", current_gmp))
                saved_ipo["update_alerts_enabled"] = (gmp_val_saved >= MIN_ALERT_GMP)
            if "update_alerts_permanently_disabled" not in saved_ipo:
                saved_ipo["update_alerts_permanently_disabled"] = False
            
            # If the new IPO alert was never sent successfully (e.g. previous API error OR GMP was <= 0% on discovery)
            if not saved_ipo.get("new_ipo_alert_sent"):
                gmp_float = parse_gmp_to_float(current_gmp)
                if gmp_float > 0.0:
                    message = message_templates.build_new_ipo_message(item)
                    if telegram_bot.send_message(message):
                        saved_ipo["new_ipo_alert_sent"] = True
                        saved_ipo["last_gmp"] = current_gmp
                        saved_ipo["last_retail_sub"] = current_sub
                        
                        is_past_close = (close_date and close_date != "N/A" and today_ist > close_date)
                        if gmp_float >= MIN_ALERT_GMP and not is_past_close:
                            saved_ipo["update_alerts_enabled"] = True
                        if is_past_close and not saved_ipo.get("update_alerts_enabled"):
                            saved_ipo["update_alerts_permanently_disabled"] = True
                            
                        if open_date <= today_ist:
                            saved_ipo["open_alert_sent"] = True
                        if close_date <= today_ist:
                            saved_ipo["closing_alert_sent"] = True
                        if listing_date <= today_ist:
                            saved_ipo["listing_alert_sent"] = True
                        state_updated = True
                    continue  # Skip updates if we just sent the main new IPO alert
                else:
                    # Still <= 0.0% GMP: do not send New IPO Alert.
                    # Update state silently for GMP and subscription changes so history is kept.
                    if current_gmp != saved_ipo.get("last_gmp"):
                        saved_ipo["last_gmp"] = current_gmp
                        state_updated = True
                    if current_sub != saved_ipo.get("last_retail_sub"):
                        saved_ipo["last_retail_sub"] = current_sub
                        state_updated = True
                    continue  # Skip checking other alerts until New IPO Alert has been sent
                
            # Capture qualification flags before checking, to detect state transitions
            was_enabled = saved_ipo.get("update_alerts_enabled")
            was_disabled = saved_ipo.get("update_alerts_permanently_disabled")
            
            # Evaluate update notifications eligibility
            is_eligible_for_updates = should_send_update_alert(item, saved_ipo, today_ist)
            
            # If state flags changed, make sure we save the state file
            if (saved_ipo.get("update_alerts_enabled") != was_enabled or 
                saved_ipo.get("update_alerts_permanently_disabled") != was_disabled):
                state_updated = True
                
            # Check for Grey Market Premium updates
            last_gmp = saved_ipo.get("last_gmp")
            if current_gmp != last_gmp:
                if is_eligible_for_updates:
                    message = message_templates.build_gmp_update_message(item, last_gmp, current_gmp)
                    if telegram_bot.send_message(message):
                        saved_ipo["last_gmp"] = current_gmp
                        state_updated = True
                else:
                    # Monitor silently: update state, but do not send Telegram alert
                    saved_ipo["last_gmp"] = current_gmp
                    state_updated = True
                    
            # Check for Retail Subscription (RII) updates
            last_sub = saved_ipo.get("last_retail_sub")
            if current_sub != last_sub:
                if is_eligible_for_updates:
                    message = message_templates.build_subscription_update_message(item, last_sub, current_sub)
                    if telegram_bot.send_message(message):
                        saved_ipo["last_retail_sub"] = current_sub
                        state_updated = True
                else:
                    # Monitor silently: update state, but do not send Telegram alert
                    saved_ipo["last_retail_sub"] = current_sub
                    state_updated = True
            
            # Check if IPO is opening today
            if open_date == today_ist and not saved_ipo.get("open_alert_sent"):
                if is_eligible_for_updates:
                    message = message_templates.build_open_today_message(item)
                    if telegram_bot.send_message(message):
                        saved_ipo["open_alert_sent"] = True
                        state_updated = True
            
            # Check if IPO is closing today
            if close_date == today_ist and not saved_ipo.get("closing_alert_sent"):
                if is_eligible_for_updates:
                    message = message_templates.build_closing_today_message(item)
                    if telegram_bot.send_message(message):
                        saved_ipo["closing_alert_sent"] = True
                        state_updated = True
                    
            # Check if IPO is listing today
            if listing_date == today_ist and not saved_ipo.get("listing_alert_sent"):
                # Listing today alert is allowed only if the IPO qualified while active
                if saved_ipo.get("update_alerts_enabled"):
                    message = message_templates.build_listing_today_message(item)
                    if telegram_bot.send_message(message):
                        saved_ipo["listing_alert_sent"] = True
                        state_updated = True
                    
    # Save the updated state to file if any notifications were sent successfully
    if state_updated:
        save_state(state)
    else:
        print("No meaningful changes detected.")
        
    print("Finished.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Global Application Error: {e}")

import os
import json
from datetime import datetime, timezone, timedelta
import ipo
import telegram_bot
import message_templates
from datetime import datetime

print(f"Bot started at {datetime.now()}")

STATE_FILE = "sent_ipos.json"

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
            message = message_templates.build_new_ipo_message(item)
            if telegram_bot.send_message(message):
                state[name] = {
                    "last_gmp": current_gmp,
                    "last_retail_sub": current_sub,
                    "new_ipo_alert_sent": True,
                    "open_alert_sent": False,
                    "closing_alert_sent": False,
                    "listing_alert_sent": False
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
            if "open_alert_sent" not in saved_ipo:
                saved_ipo["open_alert_sent"] = False
            if "closing_alert_sent" not in saved_ipo:
                saved_ipo["closing_alert_sent"] = False
            if "listing_alert_sent" not in saved_ipo:
                saved_ipo["listing_alert_sent"] = False
            
            # If the new IPO alert was never sent successfully (e.g. previous API error)
            if not saved_ipo.get("new_ipo_alert_sent"):
                message = message_templates.build_new_ipo_message(item)
                if telegram_bot.send_message(message):
                    state[name]["new_ipo_alert_sent"] = True
                    state[name]["last_gmp"] = current_gmp
                    state[name]["last_retail_sub"] = current_sub
                    if open_date <= today_ist:
                        state[name]["open_alert_sent"] = True
                    if close_date <= today_ist:
                        state[name]["closing_alert_sent"] = True
                    if listing_date <= today_ist:
                        state[name]["listing_alert_sent"] = True
                    state_updated = True
                continue  # Skip updates if we just sent the main new IPO alert
                
            # Check for Grey Market Premium updates
            last_gmp = saved_ipo.get("last_gmp")
            if current_gmp != last_gmp:
                message = message_templates.build_gmp_update_message(item, last_gmp, current_gmp)
                if telegram_bot.send_message(message):
                    state[name]["last_gmp"] = current_gmp
                    state_updated = True
                    
            # Check for Retail Subscription (RII) updates
            last_sub = saved_ipo.get("last_retail_sub")
            if current_sub != last_sub:
                message = message_templates.build_subscription_update_message(item, last_sub, current_sub)
                if telegram_bot.send_message(message):
                    state[name]["last_retail_sub"] = current_sub
                    state_updated = True
            
            # Check if IPO is opening today
            if open_date == today_ist and not saved_ipo.get("open_alert_sent"):
                message = message_templates.build_open_today_message(item)
                if telegram_bot.send_message(message):
                    state[name]["open_alert_sent"] = True
                    state_updated = True
            
            # Check if IPO is closing today
            if close_date == today_ist and not saved_ipo.get("closing_alert_sent"):
                message = message_templates.build_closing_today_message(item)
                if telegram_bot.send_message(message):
                    state[name]["closing_alert_sent"] = True
                    state_updated = True
                    
            # Check if IPO is listing today
            if listing_date == today_ist and not saved_ipo.get("listing_alert_sent"):
                message = message_templates.build_listing_today_message(item)
                if telegram_bot.send_message(message):
                    state[name]["listing_alert_sent"] = True
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

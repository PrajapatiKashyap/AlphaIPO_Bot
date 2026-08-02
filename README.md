# AlphaIPO_Bot 🚀

An automated Telegram bot that tracks and monitors good Indian Mainboard IPOs, providing real-time alerts whenever there are meaningful updates in Grey Market Premium (GMP) or Retail Subscription (RII) figures.

---

## Features

- **Automated Monitoring**: Tracks only Mainboard IPOs on NSE/BSE and ignores SME issues.
- **Positive GMP Filter**: Only tracks and monitors IPOs with a positive Grey Market Premium (GMP > 0%).
- **Smart Updates**: Sends messages only when changes occur (New IPO, GMP update, Retail Subscription update, IPO Open Today, IPO Closing Today, and Listing Today).
- **Deduplication**: Uses a local state file `sent_ipos.json` to track history and prevent duplicate alerts.
- **Allotment Links**: Automatically extracts official registrar allotment check URLs (e.g. KFintech, Link Intime, Bigshare) and includes them directly in messages.
- **Serverless Automation**: Deployed via GitHub Actions and scheduled to run automatically three times a day using a cron timer.

---

## File Structure

```text
AlphaIPO_Bot/
│
├── .github/
│   └── workflows/
│       └── ipo_bot.yml      # GitHub Actions automation workflow
│
├── config.py                # Bot configurations (Token & Chat ID)
├── ipo.py                   # Scraping and processing module
├── telegram_bot.py          # Message dispatcher using Telegram API
├── message_templates.py     # HTML template generators
├── requirements.txt         # Package dependencies
├── sent_ipos.json           # JSON state database (auto-created)
└── README.md                # Project documentation
```

---

## Setup Instructions

### 1. Prerequisites
Make sure Python 3.8+ is installed on your machine.

### 2. Installation
Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Create/edit `config.py` in the root folder and add your Telegram bot credentials:
```python
BOT_TOKEN = "your-telegram-bot-token"
CHAT_ID = "your-target-chat-or-channel-id"
```

### 4. Running Locally
Run the orchestrator script manually:
```bash
python main.py
```
On first run, it will fetch all current positive-GMP mainboard IPOs and send "New IPO" alerts to your Telegram chat. On subsequent runs, it will exit silently unless changes are detected.

---

## Automation with GitHub Actions

The repository includes a GitHub Actions workflow `.github/workflows/ipo_bot.yml` that executes the script automatically three times a day:
- **07:00 AM IST** (01:30 UTC)
- **10:00 AM IST** (04:30 UTC)
- **02:00 PM IST** (08:30 UTC)

### State Persistence
Each time the workflow runs and detects an update, it sends a Telegram alert, updates `sent_ipos.json`, and automatically commits and pushes the updated `sent_ipos.json` back to your GitHub repository.

To allow the workflow to commit the state back, ensure your repository has **Read and write permissions** enabled under **Settings > Actions > General > Workflow permissions**.

---

## Message Formats

The bot supports 6 distinct notifications:
1. **New IPO Alert**: Triggered when a new Mainboard IPO with positive GMP is found (includes allotment link placeholder).
2. **GMP Update Alert**: Triggered when the grey market premium percentage changes.
3. **Subscription Update Alert**: Triggered when the retail subscription demand changes.
4. **IPO Open Today**: Triggered on the first day bidding opens (includes allotment link placeholder).
5. **IPO Closing Today**: Triggered on the final day of bidding (includes allotment link placeholder).
6. **Listing Today**: Triggered on the day the stock lists on the exchange (includes estimated listing price calculations, no allotment link).

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Allow external data directory (e.g. persistent volume on Fly.io)
# Falls back to ./data for local development
DATA_DIR = os.environ.get("LM_DATA_DIR", os.path.join(BASE_DIR, "data"))
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
CARDS_DIR = os.path.join(DATA_DIR, "cards")
ROUTINE_CARDS_DIR = os.path.join(DATA_DIR, "routine-cards")
BABY_CARDS_DIR = os.path.join(DATA_DIR, "baby-cards")
ROUTINES_FILE = os.path.join(BASE_DIR, "routines.yaml")
BABY_CONFIG_FILE = os.path.join(BASE_DIR, "baby_config.yaml")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
SCORE_BESTS_FILE = os.path.join(DATA_DIR, "score_bests.json")
PUSH_SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, "push_subscriptions.json")
VAPID_KEYS_FILE = os.path.join(DATA_DIR, "vapid_keys.json")
PUSH_REMINDER_STATE_FILE = os.path.join(DATA_DIR, "push_reminder_state.json")

BUDGET_DIR = os.path.join(BASE_DIR, "budget")
BUDGET_DATA_DIR = os.path.join(DATA_DIR, "budget")
BUDGET_TRANSACTIONS_FILE = os.path.join(DATA_DIR, "budget", "transactions.json")
BUDGET_PLANS_DIR = os.path.join(DATA_DIR, "budget", "plans")
BUDGET_CATEGORIES_FILE = os.path.join(DATA_DIR, "budget", "categories.json")
BUDGET_IMPORT_META_FILE = os.path.join(DATA_DIR, "budget", "import_meta.json")
BUDGET_OVERVIEW_DIR = os.path.join(DATA_DIR, "budget", "overviews")
BUDGET_PLAID_ITEMS_FILE = os.path.join(DATA_DIR, "budget", "plaid_items.json")
BUDGET_BUDGETS_FILE = os.path.join(DATA_DIR, "budget", "budgets.json")

# Plaid config (optional). Populate from Cursor Cloud secrets to enable bank sync.
PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID", "").strip()
PLAID_SECRET = os.environ.get("PLAID_SECRET", "").strip()
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox").strip().lower()  # sandbox | development | production
PLAID_REDIRECT_URI = os.environ.get("PLAID_REDIRECT_URI", "").strip()

FANTASY_DIR = os.path.join(DATA_DIR, "fantasy")

CARD_WIDTH_INCHES = 5
CARD_HEIGHT_INCHES = 3

WEEK_START_DAY = 0

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Prefill for per-task push time on Edit (HH:MM, 24h). Override with LM_DEFAULT_NOTIFY_TIME.
_default_nt = os.environ.get("LM_DEFAULT_NOTIFY_TIME", "09:00").strip()
DEFAULT_NOTIFY_TIME = _default_nt if _default_nt else "09:00"

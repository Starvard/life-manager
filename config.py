import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Allow external data directory (e.g. persistent volume on Fly.io)
# Falls back to ./data for local development
DATA_DIR = os.environ.get("LM_DATA_DIR", os.path.join(BASE_DIR, "data"))
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
CARDS_DIR = os.path.join(DATA_DIR, "cards")
ROUTINE_CARDS_DIR = os.path.join(DATA_DIR, "routine-cards")
BABY_CARDS_DIR = os.path.join(DATA_DIR, "baby-cards")
ROUTINES_BUNDLED_FILE = os.path.join(BASE_DIR, "routines.yaml")
# In production, LM_DATA_DIR points at the persistent Fly volume — the image
# filesystem is rebuilt on every machine restart, so any UI edits to a file
# under BASE_DIR would silently disappear. Keep the user-edited copy on the
# volume; the bundled file in the repo only acts as a first-boot seed.
if DATA_DIR == os.path.join(BASE_DIR, "data"):
    ROUTINES_FILE = ROUTINES_BUNDLED_FILE
else:
    ROUTINES_FILE = os.path.join(DATA_DIR, "routines.yaml")
BABY_CONFIG_FILE = os.path.join(BASE_DIR, "baby_config.yaml")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
SCORE_BESTS_FILE = os.path.join(DATA_DIR, "score_bests.json")
PUSH_SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, "push_subscriptions.json")
VAPID_KEYS_FILE = os.path.join(DATA_DIR, "vapid_keys.json")
PUSH_REMINDER_STATE_FILE = os.path.join(DATA_DIR, "push_reminder_state.json")
NAV_PREFS_FILE = os.path.join(DATA_DIR, "ui_nav.json")

BUDGET_DIR = os.path.join(BASE_DIR, "budget")
BUDGET_DATA_DIR = os.path.join(DATA_DIR, "budget")
BUDGET_TRANSACTIONS_FILE = os.path.join(DATA_DIR, "budget", "transactions.json")
BUDGET_PLANS_DIR = os.path.join(DATA_DIR, "budget", "plans")
BUDGET_CATEGORIES_FILE = os.path.join(DATA_DIR, "budget", "categories.json")
BUDGET_IMPORT_META_FILE = os.path.join(DATA_DIR, "budget", "import_meta.json")
BUDGET_OVERVIEW_DIR = os.path.join(DATA_DIR, "budget", "overviews")
BUDGET_PLAID_ITEMS_FILE = os.path.join(DATA_DIR, "budget", "plaid_items.json")
BUDGET_BUDGETS_FILE = os.path.join(DATA_DIR, "budget", "budgets.json")
BUDGET_PLAID_CREDS_FILE = os.path.join(DATA_DIR, "budget", "plaid_credentials.json")

# Plaid config (optional). Populate from Cursor Cloud secrets to enable bank sync.
PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID", "").strip()
PLAID_SECRET = os.environ.get("PLAID_SECRET", "").strip()
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox").strip().lower()  # sandbox | development | production
PLAID_REDIRECT_URI = os.environ.get("PLAID_REDIRECT_URI", "").strip()

FANTASY_DIR = os.path.join(DATA_DIR, "fantasy")
RECIPES_DIR = os.path.join(DATA_DIR, "recipes")

CARD_WIDTH_INCHES = 5
CARD_HEIGHT_INCHES = 3

WEEK_START_DAY = 0

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Per-task push reminders default to blank (opt-in). Set a Notify time on a
# task in the /routines edit page to start receiving reminders for it.

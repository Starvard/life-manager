import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
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

CARD_WIDTH_INCHES = 5
CARD_HEIGHT_INCHES = 3

WEEK_START_DAY = 0

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Prefill for per-task push time on Edit (HH:MM, 24h). Override with LM_DEFAULT_NOTIFY_TIME.
_default_nt = os.environ.get("LM_DEFAULT_NOTIFY_TIME", "09:00").strip()
DEFAULT_NOTIFY_TIME = _default_nt if _default_nt else "09:00"

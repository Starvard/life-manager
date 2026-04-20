import os
import socket
import json
import time
from datetime import date, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for,
    send_file, send_from_directory, flash, jsonify, make_response,
)

import config

_CACHE_BUST = str(int(time.time()))
from services.routine_manager import load_routines, save_routines
from services.week_planner import iso_week_key, week_start_date
from services.score_bests import update_and_return_bests
from services.score_helpers import (
    weighted_week_score,
    weighted_day_score,
    daily_breakdown_weighted,
    today_weekday_index,
    week_day_summary,
    today_score_banner_context,
)
from services.card_store import (
    get_routine_cards, get_routine_card,
    toggle_routine_dot, set_routine_dot, set_routine_notes, list_routine_weeks,
    regenerate_routine_cards,
    add_extra_task, remove_extra_task,
    complete_routine_day_scheduled,
    get_baby_card, save_baby_card, update_baby_track, list_baby_days,
)
from services import push_subscriptions
from services import vapid_keys
from services.push_reminders import (
    refresh_reminder_state_after_dot_change,
    send_test_push_to_all,
)
from services.card_generator import generate_cards_pdf
from services.baby_card_generator import generate_baby_cards_pdf
from services.budget_store import (
    load_transactions, save_transactions,
    get_transactions_by_month, get_available_months,
    update_transaction, load_plan, save_plan, list_plan_months,
    compute_monthly_report, record_import, load_import_meta,
    load_categories,
    load_overview,
    refresh_overviews_from_exports,
    load_budgets, save_budgets, set_category_budget,
)
from services.budget_import import import_from_directory
from services.budget_dedupe import merge_new_transactions
from services.budget_categorizer import (
    get_all_categories, get_display_category,
    BUDGET_CATEGORIES, infer_category, recategorize_all,
    list_keyword_rules, upsert_keyword_rule, delete_keyword_rule,
    learn_rule_from_override,
)
from services.budget_csv_import import parse_csv_text
from services import plaid_client, plaid_credentials
from services.fantasy_store import (
    load_state as fantasy_load_state,
    state_for_client as fantasy_state_for_client,
    update_settings as fantasy_update_settings,
    update_plan as fantasy_update_plan,
    update_rebuild_board_patches as fantasy_update_rebuild_board,
    add_trade_idea as fantasy_add_trade_idea,
    remove_trade_idea as fantasy_remove_trade_idea,
    apply_sync_snapshot as fantasy_apply_sync_snapshot,
)
from services.fantasy_sleeper import sync_team as fantasy_sync_team
from services.fantasy_trade_jobs import refresh_trade_suggestions as fantasy_refresh_trades
from services import recipes_store, recipes_search

# Seed persistent volume on first cloud deploy
from seed_data import seed as _seed_data
_seed_data()

app = Flask(__name__)
app.secret_key = os.environ.get("LM_SECRET_KEY", "life-manager-local-key")

for d in [config.PHOTOS_DIR, config.CARDS_DIR,
          config.ROUTINE_CARDS_DIR, config.BABY_CARDS_DIR,
          config.BUDGET_DATA_DIR, config.BUDGET_PLANS_DIR,
          config.BUDGET_OVERVIEW_DIR, config.FANTASY_DIR,
          config.RECIPES_DIR]:
    os.makedirs(d, exist_ok=True)


def _network_base_url_for_phone() -> str:
    """URL to open on another device on the same Wi\u2011Fi (not 127.0.0.1)."""
    try:
        port = int(os.environ.get("LM_PORT", "5000"))
    except ValueError:
        port = 5000
    cert = os.environ.get("LM_SSL_CERT", "").strip()
    key = os.environ.get("LM_SSL_KEY", "").strip()
    ssl_on = (
        (cert and key and os.path.isfile(cert) and os.path.isfile(key))
        or os.environ.get("LM_USE_SSL", "").lower() in ("1", "true", "yes")
    )
    scheme = "https" if ssl_on else "http"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    return f"{scheme}://{ip}:{port}"


@app.context_processor
def inject_cache_bust():
    return {"cache_bust": _CACHE_BUST}


@app.context_processor
def inject_network_url():
    host = (request.host.split(":")[0].lower() if request.host else "") or ""
    loopback = host in ("127.0.0.1", "localhost", "::1")
    return {
        "network_base_url": _network_base_url_for_phone(),
        "browser_on_loopback_host": loopback,
        "default_notify_time": config.DEFAULT_NOTIFY_TIME,
    }


def _default_week_key():
    """ISO week containing today (Mon–Sun). Matches /cards/day with no date param."""
    return iso_week_key(week_start_date(date.today()))


def _anchor_date_iso_for_week(week_key: str) -> str:
    """Pick a calendar date in week_key for Day-view links (prefer today if in-range)."""
    parts = week_key.split("-W")
    if len(parts) != 2:
        return date.today().isoformat()
    try:
        y, wn = int(parts[0]), int(parts[1])
        monday = date.fromisocalendar(y, wn, 1)
    except ValueError:
        return date.today().isoformat()
    today = date.today()
    sunday = monday + timedelta(days=6)
    if monday <= today <= sunday:
        return today.isoformat()
    if today < monday:
        return monday.isoformat()
    return sunday.isoformat()


@app.context_processor
def routine_nav_defaults():
    return {
        "routine_default_week": _default_week_key(),
        "routine_today_iso": date.today().isoformat(),
    }


def _ordered_cards(cards: dict) -> dict:
    """Sort cards dict by area_order from routines.yaml."""
    data = load_routines()
    order = data.get("area_order", [])
    order_map = {k: i for i, k in enumerate(order)}
    return dict(sorted(cards.items(), key=lambda kv: order_map.get(kv[0], 999)))


# \u2500\u2500 HTML Pages \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/")
def dashboard():
    wk = request.args.get("week", _default_week_key())
    cards = _ordered_cards(get_routine_cards(wk))
    weeks = list_routine_weeks()
    baby_days = list_baby_days()
    _, _, week_score_pct = weighted_week_score(cards)
    daily_row = daily_breakdown_weighted(cards)
    week_start = next((c.get("week_start") for c in cards.values()), None)
    today_idx = today_weekday_index(week_start) if week_start else None
    today_score_pct = None
    if today_idx is not None:
        _, _, today_score_pct = weighted_day_score(cards, today_idx)
    day_metrics = week_day_summary(cards)
    score_bests = update_and_return_bests(wk, cards)
    return render_template(
        "dashboard.html",
        week_key=wk,
        cards=cards,
        weeks=weeks,
        baby_days=baby_days,
        week_score_pct=week_score_pct,
        daily_score_row=daily_row,
        today_weekday_idx=today_idx,
        today_score_pct=today_score_pct,
        day_metrics=day_metrics,
        score_bests=score_bests,
    )


@app.route("/cards")
def cards_page():
    wk = request.args.get("week", _default_week_key())
    cards = _ordered_cards(get_routine_cards(wk))
    weeks = list_routine_weeks()
    banner = today_score_banner_context(cards)
    update_and_return_bests(wk, cards)
    return render_template(
        "cards.html",
        week_key=wk,
        cards=cards,
        weeks=weeks,
        cards_day_date=_anchor_date_iso_for_week(wk),
        **banner,
    )


@app.route("/cards/day")
def cards_day_page():
    day_str = request.args.get("date", date.today().isoformat())
    try:
        selected_date = date.fromisoformat(day_str)
    except ValueError:
        selected_date = date.today()
        day_str = selected_date.isoformat()
    monday = selected_date - timedelta(days=selected_date.weekday())
    wk = iso_week_key(monday)
    day_idx = (selected_date - monday).days
    day_label = config.DAYS_OF_WEEK[day_idx]
    cards = _ordered_cards(get_routine_cards(wk))
    _, _, day_score_pct = weighted_day_score(cards, day_idx)
    return render_template(
        "cards_day.html",
        week_key=wk,
        day_idx=day_idx,
        day_label=day_label,
        selected_date=day_str,
        cards=cards,
        day_score_pct=day_score_pct,
        cards_week_for_toggle=wk,
    )


@app.route("/baby")
def baby_page():
    d = request.args.get("date", date.today().isoformat())
    card = get_baby_card(d)
    days = list_baby_days()
    return render_template("baby.html", card_date=d, card=card, days=days)


@app.route("/routines")
def routines_page():
    data = load_routines()
    order = data.get("area_order", [])
    all_areas = data.get("areas", {})
    ordered_areas = {k: all_areas[k] for k in order if k in all_areas}
    for k, v in all_areas.items():
        if k not in ordered_areas:
            ordered_areas[k] = v
    return render_template("routines.html", areas=ordered_areas)


@app.route("/routines/save", methods=["POST"])
def save_routines_form():
    data = load_routines()
    areas = data.get("areas", {})

    for area_key in list(areas.keys()):
        area = areas[area_key]
        area["name"] = request.form.get(f"area_name_{area_key}", area.get("name", area_key))

        updated_tasks = []
        i = 0
        while True:
            name_field = f"task_name_{area_key}_{i}"
            if name_field not in request.form:
                break
            if request.form.get(f"task_delete_{area_key}_{i}"):
                i += 1
                continue
            name = request.form[name_field].strip()
            if not name:
                i += 1
                continue
            task = {"name": name}
            wt = request.form.get(f"task_weight_{area_key}_{i}", "").strip()
            if wt:
                try:
                    wv = float(wt)
                    if wv > 0:
                        task["weight"] = wv
                except ValueError:
                    pass
            fpy = request.form.get(f"task_fpy_{area_key}_{i}", "").strip()
            freq = request.form.get(f"task_freq_{area_key}_{i}", "").strip()
            if fpy:
                try:
                    task["freq_per_year"] = float(fpy)
                except ValueError:
                    pass
            elif freq:
                try:
                    task["freq"] = float(freq)
                except ValueError:
                    task["freq"] = 1
            od = []
            for x in request.form.getlist(f"task_on_days_{area_key}_{i}"):
                try:
                    d = int(x)
                    if 0 <= d <= 6:
                        od.append(d)
                except ValueError:
                    pass
            if od:
                task["on_days"] = sorted(set(od))
            nt = request.form.get(f"task_notify_time_{area_key}_{i}", "").strip()
            task["notify_time"] = nt
            updated_tasks.append(task)
            i += 1

        nf = f"new_task_name_{area_key}"
        if request.form.get(nf, "").strip():
            new_task = {"name": request.form[nf].strip()}
            nwt = request.form.get(f"new_task_weight_{area_key}", "").strip()
            if nwt:
                try:
                    wv = float(nwt)
                    if wv > 0:
                        new_task["weight"] = wv
                except ValueError:
                    pass
            fpy = request.form.get(f"new_task_fpy_{area_key}", "").strip()
            freq = request.form.get(f"new_task_freq_{area_key}", "").strip()
            if fpy:
                try:
                    new_task["freq_per_year"] = float(fpy)
                except ValueError:
                    pass
            elif freq:
                try:
                    new_task["freq"] = float(freq)
                except ValueError:
                    new_task["freq"] = 1
            else:
                new_task["freq"] = 1
            od = []
            for x in request.form.getlist(f"new_task_on_days_{area_key}"):
                try:
                    d = int(x)
                    if 0 <= d <= 6:
                        od.append(d)
                except ValueError:
                    pass
            if od:
                new_task["on_days"] = sorted(set(od))
            ntn = request.form.get(f"new_task_notify_time_{area_key}", "").strip()
            new_task["notify_time"] = ntn
            updated_tasks.append(new_task)

        area["tasks"] = updated_tasks

    new_key = request.form.get("new_area_key", "").strip().lower().replace(" ", "_")
    new_name = request.form.get("new_area_name", "").strip()
    if new_key and new_name:
        areas[new_key] = {"name": new_name, "tasks": []}
        data.setdefault("area_order", []).append(new_key)

    save_routines(data)
    regenerate_routine_cards(_default_week_key())
    flash("Routines saved!", "success")
    return redirect(url_for("routines_page"))


@app.route("/routines/delete-area/<area_key>", methods=["POST"])
def delete_area(area_key):
    data = load_routines()
    data.get("areas", {}).pop(area_key, None)
    order = data.get("area_order", [])
    if area_key in order:
        order.remove(area_key)
    save_routines(data)
    flash(f"Area '{area_key}' deleted.", "success")
    return redirect(url_for("routines_page"))


@app.route("/api/routines/reorder", methods=["PATCH"])
def api_reorder_area():
    body = request.get_json(force=True)
    area_key = body.get("area_key")
    direction = body.get("direction")
    data = load_routines()
    order = data.get("area_order", list(data.get("areas", {}).keys()))
    if area_key not in order:
        return jsonify({"ok": False}), 400
    idx = order.index(area_key)
    if direction == "up" and idx > 0:
        order[idx], order[idx - 1] = order[idx - 1], order[idx]
    elif direction == "down" and idx < len(order) - 1:
        order[idx], order[idx + 1] = order[idx + 1], order[idx]
    data["area_order"] = order
    save_routines(data)
    return jsonify({"ok": True, "order": order})


# \u2500\u2500 API: Routine Cards \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/api/routine-cards/<week_key>")
def api_get_routine_cards(week_key):
    return jsonify({"areas": get_routine_cards(week_key)})


@app.route("/sw.js")
def service_worker():
    resp = make_response(
        send_from_directory(
            app.static_folder, "sw.js", mimetype="application/javascript"
        )
    )
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache, max-age=0"
    return resp


@app.route("/api/routine-cards/<week_key>/<area_key>/toggle", methods=["PATCH"])
def api_toggle_dot(week_key, area_key):
    body = request.get_json(force=True)
    task = int(body.get("task", 0))
    day = int(body.get("day", 0))
    dot = int(body.get("dot", 0))
    list_key = body.get("list", "tasks")
    if list_key not in ("tasks", "extra_tasks"):
        list_key = "tasks"
    new_val = toggle_routine_dot(
        week_key, area_key, task, day, dot, list_key=list_key
    )
    refresh_reminder_state_after_dot_change(
        week_key, area_key, list_key, task, day
    )
    return jsonify({"ok": True, "value": new_val})


@app.route("/api/routine-cards/<week_key>/<area_key>/set-dot", methods=["PATCH"])
def api_set_dot(week_key, area_key):
    body = request.get_json(force=True)
    task = int(body.get("task", 0))
    day = int(body.get("day", 0))
    dot = int(body.get("dot", 0))
    list_key = body.get("list", "tasks")
    if list_key not in ("tasks", "extra_tasks"):
        list_key = "tasks"
    value = bool(body.get("value", True))
    ok = set_routine_dot(
        week_key, area_key, task, day, dot, value, list_key=list_key
    )
    if ok:
        refresh_reminder_state_after_dot_change(
            week_key, area_key, list_key, task, day
        )
    return jsonify({"ok": ok})


@app.route(
    "/api/routine-cards/<week_key>/<area_key>/complete-scheduled-day",
    methods=["POST"],
)
def api_complete_scheduled_day(week_key, area_key):
    body = request.get_json(force=True)
    task = int(body.get("task", 0))
    day = int(body.get("day", 0))
    list_key = body.get("list", "tasks")
    if list_key not in ("tasks", "extra_tasks"):
        list_key = "tasks"
    ok = complete_routine_day_scheduled(
        week_key, area_key, task, day, list_key=list_key
    )
    if ok:
        refresh_reminder_state_after_dot_change(
            week_key, area_key, list_key, task, day
        )
    return jsonify({"ok": ok})


@app.route("/api/routine-cards/<week_key>/<area_key>/extra-task", methods=["POST"])
def api_add_extra_task(week_key, area_key):
    body = request.get_json(force=True)
    name = body.get("name", "")
    row = add_extra_task(week_key, area_key, name)
    if row is None:
        return jsonify({"ok": False}), 400
    card = get_routine_card(week_key, area_key)
    return jsonify({"ok": True, "extra_tasks": card.get("extra_tasks", [])})


@app.route("/api/routine-cards/<week_key>/<area_key>/extra-task/<int:task_idx>",
           methods=["DELETE"])
def api_remove_extra_task(week_key, area_key, task_idx):
    ok = remove_extra_task(week_key, area_key, task_idx)
    return jsonify({"ok": ok})


@app.route("/api/routine-cards/<week_key>/<area_key>/notes", methods=["PUT"])
def api_set_notes(week_key, area_key):
    body = request.get_json(force=True)
    set_routine_notes(week_key, area_key, body.get("notes", ""))
    return jsonify({"ok": True})


@app.route("/api/routine-cards/weeks")
def api_list_weeks():
    return jsonify({"weeks": list_routine_weeks()})


# \u2500\u2500 Web Push \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/api/push/vapid-public-key")
def api_push_vapid_public():
    _, pub_b64 = vapid_keys.ensure_vapid_keys()
    return jsonify({"publicKey": pub_b64})


@app.route("/api/push/subscribe", methods=["POST"])
def api_push_subscribe():
    sub = request.get_json(force=True)
    if not sub or not sub.get("endpoint"):
        return jsonify({"ok": False, "error": "invalid subscription"}), 400
    push_subscriptions.add_subscription(sub)
    return jsonify({"ok": True})


@app.route("/api/push/subscribe", methods=["DELETE"])
def api_push_unsubscribe():
    body = request.get_json(force=True, silent=True) or {}
    endpoint = body.get("endpoint", "")
    if not endpoint:
        return jsonify({"ok": False, "error": "missing endpoint"}), 400
    removed = push_subscriptions.remove_subscription(endpoint)
    return jsonify({"ok": removed})


@app.route("/api/push/test", methods=["POST"])
def api_push_test():
    sent, registered = send_test_push_to_all()
    return jsonify({"ok": True, "sent": sent, "registered": registered})


# \u2500\u2500 API: Baby Cards \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/api/baby-cards/<card_date>")
def api_get_baby_card(card_date):
    return jsonify(get_baby_card(card_date))


@app.route("/api/baby-cards/<card_date>/track", methods=["PATCH"])
def api_update_baby_track(card_date):
    body = request.get_json(force=True)
    track_key = body.pop("track", None)
    if not track_key:
        return jsonify({"error": "missing track"}), 400
    updated = update_baby_track(card_date, track_key, body)
    return jsonify({"ok": True, "track": updated})


@app.route("/api/baby-cards/days")
def api_list_baby_days():
    return jsonify({"days": list_baby_days()})


# \u2500\u2500 Budget Page \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/budget")
def budget_page():
    months = get_available_months()
    current_month = request.args.get("month", "")
    if not current_month:
        from datetime import date as _date
        current_month = _date.today().strftime("%Y-%m")
    txns = get_transactions_by_month(current_month)
    report = compute_monthly_report(current_month)
    plan = load_plan(current_month)
    categories = get_all_categories(load_transactions())
    overview = load_overview(current_month) or {}
    budgets = load_budgets().get("limits") or {}
    plaid_items = plaid_client.list_items_public()
    _creds = plaid_credentials.get_credentials()
    plaid_status = {
        "configured": plaid_client.is_configured(),
        "env": _creds["env"],
        "has_client_id": bool(_creds["client_id"]),
        "has_secret": bool(_creds["secret"]),
        "has_redirect_uri": bool(_creds["redirect_uri"]),
        "client_id_preview": (_creds["client_id"][:6] + "…") if _creds["client_id"] else "",
        "redirect_uri": _creds["redirect_uri"],
        "sources": plaid_credentials.credential_source(),
    }
    return render_template(
        "budget.html",
        months=months,
        current_month=current_month,
        transactions=txns,
        report=report,
        plan=plan,
        categories=categories,
        overview=overview,
        budgets=budgets,
        budget_categories=BUDGET_CATEGORIES,
        plaid_items=plaid_items,
        plaid_configured=plaid_client.is_configured(),
        plaid_status=plaid_status,
    )


# \u2500\u2500 API: Budget \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/api/budget/import", methods=["POST"])
def api_budget_import():
    body = request.get_json(silent=True) or {}
    replace_all = bool(body.get("replace_all"))

    budget_exports_dir = os.path.join(config.BUDGET_DIR, "2026 Budget")
    if not os.path.isdir(budget_exports_dir):
        return jsonify({"ok": False, "error": "No budget export directory found"}), 404

    overview_months = refresh_overviews_from_exports(budget_exports_dir)

    incoming = import_from_directory(budget_exports_dir)
    existing = [] if replace_all else load_transactions()
    merged = existing
    new_count = 0
    if incoming:
        merged = merge_new_transactions(existing, incoming)
        save_transactions(merged)
        new_count = len(merged) - len(existing)
        import hashlib as _hl
        fp = _hl.sha256(json.dumps([t["id"] for t in incoming]).encode()).hexdigest()[:16]
        record_import("2026 Budget", len(incoming), fp)
    elif replace_all and not incoming:
        save_transactions([])
        merged = []

    if not incoming and overview_months == 0:
        return jsonify({
            "ok": False,
            "error": "No transactions or monthly budget sheets found in export folder",
        }), 400

    return jsonify({
        "ok": True,
        "imported": len(incoming),
        "new": new_count,
        "total": len(merged),
        "duplicates_marked": sum(1 for t in merged if t.get("is_duplicate")),
        "overview_months_saved": overview_months,
    })


@app.route("/api/budget/transactions")
def api_budget_transactions():
    month = request.args.get("month", "")
    show_dupes = request.args.get("show_duplicates", "false").lower() == "true"
    if month:
        txns = get_transactions_by_month(month)
    else:
        # Copy: load_transactions returns a cached list shared between callers.
        txns = list(load_transactions())
    if not show_dupes:
        txns = [t for t in txns if not t.get("is_duplicate")]
    txns.sort(key=lambda t: t.get("date", ""), reverse=True)
    return jsonify({"transactions": txns, "count": len(txns)})


@app.route("/api/budget/transactions/<tx_id>/category", methods=["PATCH"])
def api_budget_update_category(tx_id):
    body = request.get_json(force=True) or {}
    new_cat = (body.get("category") or "").strip()
    learn = bool(body.get("learn", True))
    if not new_cat:
        return jsonify({"ok": False, "error": "Missing category"}), 400
    txns = load_transactions()
    for tx in txns:
        if tx.get("id") == tx_id:
            tx["category_override"] = new_cat
            if learn:
                learn_rule_from_override(tx, new_cat)
            save_transactions(txns)
            return jsonify({"ok": True, "transaction": tx})
    return jsonify({"ok": False, "error": "Transaction not found"}), 404


@app.route("/api/budget/transactions/<tx_id>/duplicate", methods=["PATCH"])
def api_budget_resolve_duplicate(tx_id):
    body = request.get_json(force=True)
    action = body.get("action", "dismiss")
    txns = load_transactions()
    for tx in txns:
        if tx.get("id") == tx_id:
            if action == "keep":
                tx["is_duplicate"] = False
                tx["duplicate_of"] = None
            elif action == "dismiss":
                tx["is_duplicate"] = True
            save_transactions(txns)
            return jsonify({"ok": True, "transaction": tx})
    return jsonify({"ok": False, "error": "Transaction not found"}), 404


@app.route("/api/budget/report")
def api_budget_report():
    month = request.args.get("month", "")
    if not month:
        from datetime import date as _date
        month = _date.today().strftime("%Y-%m")
    return jsonify(compute_monthly_report(month))


@app.route("/api/budget/plan/<month>")
def api_budget_get_plan(month):
    return jsonify(load_plan(month))


@app.route("/api/budget/plan/<month>", methods=["PUT"])
def api_budget_save_plan(month):
    body = request.get_json(force=True)
    save_plan(month, body)
    return jsonify({"ok": True})


@app.route("/api/budget/months")
def api_budget_months():
    tx_months = get_available_months()
    plan_months = list_plan_months()
    all_months = sorted(set(tx_months + plan_months))
    return jsonify({"months": all_months})


@app.route("/api/budget/categories")
def api_budget_categories():
    txns = load_transactions()
    return jsonify({
        "categories": get_all_categories(txns),
        "defaults": BUDGET_CATEGORIES,
    })


# ── CSV upload (bank-agnostic fallback) ─────────────────────────

@app.route("/api/budget/import-csv", methods=["POST"])
def api_budget_import_csv():
    """Upload one or more CSV files (bank export). Multipart or JSON {text:...}."""
    records: list[dict] = []
    file_names: list[str] = []

    if request.files:
        for f in request.files.getlist("files") or []:
            if not f or not f.filename:
                continue
            try:
                text = f.read().decode("utf-8", errors="replace")
            except Exception:
                continue
            records.extend(parse_csv_text(text, source_name=f.filename))
            file_names.append(f.filename)
        # Also accept single "file" field for convenience
        single = request.files.get("file")
        if single and single.filename and single.filename not in file_names:
            try:
                text = single.read().decode("utf-8", errors="replace")
            except Exception:
                text = ""
            if text:
                records.extend(parse_csv_text(text, source_name=single.filename))
                file_names.append(single.filename)
    else:
        body = request.get_json(silent=True) or {}
        text = body.get("text") or ""
        src = body.get("source") or "pasted.csv"
        if text:
            records.extend(parse_csv_text(text, source_name=src))
            file_names.append(src)

    if not records:
        return jsonify({
            "ok": False,
            "error": (
                "Could not parse any transactions. Make sure the file has a "
                "header row with columns like Date, Description, and Amount "
                "(or Debit/Credit)."
            ),
        }), 400

    # Apply auto-categorization before persisting
    for r in records:
        r["category_display"] = infer_category(r)

    existing = load_transactions()
    merged = merge_new_transactions(existing, records)
    save_transactions(merged)

    new_count = len(merged) - len(existing)
    import hashlib as _hl
    fp = _hl.sha256(json.dumps([r["id"] for r in records]).encode()).hexdigest()[:16]
    record_import(", ".join(file_names) or "csv-upload", len(records), fp)

    return jsonify({
        "ok": True,
        "files": file_names,
        "parsed": len(records),
        "new": new_count,
        "total": len(merged),
    })


# ── Plaid (Link / sync / items) ─────────────────────────────────

@app.route("/api/budget/plaid/status")
def api_budget_plaid_status():
    creds = plaid_credentials.get_credentials()
    sources = plaid_credentials.credential_source()
    return jsonify({
        "configured": plaid_client.is_configured(),
        "env": creds["env"],
        "has_client_id": bool(creds["client_id"]),
        "has_secret": bool(creds["secret"]),
        "has_redirect_uri": bool(creds["redirect_uri"]),
        "sources": sources,
        "items": plaid_client.list_items_public(),
    })


@app.route("/api/budget/plaid/credentials", methods=["GET"])
def api_budget_plaid_get_credentials():
    """Return non-secret info about the current Plaid credential state."""
    creds = plaid_credentials.get_credentials()
    sources = plaid_credentials.credential_source()
    return jsonify({
        "configured": bool(creds["client_id"] and creds["secret"]),
        "env": creds["env"],
        "has_client_id": bool(creds["client_id"]),
        "has_secret": bool(creds["secret"]),
        "has_redirect_uri": bool(creds["redirect_uri"]),
        "client_id_preview": (creds["client_id"][:6] + "…") if creds["client_id"] else "",
        "redirect_uri": creds["redirect_uri"],
        "sources": sources,
    })


@app.route("/api/budget/plaid/credentials", methods=["PUT"])
def api_budget_plaid_save_credentials():
    """Save Plaid credentials into data/budget/plaid_credentials.json."""
    body = request.get_json(force=True) or {}
    updated = plaid_credentials.save_credentials(
        client_id=body.get("client_id") if "client_id" in body else None,
        secret=body.get("secret") if "secret" in body else None,
        env=body.get("env") if "env" in body else None,
        redirect_uri=body.get("redirect_uri") if "redirect_uri" in body else None,
    )
    return jsonify({
        "ok": True,
        "configured": bool(updated["client_id"] and updated["secret"]),
        "env": updated["env"],
        "has_client_id": bool(updated["client_id"]),
        "has_secret": bool(updated["secret"]),
        "has_redirect_uri": bool(updated["redirect_uri"]),
        "sources": plaid_credentials.credential_source(),
    })


@app.route("/api/budget/plaid/credentials", methods=["DELETE"])
def api_budget_plaid_clear_credentials():
    plaid_credentials.clear_credentials()
    return jsonify({
        "ok": True,
        "configured": plaid_client.is_configured(),
        "sources": plaid_credentials.credential_source(),
    })


@app.route("/api/budget/plaid/link-token", methods=["POST"])
def api_budget_plaid_link_token():
    result = plaid_client.create_link_token()
    if result.get("error"):
        return jsonify({"ok": False, "error": result["error"]}), 400
    return jsonify({"ok": True, **result})


@app.route("/api/budget/plaid/exchange", methods=["POST"])
def api_budget_plaid_exchange():
    body = request.get_json(force=True) or {}
    public_token = body.get("public_token") or ""
    institution_name = body.get("institution_name") or ""
    if not public_token:
        return jsonify({"ok": False, "error": "Missing public_token"}), 400
    result = plaid_client.exchange_public_token(public_token, institution_name)
    if result.get("error"):
        return jsonify({"ok": False, "error": result["error"]}), 400
    return jsonify(result)


@app.route("/api/budget/plaid/sync", methods=["POST"])
def api_budget_plaid_sync():
    result = plaid_client.sync_all_items()
    if not result.get("ok"):
        return jsonify(result), 400
    # Re-categorize to apply up-to-date rules
    txns = load_transactions()
    recategorize_all(txns)
    save_transactions(txns)
    return jsonify(result)


@app.route("/api/budget/plaid/items/<item_id>", methods=["DELETE"])
def api_budget_plaid_remove_item(item_id):
    ok = plaid_client.remove_item(item_id)
    return jsonify({"ok": ok})


# ── Budgets (simple over/under) ─────────────────────────────────

@app.route("/api/budget/budgets", methods=["GET"])
def api_budget_get_budgets():
    return jsonify(load_budgets())


@app.route("/api/budget/budgets", methods=["PUT"])
def api_budget_save_budgets():
    body = request.get_json(force=True) or {}
    limits = body.get("limits") if isinstance(body, dict) else None
    if not isinstance(limits, dict):
        return jsonify({"ok": False, "error": "Expected {limits: {category: amount}}"}), 400
    save_budgets(limits)
    return jsonify({"ok": True, **load_budgets()})


@app.route("/api/budget/budgets/<path:category>", methods=["PUT"])
def api_budget_set_one_budget(category):
    body = request.get_json(force=True) or {}
    amount = body.get("amount")
    res = set_category_budget(category, amount)
    return jsonify({"ok": True, **res})


@app.route("/api/budget/recategorize", methods=["POST"])
def api_budget_recategorize():
    txns = load_transactions()
    changed = recategorize_all(txns)
    save_transactions(txns)
    return jsonify({"ok": True, "changed": changed, "total": len(txns)})


# ── Keyword rules ───────────────────────────────────────────────

@app.route("/api/budget/rules", methods=["GET"])
def api_budget_list_rules():
    return jsonify({"rules": list_keyword_rules()})


@app.route("/api/budget/rules", methods=["POST"])
def api_budget_upsert_rule():
    body = request.get_json(force=True) or {}
    keyword = (body.get("keyword") or "").strip()
    category = (body.get("category") or "").strip()
    if not keyword or not category:
        return jsonify({"ok": False, "error": "Missing keyword or category"}), 400
    upsert_keyword_rule(keyword, category)
    return jsonify({"ok": True, "rules": list_keyword_rules()})


@app.route("/api/budget/rules/<path:keyword>", methods=["DELETE"])
def api_budget_delete_rule(keyword):
    ok = delete_keyword_rule(keyword)
    return jsonify({"ok": ok, "rules": list_keyword_rules()})


# \u2500\u2500 Research \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/research")
def research_page():
    topics = [
        {
            "slug": "am-facility-cost",
            "endpoint": "research_am_facility_cost",
            "title": "Cost of Running an Additive Manufacturing Facility",
            "summary": (
                "Full CapEx + OpEx breakdown for a small-to-mid sized AM shop: "
                "printers and peripheral equipment, facility build-out, software, "
                "personnel, internet / IT, consumables, maintenance, and "
                "per-machine operating cost."
            ),
        },
    ]
    return render_template("research.html", topics=topics)


@app.route("/research/am-facility-cost")
def research_am_facility_cost():
    return render_template("research/am_facility_cost.html")


# \u2500\u2500 Fantasy (Sleeper) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/fantasy")
def fantasy_page():
    state = fantasy_load_state()
    return render_template(
        "fantasy.html",
        fantasy_bootstrap=fantasy_state_for_client(state),
    )


@app.route("/api/fantasy/state")
def api_fantasy_state():
    return jsonify(fantasy_state_for_client(fantasy_load_state()))


@app.route("/api/fantasy/settings", methods=["PUT"])
def api_fantasy_settings():
    body = request.get_json(silent=True) or {}
    state = fantasy_update_settings(body)
    return jsonify({"ok": True, "state": fantasy_state_for_client(state)})


@app.route("/api/fantasy/plan", methods=["PUT"])
def api_fantasy_plan():
    body = request.get_json(silent=True) or {}
    state = fantasy_update_plan(body)
    return jsonify({"ok": True, "state": fantasy_state_for_client(state)})


@app.route("/api/fantasy/rebuild-board", methods=["PATCH"])
def api_fantasy_rebuild_board():
    body = request.get_json(silent=True) or {}
    assets_patch = body.get("assets")
    patches = assets_patch if isinstance(assets_patch, dict) else body
    if not isinstance(patches, dict):
        patches = {}
    state = fantasy_update_rebuild_board(patches)
    return jsonify({"ok": True, "state": fantasy_state_for_client(state)})


@app.route("/api/fantasy/trade-ideas", methods=["POST"])
def api_fantasy_trade_idea_add():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    state = fantasy_add_trade_idea(text)
    return jsonify({"ok": True, "state": fantasy_state_for_client(state)})


@app.route("/api/fantasy/trade-ideas/<idea_id>", methods=["DELETE"])
def api_fantasy_trade_idea_remove(idea_id):
    state = fantasy_remove_trade_idea(idea_id)
    return jsonify({"ok": True, "state": fantasy_state_for_client(state)})


@app.route("/api/fantasy/sync", methods=["POST"])
def api_fantasy_sync():
    state = fantasy_load_state()
    settings = state.get("settings") or {}
    result = fantasy_sync_team(settings)
    if not result.get("ok"):
        return jsonify({"ok": False, "error": result.get("error", "Sync failed")}), 400
    snap = result["snapshot"]
    fantasy_apply_sync_snapshot(snap)
    body = request.get_json(silent=True) or {}
    if body.get("refresh_trades"):
        fantasy_refresh_trades()
    return jsonify({"ok": True, "state": fantasy_state_for_client(fantasy_load_state())})


@app.route("/api/fantasy/trade-refresh", methods=["POST"])
def api_fantasy_trade_refresh():
    try:
        out = fantasy_refresh_trades()
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e) or "Trade refresh crashed",
            "state": fantasy_state_for_client(fantasy_load_state()),
        })
    if out.get("skipped"):
        return jsonify({
            "ok": True,
            "skipped": True,
            "state": fantasy_state_for_client(fantasy_load_state()),
        })
    if not out.get("ok"):
        return jsonify({
            "ok": False,
            "error": out.get("error", "Refresh failed"),
            "state": fantasy_state_for_client(fantasy_load_state()),
        })
    return jsonify({"ok": True, "state": fantasy_state_for_client(fantasy_load_state())})


# ── Home Recipes ────────────────────────────────────────────────

@app.route("/recipes")
def recipes_page():
    week_key = recipes_store.current_week_key()
    return render_template(
        "recipes.html",
        recipes_bootstrap={
            "recipes": recipes_store.list_recipes(),
            "grocery": recipes_store.list_grocery(),
            "inventory": recipes_store.list_inventory(),
            "menu": recipes_store.get_week_menu(week_key),
            "categories": recipes_store.DEFAULT_CATEGORIES,
            "menu_slots": recipes_store.MENU_SLOTS,
            "menu_targets": recipes_store.MENU_SLOT_TARGETS,
            "current_week": week_key,
            "today": date.today().isoformat(),
        },
    )


@app.route("/api/recipes")
def api_recipes_list():
    q = request.args.get("q", "")
    if q:
        return jsonify({"recipes": recipes_store.search_recipes_local(q)})
    return jsonify({"recipes": recipes_store.list_recipes()})


@app.route("/api/recipes", methods=["POST"])
def api_recipes_create():
    body = request.get_json(silent=True) or {}
    recipe = recipes_store.create_recipe(body)
    return jsonify({"ok": True, "recipe": recipe})


@app.route("/api/recipes/<recipe_id>")
def api_recipes_get(recipe_id):
    rec = recipes_store.get_recipe(recipe_id)
    if not rec:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "recipe": rec})


@app.route("/api/recipes/<recipe_id>", methods=["PUT"])
def api_recipes_update(recipe_id):
    body = request.get_json(silent=True) or {}
    rec = recipes_store.update_recipe(recipe_id, body)
    if not rec:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "recipe": rec})


@app.route("/api/recipes/<recipe_id>", methods=["DELETE"])
def api_recipes_delete(recipe_id):
    ok = recipes_store.delete_recipe(recipe_id)
    return jsonify({"ok": ok})


@app.route("/api/recipes/<recipe_id>/to-grocery", methods=["POST"])
def api_recipes_to_grocery(recipe_id):
    res = recipes_store.add_recipe_ingredients_to_grocery(recipe_id)
    if res.get("error"):
        return jsonify({"ok": False, **res}), 404
    return jsonify({"ok": True, **res, "items": recipes_store.list_grocery()})


@app.route("/api/recipes/search-online")
def api_recipes_search_online():
    q = request.args.get("q", "")
    return jsonify(recipes_search.search_online(q))


@app.route("/api/recipes/import-online", methods=["POST"])
def api_recipes_import_online():
    body = request.get_json(silent=True) or {}
    payload = body.get("recipe") or {}
    external_id = payload.get("external_id") or body.get("external_id")
    if external_id and not payload.get("ingredients"):
        fetched = recipes_search.lookup_online(external_id)
        if fetched:
            payload = fetched
    if not payload or not (payload.get("name") or "").strip():
        return jsonify({"ok": False, "error": "Could not import recipe."}), 400
    recipe = recipes_store.create_recipe(payload)
    return jsonify({"ok": True, "recipe": recipe})


# Grocery list ----------------------------------------------------

@app.route("/api/recipes/grocery")
def api_grocery_list():
    return jsonify({"items": recipes_store.list_grocery()})


@app.route("/api/recipes/grocery", methods=["POST"])
def api_grocery_add():
    body = request.get_json(silent=True) or {}
    try:
        item = recipes_store.add_grocery_item(body)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "item": item})


@app.route("/api/recipes/grocery/<item_id>", methods=["PATCH"])
def api_grocery_update(item_id):
    body = request.get_json(silent=True) or {}
    item = recipes_store.update_grocery_item(item_id, body)
    if not item:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "item": item})


@app.route("/api/recipes/grocery/<item_id>", methods=["DELETE"])
def api_grocery_delete(item_id):
    ok = recipes_store.delete_grocery_item(item_id)
    return jsonify({"ok": ok})


@app.route("/api/recipes/grocery/clear-checked", methods=["POST"])
def api_grocery_clear_checked():
    removed = recipes_store.clear_grocery_checked()
    return jsonify({"ok": True, "removed": removed, "items": recipes_store.list_grocery()})


@app.route("/api/recipes/grocery/move-checked-to-inventory", methods=["POST"])
def api_grocery_move_to_inventory():
    res = recipes_store.move_checked_grocery_to_inventory()
    return jsonify({
        "ok": True,
        **res,
        "items": recipes_store.list_grocery(),
        "inventory": recipes_store.list_inventory(),
    })


# Inventory -------------------------------------------------------

@app.route("/api/recipes/inventory")
def api_inventory_list():
    return jsonify({"items": recipes_store.list_inventory()})


@app.route("/api/recipes/inventory", methods=["POST"])
def api_inventory_add():
    body = request.get_json(silent=True) or {}
    try:
        item = recipes_store.add_inventory_item(body)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "item": item})


@app.route("/api/recipes/inventory/<item_id>", methods=["PATCH"])
def api_inventory_update(item_id):
    body = request.get_json(silent=True) or {}
    item = recipes_store.update_inventory_item(item_id, body)
    if not item:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "item": item})


@app.route("/api/recipes/inventory/<item_id>", methods=["DELETE"])
def api_inventory_delete(item_id):
    ok = recipes_store.delete_inventory_item(item_id)
    return jsonify({"ok": ok})


# Weekly menu -----------------------------------------------------

@app.route("/api/recipes/menu")
def api_menu_get():
    week_key = request.args.get("week", "")
    return jsonify({"ok": True, "menu": recipes_store.get_week_menu(week_key)})


@app.route("/api/recipes/menu/<slot>", methods=["POST"])
def api_menu_add(slot):
    body = request.get_json(silent=True) or {}
    week_key = body.get("week_key") or request.args.get("week", "")
    entry = recipes_store.add_menu_entry(week_key, slot, body)
    if not entry:
        return jsonify({"ok": False, "error": "Invalid slot or empty entry."}), 400
    return jsonify({
        "ok": True,
        "entry": entry,
        "menu": recipes_store.get_week_menu(week_key),
    })


@app.route("/api/recipes/menu/<slot>/<entry_id>", methods=["DELETE"])
def api_menu_remove(slot, entry_id):
    week_key = request.args.get("week", "")
    ok = recipes_store.remove_menu_entry(week_key, slot, entry_id)
    return jsonify({
        "ok": ok,
        "menu": recipes_store.get_week_menu(week_key),
    })


@app.route("/api/recipes/menu/clear", methods=["POST"])
def api_menu_clear():
    body = request.get_json(silent=True) or {}
    week_key = body.get("week_key") or request.args.get("week", "")
    ok = recipes_store.clear_week_menu(week_key)
    return jsonify({
        "ok": ok,
        "menu": recipes_store.get_week_menu(week_key),
    })


@app.route("/api/recipes/menu/to-grocery", methods=["POST"])
def api_menu_to_grocery():
    body = request.get_json(silent=True) or {}
    week_key = body.get("week_key") or request.args.get("week", "")
    res = recipes_store.add_menu_to_grocery(week_key)
    return jsonify({
        "ok": True,
        **res,
        "items": recipes_store.list_grocery(),
    })


# \u2500\u2500 PDF Export \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/api/routine-cards/<week_key>/export-pdf", methods=["POST"])
def api_export_routine_pdf(week_key):
    cards = get_routine_cards(week_key)
    plans = []
    for area_key, card in cards.items():
        plan = {
            "key": area_key,
            "name": card["area_name"],
            "week_key": card["week_key"],
            "week_start": card["week_start"],
            "tasks": [],
        }
        for task in card["tasks"]:
            dots = task.get("scheduled", [len(d) for d in task["days"]])
            plan["tasks"].append({"name": task["name"], "freq": task["freq"], "dots": dots})
        for task in card.get("extra_tasks", []):
            dots = task.get("scheduled", [len(d) for d in task["days"]])
            plan["tasks"].append({
                "name": task["name"] + " (this week)",
                "freq": task.get("freq", 1),
                "dots": dots,
            })
        plans.append(plan)
    filepath = generate_cards_pdf(plans, week_key)
    return jsonify({"ok": True, "filename": os.path.basename(filepath)})


@app.route("/cards/download/<week_key>")
def download_cards(week_key):
    filepath = os.path.join(config.CARDS_DIR, f"{week_key}.pdf")
    if not os.path.exists(filepath):
        flash("PDF not found.", "error")
        return redirect(url_for("cards_page"))
    return send_file(filepath, as_attachment=True,
                     download_name=f"routine-cards-{week_key}.pdf")


@app.route("/baby/download/<filename>")
def download_baby_pdf(filename):
    filepath = os.path.join(config.CARDS_DIR, filename)
    if not os.path.exists(filepath) or not filename.startswith("baby-"):
        flash("File not found.", "error")
        return redirect(url_for("baby_page"))
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/photos/<week_key>/<filename>")
def serve_photo(week_key, filename):
    photo_path = os.path.join(config.PHOTOS_DIR, week_key, filename)
    if os.path.exists(photo_path):
        return send_file(photo_path)
    return "Not found", 404


# \u2500\u2500 Startup \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _ssl_context():
    cert = os.environ.get("LM_SSL_CERT", "").strip()
    key = os.environ.get("LM_SSL_KEY", "").strip()
    if cert and key and os.path.isfile(cert) and os.path.isfile(key):
        return (cert, key)
    if os.environ.get("LM_USE_SSL", "").lower() in ("1", "true", "yes"):
        return "adhoc"
    return None


def _start_background_schedulers():
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and app.debug:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return
    try:
        from services.push_reminders import run_reminder_scan
    except ImportError:
        run_reminder_scan = None
    try:
        from services.fantasy_trade_jobs import refresh_trade_suggestions
    except ImportError:
        refresh_trade_suggestions = None

    sched = BackgroundScheduler()
    if run_reminder_scan:
        try:
            interval = int(os.environ.get("LM_REMINDER_INTERVAL_MINUTES", "30"))
        except ValueError:
            interval = 30
        interval = max(5, interval)
        sched.add_job(
            run_reminder_scan,
            "interval",
            minutes=interval,
            id="life_manager_push_reminders",
            replace_existing=True,
        )

    if (
        refresh_trade_suggestions
        and os.environ.get("LM_FANTASY_TRADE_CRON", "1").lower() not in ("0", "false", "no")
    ):
        try:
            dow = int(os.environ.get("LM_FANTASY_TRADE_CRON_DOW", "6"))
        except ValueError:
            dow = 6
        dow = max(0, min(6, dow))
        try:
            hour = int(os.environ.get("LM_FANTASY_TRADE_CRON_HOUR", "12"))
        except ValueError:
            hour = 12
        hour = max(0, min(23, hour))
        try:
            minute = int(os.environ.get("LM_FANTASY_TRADE_CRON_MINUTE", "0"))
        except ValueError:
            minute = 0
        minute = max(0, min(59, minute))
        sched.add_job(
            refresh_trade_suggestions,
            "cron",
            day_of_week=dow,
            hour=hour,
            minute=minute,
            id="fantasy_trade_weekly",
            replace_existing=True,
        )

    if sched.get_jobs():
        sched.start()


# \u2500\u2500 Health check (for Fly.io / load balancers) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@app.route("/healthz")
def health_check():
    return jsonify({"status": "ok"})


# \u2500\u2500 Startup \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

# Start background jobs for both dev (python app.py) and production (gunicorn)
_start_background_schedulers()


if __name__ == "__main__":
    ip = _get_local_ip()
    port = int(os.environ.get("LM_PORT", "5000"))
    ssl_ctx = _ssl_context()
    scheme = "https" if ssl_ctx else "http"
    print(f"\n  Life Manager running at:")
    print(f"    Local:   {scheme}://127.0.0.1:{port}")
    print(f"    Network: {scheme}://{ip}:{port}")
    if ssl_ctx:
        print(
            "    >>> HTTPS is ON \u2014 use these https:// links on your phone.\n"
            "        If the phone shows ERR_SSL_PROTOCOL_ERROR, you are hitting a server\n"
            "        that is still on plain HTTP; restart using start-with-push.bat.\n"
        )
    if not ssl_ctx:
        print(
            "    Web Push on Android needs HTTPS: set LM_USE_SSL=1 (dev adhoc cert) or "
            "LM_SSL_CERT + LM_SSL_KEY, or use a tunnel / reverse proxy.\n"
        )
    else:
        print(
            "    Accept the browser warning for the adhoc/LAN cert to enable push.\n"
        )
    app.run(
        debug=True,
        host="0.0.0.0",
        port=port,
        ssl_context=ssl_ctx,
    )

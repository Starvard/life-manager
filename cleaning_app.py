"""Production WSGI wrapper that registers optional app extensions.

Gunicorn imports `app` from this module. The existing application remains in
app.py; this wrapper imports it and then registers the Cleaning blueprint in a
plain, explicit way.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from app import app
from services.cleaning_store import (
    clear_room,
    get_cleaning_state,
    reset_all,
    set_task_done,
)

cleaning_bp = Blueprint("cleaning", __name__)


@cleaning_bp.route("/cleaning")
def cleaning_page():
    return render_template("cleaning.html", cleaning=get_cleaning_state())


@cleaning_bp.route("/api/cleaning", methods=["GET"])
def api_cleaning_state():
    return jsonify({"ok": True, **get_cleaning_state()})


@cleaning_bp.route("/api/cleaning/toggle", methods=["PATCH"])
def api_cleaning_toggle():
    body = request.get_json(force=True) or {}
    task_id = str(body.get("task_id", ""))
    done = bool(body.get("done", True))
    ok = set_task_done(task_id, done)
    status = 200 if ok else 404
    return jsonify({"ok": ok, **get_cleaning_state()}), status


@cleaning_bp.route("/api/cleaning/room/<room_id>/clear", methods=["POST"])
def api_cleaning_clear_room(room_id):
    ok = clear_room(room_id)
    status = 200 if ok else 404
    return jsonify({"ok": ok, **get_cleaning_state()}), status


@cleaning_bp.route("/api/cleaning/reset", methods=["POST"])
def api_cleaning_reset():
    reset_all()
    return jsonify({"ok": True, **get_cleaning_state()})


if "cleaning.cleaning_page" not in app.view_functions:
    app.register_blueprint(cleaning_bp)

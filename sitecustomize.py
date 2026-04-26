"""Runtime app extension hooks.

This file is imported automatically by Python at process startup. It registers
the Cleaning checklist blueprint without rewriting the large Flask app entry
file.
"""

from __future__ import annotations

_registered_app_ids: set[int] = set()


def _install_cleaning_blueprint(app):
    if id(app) in _registered_app_ids:
        return
    _registered_app_ids.add(id(app))

    try:
        from flask import Blueprint, jsonify, render_template, request
        from services.cleaning_store import (
            clear_room,
            get_cleaning_state,
            reset_all,
            set_task_done,
        )
    except Exception:
        # Do not block app startup if this optional module has a typo.
        # Flask will still boot; the error will surface during development.
        return

    bp = Blueprint("cleaning", __name__)

    @bp.route("/cleaning")
    def cleaning_page():
        return render_template("cleaning.html", cleaning=get_cleaning_state())

    @bp.route("/api/cleaning", methods=["GET"])
    def api_cleaning_state():
        return jsonify({"ok": True, **get_cleaning_state()})

    @bp.route("/api/cleaning/toggle", methods=["PATCH"])
    def api_cleaning_toggle():
        body = request.get_json(force=True) or {}
        task_id = str(body.get("task_id", ""))
        done = bool(body.get("done", True))
        ok = set_task_done(task_id, done)
        status = 200 if ok else 404
        return jsonify({"ok": ok, **get_cleaning_state()}), status

    @bp.route("/api/cleaning/room/<room_id>/clear", methods=["POST"])
    def api_cleaning_clear_room(room_id):
        ok = clear_room(room_id)
        status = 200 if ok else 404
        return jsonify({"ok": ok, **get_cleaning_state()}), status

    @bp.route("/api/cleaning/reset", methods=["POST"])
    def api_cleaning_reset():
        reset_all()
        return jsonify({"ok": True, **get_cleaning_state()})

    if "cleaning.cleaning_page" not in app.view_functions:
        app.register_blueprint(bp)


def _patch_flask():
    try:
        import flask
    except Exception:
        return

    original_init = flask.Flask.__init__

    if getattr(original_init, "_life_manager_cleaning_patch", False):
        return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_cleaning_blueprint(self)

    patched_init._life_manager_cleaning_patch = True
    flask.Flask.__init__ = patched_init


_patch_flask()

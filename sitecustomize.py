"""Runtime app extension hooks.

This file is imported automatically by Python at process startup. It registers
optional app extensions without rewriting the large Flask app entry file.
"""

from __future__ import annotations

_registered_app_ids: set[int] = set()


def _ordered_routine_areas() -> dict:
    from services.routine_manager import load_routines

    data = load_routines()
    order = data.get("area_order", [])
    all_areas = data.get("areas", {})
    ordered_areas = {k: all_areas[k] for k in order if k in all_areas}
    for k, v in all_areas.items():
        if k not in ordered_areas:
            ordered_areas[k] = v
    return ordered_areas


def _install_legacy_routines_restore(app):
    """Restore the full routines editor as the primary /routines page."""

    if getattr(app, "_legacy_routines_restore_installed", False):
        return
    app._legacy_routines_restore_installed = True

    from flask import render_template, request

    @app.before_request
    def _legacy_routines_before_request():
        if request.path == "/routines" and request.method == "GET":
            return render_template("routines.html", areas=_ordered_routine_areas())

        if request.path == "/routines/save" and request.method == "POST":
            view = app.view_functions.get("save_routines_form")
            if not view:
                return None
            response = app.make_response(view())
            if response.status_code in (301, 302, 303, 307, 308):
                response.headers["Location"] = "/routines"
            return response

        if request.path.startswith("/routines/delete-area/") and request.method == "POST":
            view = app.view_functions.get("delete_area")
            if not view:
                return None
            area_key = (request.view_args or {}).get("area_key") or request.path.rsplit("/", 1)[-1]
            response = app.make_response(view(area_key))
            if response.status_code in (301, 302, 303, 307, 308):
                response.headers["Location"] = "/routines"
            return response

        return None


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

    if getattr(original_init, "_life_manager_extension_patch", False):
        return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_cleaning_blueprint(self)
        _install_legacy_routines_restore(self)

    patched_init._life_manager_extension_patch = True
    flask.Flask.__init__ = patched_init


_patch_flask()

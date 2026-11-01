from flask import render_template, request, jsonify
from sqlalchemy import or_, desc
from extensions import db, limiter
from helpers import login_required, admin_user_id_key
from models import ActivityLog
from . import admin_bp


@admin_bp.route("/activity-logs")
@admin_bp.route("/logs")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def activity_logs():
    module_name = "logs"
    module_filter = request.args.get("module", "").strip()
    action_filter = request.args.get("action", "").strip()
    search_query = request.args.get("search", "").strip()

    query = ActivityLog.query

    if module_filter:
        query = query.filter(ActivityLog.module == module_filter)

    if action_filter:
        query = query.filter(ActivityLog.action == action_filter)

    if search_query:
        like_term = f"%{search_query}%"
        query = query.filter(
            or_(
                ActivityLog.username.ilike(like_term),
                ActivityLog.description.ilike(like_term),
                ActivityLog.ip_address.ilike(like_term),
                ActivityLog.record_id.ilike(like_term),
            )
        )

    logs = query.order_by(desc(ActivityLog.created_at), desc(ActivityLog.id)).limit(100).all()

    # Get distinct modules and actions for filter dropdowns
    available_modules = [r[0] for r in db.session.query(ActivityLog.module).distinct().all() if r[0]]
    available_actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().all() if r[0]]

    # Ensure standard options exist in dropdowns
    for default_mod in ["UserRateLimit", "IpRateLimit", "Error500"]:
        if default_mod not in available_modules:
            available_modules.append(default_mod)

    for default_act in ["USER_RATE_LIMIT", "IP_RATE_LIMIT", "500_INTERNAL_ERROR"]:
        if default_act not in available_actions:
            available_actions.append(default_act)

    return render_template(
        "admin/activity_log/index.html",
        module=module_name,
        logs=logs,
        selected_module=module_filter,
        selected_action=action_filter,
        search_query=search_query,
        available_modules=sorted(available_modules),
        available_actions=sorted(available_actions),
    )


@admin_bp.route("/activity-logs/<int:log_id>")
@login_required
def activity_log_detail(log_id):
    log = db.session.get(ActivityLog, log_id)
    if not log:
        return jsonify({"success": False, "message": "Log entry not found"}), 404
    return jsonify({
        "success": True,
        "log": log.to_dict()
    })

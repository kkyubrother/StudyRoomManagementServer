import datetime as dt

from flask import (
    Blueprint,
    request,
)

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from ..model import db, Log

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_logs():
    q = Log.query

    log_type = request.args.get("type", type=str)
    if isinstance(log_type, str):
        q = q.filter_by(log_type=log_type)

    user_id = request.args.get("user_id", type=int)
    if isinstance(user_id, int):
        q = q.filter_by(user_id=user_id)

    date = request.args.get("date", type=dt.date.fromisoformat)
    if isinstance(date, dt.date):
        before_dt = dt.datetime.fromordinal(date.toordinal()) - dt.timedelta(hours=9)
        after_dt = before_dt + dt.timedelta(days=1)
        q = q.filter(Log.created >= before_dt.isoformat(" "))
        q = q.filter(Log.created <= after_dt.isoformat(" "))

    need_all = request.args.get("date", type=str)
    if need_all == "all":
        return {
            "message": "ok",
            "logs": [log.publics_to_dict() for log in q.all()],
        }

    page = request.args.get("page", type=int, default=1)
    per_page = request.args.get("per_page", type=int, default=100)
    q = q.paginate(page=page, per_page=per_page)

    return {
        "message": "ok",
        "logs": [log.publics_to_dict() for log in q.items],
        "has_next": q.has_next,
        "has_prev": q.has_prev,
        "next_num": q.next_num,
        "prev_num": q.prev_num,
        "total": q.total,
    }


@bp.route("", methods=("POST",))
@check_user_from_cookie_authorization
def post_log():
    db.session.add(Log(
        chat_id=request.form.get("chat_id", type=int),
        tg_name=request.form.get("tg_name", type=str),
        user_id=request.form.get("user_id", type=int, default=1),
        username=request.form.get("username", type=str),
        birthday=request.form.get("birthday", type=str),
        age=request.form.get("age", type=int),
        gender=request.form.get("gender", type=int),
        grade=request.form.get("grade", default=0, type=int),
        department=request.form.get("department", type=str),
        sms=request.form.get("sms", type=int),
        log_type="post."+request.form.get("log_type", type=str),
        extra_data_str=request.form.get("extra_data_str", type=str)
    ))
    db.session.commit()
    return {"message": "ok"}

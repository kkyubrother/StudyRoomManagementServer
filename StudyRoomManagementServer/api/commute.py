import datetime as dt

from flask import (
    Blueprint,
    request
)
from sqlalchemy import extract, and_

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from StudyRoomManagementServer.util.qr_code import parse_qr_code
from ..model import User, db, Commute

bp = Blueprint("commute", __name__, url_prefix="/api/commute")


@bp.route("", methods=["GET"])
@check_user_from_cookie_authorization
# @need_authorization
def get_commute():
    date = dt.date.fromisoformat(request.args.get("date"))
    action = request.args.get("action")

    if action == "date":
        commutes = Commute.query.filter(
            extract("year", Commute.enter_time) == date.year,
            extract("month", Commute.enter_time) == date.month,
            extract("day", Commute.enter_time) == date.day,
        ).all()

    elif action == "month":
        commutes = Commute.query.filter(
            and_(
                extract("year", Commute.enter_time) == date.year,
                extract("month", Commute.enter_time) == date.month)
        ).all()

    elif action == "person":
        commutes = Commute.query.filter(
            extract("year", Commute.enter_time) == date.year,
            extract("month", Commute.enter_time) == date.month,
            extract("day", Commute.enter_time) == date.day,
            Commute.user_id == request.args.get("user_id", type=int)
        ).all()

    else:
        return {
            "message": "commute.bad_request.need_action"
        }, 400

    commutes = [
        {
            "commute_id": commute.id,
            "enter_time": commute.enter_time,
            "exit_time": commute.exit_time,
            "record": commute.record,
            "user": User.query.filter_by(id=commute.user_id).first().publics_to_dict()
        } for commute in commutes
    ]

    return {
        "data": commutes
    }


@bp.route("", methods=["POST"])
@check_user_from_cookie_authorization
def post_commute():
    _, user_id, _ = parse_qr_code(request.json.get("qr_code"))

    action = request.json.get("action")
    record = request.json.get("record")
    if action == "enter":
        created = (dt.datetime.utcnow() + dt.timedelta(hours=9))
        commute = Commute.query.filter_by(user_id=user_id, enter_time=created.date()).order_by(Commute.id.desc()).first()
        if commute and not commute.exit_time:
            return {
                "message": "commute.bad_request.not_exit"
            }, 400

        commute = Commute(user_id=user_id, enter_time=created, record=record)
        db.session.add(commute)
        db.session.commit()
        return {
            "message": "okay",
            "commute_id": commute.id
        }

    elif action == "exit":
        commute = Commute.query.filter_by(user_id=user_id).order_by(Commute.id.desc()).first()
        if not commute:
            return {
                "message": "commute.not_found"
            }, 404

        elif commute.exit_time:
            return {
                "message": "commute.not_found.not_enter"
            }, 404

        commute.exit_time = (dt.datetime.utcnow() + dt.timedelta(hours=9))
        db.session.add(commute)
        db.session.commit()
        return {
            "message": "okay",
            "commute_id": commute.id
        }

    return {
        "message": "commute.action.bad_request"
    }, 400

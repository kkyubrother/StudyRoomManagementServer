from random import choice
from string import digits

from flask import Blueprint, request, current_app

from StudyRoomManagementServer.cms_config import get_config as get_config_obj
from StudyRoomManagementServer.constants.status import Status
from StudyRoomManagementServer.controller.books import get_book_timetable_img, get_book_list, delete_book, \
    delete_book_by_admin, get_book
from StudyRoomManagementServer.controller.users import get_qr_img_by_user_obj, update_user
from StudyRoomManagementServer.error_handler import Conflict, NotFound, BadRequest, Forbidden
from StudyRoomManagementServer.model import User, db

bp = Blueprint("bot", __name__, url_prefix="/api/bot")


@bp.route("/users/by_chat_id/<int:chat_id>", methods=["GET"])
def get_user_by_chat_id(chat_id: int):
    user = User.query.filter_by(chat_id=chat_id).first()

    if user:
        return user.publics_to_dict()

    raise NotFound("No User", f"chat_id={chat_id}")


@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user_by_user_id(user_id: int):
    user = User.query.filter_by(id=user_id).first()

    if user:
        return user.publics_to_dict()

    raise NotFound("No User", f"user_id={user_id}")


@bp.route("/users", methods=["POST"])
def post_user_by_chat_id():
    chat_id = request.form.get("chat_id", type=str)
    tg_name = request.form.get("tg_name", type=str)

    user = User.query.filter_by(chat_id=chat_id).first()
    if user:
        if user.status == Status.CAN_RESTART:
            user.status = Status.NORMAL
            t = "restarted"

        else:
            raise Conflict("Already Registered", f"user_id={user.id}")

    else:
        user = User(chat_id=chat_id, tg_name=tg_name)
        t = "created"
        db.session.add(user)

    db.session.commit()

    return {"message": t, "user_id": user.id}


@bp.route("/users/by_chat_id/<int:chat_id>", methods=["PUT"])
def put_user_data_by_chat_id(chat_id: int):
    user = User.query.filter_by(chat_id=chat_id).first()

    return update_user(
        user,
        request.form.get("username", type=str),
        request.form.get("birthday", type=str),
        request.form.get("age", type=int),
        request.form.get("gender", type=int),
        request.form.get("num", type=str),
        request.form.get("department", type=str),
        request.form.get("grade", type=int)
    )


@bp.route("/users/by_chat_id/<int:chat_id>/sms", methods=["GET"])
def request_sms_code_by_chat_id(chat_id: int):
    user = User.query.filter_by(chat_id=chat_id).first()
    if not user:
        raise NotFound("No User", f"chat_id={chat_id}")

    if user.num is None:
        raise Forbidden("Need num", f"chat_id={chat_id}")

    new_code = generate_new_code()
    user.sms = 3_000_000 + new_code
    db.session.commit()

    from StudyRoomManagementServer.util.sms import send

    send(user.num, f"인증번호: {new_code:0>6}")

    if current_app.debug:
        return {
            "message": "send new code",
            "sms": user.sms % 1_000_000,
        }
    return {"message": "send new code"}


@bp.route("/users/by_chat_id/<int:chat_id>/sms", methods=["POST"])
def challenge_sms_code_by_chat_id(chat_id: int):
    user = User.query.filter_by(chat_id=chat_id).first()
    sms_code = request.form.get("sms", type=int)

    if sms_code is None:
        raise BadRequest("Need SMS", f"chat_id={chat_id}")

    if not user:
        raise NotFound("No User", f"chat_id={chat_id}")

    if user.sms < 0:
        raise Forbidden("exceed try", f"chat_id={chat_id}")

    elif user.sms % 1_000_000 == int(sms_code):
        user.sms = 1
        db.session.commit()
        return {"message": "valid"}

    else:
        user.sms = user.sms - 1_000_000
        db.session.commit()
        raise Forbidden("invalid", f"chat_id={chat_id}, sms_code={sms_code}")


@bp.route("/users/by_chat_id/<int:chat_id>/qr.png", methods=["GET"])
def get_qr_img_by_chat_id(chat_id: int):
    user = User.query.filter_by(chat_id=chat_id).first()

    if not user:
        raise NotFound("No User", f"chat_id={chat_id}")

    return get_qr_img_by_user_obj(user)


@bp.route("/books/timetable/<string:date_string>.png", methods=["GET"])
def get_timetable_img_by_chat_id(date_string: str):
    return get_book_timetable_img(date_string)


@bp.route("/books", methods=["GET"])
def get_books():
    return get_book_list()


@bp.route("/books/<string:date_str>", methods=["GET"])
def get_book_list_by_date_str(date_str: str):
    return get_book_list(date_str)


@bp.route("/books/<string:date_str>/<int:chat_id>", methods=["GET"])
def get_book_list_by_chat_id_and_date_str(date_str: str, chat_id: int):
    user_id = User.query.filter_by(chat_id=chat_id).first().id
    return get_book_list(date_str, user_id)


@bp.route("/users/by_chat_id/<int:chat_id>/books/<int:book_id>", methods=["DELETE"])
def del_book_by_chat_id(chat_id: int, book_id: int):
    user_id = User.query.filter_by(chat_id=chat_id).first().id
    reason = request.form.get("reason", type=str)
    return delete_book(user_id, book_id, reason)


@bp.route("/admin/<int:admin_id>/<int:chat_id>/books/<int:book_id>", methods=["DELETE"])
def del_book_by_admin(admin_id: int, chat_id: int, book_id: int):
    user_id = User.query.filter_by(chat_id=chat_id).first().id
    reason = request.form.get("reason", type=str)
    return delete_book_by_admin(user_id, book_id, admin_id, reason)


@bp.route("/config/book/open_close_time", methods=["GET"])
def get_config_book_room_open_close_time():
    config_obj = get_config_obj()
    return {
        "weekdays_open": getattr(config_obj, "book_room_weekdays_open").isoformat(),
        "weekdays_close": getattr(config_obj, "book_room_weekdays_close").isoformat(),
        "weekend_open": getattr(config_obj, "book_room_weekend_open").isoformat(),
        "weekend_close": getattr(config_obj, "book_room_weekend_close").isoformat(),
    }


@bp.route("/books/<int:book_id>", methods=["GET"])
def get_book_by_book_id(book_id: int):
    return get_book(book_id)


def generate_new_code() -> int:
    code = int("".join([choice(digits) for _ in range(6)]))
    if code == 1:
        return generate_new_code()
    return code

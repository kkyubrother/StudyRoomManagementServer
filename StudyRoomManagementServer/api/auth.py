import datetime as dt
from random import choice
from string import digits
from typing import Optional, Union, Dict, Tuple

import pytz
from flask import (
    Blueprint,
    request,
    make_response,
)

from StudyRoomManagementServer.access import chat_id_required, token_required
from StudyRoomManagementServer.auth_decorator import (
    need_authorization, create_bearer_token, Authorization, check_config_authorization,
    get_user_from_cookie_authorization, check_bot_authorization, check_user_from_cookie_authorization
)
from StudyRoomManagementServer.constants import Grade
from StudyRoomManagementServer.model import User, db
from StudyRoomManagementServer.util.qr_code import get_user_from_qr_code
from StudyRoomManagementServer.util.utils import create_log
from StudyRoomManagementServer.util.utils import get_grade_color, tz_conv
from .lib.user import (
    generate_new_sms_code
)
from .. import access
from ..util import sms

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
otp_storage = {}

OTP_LENGTH = 6
OTP_ERROR_BAD_REQUEST = -400
OTP_ERROR_FORBIDDEN = -403
OTP_ERROR_NOT_FOUND = -404
OTP_ERROR_TIMEOUT = -502
OTP_ERROR_CODE_RESPONSE = {
    OTP_ERROR_BAD_REQUEST: ({"status": "reject", "message": "올바른 OTP 요청이 아닙니다."}, 400),
    OTP_ERROR_FORBIDDEN: ({"status": "reject", "message": "OTP 요청을 먼저 해야 합니다."}, 403),
    OTP_ERROR_NOT_FOUND: ({"status": "reject", "message": "올바른 OTP 가 아닙니다."}, 403),
    OTP_ERROR_TIMEOUT: ({"status": "reject", "message": "OTP 이용 시간 초과(10분 이내로 인증하세요)"}, 403),
}
QR_LAST_UPDATE_DATETIME = dt.datetime(2021, 3, 31, 18, 0, 0, 0, pytz.timezone("Asia/Seoul"))


def get_new_otp() -> str:
    new_otp = "".join([choice(digits) for _ in range(OTP_LENGTH)])
    return new_otp


def _check_otp_code_in_storage(request_otp_code: str) -> int:
    """OTP 코드 확인"""
    if not request_otp_code:
        return OTP_ERROR_BAD_REQUEST

    elif len(request_otp_code) != OTP_LENGTH:
        return OTP_ERROR_BAD_REQUEST

    otp_set = set([v["otp_code"] for v in otp_storage.values()])

    if request_otp_code not in otp_set:
        return OTP_ERROR_NOT_FOUND

    user_id, created = [(k, v["created"],) for k, v in otp_storage.items() if v["otp_code"] == request_otp_code][0]
    del otp_storage[user_id]

    if (created + dt.timedelta(minutes=10)) <= dt.datetime.utcnow():
        return OTP_ERROR_TIMEOUT

    return user_id


def _check_otp_request() -> Union[Tuple[Dict[str, str], int], User]:
    data = request.get_json(silent=True)
    if not data:
        return {"status": "reject", "message": "잘못된 요청"}, 400

    result = _check_otp_code_in_storage(data.get("otp_code"))
    if result in OTP_ERROR_CODE_RESPONSE:
        return OTP_ERROR_CODE_RESPONSE[result]

    elif result <= 0:
        return {"status": "reject", "message": "OTP 요청 실패"}, 400

    user = User.query.filter_by(id=result).first()

    print("result", result)
    return user


def _check_user_can_send_message(user_id: int) -> Union[Tuple[Dict[str, str], int], User]:
    user: Optional[User] = User.query.filter_by(id=user_id).first()
    if not user:
        return {"status": "reject", "message": "사용자가 없습니다."}, 404

    elif not user.num:
        return {"status": "reject", "message": "전화번호가 없습니다."}, 403

    return user


@bp.route("/otp", methods=["GET"])
def get_otp():
    print("api.auth.get_otp")
    ip = request.remote_addr
    auth = request.authorization

    if ip != "127.0.0.1":
        return {"status": "reject", "message": "허가되지 않은 접근입니다."}, 401

    elif not auth:
        return {"status": "reject", "message": "인증요소가 없습니다."}, 401

    elif "username" not in auth or "password" not in auth:
        return {"status": "reject", "message": "인증요소가 불완전합니다."}, 401

    elif check_config_authorization(auth["username"], auth["password"]):
        user = User.query.filter_by(id=1).first()
        otp_storage[user.id] = {
            "otp_code": get_new_otp(),
            "created": dt.datetime.utcnow(),
        }
        return {
            "status": "confirm",
            "message": "OTP 발급 성공",
            "otp": otp_storage[user.id]["otp_code"],
        }

    return {
        "ip": ip,
        "header_auth": auth
    }


@bp.route("/otp", methods=["POST"])
def post_otp():
    print("api.auth.post_otp")
    is_valid_referrer = access.is_allow_referrer(request.referrer)
    if not is_valid_referrer:
        return {"status": "reject", "message": "올바르지 않은 주소의 접근입니다."}, 400

    user = _check_otp_request()
    if not isinstance(user, User):
        print("this")
        if not user:
            return {"message": "error"}, 403
        return user

    resp = make_response({
        "status": "confirm",
        "message": "인증 성공",
    })
    resp.set_cookie("Authorization", create_bearer_token(user), max_age=dt.timedelta(days=1), httponly=True)
    return resp


@bp.route("/bot", methods=["POST"])
@check_bot_authorization
def post_bot():
    print("api.auth.post_bot")
    referrer = request.referrer
    if referrer:
        return {"status": "reject", "message": "올바르지 않은 접근입니다."}, 400

    user = User.query.filter_by(id=1).first()
    resp = make_response({
        "status": "confirm",
        "message": "인증 성공",
    })
    resp.set_cookie("Authorization", create_bearer_token(user), max_age=dt.timedelta(minutes=1), httponly=True)
    return resp


@bp.route("/test", methods=["GET"])
def get_test():
    print("api.auth.test")
    return get_user_from_cookie_authorization().publics_to_dict()


@bp.route("/otp/request", methods=["POST"])
@need_authorization(allow=(Authorization.BOT, Authorization.CONFIG,))
def post_otp_request(user: User):
    print("api.auth.post_otp_request")
    if not user.valid:
        return {"status": "reject", "message": "인증되지 않았습니다."}, 403

    elif user.grade < 15:
        return {"status": "reject", "message": "권한이 없습니다."}, 403

    otp_storage[user.id] = {
        "otp_code": get_new_otp(),
        "created": dt.datetime.utcnow(),
    }
    return {
        "status": "confirm",
        "message": "OTP 발급 성공",
        "otp": otp_storage[user.id]["otp_code"],
    }


@bp.route("/otp/response", methods=["POST"])
def post_otp_response():
    print("api.auth.post_otp_response")

    user = _check_otp_request()
    if not isinstance(user, User):
        return user

    return {
        "status": "confirm",
        "message": "인증 성공",
        "token": create_bearer_token(user)
    }


@bp.route("/sms/request", methods=["POST"])
@need_authorization(allow=(Authorization.BOT, Authorization.CONFIG,))
# @check_user_from_cookie_authorization
def post_sms_request():
    print("api.auth.post_sms_request")
    data = request.get_json()
    if "user_id" not in data:
        return {"status": "reject", "message": "user_id 가 없습니다."}, 400

    user = _check_user_can_send_message(data["user_id"])
    if not isinstance(user, User):
        return user

    user.sms = generate_new_sms_code()
    db.session.commit()

    sms.send(user.num, f"인증번호: {user.sms:0>6}")

    return {"status": "confirm", "message": "인증번호를 전송하였습니다."}


@bp.route("/sms/response", methods=["POST"])
@need_authorization(allow=(Authorization.BOT, Authorization.CONFIG,))
def post_sms_response():
    print("api.auth.post_sms_response")
    data = request.get_json()
    if "user_id" not in data:
        return {"status": "reject", "message": "user_id 가 없습니다."}, 400

    user: Optional[User] = User.query.filter_by(id=data["user_id"]).first()
    if not user:
        return {"status": "reject", "message": "사용자가 없습니다."}, 404

    elif not user.num:
        return {"status": "reject", "message": "전화번호가 없습니다."}, 403

    elif "sms_code" not in data:
        return {"status": "reject", "message": "SMS 코드가 없습니다."}, 400

    elif user.sms < 0:
        return {"status": "reject", "message": "SMS 인증 기회를 초과하였습니다."}, 403

    elif user.sms % 1_000_000 != int(data["sms_code"]):
        user.sms = user.sms - 1_000_000
        db.session.commit()
        return {"status": "reject", "message": "SMS 인증 코드가 다릅니다."}, 403

    elif user.sms % 1_000_000 == int(data["sms_code"]):
        user.sms = 1
        db.session.commit()
        return {"status": "confirm", "message": "인증되었습니다."}

    else:
        user.sms = user.sms - 1_000_000
        db.session.commit()
        return {"status": "reject", "message": "잘못된 요청."}, 400


@bp.route("/qr/response", methods=["POST"])
@need_authorization(allow=(Authorization.QR,))
def post_qr_authorization(user: User):
    print("api.auth.post_qr_authorization")
    if not user.valid:
        db.session.add(create_log(user, None, log_type="auth", extra_data={"success": False}))
        db.session.commit()
        return {"status": "reject", "message": "인증되지 않았습니다."}, 403

    db.session.add(create_log(user, None, log_type="auth", extra_data={"success": True}))
    db.session.commit()
    return {"status": "confirm", "message": "인증되었습니다."}


@bp.route("/qr/enter", methods=["POST"])
@need_authorization(allow=(Authorization.QR,))
def post_qr_authorization_enter(user: User):
    print("api.auth.post_qr_authorization_enter")
    if not user.valid:
        db.session.add(create_log(user, None, log_type="auth", extra_data={"success": False}))
        db.session.commit()
        return {"status": "reject", "message": "인증되지 않았습니다."}, 403

    result = user.publics_to_dict()
    result["name"] = user.username
    result["gradeClass"] = "text-" + get_grade_color(user.grade)

    db.session.add(create_log(user, None, log_type="auth", extra_data={"success": True}))
    db.session.commit()
    result["status"] = "confirm"
    result["message"] = "인증되었습니다."
    return result


@bp.route("/otp", methods=["GET"])
@token_required
@chat_id_required
def get_otp_code(chat_id: int):
    print("api.auth.get_otp_code")
    user = User.query.filter_by(chat_id=chat_id).first()
    if user.grade >= Grade.manager:
        return {"code": get_new_otp()}
    else:
        return {"code": None}, 401


@bp.route("/qr", methods=["POST"])
# @login_required
def auth_qr():
    print("api.auth.auth_qr")
    if request.is_json:
        qr_code = request.json.get("qr_code")
    else:
        qr_code = request.form.get("qr_code", type=str)

    if not qr_code:
        return {
            "message_code": 40000,
            "message": "올바르지 않은 요청입니다",
            "msg": "올바르지 않은 요청입니다",
        }, 400

    try:
        user, qr = get_user_from_qr_code(qr_code=qr_code)
    except Exception as e:
        print(e)
        return {
            "message_code": 40000,
            "message": "잘못된 QR 입니다.",
            "msg": "잘못된 QR 입니다.",
        }, 400

    result = user.publics_to_dict()
    result["name"] = user.username
    result["gradeClass"] = "text-" + get_grade_color(user.grade)

    if tz_conv(qr.created) < QR_LAST_UPDATE_DATETIME:
        if user.grade >= Grade["vip"]:
            result["message"] = "VIP 회원권 재발급이 필요합니다!"

    db.session.add(
        create_log(user, None, log_type="auth", extra_data={"success": True})
    )
    db.session.commit()
    return result


@bp.route("/sms/message", methods=["POST"])
# @need_authorization(allow=(Authorization.BOT, Authorization.CONFIG, Authorization.WEB,))
@check_user_from_cookie_authorization
def post_sms_text_request():
    print("api.auth.post_sms_text_request")
    data = request.get_json()
    if "user_id" not in data:
        return {"status": "reject", "message": "user_id 가 없습니다."}, 400

    elif "text" not in data or not data["text"]:
        return {"status": "reject", "message": "text 가 없습니다."}, 400

    text: str = data['text']

    if "from" in data:
        from_tel = data["from"]
    else:
        from_tel = None

    user = _check_user_can_send_message(data["user_id"])
    if not isinstance(user, User):
        return user

    text = text.replace("%이름%", user.username)

    db.session.commit()

    if from_tel:
        result = sms.send_v2(from_tel, user.num, text)
    else:
        result = sms.send(user.num, text)

    return {"status": "confirm", "message": "전송하였습니다.", "result": result}


@bp.route(
    "/otp/debug",
    methods=[
        "GET",
    ],
)
def post_otp_request_debug():
    print("api.auth.post_otp_request_debug")
    otp_storage[1] = {
        "otp_code": get_new_otp(),
        "created": dt.datetime.utcnow(),
    }
    return {
        "status": "confirm",
        "message": "OTP 발급 성공",
        "otp": otp_storage[1]["otp_code"],
    }

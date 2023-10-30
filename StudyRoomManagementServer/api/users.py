from secrets import token_urlsafe
from typing import Tuple

from flask import (
    Blueprint,
    request,
    Response
)
from werkzeug.wsgi import FileWrapper

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from StudyRoomManagementServer.util.qr_code import parse_qr_code
from StudyRoomManagementServer.util.qr_img import create_qr_image
from .lib import user as checker
from ..model import User, db, QR


def generate_new_qr_key_v1() -> Tuple[str, str]:
    skey = token_urlsafe(64)
    ukey = skey
    return skey, ukey,


bp = Blueprint("users", __name__, url_prefix="/api/users")


BOOK_STATUS_OK = 200
BOOK_STATUS_PAYED = 240
BOOK_STATUS_FIELD = 250


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_users():
    return {
        "message": "ok",
        "users": [u.publics_to_dict() for u in User.query.all()]
    }


@bp.route("/<int:user_id>", methods=("GET",))
@check_user_from_cookie_authorization
def get_user_by_id(user_id: int):

    return {
        "message": "ok",
        "user": User.query.filter_by(id=user_id).first().publics_to_dict()
    }


@bp.route("/chat_id/<int:chat_id>", methods=("GET",))
@check_user_from_cookie_authorization
def get_user_by_chat_id(chat_id: int):

    return {
        "message": "ok",
        "user": User.query.filter_by(chat_id=chat_id).first().publics_to_dict()
    }


@bp.route("/<int:user_id>/qr.png", methods=("GET",))
@check_user_from_cookie_authorization
def user_qr_image(user_id: int):
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"message": "No user"}, 404

    elif not user.valid:
        return {"message": "Need SMS auth"}, 403

    if not user.qr:
        skey, ukey = generate_new_qr_key_v1()
        qr = QR(user_id=user.id, skey=skey, revision=1)
        db.session.add(qr)
        db.session.commit()
    else:
        qr = user.qr[-1]
    qr_img = create_qr_image(user, qr)

    return Response(FileWrapper(qr_img), mimetype="image/png", direct_passthrough=True)


@bp.route("/<int:user_id>/qr.txt", methods=("GET",))
@check_user_from_cookie_authorization
def user_qr_txt(user_id: int):
    user = User.query.filter_by(id=user_id).first()
    qr = user.qr[-1]
    return {"message": f"{qr.revision}0{user.id:04x}{qr.skey}"}


@bp.route("/qr", methods=("POST",))
def post_qr():
    qr = request.values.get("qr", request.json.get("qr"), type=str)
    try:
        revision, user_id, ukey = parse_qr_code(qr)

        user = User.query.filter_by(id=user_id).first()
        if user:
            user = user.publics_to_dict()
            del user["chat_id"]
            return {
                "message": "ok",
                "user": user
            }
    except ValueError as ve:
        return {"message": f"{ve}"}, 400

    return {
               "message": "존재하지 않습니다.",
               "status_code": 404
           }, 404


@bp.route("/<int:user_id>", methods=("PUT",))
@check_user_from_cookie_authorization
def put_user(user_id: int):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return {"message": "No User"}, 404

    data = request.get_json()

    if "username" in data:
        if not checker.is_username(data['username']):
            return {"message": "회원 이름이 올바르지 않습니다."}, 400
        user.username = checker.get_username(data['username'])

    if "birthday" in data:
        if not checker.is_birthday(data['birthday']):
            return {"message": "회원 생일이 올바르지 않습니다."}, 400
        user.birthday = data['birthday']

    if "gender" in data:
        if not checker.is_gender(data['gender']):
            return {"message": "회원 성별이 올바르지 않습니다."}, 400
        user.gender = checker.get_gender(int(data['gender']))

    if "age" in data:
        y, _, _ = checker.get_birthday(data['birthday']) if "birthday" in data else checker.get_birthday(user.birthday)
        try:
            calculated_age = checker.get_age(y)
        except ValueError:
            return {"message": "회원 나이가 올바르지 않습니다."}, 400

        age = int(data['age'])
        if age == calculated_age:
            user.age = age
        else:
            return {"message": "회원 나이가 올바르지 않습니다."}, 400

    elif "birthday" in data:
        y, _, _ = checker.get_birthday(data['birthday'])
        try:
            user.age = checker.get_age(y)
        except ValueError:
            return {"message": "회원 나이가 올바르지 않습니다."}, 400

    if "tel" in data:
        if not checker.is_tel(data['tel']):
            return {"message": "회원 전화번호가 올바르지 않습니다."}, 400
        user.num = checker.get_tel(data['tel'])
        user.sms = None

    if "grade" in data:
        if not checker.is_grade(int(data['grade'])):
            return {"message": "회원 등급이 올바르지 않습니다."}, 400
        user.grade = checker.get_grade(int(data['grade']))

    if "department" in data:
        user.department = checker.get_department(data['department'])

    db.session.commit()

    return {"user": user.publics_to_dict()}

import datetime as dt
import functools
from enum import Enum, auto
from typing import Optional, Tuple, Union

import jwt
from flask import request, current_app

from StudyRoomManagementServer.util.qr_code import parse_qr_code
from .model import User


class StrEnum(str, Enum):
    def _generate_next_value_(self, start, count, last_values):
        return self

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class Authorization(StrEnum):
    QR = auto()
    QRV1 = auto()
    QRV2 = auto()
    BOT = auto()
    WEB = auto()
    CONFIG = auto()


def need_authorization(allow: Union[Tuple[str], Tuple[Authorization, Authorization]] = tuple(Authorization)):
    allow = set(allow)

    def wrapper(func):
        @functools.wraps(func)
        def inner_wrapper(*args, **kwargs):
            if "Authorization" not in request.headers:
                print(f"UnAuthorization: {'No Header'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

            authorization = request.headers.get("Authorization", default="None None", type=str)
            if " " not in authorization:
                print(f"UnAuthorization: {'No Space'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

            auth_type, auth_code = authorization.split(' ', 1)
            if (Authorization.QR in allow or Authorization.QRV1 in allow) and auth_type == "QR":
                user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
                if not user:
                    print(f"UnAuthorization: {auth_type} {'No User'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                return func(user, *args, **kwargs)

            elif (Authorization.QR in allow or Authorization.QRV2 in allow) and auth_type == "QRV2":
                user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
                if not user:
                    print(f"UnAuthorization: {auth_type} {'No User'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                return func(user, *args, **kwargs)

            elif Authorization.BOT in allow and auth_type == "BOT":
                if current_app.config["AUTH"]["CafeManagementBot"] != auth_code:
                    print(f"UnAuthorization: {auth_type} {auth_code} {'No AuthCode'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

                if "Chat-Id" in request.headers:
                    chat_id = request.headers.get("Chat-Id", type=int, default=-1)
                elif "chat_id" in request.values:
                    chat_id = request.values.get("chat_id", type=int, default=-1)
                else:
                    print(f"UnAuthorization: {auth_type} {auth_code} {'No Chat-Id'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

                user = User.query.filter_by(chat_id=chat_id).first()
                if not user:
                    print(f"UnAuthorization: {auth_type} {auth_code} {'No User'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                return func(user, *args, **kwargs)

            elif Authorization.WEB in allow and auth_type == "Bearer":
                decoded = jwt.decode(auth_code, current_app.config.get("JWT_SECRET_KEY"), algorithms="HS256")
                user = User.query.filter_by(id=decoded["user_id"]).first()
                if not user:
                    print(f"UnAuthorization: {auth_type} {auth_code} {'No User'}")
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                return func(user, *args, **kwargs)

            elif Authorization.CONFIG in allow and auth_type in current_app.config.get("AUTH", {}):
                if current_app.config.get("AUTH", {}).get(auth_type) == auth_code:
                    if "Chat-Id" in request.headers:
                        chat_id = request.headers.get("Chat-Id", type=int, default=-1)
                        user = User.query.filter_by(chat_id=chat_id).first()
                        if not user:
                            print(f"UnAuthorization: {auth_type} {auth_code} {'No User'}")
                            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                        return func(user, *args, **kwargs)
                    elif "User-Id" in request.headers:
                        user_id = request.headers.get("User-Id", type=int, default=-1)
                        user = User.query.filter_by(id=user_id).first()
                        if not user:
                            print(f"UnAuthorization: {auth_type} {auth_code} {'No User'}")
                            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                        return func(user, *args, **kwargs)
                    else:
                        return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                else:
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            else:
                print(f"UnAuthorization: {'No Data'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

        return inner_wrapper
    return wrapper


def create_bearer_token(user: User, expire: Optional[dt.datetime] = None) -> str:
    """기본 1일 딜레이"""
    payload = {
        "user_id": user.id,
        "username": user.username
    }
    if expire:
        payload['exp'] = expire
    else:
        payload['exp'] = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(days=1)
    return jwt.encode(
        payload,
        current_app.config.get("JWT_SECRET_KEY"),
        algorithm="HS256"
    )


def check_bearer_token(token: str) -> Optional[User]:
    decoded = jwt.decode(token, current_app.config.get("JWT_SECRET_KEY"), algorithms="HS256")
    user = User.query.filter_by(id=decoded["user_id"]).first()
    if not user:
        return None
    return user


def get_user_from_cookie_authorization() -> User:
    auth = request.cookies.get("Authorization")
    if not auth:
        raise Exception({"status": "reject", "message": "인증 정보가 없습니다."})

    user = check_bearer_token(auth)
    if not user:
        raise Exception({"status": "reject", "message": "인증 정보가 없습니다."})

    return user


def check_config_authorization(username: str, password: str) -> bool:
    return current_app.config["AUTH"].get(username) == password


def check_user_from_cookie_authorization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user = get_user_from_cookie_authorization()
            print(user)
        except Exception as e:
            print(e)
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
        return func(*args, **kwargs)
    return wrapper


def check_bot_authorization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if "Authorization" not in request.headers:
                print(f"UnAuthorization: {'No Header'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

            authorization = request.headers.get("Authorization", default="None None", type=str)
            if " " not in authorization:
                print(f"UnAuthorization: {'No Space'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

            auth_type, auth_code = authorization.split(' ', 1)

            if current_app.config["AUTH"]["CafeManagementBot"] != auth_code:
                print(f"UnAuthorization: {auth_type} {auth_code} {'No AuthCode'}")
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
        except Exception as e:
            print(e)
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
        return func(*args, **kwargs)
    return wrapper


def get_user_from_bot_authorization() -> User:
    if "Authorization" not in request.headers:
        print(f"UnAuthorization: {'No Header'}")
        raise Exception("인증 정보가 없습니다.")

    authorization = request.headers.get("Authorization", default="None None", type=str)
    if " " not in authorization:
        print(f"UnAuthorization: {'No Space'}")
        raise Exception("인증 정보가 없습니다.")

    auth_type, auth_code = authorization.split(' ', 1)

    if current_app.config["AUTH"]["CafeManagementBot"] != auth_code:
        print(f"UnAuthorization: {auth_type} {auth_code} {'No AuthCode'}")
        raise Exception("인증 정보가 없습니다.")

    if "Chat-Id" in request.headers:
        chat_id = request.headers.get("Chat-Id", type=int, default=-1)
    elif "chat_id" in request.values:
        chat_id = request.values.get("chat_id", type=int, default=-1)
    else:
        print(f"UnAuthorization: {auth_type} {auth_code} {'No Chat-Id'}")
        raise Exception("인증 정보가 없습니다.")

    user = User.query.filter_by(chat_id=chat_id).first()
    if not user:
        print(f"UnAuthorization: {auth_type} {auth_code} {'No User'}")
        raise Exception("인증 정보가 없습니다.")
    return user

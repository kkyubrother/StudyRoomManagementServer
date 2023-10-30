import datetime as dt
import functools
from typing import Tuple, Optional

import jwt
from flask import request, current_app

from StudyRoomManagementServer.util.qr_code import parse_qr_code
from ...cms_config import get_config
from ...model import RoomBook, User


def raise_for_duplication(
    room_id: int, date: dt.date, start_time: dt.time, end_time: dt.time
) -> None:
    start_time_second = start_time.hour * 60 + start_time.minute
    end_time_second = end_time.hour * 60 + end_time.minute

    for room_book in RoomBook.query.filter_by(reason=None).filter_by(book_date=date, room_id=room_id).all():
        rb_s = room_book.start_time_second
        rb_e = room_book.end_time_second
        s = start_time_second
        e = end_time_second
        t = f"{rb_s} - {rb_e} || {s} - {e}"
        if rb_e > s and rb_s < e:
            if rb_s < s and rb_e > e:
                raise ValueError(s, e, "이전 예약이 신규 보다 큼", t)
            elif rb_s >= s and rb_e <= e:
                raise ValueError(s, e, "신규 예약이 이전 보다 큼", t)
            elif rb_s < s:
                raise ValueError(rb_s, e, "일부 겹침: 시작시간 뒤미룸", t)
            elif rb_e > e:
                raise ValueError(s, rb_e, "일부 겹침: 종료시간 앞당김", t)
            else:
                raise ValueError(s, e, "상정 외 사태", t)


def get_date() -> dt.date:
    date = request.values.get("date", request.json.get("date"), type=dt.date.fromisoformat)
    if date is None:
        raise ValueError("날짜가 없거나 iso format 이 아닙니다.")

    if isinstance(date, str):
        try:
            date = dt.date.fromisoformat(date)
        except ValueError:
            raise ValueError("날짜가 없거나 iso format 이 아닙니다.")

    return date


def _raise_for_time(time: Optional[dt.time]) -> dt.time:
    if time is None:
        raise ValueError("시간이 없거나 iso format 이 아닙니다.")

    if isinstance(time, str):
        try:
            time = dt.time.fromisoformat(time)
        except ValueError:
            raise ValueError("시간이 없거나 iso format 이 아닙니다.")

    # if not time.tzinfo:
        # time = time - dt.timedelta(hours=9)
        # print(time.isoformat())
        # print(dt.time.fromisoformat(time.isoformat() + "+00:00").isoformat())
        # print(dt.time.fromisoformat(time.isoformat() + "+09:00").isoformat())
        # time = dt.time.fromisoformat(time.isoformat() + "+00:00")

    return time


def get_date_and_time() -> Tuple[dt.date, dt.time, dt.time]:
    date = get_date()

    start_time = request.values.get("start_time", request.json.get("start_time"), type=dt.time.fromisoformat)
    start_time = _raise_for_time(start_time)

    end_time = request.values.get("end_time", request.json.get("end_time"), type=dt.time.fromisoformat)
    end_time = _raise_for_time(end_time)

    return date, start_time, end_time,


def get_chat_id() -> int:
    chat_id = request.values.get("chat_id", request.json.get("chat_id"), type=int)
    if chat_id is None:
        raise ValueError("chat_id가 없습니다.")

    if isinstance(chat_id, str):
        try:
            chat_id = int(chat_id)
        except ValueError:
            raise ValueError("chat_id가 없습니다.")

    return chat_id


def get_user_id() -> int:
    user_id = request.values.get("user_id", request.json.get("user_id"), type=int)
    if user_id is None:
        raise ValueError("user_id가 없습니다.")

    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            raise ValueError("user_id가 없습니다.")

    return user_id


def get_client_name() -> str:
    client_name = request.values.get("client_name", type=str)
    if request.json and not client_name:
        client_name = request.json.get("client_name")
    if not client_name:
        client_name = request.headers.get("User-Agent")

    if client_name is None:
        return "no_name"
    return client_name


def raise_can_book_date(now: dt.datetime, book_date: dt.date):
    if book_date < now.date() or (now.date() == book_date and now.time() > get_config().book_room_limit_time):
        limit = get_config().book_room_limit_time
        raise ValueError(f"예약은 당일 `AM {limit.hour:0>2}:{limit.minute:0>2}` 까지 가능합니다.")


def need_qr_authorization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "Authorization" not in request.headers:
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

        auth_type, auth_code = request.headers.get("Authorization", default="None None", type=str).split(' ', 1)
        if auth_type == "QR":
            user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        elif auth_type == "QRV2":
            user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
    return wrapper


def need_authorization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "Authorization" not in request.headers:
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

        authorization = request.headers.get("Authorization", default="None None", type=str)
        if " " not in authorization:
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

        auth_type, auth_code = authorization.split(' ', 1)
        if auth_type == "QR":
            user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        elif auth_type == "QRV2":
            user = User.query.filter_by(id=parse_qr_code(auth_code)[1]).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        elif auth_type == "BOT":
            if "Chat-Id" not in request.headers:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            chat_id = request.headers.get("Chat-Id", type=int, default=-1)
            user = User.query.filter_by(chat_id=chat_id).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        elif auth_type == "Bearer":
            print(request.headers.get("Authorization"))
            decoded = jwt.decode(auth_code, current_app.config.get("JWT_SECRET_KEY"), algorithms="HS256")
            user = User.query.filter_by(id=decoded["user_id"]).first()
            if not user:
                return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
            return func(user, *args, **kwargs)

        elif auth_type in current_app.config.get("AUTH", {}):
            if current_app.config.get("AUTH", {}).get(auth_type) == auth_code:
                if "Chat-Id" in request.headers:
                    chat_id = request.headers.get("Chat-Id", type=int, default=-1)
                    user = User.query.filter_by(chat_id=chat_id).first()
                    if not user:
                        return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                    return func(user, *args, **kwargs)
                elif "User-Id" in request.headers:
                    user_id = request.headers.get("User-Id", type=int, default=-1)
                    user = User.query.filter_by(id=user_id).first()
                    if not user:
                        return {"status": "reject", "message": "인증 정보가 없습니다."}, 401
                    return func(user, *args, **kwargs)
                else:
                    return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

        else:
            return {"status": "reject", "message": "인증 정보가 없습니다."}, 401

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

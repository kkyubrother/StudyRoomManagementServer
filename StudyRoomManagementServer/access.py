import datetime as dt
import functools
from typing import TypedDict, Optional, NoReturn

from flask import request, current_app

from .error_handler import BadRequest


class DT(TypedDict):
    date: dt.date
    start_time: Optional[dt.time]
    end_time: Optional[dt.time]


def raise_for_token() -> NoReturn:
    ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
    token = request.headers.get("TOKEN")
    referer = request.headers.get("Referer")
    ua = request.user_agent.string

    if token is None:
        current_app.logger.info(f"Access denied {ip}: TOKEN is None, ua={ua}")
        raise BadRequest("Need TOKEN")

    if referer and (current_app.debug and not referer.startswith("http://localhost")):
        print(f"Access denied {ip}: Referer is not None, ua={ua}, referer={referer}")
        current_app.logger.info(f"Access denied {ip}: Referer is not None, ua={ua}")
        raise BadRequest("Need TOKEN")

    client_ua = ua.split("/", 1)[0]
    if client_ua in current_app.config["AUTH"]:
        if token != current_app.config["AUTH"][client_ua]:
            current_app.logger.info(
                f"Access denied {ip}: TOKEN was not match, token={token}, ua={ua}"
            )
            raise BadRequest("invalid TOKEN")

    else:
        current_app.logger.info(
            f"Access denied {ip}: Not allowed ua, token={token}, ua={ua}"
        )
        raise BadRequest("invalid TOKEN USER")

    current_app.logger.info(f"Access {ip}: ua={ua}")


def raise_for_chat_id() -> int:
    chat_id = request.args.get("chat_id", None, type=int)
    if not chat_id:
        chat_id = request.form.get("chat_id", None, type=int)

    if not chat_id or chat_id <= 0:
        current_app.logger.info(f"in book: No chat_id")
        raise ValueError()

    return chat_id


def raise_for_book_dt(only_date: bool = False) -> DT:
    date = request.args.get("date", type=dt.date.fromisoformat)
    if not date:
        date = request.form.get("date", type=dt.date.fromisoformat)
        if not date:
            raise ValueError()

    if only_date:
        start_time = None
        end_time = None

    else:
        start_time = request.args.get("start_time", type=dt.time.fromisoformat)
        if not start_time:
            start_time = request.form.get("start_time", type=dt.time.fromisoformat)
            if not start_time:
                raise ValueError()

        end_time = request.args.get("end_time", type=dt.time.fromisoformat)
        if not end_time:
            end_time = request.form.get("end_time", type=dt.time.fromisoformat)
            if not end_time:
                raise ValueError()

    return {
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
    }


def token_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        raise_for_token()
        return func(*args, **kwargs)

    return wrapper


def chat_id_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            chat_id = raise_for_chat_id()
            return func(chat_id, *args, **kwargs)
        except ValueError:
            return {"message": "Need register"}, 401

    return wrapper


# After 2.10.6
def is_allow_referrer(referrer: str) -> bool:
    """Referrer 확인
    Demo 도메인 변경 오류가 많이 생겨서 비활성화합니다.
    """
    return True

    # if not referrer:
    #     return False
    #
    # is_referrer_start_localhost3000 = str(referrer).startswith("http://localhost:3000")
    # is_referrer_start_localhost5000 = str(referrer).startswith("http://localhost:5000")
    # is_referrer_start_127_0_0_15000 = str(referrer).startswith("http://127.0.0.1:5000")
    # is_referrer_start_192_168_0_57 = str(referrer).startswith("http://192.168.0.57:8000")
    # is_referrer_start_cafe_kkyubr = str(referrer).startswith("https://cafe.kkyubr.com")
    # is_referrer_start_store_kesuna = str(referrer).startswith("https://store.kesuna.com")
    # is_referrer_start_store_kkyubr = str(referrer).startswith("https://store2.kkyubr.com")
    # return (is_referrer_start_localhost3000 or is_referrer_start_localhost5000 or
    #         is_referrer_start_127_0_0_15000 or is_referrer_start_cafe_kkyubr or
    #         is_referrer_start_192_168_0_57 or is_referrer_start_store_kesuna or
    #         is_referrer_start_store_kkyubr)

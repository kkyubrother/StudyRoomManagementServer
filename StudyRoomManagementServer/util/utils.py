from typing import List, Optional

from StudyRoomManagementServer import constants


def get_grade_color(grade: int) -> str:
    if isinstance(grade, str):
        grade = constants.Grade[grade]

    if grade == constants.Grade["normal"]:
        return "transport"
    elif grade == constants.Grade["admin"]:
        return "primary"
    elif grade == constants.Grade["manager"]:
        return "success"
    elif grade == constants.Grade["warning"]:
        return "warning"
    elif grade == constants.Grade["danger"]:
        return "danger"
    elif grade == constants.Grade["vip"]:
        return "info"
    else:
        return "muted"


import datetime as dt
import pytz


def tz_conv(
    original: dt.datetime,
    current_tz_str: str = "UTC",
    target_tz_str: str = "Asia/Seoul",
) -> dt.datetime:
    current_tz = pytz.timezone(current_tz_str)
    target_tz = pytz.timezone(target_tz_str)
    target_dt = current_tz.localize(original).astimezone(target_tz)
    return target_tz.normalize(target_dt)


from StudyRoomManagementServer.model import Log, User


def distinct_log(logs: List[Log]) -> list:
    checked_id = set()

    for log in logs:
        if log.user_id not in checked_id:
            checked_id.add(log.user_id)
            yield log


import json


def create_log(
    user: User, tg_name=None, log_type: str = None, extra_data: dict = None
) -> "Log":
    """로그 생성 도우미"""
    return Log(
        chat_id=user.chat_id,
        tg_name=tg_name,
        user_id=user.id,
        username=user.username,
        birthday=user.birthday,
        age=user.age,
        gender=user.gender,
        encrypted_num=user.encrypted_num,
        grade=user.grade,
        department=user.department,
        sms=user.sms,
        log_type=log_type,
        extra_data_str=json.dumps(extra_data),
    )


def create_web_log(
        log_type: str, extra_data: dict, user_id: Optional[int] = None
) -> Log:
    """웹용 로그 생성 도우미"""
    if user_id is None:
        user_id = -1
    if not log_type.startswith("web"):
        log_type = "web." + log_type
    return Log(
        user_id=user_id,
        log_type=log_type,
        extra_data_str=json.dumps(extra_data, ensure_ascii=False),
    )


import hashlib
import hmac
from flask import current_app


def verify(request_data):
    request_data = request_data.copy()
    request_data.pop("hash", None)
    request_data_alphabetical_order = sorted(request_data.items(), key=lambda x: x[0])
    data_check_string = []

    for data_pair in request_data_alphabetical_order:
        key, value = data_pair[0], data_pair[1]
        data_check_string.append(f"{key}={value}")

    data_check_string = "\n".join(data_check_string)
    secret_key = hashlib.sha256(
        current_app.config.get("BOT_TOKEN", "").encode()
    ).digest()
    return hmac.new(
        secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
    ).hexdigest()

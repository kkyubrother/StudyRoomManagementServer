import datetime as dt
import re
from random import choice
from secrets import token_urlsafe
from string import digits
from typing import Tuple, Optional

from flask import (
    send_file,
)

from StudyRoomManagementServer.error_handler import BadRequest, Forbidden
from StudyRoomManagementServer.model import User
from StudyRoomManagementServer.model import db, QR
from StudyRoomManagementServer.util.qr_img import create_qr_image

AGE_MINIMUM = 18
AGE_MAXIMUM = 100


PATTERN_NOT_NAME = re.compile(r"[^가-힣]")
PATTERN_AGE = re.compile(r"\d+")
PATTERN_NUM = re.compile(
    r"^(?P<num0>010)?[\s\-\.]?(?P<num1>\d{4})[\s\-\.]?(?P<num2>\d{4})$"
)

PATTERN_BIRTHDAY = re.compile(r"(?P<y>\d{2,4})(?P<m>\d{2})(?P<d>\d{2})")
PATTERN_SOCIAL_SECURITY_NUMBER = re.compile(r"(?P<birthday>\d{6})(?P<gender>\d)")


def raise_for_username(username: str) -> str:
    username = username.strip()

    if PATTERN_NOT_NAME.findall(username):
        raise BadRequest("Wrong username", f"birthday={username}")

    if len(username) < 2:
        raise BadRequest("Wrong username", f"birthday={username}")

    return username


def raise_for_birthday(birthday: str) -> Tuple[str, int]:
    res = PATTERN_BIRTHDAY.match(birthday)
    if not res:
        raise BadRequest("Wrong birthday", f"birthday={birthday}")

    r = res.groupdict()

    y = int(r["y"])
    m = int(r["m"])
    d = int(r["d"])

    if not (12 >= m >= 1 and 31 >= d >= 1):
        raise BadRequest("Wrong birthday", f"birthday={birthday}")

    if y < 40:
        y += 2000
    else:
        y += 1900

    age = dt.datetime.now().year - y + 1

    return birthday, raise_for_age(age)


def raise_for_age(age: int) -> int:
    if AGE_MAXIMUM > age > AGE_MINIMUM:
        return age
    raise BadRequest("Wrong age", f"age={age}")


def raise_for_num(num: str) -> str:
    try:
        num_res = PATTERN_NUM.match(num)
        if not num_res:
            raise BadRequest("Wrong num", f"num={num}")

        num_dict = num_res.groupdict()
        num0 = num_dict["num0"] if num_dict["num0"] else "010"
        return num0 + "-" + num_dict["num1"] + "-" + num_dict["num2"]

    except Exception as e:
        raise BadRequest("Wrong num", f"num={num}, e={e}")


def raise_for_gender(gender: int) -> int:
    if gender not in {1, 2, 3, 4}:
        raise BadRequest("Wrong gender", f"gender={gender}")
    return gender


def raise_for_department(department: str) -> str:
    return department


def raise_for_grade(grade: int) -> int:
    return grade


def generate_new_code() -> int:
    code = int("".join([choice(digits) for _ in range(6)]))
    if code == 1:
        return generate_new_code()
    return code


def get_qr_img_by_user_obj(user: User):
    if user.sms != 1:
        raise Forbidden("Need SMS auth", f"chat_id={user.chat_id}")

    skey = token_urlsafe(64)
    qr = QR(
        user_id=user.id,
        skey=skey,
        revision=1,
    )
    db.session.add(qr)
    db.session.commit()

    qr_img = create_qr_image(user, qr)
    return send_file(qr_img, mimetype="image/png")


def update_user(
        user: User,
        username: Optional[str] = None,
        birthday: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[int] = None,
        num: Optional[str] = None,
        department: Optional[str] = None,
        grade: Optional[int] = None,
):

    if username:
        user.username = raise_for_username(username)

    if birthday:
        user.birthday, user.age = raise_for_birthday(birthday)

    if age:
        user.age = raise_for_age(age)

    if gender:
        user.gender = raise_for_gender(gender)

    if num:
        user.num = raise_for_num(num)

    if department:
        user.department = raise_for_department(department)

    if grade:
        user.grade = raise_for_grade(grade)

    db.session.commit()

    return {"message": "ok"}

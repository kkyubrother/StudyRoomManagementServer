import datetime as dt
import re
from random import choice
from string import digits
from typing import Tuple, Dict, Union

AGE_MINIMUM = 18
AGE_MAXIMUM = 100

PATTERN_NOT_NAME = re.compile(r"[^가-힣]")
PATTERN_AGE = re.compile(r"\d+")
PATTERN_TEL = re.compile(
    r"^(?P<tel0>010)?[\s\-\.]?(?P<tel1>\d{4})[\s\-\.]?(?P<tel2>\d{4})$"
)

PATTERN_BIRTHDAY = re.compile(r"(?P<y>\d{2,4})(?P<m>\d{2})(?P<d>\d{2})")
PATTERN_SOCIAL_SECURITY_NUMBER = re.compile(r"(?P<birthday>\d{6})(?P<gender>\d)")


DEPARTMENT_DATA = [
    {
        "variation": ["기타"],
        "name": "기타",
        "key": "기타",
    },
]


def is_username(username: str) -> bool:
    username = username.strip()
    return not (PATTERN_NOT_NAME.findall(username) or len(username) < 2)


def get_username(username: str) -> str:
    if is_username(username):
        return username.strip()
    raise ValueError("Not Username")


def is_birthday(birthday: str) -> bool:
    res = PATTERN_BIRTHDAY.match(birthday)

    r = res.groupdict()

    y = int(r["y"])
    m = int(r["m"])
    d = int(r["d"])

    return 12 >= m >= 1 and 31 >= d >= 1


def get_birthday(birthday: str) -> Tuple[int, int, int]:
    if is_birthday(birthday):
        res = PATTERN_BIRTHDAY.match(birthday)

        r = res.groupdict()

        y = int(r["y"])
        m = int(r["m"])
        d = int(r["d"])

        if y < 40:
            y += 2000
        else:
            y += 1900

        return y, m, d,
    raise ValueError("Not birthday")


def is_age(age: int) -> bool:
    return AGE_MAXIMUM > age > AGE_MINIMUM


def get_age(year: int) -> int:
    age = dt.datetime.now().year - year + 1
    if is_age(age):
        return age
    raise ValueError("Not year")


def is_tel(tel: str) -> bool:
    tel_res = PATTERN_TEL.match(tel)
    return bool(tel_res)


def get_tel(tel: str) -> str:
    if is_tel(tel):
        tel_res = PATTERN_TEL.match(tel)

        tel_dict = tel_res.groupdict()
        tel0 = tel_dict["tel0"] if tel_dict["tel0"] else "010"
        return tel0 + "-" + tel_dict["tel1"] + "-" + tel_dict["tel2"]
    raise ValueError("Not tel")


def is_gender(gender: int) -> bool:
    return gender in {1, 2, 3, 4}


def get_gender(gender: int) -> int:
    if is_gender(gender):
        return gender
    raise ValueError("Not gender")


def _preprocess_department(department: str) -> str:
    d = department
    if d.find('(') != -1:
        d = d[:d.find('(')].strip()
    return d.strip().strip('.').rstrip("입니다").strip().rstrip("지역").strip()


def is_department(department: str) -> bool:
    if not department:
        return False
    d = _preprocess_department(department)
    for v in DEPARTMENT_DATA:
        if d in set(v['variation']):
            return True
    return False


def get_department(department: str) -> Union[Dict[str, str], str]:
    if not department:
        return department
    d = _preprocess_department(department)
    for v in DEPARTMENT_DATA:
        if d in set(v['variation']):
            return v.copy()
    return department


def is_grade(grade: int) -> bool:
    return (grade < 0) or (grade in {0, 10, 15, 20})


def get_grade(grade: int) -> int:
    return grade


def generate_new_sms_code() -> int:
    code = int("".join([choice(digits) for _ in range(6)]))
    if code == 1:
        return generate_new_sms_code()
    return 3_000_000 + code

from typing import Tuple, NamedTuple

from StudyRoomManagementServer.model import User, QR


class QrResult(NamedTuple):
    """QR 분석 결과"""
    qr_code: str
    revision: int
    user_id: int
    user_key: str


def __parse_qr_code_v1(qr_code: str) -> QrResult:
    """V1 qr 분석"""
    revision, code = qr_code.split("0", 1)
    user_id = int(code[:4], base=16)
    ukey = code[4:]
    return QrResult(qr_code, revision, user_id, ukey)


def parse_qr_code(qr_code: str) -> Tuple[int, int, str]:
    """qr 분석"""
    try:
        _, revision, user_id, user_key = __parse_qr_code_v1(qr_code)

    except ValueError:  # check version split
        raise ValueError("Wrong QR")
    except Exception as e:
        print(e)
        raise ValueError("Wrong QR")

    return revision, user_id, user_key


def get_user_from_qr_code(qr_code: str) -> Tuple[User, QR]:
    """QR 코드에서 사용자 추출"""
    _, user_id, user_key = parse_qr_code(qr_code)

    try:
        qr = QR.query.filter_by(user_id=user_id).order_by(QR.id.desc()).first()
    except Exception as e:  # check uid
        print(e)
        raise ValueError from e

    if qr is None:  # check exist
        return ValueError("Not Member")

    elif user_key != qr.skey:
        return ValueError("Qr Auth Fail")

    return User.query.filter_by(id=user_id).first(), qr

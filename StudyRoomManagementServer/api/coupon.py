import re
from enum import auto
from typing import Optional

from flask import (
    Blueprint,
    request,
    abort
)

from StudyRoomManagementServer.util.enum_base import StrEnum
from ..model import db, Coupon

bp = Blueprint("coupons", __name__, url_prefix="/api/coupons")
DUMMY_COUPON = {
    "left": 1,
    "inner_member": True
}
regex_tel = re.compile(r"\d{3}-?\d{4}-?\d{4}")


class RequestType(StrEnum):
    save = auto()
    need_save = auto()
    is_save = auto()
    use = auto()
    need_use = auto()
    is_use = auto()
    all = auto()
    view = auto()
    view_all = auto()
    is_message = auto()


need_data = {
    RequestType.need_save: 0,
    RequestType.need_use: 0,
    RequestType.is_message: "",
}


@bp.errorhandler(400)
@bp.errorhandler(401)
@bp.errorhandler(403)
@bp.errorhandler(404)
def custom40x(error):
    return error.description, error.code


def get_device_id() -> int:
    device_id = request.args.get("device_id", type=int)
    if not device_id:
        return abort(400, {"message": "coupon.device.bad_request"})
    elif device_id < 0:
        return abort(404, {"message": "coupon.device.not_exist"})
    return device_id


def get_tel() -> str:
    tel = request.args.get("tel", type=str)
    if not tel or not regex_tel.match(tel):
        return abort(400, {"message": "coupon.tel.bad_request"})
    return tel.replace("-", "")


def get_request_amount() -> int:
    request_amount = request.args.get("request_amount", type=int)
    if request_amount is None:
        return abort(400, {"message": "coupon.request_amount.bad_request"})
    elif request_amount < 0:
        return abort(400, {"message": "coupon.request_amount.bad_request"})
    return request_amount


def get_coupon_amount(tel: str) -> int:
    coupons = Coupon.query.filter_by(tel=tel).all()
    return sum([coupon.amount for coupon in coupons])


def get_user_id(tel: str) -> Optional[int]:
    try:
        return Coupon.query.filter_by(tel=tel).order_by(Coupon.id.desc()).one().user_id
    except:
        return


@bp.route("", methods=("GET",))
# @check_user_from_cookie_authorization
def get_coupons():
    device_id = get_device_id()

    request_type = request.args.get("request_type", type=str)

    if request_type == RequestType.save:
        tel = get_tel()

        if not need_data[RequestType.need_save]:
            return {"message": "coupon.save.bad_request"}, 400

        request_amount = need_data[RequestType.need_save]
        need_data[RequestType.need_save] = 0

        user_id = get_user_id(tel)

        coupon = Coupon(
            user_id=user_id,
            tel=tel,
            status=Coupon.CouponStatus.usable,
            amount=request_amount,
            device_id=device_id,
        )
        db.session.add(coupon)
        db.session.commit()
        coupon.group_id = coupon.id
        db.session.commit()

        return {
            "amount": get_coupon_amount(tel),
        }

    elif request_type == RequestType.need_save:
        need_data[RequestType.need_save] = get_request_amount()
        return {"message": "ok"}

    elif request_type == RequestType.is_save:
        return {
            "amount": need_data[RequestType.need_save]
        }

    elif request_type == RequestType.use:
        tel = get_tel()

        # 사용 대기가 아닐 때
        if not need_data[RequestType.need_use]:
            need_data[RequestType.is_message] = "coupon.use.bad_request"
            need_data[RequestType.need_use] = 0
            return {"message": "coupon.use.bad_request"}, 400

        # 쿠폰 갯수가 미달일 때
        coupon_count = get_coupon_amount(tel)
        if coupon_count < need_data[RequestType.need_use]:
            need_amount = need_data[RequestType.need_use]
            need_data[RequestType.is_message] = f"coupon.amount.forbidden.{coupon_count}"
            need_data[RequestType.need_use] = 0
            return {
                "message": "coupon.amount.forbidden",
                "coupon_count": coupon_count,
                "need_amount": need_amount,
            }, 403

        # 사용자 정보 불러오기
        user_id = get_user_id(tel)
        request_amount = need_data[RequestType.need_use]

        # 쿠폰 사용 정보 등록
        coupon = Coupon(
            user_id=user_id,
            tel=tel,
            status=Coupon.CouponStatus.used,
            amount=request_amount * -1,
            device_id=device_id,
        )
        db.session.add(coupon)
        db.session.commit()
        coupon.group_id = coupon.id
        db.session.commit()

        # 서버 정보 초기화
        need_data[RequestType.need_use] = 0
        need_data[RequestType.is_message] = f"coupon.use.success.{request_amount}"

        return {
            "coupon_count": get_coupon_amount(tel),
        }

    elif request_type == RequestType.need_use:
        need_data[RequestType.need_use] = get_request_amount()
        need_data[RequestType.is_message] = ""
        return {"message": "ok"}

    elif request_type == RequestType.is_use:
        return {
            "amount": need_data[RequestType.need_use],
            "is_message": need_data[RequestType.is_message],
        }

    elif request_type == RequestType.all:
        coupons = Coupon.query.all()
        return {
            "data": [coupon.to_dict() for coupon in coupons]
        }

    elif request_type == RequestType.view:
        tel = get_tel()

        return {
            "coupon_count": get_coupon_amount(tel),
        }

    elif request_type == RequestType.view_all:
        tel = get_tel()
        coupons = Coupon.query.filter_by(tel=tel).all()

        return {
            "data": [coupon.to_dict() for coupon in coupons]
        }

    elif request_type == RequestType.is_message:
        message = need_data[RequestType.is_message]
        need_data[RequestType.is_message] = ""
        return {
            "is_message": message,
        }

    else:
        return {"message": "coupon.request_type.bad_request"}, 400
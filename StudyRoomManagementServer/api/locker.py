import base64
import datetime as dt
import hashlib
import os
from typing import Tuple, Optional, Dict

from flask import Blueprint, request, current_app

from ..model import db, User, Locker, LockerRental, LockerPayment
from ..util.grade import is_admin

bp = Blueprint("locker", __name__, url_prefix="/api/locker")


def month_payment_location_group_2(month: int) -> int:
    """월에 따른 금액 안내"""
    if month == 1:
        return 15_000

    elif month == 2:
        return 30_000

    elif month == 3:
        return 40_000

    elif month == 4:
        return 55_000

    elif month == 5:
        return 70_000

    elif month == 6:
        return 80_000

    else:
        raise ValueError("locker.badRequest")


def month_payment(month: int) -> int:
    """월에 따른 금액 안내"""
    if month == 1:
        return 10_000

    elif month == 2:
        return 20_000

    elif month == 3:
        return 25_000

    elif month == 4:
        return 30_000

    elif month == 5:
        return 35_000

    elif month == 6:
        return 45_000

    else:
        raise ValueError("locker.badRequest")


def save_id_picture(id_picture: str) -> str:
    """폴더 경로"""
    id_pictures_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER"), "locker_payment_id_pictures")
    if not os.path.isdir(id_pictures_dir):
        os.makedirs(id_pictures_dir)

    id_picture_file_data = base64.b64decode(id_picture)
    id_picture_file_name = hashlib.sha1(id_picture_file_data).hexdigest() + '.jpg'
    id_picture_file_path = os.path.join(id_pictures_dir, id_picture_file_name)
    with open(id_picture_file_path, 'wb') as f:
        f.write(id_picture_file_data)
    return id_picture_file_name


def bad_request() -> Tuple[Dict[str, str], int]:
    return {"message": "locker.badRequest"}, 400


def forbidden() -> Tuple[Dict[str, str], int]:
    return {"message": "locker.forbidden"}, 403


def not_found() -> Tuple[Dict[str, str], int]:
    return {"message": "locker.notFound"}, 404


@bp.route("", methods=("GET",))
# @check_user_from_cookie_authorization
def get_lockers():
    """(전체)? 락커 조회"""
    locker_id = request.args.get("locker_id", type=int)

    q = Locker.query

    if locker_id:
        return q.filter_by(id=locker_id).first().to_dict()

    return {"data": [locker.to_dict() for locker in q.all()]}


@bp.route("", methods=("POST",))
# @check_user_from_cookie_authorization
def post_locker_rental():
    """락커 대여 등록"""
    user_id: int = request.json.get("user_id")
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        return bad_request()
    elif not user.valid:
        return forbidden()

    locker_id: int = request.json.get("locker_id")
    locker: Locker = Locker.query.filter_by(id=locker_id).first()
    if not locker:
        return bad_request()

    department: str = request.json.get("department")
    if not department:
        return bad_request()

    start_dt: str = request.json.get("start_dt")
    if not start_dt:
        start_dt = dt.datetime.utcnow()
    else:
        try:
            start_dt = dt.datetime.fromisoformat(start_dt)
        except Exception as e:
            print(e)
            return bad_request()

    rental_period: int = request.json.get("rental_period")
    if not rental_period:
        return bad_request()
    else:
        try:
            rental_period = int(rental_period)
            if rental_period < 1 or 6 < rental_period:
                return bad_request()
        except Exception as e:
            print(e)
            return bad_request()

    deposit: int = request.json.get("deposit")
    if deposit and int(deposit) < 0:
        return bad_request()

    id_picture: str = request.json.get("id_picture")
    if not id_picture:
        return bad_request()

    rental_key: int = request.json.get("rental_key")
    if not rental_key:
        rental_key = 1
    else:
        rental_key = int(rental_key)

    payment_required: bool = request.json.get("payment_required")
    if payment_required is None:
        payment_required = True

    licenser_id: int = request.json.get("licenser_id")
    if not licenser_id:
        return bad_request()

    licenser: User = User.query.filter_by(id=licenser_id).first()
    if not licenser:
        return bad_request()

    location_group = locker.location_group
    if location_group == 2:
        payment = month_payment_location_group_2(rental_period)
    else:
        payment = month_payment(rental_period)

    rental = LockerRental(
        user_id=user.id,
        locker_id=locker.id,
        department=department,
        payment_required=payment_required,
        deposit=deposit,
        created=start_dt,
    )
    payment = LockerPayment(
        locker_id=locker.id,
        period=rental_period,
        payment=payment,
        id_picture=id_picture,
        licenser_id=licenser.id,
        admission=LockerPayment.ADMISSION_ACCEPT,
    )

    try:
        db.session.add(rental)
        db.session.commit()

        payment.locker_rental_id = rental.id
        rental.deadline = rental.created + dt.timedelta(days=rental_period * 30)

        db.session.add(payment)
        db.session.commit()

        locker.main_key = rental_key
        db.session.commit()

        return rental.to_dict()
    except Exception as e:
        print(e)
    return bad_request()


@bp.route("/<int:locker_rental_id>", methods=("POST",))
# @check_user_from_cookie_authorization
def post_register_rental(locker_rental_id: int):
    """락커 대여 결제 등록"""
    rental: LockerRental = LockerRental.query.filter_by(id=locker_rental_id).first()
    if not rental:
        return bad_request()

    locker: Locker = Locker.query.filter_by(id=rental.locker_id).first()
    if not locker:
        return bad_request()

    rental_period: int = request.json.get("rental_period")
    if not rental_period:
        return bad_request()
    else:
        try:
            rental_period = int(rental_period)
            if rental_period < 1 or 6 < rental_period:
                return bad_request()
        except Exception as e:
            print(e)
            return bad_request()

    id_picture: str = request.json.get("id_picture")
    if not id_picture:
        return bad_request()

    location_group = locker.location_group
    if location_group == 2:
        payment = month_payment_location_group_2(rental_period)
    else:
        payment = month_payment(rental_period)

    payment = LockerPayment(
        locker_id=rental.locker_id,
        locker_rental_id=locker_rental_id,
        period=rental_period,
        payment=payment,
        id_picture=id_picture,
    )
    db.session.add(payment)
    db.session.commit()
    return payment.to_dict()


@bp.route("/<int:locker_rental_id>/<int:locker_payment_id>", methods=("GET",))
# @check_user_from_cookie_authorization
def get_rental_payment(locker_rental_id: int, locker_payment_id: int):
    """락커 대여 결제 확인"""
    if locker_rental_id == 0 and locker_payment_id != 0:
        payment = LockerPayment.query.filter_by(id=locker_payment_id).first()
        if payment:
            return payment.to_dict()
        return bad_request()

    rental = LockerRental.query.filter_by(id=locker_rental_id).first()
    if not rental:
        return bad_request()

    if locker_payment_id == 0:
        payments = LockerPayment.query.filter_by(locker_rental_id=rental.id).all()
        return {"data": [payment.to_dict() for payment in payments]}

    payment = LockerPayment.query.filter_by(id=locker_payment_id, locker_rental_id=rental.id).first()
    if not payment:
        return bad_request()

    return payment.to_dict()


@bp.route("/<int:locker_rental_id>", methods=("PUT",))
# @check_user_from_cookie_authorization
def put_rental(locker_rental_id: int):
    """락커 대여 결제 응답"""
    rental: LockerRental = LockerRental.query.filter_by(id=locker_rental_id).first()
    if not rental:
        return bad_request()

    data = request.get_json()

    if 'deadline' in data:
        try:
            rental.deadline = dt.datetime.fromisoformat(data['deadline'])
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    if "rental_key" in data:
        locker: Locker = Locker.query.filter_by(id=rental.locker_id).first()
        try:
            locker.main_key = int(data['rental_key'])
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    if "locker_id" in data:
        try:
            old_locker: Locker = Locker.query.filter_by(id=rental.locker_id).first()
            new_locker: Locker = Locker.query.filter_by(id=data['locker_id']).first()
            rental.locker_id = new_locker.id
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    if "payment_required" in data:
        try:
            rental.payment_required = data['payment_required']
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    if "deposit" in data:
        try:
            rental.deposit = int(data['deposit'])
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    if 'vitalization' in data:
        try:
            rental.vitalization = data['vitalization']
            db.session.commit()
        except Exception as e:
            print(e)
            return bad_request()

    return rental.to_dict()


@bp.route("/<int:locker_rental_id>/<int:locker_payment_id>", methods=("PUT",))
# @check_user_from_cookie_authorization
def put_rental_payment(locker_rental_id: int, locker_payment_id: int):
    """락커 대여 결제 응답"""
    rental = LockerRental.query.filter_by(id=locker_rental_id).first()
    if not rental:
        return bad_request()

    payment: LockerPayment = LockerPayment.query.filter_by(id=locker_payment_id, locker_rental_id=rental.id).first()
    if not payment:
        return bad_request()
    elif payment.admission != LockerPayment.ADMISSION_READY:
        return bad_request()

    licenser_id: int = request.json.get("licenser_id")
    licenser: User = User.query.filter_by(id=licenser_id).first()
    if not licenser:
        return bad_request()
    elif not is_admin(licenser):
        return forbidden()

    admission: int = request.json.get("admission")
    if admission is None or int(admission) not in {0, 1, 2}:
        return bad_request()

    reason: Optional[str] = request.json.get("reason")

    payment.licenser_id = licenser.id
    payment.admission = admission
    payment.reason = reason

    if admission == LockerPayment.ADMISSION_ACCEPT:
        rental.deadline = rental.deadline + dt.timedelta(days=30 * payment.period)
    db.session.commit()

    return rental.to_dict()


@bp.route("/new", methods=("POST",))
# @check_user_from_cookie_authorization
def post_new_locker():
    """락커 추가"""
    locker_num: int = request.json.get("locker_num")
    location_x: int = request.json.get("location_x")
    location_y: int = request.json.get("location_y")

    if not locker_num or locker_num <= 0 or not location_x or not location_y:
        return bad_request()

    unavailable: bool = request.json.get("unavailable", False)
    location_group: int = request.json.get("location_group", 1)
    main_key: int = request.json.get("main_key", 0)
    spare_key: int = request.json.get("spare_key", 0)

    filter_d = {
        "unavailable": False, "location_group": location_group, "location_x": location_x, "location_y": location_y
    }
    if not unavailable and Locker.query.filter_by(**filter_d).first():
        return bad_request()

    locker = Locker(
        locker_num=locker_num, unavailable=unavailable,
        location_group=location_group, location_x=location_x, location_y=location_y,
        main_key=main_key, spare_key=spare_key
    )
    db.session.add(locker)
    db.session.commit()
    return locker.to_dict()


@bp.route("", methods=("PUT",))
# @check_user_from_cookie_authorization
def put_locker():
    """락커 수정"""
    locker_id = request.args.get("locker_id", type=int)
    locker = Locker.query.filter_by(id=locker_id).first()
    if not locker:
        return not_found()

    unavailable: bool = request.json.get("unavailable")
    if unavailable is None:
        unavailable = locker.unavailable
    else:
        unavailable = bool(unavailable)

    locker_num: int = request.json.get("locker_num")
    if not locker_num:
        locker_num = locker.locker_num

    location_x: int = request.json.get("location_x")
    if not location_x:
        location_x = locker.location_x

    location_y: int = request.json.get("location_y")
    if not location_y:
        location_y = locker.location_y

    location_group: int = request.json.get("location_group")
    if not location_group:
        location_group = locker.location_group

    if not locker_num or locker_num <= 0 or not location_x or not location_y:
        return bad_request()

    filter_d = {
        "unavailable": False, "location_group": location_group, "location_x": location_x, "location_y": location_y
    }
    if not unavailable and Locker.query.filter_by(**filter_d).first():
        return bad_request()

    locker.unavailable = unavailable
    locker.locker_num = locker_num
    locker.location_x = location_x
    locker.location_y = location_y
    locker.location_group = location_group

    main_key: int = request.json.get("main_key")
    if main_key is not None:
        if main_key not in {0, 1, 2}:
            return bad_request()
        locker.main_key = main_key

    spare_key: int = request.json.get("spare_key")
    if spare_key is not None:
        if spare_key not in {0, 1, 2}:
            return bad_request()
        locker.spare_key = spare_key

    db.session.commit()
    return Locker.query.filter_by(id=locker_id).first().to_dict()


@bp.route("/rental", methods=("GET",))
# @check_user_from_cookie_authorization
def get_rental_charge():
    """락커 대여 요금 관련 정보"""
    month = request.args.get("month", type=int)
    location_group = request.args.get("location_group", type=int, default=1)

    try:
        if location_group == 2:
            func_month_payment = month_payment_location_group_2
        else:
            func_month_payment = month_payment

        if month:
            return {"payment": func_month_payment(month)}
        else:
            return {"data": [{"rental_period": month, "payment": func_month_payment(month)} for month in range(1, 7)]}
    except Exception:
        return bad_request()
    pass


@bp.route("/<int:locker_rental_id>", methods=("GET",))
# @check_user_from_cookie_authorization
def get_rental(locker_rental_id: int):
    """락커 대여 정보 조회"""
    if locker_rental_id == 0:
        user_id: Optional[int] = request.args.get("user_id")
        q = LockerRental.query

        if user_id:
            rental: LockerRental = q.filter_by(user_id=user_id).order_by(LockerRental.id.desc()).first()
            if not rental:
                return not_found()
            else:
                return rental.to_dict()

        return {"data": [rental.to_dict() for rental in LockerRental.query.all()]}
    rental = LockerRental.query.filter_by(id=locker_rental_id).first()
    if not rental:
        return bad_request()
    return rental.to_dict()

@bp.route("/init", methods=("GET",))
# @check_user_from_cookie_authorization
def init_locker():
    """락커 초기 설정"""
    if len(Locker.query.all()) != 0:
        return "exist"
    for locker_num in range(1, 25):
        d = {
            "locker_num": locker_num,
            "location_x": ((locker_num - 1) // 6) + 1,
            "location_y": ((locker_num - 1) % 6) + 1
        }

        locker = Locker(
            locker_num=locker_num, unavailable=False,
            location_group=1, location_x=d["location_x"], location_y=d["location_y"]
        )
        db.session.add(locker)
    db.session.commit()
    return "ok"

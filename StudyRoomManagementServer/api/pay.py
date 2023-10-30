import datetime as dt
from typing import Dict, Union, Tuple, Optional

from flask import (
    Blueprint,
    request,
    Response,
)
from werkzeug.wsgi import FileWrapper

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from StudyRoomManagementServer.util.receipt import Store, Receipt, CreditCard, Menu, make_receipt_image_file
from StudyRoomManagementServer.util.utils import create_web_log
from .lib.book import get_client_name
from ..model import db, Pay, RoomBook, Transaction, SavedMoney, User, Room

STATUS_WAITING = "waiting"
STATUS_CONFIRM = "confirm"
STATUS_REJECT = "reject"


bp = Blueprint("pays", __name__, url_prefix="/api/pays")


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_pays():
    q = Pay.query

    user_id = request.form.get("user_id", type=int)
    if user_id is not None:
        q = q.filter_by(user_id=user_id)

    book_id = request.form.get("book_id", type=int)
    if book_id is not None:
        q = q.filter_by(book_id=book_id)

    cashier = request.form.get("cashier", type=str)
    if cashier is not None:
        q = q.filter_by(cashier=cashier)

    pay_type = request.form.get("pay_type", type=str)
    if pay_type is not None:
        q = q.filter_by(pay_type=pay_type)

    date = request.args.get("date", type=dt.date.fromisoformat)
    if isinstance(date, dt.date):
        before_dt = dt.datetime.fromordinal(date.toordinal()) - dt.timedelta(hours=9)
        after_dt = before_dt + dt.timedelta(days=1)
        q = q.filter(Pay.created >= before_dt.isoformat(" "))
        q = q.filter(Pay.created <= after_dt.isoformat(" "))

    pays = [pay.publics_to_dict() for pay in q.all()]
    return {"message": "ok", "pays": pays}


@bp.route("/<int:pay_id>", methods=("GET",))
@check_user_from_cookie_authorization
def get_pay(pay_id: int):
    pay = Pay.query.filter_by(id=pay_id).first()
    if pay is None:
        return {"message": "해당 지불건이 없습니다."}, 404

    response = pay.publics_to_dict()

    transaction = Transaction.query.filter_by(pay_id=pay_id).first()
    if transaction:
        response['transaction'] = transaction.publics_to_dict()
    else:
        response['transaction'] = None

    return response


@bp.route("/<int:pay_id>/receipt.png", methods=("GET",))
@check_user_from_cookie_authorization
def get_pay_receipt(pay_id: int):
    pay = Pay.query.filter_by(id=pay_id).first()
    if pay is None:
        return {"message": "해당 지불건이 없습니다."}, 404

    menus = []
    store = Store("카페", "부산 강서구 낙동북로 477 강서구청", "강서구", "000-00-12345", "010-0000-0000")
    if pay.saved_money_id:
        menus.append(Menu(f"후원", pay.paid, 1))
    else:
        book: RoomBook = RoomBook.query.filter_by(id=pay.book_id).first()
        room: Room = Room.query.filter_by(id=book.room_id).first()
        if room.type == 1:
            menus.append(Menu(f"스터디룸 {pay.paid / 1000}시간", pay.paid, 1))
        elif room.type == 2:
            menus.append(Menu(f"세미나룸 {pay.paid / 1000}시간", pay.paid, 1))
        elif room.type == 3:
            menus.append(Menu(f"컨퍼런스 {pay.paid / 1000}시간", pay.paid, 1))

    transaction = Transaction.query.filter_by(pay_id=pay_id).first()
    if transaction:
        payment = CreditCard(
            transaction.issuer_name.strip(),
            transaction.card_bin.strip(),
            transaction.halbu,
            int(transaction.authorization_number),
            transaction.acquisition_company_name.strip()
        )
    else:
        payment = None

    receipt_img_file = make_receipt_image_file(Receipt(pay.id, pay.created, menus, store, payment))
    f = FileWrapper(receipt_img_file)
    response = Response(f, mimetype="image/png", direct_passthrough=True)
    response.headers["Cache-Control"] = "no-cache"

    return response


def __add_saved_money(paid: int, name: Optional[str] = None, user_id: Optional[int] = None) -> SavedMoney:
    if name is not None and len(name.strip()) > 0:
        sm = SavedMoney.query.filter_by(name=name).first()
        sm_type = SavedMoney.TYPE_DEPARTMENT
        user_id = None

    elif user_id is not None:
        sm = SavedMoney.query.filter_by(user_id=user_id).first()
        sm_type = SavedMoney.TYPE_PERSONAL
        name = None

    else:
        raise ValueError("__add_saved_money::Need name or user_id")

    if not sm:
        sm = SavedMoney(
            type=sm_type,
            name=name,
            user_id=user_id,
            money=paid,
        )

    else:
        sm.money = sm.money + paid

    return sm


def __process_pay(
        user_id: int,
        cashier: str,
        pay_type: str,
        paid: int,
        client_name: Optional[str] = None,
        book_id: Optional[int] = None,
        saved_money_id: Optional[int] = None,
        comment: Optional[str] = None,
) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    pay = Pay(
        user_id=user_id,
        book_id=book_id,
        saved_money_id=saved_money_id,
        cashier=cashier,
        pay_type=pay_type,
        paid=paid,
        comment=comment,
    )
    db.session.add(pay)
    db.session.commit()

    if pay_type.startswith("card"):
        pay.status = Pay.STATUS_CONFIRM

    elif pay_type.startswith("donation"):
        if pay_type.startswith("donation.card"):
            pay.status = Pay.STATUS_CONFIRM


            # Transaction 비활성화로, 즉시 추가되도록 변경
            name = pay_type.lstrip("donation.card").lstrip(".")
            sm = __add_saved_money(paid, name, user_id)
            db.session.add(sm)
            db.session.commit()
            pay.saved_money_id = sm.id
            db.session.add(pay)
            db.session.commit()

        elif pay_type.startswith("donation.transfer") or pay_type.startswith("donation.cash"):
            name = pay_type.lstrip("donation.").lstrip("transfer").lstrip("cash").lstrip(".")
            sm = __add_saved_money(paid, name, user_id)
            db.session.add(sm)
            db.session.commit()
            pay.saved_money_id = sm.id
            pay.status = Pay.STATUS_CONFIRM

    elif pay_type.startswith("transfer") or pay_type.startswith("cash"):
        pay.status = Pay.STATUS_CONFIRM

    elif pay_type.startswith("saved_money.d"):
        name = pay_type.lstrip("saved_money.d.")
        sm = SavedMoney.query.filter_by(name=name).first()

        if sm is None:
            pay.comment = f"해당 적립금이 없습니다({pay.comment})."
            pay.status = STATUS_REJECT

        elif sm.money < paid:
            pay.comment = f"해당 적립금이 부족합니다(잔액: {sm.money}원)({pay.comment})."
            pay.status = STATUS_REJECT

        else:
            before_money = sm.money
            sm.money = sm.money - paid
            after_money = sm.money

            if before_money != (after_money + paid) or sm.money < 0:
                pay.status = STATUS_REJECT
                pay.comment = f"내부 검증 오류 발생({pay.comment})"

            else:
                pay.comment = f"결제되었습니다(잔액: {sm.money}원)({pay.comment})."
                pay.status = STATUS_CONFIRM
                db.session.add(sm)

    elif pay_type.startswith("saved_money.p"):
        sm = SavedMoney.query.filter_by(user_id=user_id).first()

        if sm is None:
            pay.comment = "적립 내역이 없습니다."
            pay.status = STATUS_REJECT

        elif sm.money < paid:
            pay.comment = f"적립금이 부족합니다(잔액: {sm.money}원)."
            pay.status = STATUS_REJECT

        else:
            before_money = sm.money
            sm.money = sm.money - paid
            after_money = sm.money

            if before_money != (after_money + paid) or sm.money < 0:
                pay.status = STATUS_REJECT
                pay.comment = "내부 검증 오류 발생"

            else:
                pay.comment = f"결제되었습니다(잔액: {sm.money}원)."
                pay.status = STATUS_CONFIRM
                db.session.add(sm)

    elif pay_type.startswith("etc"):
        pay.status = Pay.STATUS_CONFIRM

    elif pay_type.startswith("notion"):
        pay.status = Pay.STATUS_CONFIRM

    db.session.add(pay)
    db.session.commit()

    return {"message": "ok", "pay": pay.publics_to_dict()}


@bp.route("", methods=("POST",))
@check_user_from_cookie_authorization
def post_pay():
    user_id: int = request.json.get("user_id")
    book_id: Optional[int] = request.json.get("book_id")
    cashier: str = request.json.get("cashier")
    pay_type: str = request.json.get("pay_type")
    paid: int = request.json.get("paid")
    comment: Optional[str] = request.json.get("comment")
    client_name: str = get_client_name()
    if client_name is None:
        client_name = cashier

    db.session.add(create_web_log("post_pay", {
        "user_id": user_id,
        "book_id": book_id,
        "cashier": cashier,
        "pay_type": pay_type,
        "paid": paid,
        "comment": comment,
        "client_name": client_name,
    }))
    db.session.commit()

    try:
        user_id = int(user_id)
        book_id = int(book_id) if book_id is not None else None
        cashier = str(cashier)
        pay_type = str(pay_type)
        paid = int(paid)
        comment = str(comment) if comment is not None else None
        client_name = str(client_name)

        if not cashier or not pay_type or paid is None:
            return {"message": "올바르지 않은 요청입니다."}, 400
    except:
        return {"message": "올바르지 않은 요청입니다."}, 400

    if not User.query.filter_by(id=user_id).first():
        return {"message": "사용자가 없습니다."}, 403

    if book_id is not None:
        book = RoomBook.query.filter_by(user_id=user_id, id=book_id).first()
        if book is None:
            return {"message": "해당 예약이 없습니다."}, 404

        pay: Pay = Pay.query.filter_by(user_id=user_id, book_id=book_id).first()
        if pay is not None:
            if pay.status == STATUS_CONFIRM:
                return {"message": "이미 해당 지불건이 존재합니다."}, 400
            elif pay.status == STATUS_WAITING:
                if (pay.created + dt.timedelta(minutes=10)) < dt.datetime.now():
                    pay.status = STATUS_REJECT
                    pay.comment = "[TIMEOUT] Auto"
                    db.session.add(pay)
                    db.session.commit()
                else:
                    return {"message": "이미 해당 지불건이 대기중입니다."}, 400

    return __process_pay(user_id, cashier, pay_type, paid, client_name, book_id, comment=comment)


@bp.route("/<int:pay_id>", methods=("PUT",))
@check_user_from_cookie_authorization
def put_pay(pay_id: int):
    pay = Pay.query.filter_by(id=pay_id).first()
    if pay is None:
        return {"message": "Not Exist"}, 404

    cashier = request.form.get("cashier", type=str)
    if cashier is not None:
        pay.cashier = cashier

    pay_type = request.form.get("pay_type", type=str)
    if pay_type is not None:
        pay.pay_type = pay_type

    paid = request.form.get("paid", type=int)
    if paid is not None:
        pay.paid = paid

    comment = request.form.get("comment", type=str)
    if comment is not None:
        pay.comment = comment

    db.session.add(create_web_log("put_pay", pay.publics_to_dict()))
    db.session.commit()
    return pay.publics_to_dict()


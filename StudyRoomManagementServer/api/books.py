import datetime as dt
import json
from typing import Dict, Union, Tuple, Optional, List

import pytz
from flask import Blueprint, request, current_app, Response, jsonify
from werkzeug.wsgi import FileWrapper

from StudyRoomManagementServer.auth_decorator import need_authorization, Authorization, check_user_from_cookie_authorization, \
    get_user_from_cookie_authorization
from StudyRoomManagementServer.util import sms
from StudyRoomManagementServer.util.timetable import create_timetable
from StudyRoomManagementServer.util.utils import create_web_log
from .lib.book import (
    raise_for_duplication,
    get_date_and_time,
    get_chat_id,
    get_user_id,
    get_client_name,
)
from .lib.user import is_department, get_department
from .rooms import is_room_available, create_book_from_block
from ..cms_config import get_config
from ..constants import Grade
from ..model import RoomBook, Room, User, db, Pay, Log, SavedMoney, Transaction, Message

bp = Blueprint("books", __name__, url_prefix="/api/books")


def _get_books_args() -> Tuple[int, dt.date, str]:
    user_id: int = request.args.get("user_id", type=int)
    book_date: dt.date = request.args.get("book_date", type=dt.date.fromisoformat)
    department: str = request.args.get("department", type=str)

    db.session.add(
        create_web_log(
            "get_books",
            {
                "user_id": user_id,
                "book_date": book_date.isoformat() if book_date is not None else None,
                "department": department,
            },
        )
    )
    db.session.commit()

    return user_id, book_date, department


def remove_no_show():
    now = dt.datetime.utcnow() + dt.timedelta(hours=9)
    if now.hour < 9:
        return
    start_time_limit = (now - dt.timedelta(minutes=20)).time()

    for book in RoomBook.query.filter_by(book_date=now.date()).all():
        book: RoomBook
        if book.start_time >= start_time_limit:
            continue

        if not Pay.query.filter_by(book_id=book.id).first():
            user = User.query.filter_by(id=book.user_id).first()
            book_id = book.id
            # book.status = RoomBook.STATUS_CANCELED
            # book.reason = f"노쇼로 예약이 취소됨(예약 id: {book_id})"

            log = Log(
                user_id=book.user_id,
                grade=user.grade,
                log_type="book.del.record",
                extra_data_str=json.dumps(book.publics_to_dict())
            )
            db.session.add(log)
            db.session.delete(book)
            db.session.add(Message(
                chat_id=user.chat_id,
                data=f"노쇼로 예약이 취소됨(예약 id: {book_id})",
                states=Message.STATE_NEED_SEND
            ))
            db.session.commit()


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_books():
    print("api.books.get_books")
    user_id, book_date, department = _get_books_args()
    print(book_date, type(book_date))
    q = RoomBook.query.filter_by(reason=None)

    if user_id is not None:
        q = q.filter_by(user_id=user_id)

    if book_date is not None:
        q = q.filter_by(book_date=book_date)

    books = [rb.publics_to_dict() for rb in q.all()]

    if department is not None:
        temp_books = []
        for book in books:
            if is_department(book["department"]):
                d = get_department(book["department"])
                if isinstance(d, dict) and d["key"] == department:
                    d["department"] = d["name"]
                    temp_books.append(book)
            elif department == "etc":
                temp_books.append(book)

        books = temp_books

    for book in books:
        book["room"] = Room.query.filter_by(id=book["room_id"]).order_by(Room.id.desc()).first().publics_to_dict()
        book["user"] = User.query.filter_by(id=book["user_id"]).order_by(User.id.desc()).first().publics_to_dict()

        pay = Pay.query.filter_by(book_id=book["book_id"]).order_by(Pay.id.desc()).first()
        if pay:
            book["pay"] = pay.publics_to_dict()

    return {"message": "ok", "books": books}


@bp.route("<string:date_string>.png")
@check_user_from_cookie_authorization
def get_book_timetable(date_string: str):
    print("api.books.get_book_timetable")
    remove_no_show()
    create_book_from_block()

    # block = [5, 6, 8, 10, 3]
    try:
        date = dt.date.fromisoformat(date_string)
        # if date.weekday() == 6 or date.weekday() == 2:  # 일요일 또는 수요일
        #     block.append(9)
    except ValueError:
        return {"message": "date is wrong"}, 400

    if request.args.get("chat_id"):
        user = User.query.filter_by(
            chat_id=request.args.get("chat_id", type=int)
        ).first()
        with_text = user and user.grade >= Grade.get("manager")
    else:
        with_text = False

    books = RoomBook.query\
        .filter_by(book_date=date, reason=None)\
        .filter(RoomBook.status != RoomBook.STATUS_CANCELED)\
        .all()

    f = FileWrapper(create_timetable(date_string, books, with_text))
    response = Response(f, mimetype="image/png", direct_passthrough=True)
    response.headers["Cache-Control"] = "no-cache"

    return response


@bp.route("", methods=("POST",))
@check_user_from_cookie_authorization
def post_book():
    print("api.books.post_book")
    action = request.json.get("action")
    data = request.json

    db.session.add(create_web_log("post_book", request.get_json(silent=True)))
    db.session.commit()

    if action == "prepare":
        return _post_book_action_prepare(data)

    elif action == "confirm":
        return _post_book_action_confirm(data)

    elif action == "immediately":
        return _post_book_action_immediately(data)
    pass


def _post_book_action_immediately(
    data: dict,
) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    prepare = _post_book_action_prepare(data)
    if "temp_book_idx" in prepare:
        return _post_book_action_confirm(data, int(prepare["temp_book_idx"]))
    else:
        return prepare


def _post_book_action_confirm(
    data: dict, temp_book_idx: Optional[int] = None
) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    """방 예약을 승인합니다."""
    temp_book_idx = (
        temp_book_idx if temp_book_idx is not None else data["temp_book_idx"]
    )

    room_book: RoomBook = (
        RoomBook.query.filter_by(reason=None).filter_by(id=temp_book_idx).first()
    )
    if not room_book:
        return {"message": "예약이 불가능합니다.\n사유: 선 예약을 해야 합니다."}, 403

    elif room_book.created < (dt.datetime.utcnow() - dt.timedelta(minutes=10)):
        print(room_book.created)
        db.session.delete(room_book)
        db.session.commit()
        return {"message": "예약이 불가능합니다.\n사유: 임시 예약 시간(10분) 초과"}, 403

    room_book.department = data["department"]
    room_book.purpose = data["purpose"]
    room_book.obj = data["obj"]
    room_book.status = 200
    db.session.commit()

    book = room_book.publics_to_dict()
    book["room"] = Room.query.filter_by(id=room_book.room_id).first().publics_to_dict()
    book["user"] = User.query.filter_by(id=room_book.user_id).first().publics_to_dict()

    pay = Pay.query.filter_by(book_id=book["book_id"]).first()
    if pay:
        book["pay"] = pay.publics_to_dict()

    room: Room = Room.query.filter_by(id=room_book.room_id).first()
    user: User = User.query.filter_by(id=room_book.user_id).first()
    # __add_book_at_spreadsheet(room_book, room, user)

    if user.id == 1:
        pass
    elif room_book.start_time_second < 9 * 60:
        sms.send(user.num, "해당시간은 운영시간이 아니므로 가게에 꼭 연락주세요.")
    elif room_book.end_time_second > 22 * 60:
        sms.send(user.num, "해당시간은 운영시간이 아니므로 가게에 꼭 연락주세요.")

    return {"message": "예약됨", "book": book}


def _post_book_action_prepare(
    data: dict,
) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    """방 예약을 준비합니다."""
    now = dt.datetime.now(pytz.timezone("Asia/Seoul"))
    chat_id, user_id = None, None
    try:
        chat_id = get_chat_id()
    except ValueError as ve:
        try:
            user_id = get_user_id()
        except ValueError as ve2:
            return {"message": f"{ve}\n{ve2}"}, 400

    client_name = get_client_name()

    try:
        book_date, start_time, end_time = get_date_and_time()
        # if not client_name.startswith("Mozilla/5.0"):
        #     raise_can_book_date(now=now, book_date=book_date)
    except ValueError as ve:
        return {"message": f"{ve}"}, 400

    if chat_id:
        user = User.query.filter_by(chat_id=chat_id).first()
    else:
        user = User.query.filter_by(id=user_id).first()

    if user is None:
        return {"message": "회원가입이 필요합니다."}, 401

    elif not user.valid:
        return {"message": "전화번호 인증이 필요합니다"}, 403

    is_admin = user.id == 1

    if get_config().cafe_is_close and not is_admin:
        return {"message": "현재는 예약이 불가합니다"}, 403

    if book_date in get_config().cafe_close_date and not is_admin:
        return {
            "message": f"{book_date.month:0>2}월 {book_date.day:0>2}일은 영업하지 않습니다."
        }, 403

    if book_date.weekday() < 5:
        # 평일
        week_txt = "평일"
        config_open_time = get_config().book_room_weekdays_open
        config_close_time = get_config().book_room_weekdays_close
    else:
        week_txt = "주말"
        config_open_time = get_config().book_room_weekend_open
        config_close_time = get_config().book_room_weekend_close

    if start_time < config_open_time and not is_admin:
        return {
            "message": f"{week_txt}은 {config_open_time.hour:0>2}:{config_open_time.minute:0>2} 부터 예약이 가능합니다."
        }, 400

    elif end_time > config_close_time and not is_admin:
        return {
            "message": f"{week_txt}은 {config_close_time.hour:0>2}:{config_close_time.minute:0>2} 까지 예약이 가능합니다."
        }, 400

    start_time_second = start_time.hour * 60 + start_time.minute
    end_time_second = end_time.hour * 60 + end_time.minute

    people_no = data["people_no"]
    room_type = data["room_type"]
    room_no = data["room_no"] if "room_no" in data else None

    if people_no <= -6 and not is_admin:
        return {"message": "인원수가 올바르지 않습니다."}, 400

    if Room.query.filter_by(type=room_type).first() is None:
        return {"message": "잘못된 room_type 입니다."}, 400

    q = Room.query.filter_by(type=room_type)
    if room_no is not None:
        q = q.filter_by(no=room_no)

    for room in q.all():
        available, reason = is_room_available(room.type, room.no, book_date)
        if available:
            try:
                raise_for_duplication(room.id, book_date, start_time, end_time)
                break
            except Exception as e:
                current_app.logger.error(str(e))
                continue
    else:
        return {"message": "예약이 불가능합니다.\n사유:빈방이 없습니다."}, 403

    if user.grade < 15:
        if (now + dt.timedelta(days=30)).date() < book_date:
            return {"message": "2주일 이내로만 예약 가능합니다."}, 403

    status = 100

    room_book = RoomBook(
        status=status,
        people_no=people_no,
        room_id=room.id,
        user_id=user.id,
        book_date=book_date,
        start_time_second=start_time_second,
        end_time_second=end_time_second,
        department=None,
        purpose=None,
        obj=None,
        reason=None,
    )
    db.session.add(room_book)
    db.session.commit()

    expire = dt.datetime.now() + dt.timedelta(minutes=10)
    return {
        "temp_book_idx": room_book.id,
        "temp_book_expire": expire.isoformat(),
    }


@bp.route("/<int:book_id>", methods=("PUT",))
@check_user_from_cookie_authorization
def put_book(book_id: int):
    print("api.books.put_book")
    data = request.get_json()

    db.session.add(create_web_log("put_book", {"book_id": book_id}))
    db.session.commit()

    if "action" in data and data["action"] == "cancel":
        return _put_book_cancel_handle(book_id)

    book = RoomBook.query.filter_by(reason=None).filter_by(id=book_id).first()
    if not book:
        return {"message": "No Book"}, 404

    if "action" not in data:
        return {"message": "No action"}, 400

    action = str(data.get("action", ""))

    if action == "change.room":
        return _action_change_room(book, data)

    return {"message": "Bad Request"}, 400


# @need_qr_authorization
@need_authorization(
    allow=(
        Authorization.QR,
        Authorization.WEB,
    )
)
def _put_book_cancel_handle(user: User, book_id: int):
    return _put_book_cancel(user, book_id)


def _refund_pay_type_saved_money(user: User, book: RoomBook, paid: int, cashier: str = "cashier") -> Pay:
    try:
        saved_money: SavedMoney = SavedMoney.query.filter_by(
            name=book.department
        ).first()
        if not saved_money:
            raise Exception({"status": "reject", "message": "지역 적립금 환불에 실패하였습니다."}, 403)

        refund_pay = Pay(
            user_id=user.id,
            book_id=book.id,
            saved_money_id=saved_money.id,
            cashier=cashier,
            pay_type=f"saved_money.d.refund.{book.department}",
            paid=paid,
            comment="지역 적립금으로 환불됩니다.",
            status=Pay.STATUS_WAITING,
        )
        saved_money.money = saved_money.money + refund_pay.paid
        refund_pay.status = Pay.STATUS_CONFIRM
        db.session.add(saved_money)
        db.session.add(refund_pay)
        db.session.commit()
        return refund_pay
        # cancel_reason += f"(지역 적립금 환불: {refund_pay.paid})."

    except Exception as e:
        print(e)
        raise Exception({
            "status": Pay.STATUS_REJECT,
            "message": f"지역 적립금 환불에 실패하였습니다({e})",
        }, 403) from e


def _refund_pay_type_card_without_transaction(user: User, book: RoomBook, paid: int, cashier: str = "cashier") -> Pay:
    try:
        refund_pay = Pay(
            user_id=user.id,
            book_id=book.id,
            cashier=cashier,
            pay_type=f"card.refund.{book.department}",
            paid=paid,
            comment="카드 환불 성공",
            status=Pay.STATUS_CONFIRM,
        )
        db.session.add(refund_pay)
        db.session.commit()
        return refund_pay

        # cancel_reason += f"(카드 환불 요청: [{transaction.issuer_name.strip()}] {refund_pay.paid})."
    except Exception as e:
        print(e)
        raise Exception({
            "status": Pay.STATUS_REJECT,
            "message": f"지역 적립금 환불에 실패하였습니다({e})",
        }, 403) from e
        # return {
        #     "status": Pay.STATUS_REJECT,
        #     "message": f"지역 적립금 환불에 실패하였습니다({e})",
        # }, 403
    pass

def _put_book_cancel(user: User, book_id: int):
    ua = request.user_agent
    try:
        data = request.get_json()
        cashier = data["cashier"] if "cashier" in data else ua.string
    except:
        cashier = ua.string

    book: Optional[RoomBook] = RoomBook.query.filter_by(id=book_id).first()

    if not book:
        return {"status": "reject", "message": "해당 예약이 없습니다."}, 404

    elif (book.book_date + dt.timedelta(days=1)) < dt.datetime.now():
        return {"status": "reject", "message": "지나간 예약은 취소할 수 없습니다."}, 403

    elif book.user_id != user.id:
        return {"status": "reject", "message": "본인 예약만 취소 가능합니다."}, 403

    refund_pay: Optional[Pay] = None

    pays: List[Optional[Pay]] = Pay.query.filter_by(
        book_id=book.id, status=Pay.STATUS_CONFIRM
    ).all()
    cancel_reason = f"[{dt.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}]"

    if not pays or len(pays) == 0:
        if Pay.query.filter_by(book_id=book.id, status=Pay.STATUS_WAITING).all():
            return {
                "status": Pay.STATUS_REJECT,
                "message": "결제 대기중인 예약은 취소가 불가합니다. 잠시 후에 다시 시도하세요.",
            }, 403
        cancel_reason += "사용자가 취소하였습니다."

        book.reason = cancel_reason
        book.status = RoomBook.STATUS_CANCELED
        db.session.add(book)
        db.session.add(
            create_web_log(
                "book.cancel.success", {"cancel_reason": cancel_reason}, user.id
            )
        )
        db.session.commit()

        result = book.publics_to_dict()
        result["status"] = Pay.STATUS_CONFIRM
        result["message"] = cancel_reason
        result["refund_pay"] = None
        return result

    elif len(pays) >= 2 and pays[0].paid == pays[-1].paid:
        cancel_reason += "사용자가 취소했습니다(취소 환불 내역이 존재합니다)."

    elif len(pays) == 1:
        # data = request.get_json()
        # cashier = data["cashier"] if "cashier" in data else ua.string
        pay = pays[0]
        cancel_reason = f"사용자가 취소했습니다"
        paid = pay.paid

        if pay.pay_type.startswith("saved_money.d"):
            try:
                refund_pay = _refund_pay_type_saved_money(user, book, paid, cashier)
                cancel_reason += f"(지역 적립금 환불: {refund_pay.paid})."
            except Exception as e:
                print(e)
                return {
                    "status": Pay.STATUS_REJECT,
                    "message": f"적립금 환불에 실패하였습니다({e})",
                }, 403

        elif pay.pay_type.startswith("transfer"):
            try:
                saved_money: SavedMoney = SavedMoney.query.filter_by(
                    name=book.department
                ).first()
                if not saved_money:
                    return {"status": "reject", "message": "적립금 환불에 실패하였습니다."}, 403

                refund_pay = Pay(
                    user_id=user.id,
                    book_id=book.id,
                    saved_money_id=saved_money.id,
                    cashier=cashier,
                    pay_type=f"transfer.refund.{book.department}",
                    paid=paid,
                    comment="이체는 적립금으로 환불됩니다.",
                    status="waiting",
                )
                saved_money.money = saved_money.money - refund_pay.paid
                refund_pay.status = Pay.STATUS_CONFIRM
                db.session.add(saved_money)
                db.session.add(refund_pay)
                db.session.commit()

                cancel_reason += (
                    f"(이체 금액을 {book.department} 적립금으로 환불: {refund_pay.paid} 원)."
                )
            except Exception as e:
                print(e)
                return {
                    "status": Pay.STATUS_REJECT,
                    "message": f"적립금 환불에 실패하였습니다({e})",
                }, 403

        elif pay.pay_type.startswith("card"):
            transaction: Transaction = Transaction.query.filter_by(
                pay_id=pay.id
            ).first()
            if (
                not transaction
                or transaction.type != 100
                or transaction.response_code != "0000"
            ):
                return {
                    "status": "reject",
                    "message": "카드 결제 정보가 올바르지 않습니다. 관리자에게 문의 바랍니다.",
                }, 403

            try:
                refund_pay = Pay(
                    user_id=user.id,
                    book_id=book.id,
                    cashier=cashier,
                    pay_type=f"card.refund.{book.department}",
                    paid=paid,
                    comment="카드 환불 요청중",
                    status="waiting",
                )
                db.session.add(refund_pay)
                db.session.commit()

                refund_transaction = Transaction(
                    user_id=book.user_id,
                    pay_id=refund_pay.id,
                    client_name=transaction.client_name,
                    type=102,
                    money=transaction.money,
                    tax=transaction.tax,
                    bongsa=transaction.bongsa,
                    halbu=transaction.halbu,
                    agree_num=transaction.authorization_number,
                    agree_date=transaction.approval_datetime,
                    cat_id=transaction.cat_id,
                    myunse=transaction.myunse,
                )
                db.session.add(refund_transaction)
                db.session.commit()

                cancel_reason += f"(카드 환불 요청: [{transaction.issuer_name.strip()}] {refund_pay.paid})."
            except Exception as e:
                print(e)
                return {
                    "status": Pay.STATUS_REJECT,
                    "message": f"적립금 환불에 실패하였습니다({e})",
                }, 403
        else:
            return {
                "status": Pay.STATUS_REJECT,
                "message": "결제 정보가 올바르지 않습니다. 관리자에게 문의 바랍니다.",
            }, 403
    else:
        return {
            "status": Pay.STATUS_REJECT,
            "message": "결제 정보가 올바르지 않습니다. 관리자에게 문의 바랍니다.",
        }, 403

    if not refund_pay:
        return {
            "status": Pay.STATUS_REJECT,
            "message": "결제 정보가 올바르지 않습니다. 관리자에게 문의 바랍니다.",
        }, 403

    book.reason = cancel_reason
    book.status = RoomBook.STATUS_CANCELED
    db.session.add(book)
    db.session.add(
        create_web_log("book.cancel.success", {"cancel_reason": cancel_reason}, user.id)
    )
    db.session.commit()

    result = book.publics_to_dict()
    result["status"] = refund_pay.status
    result["message"] = cancel_reason
    result["refund_pay"] = refund_pay.publics_to_dict()
    return result


@bp.route("/<int:book_id>/admin", methods=("DELETE",))
# @need_authorization(allow=(Authorization.WEB,))
@check_user_from_cookie_authorization
def del_book_by_admin(book_id: int):
    """웹에서 매니저가 호출하는 예약 삭제"""
    print("api.books.del_book_by_admin")
    user = get_user_from_cookie_authorization()
    commander_chat_id = user.chat_id
    user_id = user.id
    reason = "Admin"

    db.session.add(
        create_web_log(
            "del_book.request",
            {
                "book_id": book_id,
                "commander_chat_id": commander_chat_id,
                "user_id": user_id,
                "reason": reason,
            },
        )
    )
    db.session.commit()

    book = RoomBook.query.filter_by(id=book_id).first()
    if not book:
        return {"message": "No Book"}, 404

    try:

        if User.query.filter_by(chat_id=commander_chat_id).one().grade < Grade.get("manager"):
            return {"message": "Need admin"}, 403

    except:
        return {"message": "Need admin"}, 403

    book.reason = reason
    log_type = "admin.book.delete"

    log = Log(
        chat_id=commander_chat_id,
        user_id=user_id,
        log_type=log_type,
    )
    log.extra_data = {
        "room_book_id": book_id,
        "reason": reason,
        "commander_chat_id": commander_chat_id,
        "flag_command_admin": True,
    }

    db.session.add(log)
    db.session.add(book)
    db.session.commit()

    # room = Room.query.filter_by(id=book.room_id).first()
    # user = User.query.filter_by(id=book.user_id).first()

    book_pay: Optional[Pay] = Pay.query.filter_by(book_id=book_id).one_or_none()
    if book_pay:
        book_pay.pay_type = book_pay.pay_type + '.canceled'
        db.session.commit()

    return {
        "message": "삭제 성공",
    }


@bp.route("/<int:book_id>", methods=("DELETE",))
@check_user_from_cookie_authorization
def del_book(book_id: int):
    """예약 삭제"""
    print("api.books.del_book")
    db.session.add(create_web_log("del_book", {"book_id": book_id}))
    db.session.commit()

    if request.json:
        commander_chat_id = request.json.get("commander_chat_id")
        user_id = request.json.get("user_id")
        reason = request.json.get("reason")

        if commander_chat_id:
            commander_chat_id = int(commander_chat_id)
        if user_id:
            user_id = int(user_id)
        if reason:
            reason = str(reason)
    else:
        commander_chat_id = request.form.get("commander_chat_id", type=int)
        user_id = request.form.get("user_id", type=int)
        reason = request.form.get("reason", type=str)

    db.session.add(
        create_web_log(
            "del_book.request",
            {
                "book_id": book_id,
                "commander_chat_id": commander_chat_id,
                "user_id": user_id,
                "reason": reason,
            },
        )
    )
    db.session.commit()

    book = RoomBook.query.filter_by(id=book_id).first()
    if not book:
        return {"message": "No Book"}, 404

    flag_command_admin = False
    if commander_chat_id:
        try:
            flag_command_admin = (
                User.query.filter_by(chat_id=commander_chat_id).first().grade >= Grade.get("manager")
            )
        except:
            pass

    if flag_command_admin:
        pass
    else:
        now = dt.datetime.now(pytz.timezone("Asia/Seoul"))
        if book.book_date.date() < now.date():
            return {
                "message": "예약 삭제가 불가능합니다.\n사유: 취소 기한을 초과하였습니다.",
                "reason": "취소 기한을 초과하였습니다.",
            }, 403

        elif book.book_date.date() == now.date():
            if now.hour >= 4 and not get_client_name().startswith("Mozilla/5.0"):
                return {
                    "message": "예약 삭제가 불가능합니다.\n사유: 취소 기한을 초과하였습니다.",
                    "reason": "당일 예약은 취소 불가능합니다.",
                }, 403

    book.reason = reason
    log_type = "admin.book.delete" if flag_command_admin else "user.book.cancel"

    log = Log(
        chat_id=commander_chat_id,
        user_id=user_id,
        log_type=log_type,
    )
    log.extra_data = {
        "room_book_id": book_id,
        "reason": reason,
        "commander_chat_id": commander_chat_id,
        "flag_command_admin": flag_command_admin,
    }

    db.session.add(log)
    db.session.add(book)
    db.session.commit()

    return {
        "message": "삭제 성공",
    }


def _action_change_room(
    book: RoomBook, data: Dict[str, str]
) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    """방 변경 요청"""
    db.session.add(
        create_web_log(
            "action_change_room",
            {
                "book_id": book.id,
                "user_id": book.user_id,
                "room_type": data.get("room_type"),
                "room_no": data.get("room_no"),
            },
        )
    )
    db.session.commit()
    if "room_type" not in data or "room_no" not in data:
        return {"message": "Bad Request"}, 400
    room_type = int(data["room_type"])
    room_no = int(data["room_no"])
    room = Room.query.filter_by(type=room_type, no=room_no).first()

    original_room = Room.query.filter_by(id=book.room_id).first()

    try:
        raise_for_duplication(
            room.id, book.book_date.date(), book.start_time, book.end_time
        )

        book.room_id = room.id
        db.session.commit()

        user = User.query.filter_by(id=book.user_id).first()
        return {"message": "Change room", "room": room.publics_to_dict()}
    except ValueError:
        return {"message": "Can not change room"}, 400

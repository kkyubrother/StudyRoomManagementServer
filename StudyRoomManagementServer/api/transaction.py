import datetime as dt

from flask import (
    Blueprint,
    request,
    make_response,
)

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from StudyRoomManagementServer.util.utils import create_web_log
from .lib.book import get_client_name
from ..model import Transaction, User, Pay, db, SavedMoney, RoomBook, Message

bp = Blueprint("transaction", __name__, url_prefix="/api/transaction")

# CAT_ID = 2267950001
CAT_ID = Transaction.STUDY_CAT_ID
TYPE_NONE = Transaction.TYPE_NONE
TYPE_CARD_REQUEST = Transaction.TYPE_CARD_REQUEST
TYPE_CARD_FALLBACK_REQUEST = Transaction.TYPE_CARD_FALLBACK_REQUEST
TYPE_CARD_CANCEL_REQUEST = Transaction.TYPE_CARD_CANCEL_REQUEST

TYPE_READER_RESET = 400
TYPE_REQUEST_STOP = 401
TYPE_RESTART_NVCAT = 402
TYPE_JUST_BEFORE_TRANSACTION = 403
TYPE_CARD_BIN = 404

idx = 0


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_transaction():
    client_name = get_client_name()

    for transaction in Transaction.query.filter_by(
        response_original=None,
        client_name=client_name,
    ).all():
        if (transaction.created + dt.timedelta(seconds=30)) < dt.datetime.now():
            if (transaction.created + dt.timedelta(seconds=35)) < dt.datetime.now():
                _update_pay_timeout(transaction)
        else:
            response = make_response(transaction.publics_to_dict())
            response.headers["Cache-Control"] = "no-cache"

            db.session.add(create_web_log("get_transaction", transaction.publics_to_dict()))
            db.session.commit()

            return response

    else:
        db.session.commit()
        return {
            "type": TYPE_NONE,
        }


@bp.route("/all", methods=['GET'])
@check_user_from_cookie_authorization
def get_all_transactions():
    result = [
        t.publics_to_dict() for t in
        Transaction.query.all()
    ]
    return {
        "message": "ok",
        "transactions": result
    }


@bp.route("/<int:transaction_id>", methods=("GET",))
@check_user_from_cookie_authorization
def get_transaction_item(transaction_id: int):
    transaction = Transaction.query.filter_by(id=transaction_id).first()

    if transaction:
        response = make_response(transaction.publics_to_dict())
        response.headers["Cache-Control"] = "no-cache"

        db.session.add(create_web_log("get_transaction_item", transaction.publics_to_dict()))
        db.session.commit()

        return response

    else:
        return {
            "type": TYPE_NONE,
        }


@bp.route("", methods=("POST",))
@check_user_from_cookie_authorization
def post_transaction():
    transaction_id = request.form.get("transaction_id", type=int)
    transaction = Transaction.query.filter_by(id=transaction_id).first()

    db.session.add(create_web_log("post_transaction.begin", transaction.publics_to_dict()))
    db.session.commit()

    for k, v in request.form.items():
        if "transaction_id" == k:
            continue

        if not v:
            continue

        if hasattr(transaction, k):
            setattr(transaction, k, v)

    db.session.add(create_web_log("post_transaction.end", transaction.publics_to_dict()))
    db.session.commit()

    response_original = request.form.get("response_original", type=str)
    pay = Pay.query.filter_by(id=transaction.pay_id).first()
    if response_original is not None and response_original.startswith("[ERROR]"):
        pay.status = Pay.STATUS_REJECT
        pay.comment = "카드 결제 실패"

    elif "card.refund" in pay.pay_type:
        _update_card_refund(pay, transaction)
        db.session.add(create_web_log("transaction.card.refund.success", pay.publics_to_dict(), pay.user_id))

    else:
        _update_card_payment(pay, transaction)

    if str(pay.pay_type).startswith("donation.card") and pay.status == Pay.STATUS_CONFIRM:
        sm: SavedMoney = SavedMoney.query.filter_by(id=pay.saved_money_id).first()
        sm.money = sm.money + pay.paid
        db.session.add(sm)
        db.session.commit()

    db.session.add(create_web_log("post_transaction.pay", pay.publics_to_dict()))
    db.session.commit()

    db.session.add(pay)
    db.session.add(transaction)
    db.session.commit()
    return {
        "message": "ok",
        "transaction": transaction.publics_to_dict()
    }


def _update_pay_timeout(transaction: Transaction):
    """해당 결재는 시간 초과로 등록한다"""
    transaction.response_original = "[TIMEOUT] Local"
    pay = Pay.query.filter_by(id=transaction.pay_id).first()
    pay.status = Pay.STATUS_REJECT
    pay.comment = "결제 대기시간 초과"
    db.session.add(transaction)
    db.session.add(pay)
    db.session.commit()


def _update_card_payment(pay: Pay, transaction: Transaction):
    """카드 결제 처리"""
    if transaction.transaction_amount is None:
        pay.status = Pay.STATUS_REJECT
        pay.comment = "카드 결제 오류"

    elif pay.paid == transaction.money == int(transaction.transaction_amount):
        if transaction.response_code == '0000':
            pay.status = Pay.STATUS_CONFIRM
            pay.comment = "카드 결제 성공"

            user = User.query.filter_by(id=pay.user_id).first()
            db.session.add(Message(
                chat_id=user.chat_id,
                tg_name=user.username,
                user_id=user.id,
                data=f"{pay.id}",
                states=Message.STATE_RECEIPT_SEND,
            ))
        else:
            pay.status = Pay.STATUS_REJECT
            pay.comment = f"{transaction.response_message}".strip()
    else:
        pay.status = Pay.STATUS_REJECT
        pay.comment = "카드 결제 오류"
    db.session.add(pay)


def _update_card_refund(pay: Pay, transaction: Transaction):
    """카드 환불 처리"""
    if transaction.transaction_amount is None:
        pay.status = Pay.STATUS_REJECT
        pay.comment = "카드 환불 오류"

    else:
        pay.status = Pay.STATUS_CONFIRM
        pay.comment = "카드 환불 성공"

    book: RoomBook = RoomBook.query.filter_by(id=pay.book_id).first()
    book.status = RoomBook.STATUS_CANCELED
    db.session.add(book)
    db.session.add(pay)

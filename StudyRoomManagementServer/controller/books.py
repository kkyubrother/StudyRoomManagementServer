import datetime as dt
from typing import Optional

import pytz
from flask import request, Response
from werkzeug.wsgi import FileWrapper

# from .. import spreadsheet as sps
from StudyRoomManagementServer.api.books import remove_no_show, create_book_from_block
from StudyRoomManagementServer.constants import Grade
from StudyRoomManagementServer.error_handler import Forbidden, NotFound
from StudyRoomManagementServer.model import Room, RoomBook, User, db
from StudyRoomManagementServer.util.timetable import create_timetable
from StudyRoomManagementServer.util.utils import create_log


def get_book_timetable_img(date_string: str):
    remove_no_show()
    create_book_from_block()

    # return send_file("static/img/deleted2.png", mimetype="image/png")
    # block = [5, 6, 8, 10]
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

    # books = RoomBook.query.filter_by(book_date=date).all()

    books = RoomBook.query\
        .filter_by(book_date=dt.datetime(date.year, date.month, date.day), reason=None)\
        .filter(RoomBook.status != RoomBook.STATUS_CANCELED)\
        .all()
    # books: List[RoomBook] = RoomBook.query.filter_by(book_date=date).all()
    # books = [book for book in books if book.status != RoomBook.STATUS_CANCELED]

    f = FileWrapper(create_timetable(date_string, books, with_text))
    response = Response(f, mimetype="image/png", direct_passthrough=True)
    response.headers["Cache-Control"] = "no-cache"

    return response


def get_book_list(date_str: Optional[str] = None, user_id: Optional[int] = None):
    try:
        date = dt.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        date = None

    room_book_query = RoomBook.query
    if user_id:
        room_book_query = room_book_query.filter_by(user_id=user_id)

    if date:
        room_book_query = room_book_query.filter_by(book_date=dt.datetime(date.year, date.month, date.day))
    else:
        room_book_query = room_book_query.filter(
            RoomBook.book_date >= dt.datetime.now(tz=pytz.timezone("Asia/Seoul")).date()
        )

    rt = list()
    for room_book in room_book_query.all():
        room = Room.query.filter_by(id=room_book.room_id).first()
        if user_id:
            user = User.query.filter_by(id=user_id).first()
        else:
            user = User.query.filter_by(id=room_book.user_id).first()

        room_book = room_book.publics_to_dict()
        room_book["room"] = room.publics_to_dict()
        room_book["user"] = user.publics_to_dict()
        room_book["user"]["valid"] = user.valid
        del room_book["room_id"]
        del room_book["user_id"]
        del room_book["room"]["room_id"]
        del room_book["user"]["delete_que"]
        del room_book["user"]["tg_name"]
        del room_book["user"]["sms"]
        rt.append(room_book)

    return {"message": "조회 성공", "data": rt}


def delete_book(user_id: int, book_id: int, reason: str = ""):
    room_book: RoomBook = RoomBook.query.filter_by(id=book_id).filter_by(user_id=user_id).first()
    if not room_book:
        raise NotFound("예약 삭제가 불가능합니다.\n사유: 해당 예약을 찾을 수 없습니다.", f"book_id={book_id}")

    now = dt.datetime.now(pytz.timezone("Asia/Seoul"))

    if room_book.book_date.date() < now.date():
        raise NotFound("예약 삭제가 불가능합니다.\n사유: 취소 기한을 초과하였습니다.", f"book_id={book_id}")
    elif room_book.book_date.date() == now.date():
        if now.hour >= 4:
            raise Forbidden(
                "예약 삭제가 불가능합니다.\n사유: 당일 예약은 취소 불가능합니다.", f"book_id={book_id}"
            )

    elif room_book.status == 200 and reason == "timeout":
        raise Forbidden("예약 삭제가 불가능합니다.\n사유: 자동 취소 불가", f"book_id={book_id}")

    user = User.query.filter_by(id=room_book.user_id).one()

    log = create_log(
        user,
        None,
        "book.cancel",
        {
            "room_book_id": room_book.id,
            "room_book": str(room_book),
            "reason": reason,
        },
    )

    db.session.add(log)
    db.session.commit()

    room_book.reason = reason
    room_book.status = RoomBook.STATUS_CANCELED
    db.session.commit()

    return {
        "message": "삭제 성공",
    }


def delete_book_by_admin(user_id: int, book_id: int, admin_id: int, reason: str = ""):
    room_book: RoomBook = RoomBook.query.filter_by(id=book_id).filter_by(user_id=user_id).first()
    if not room_book:
        raise NotFound("예약 삭제가 불가능합니다.\n사유: 해당 예약을 찾을 수 없습니다.", f"book_id={book_id}")

    flag_command_admin = False
    try:
        flag_command_admin = (
            User.query.filter_by(chat_id=admin_id).one().grade
            >= Grade.admin
        )
    except Exception:
        pass

    if not flag_command_admin:
        raise Forbidden("권한 부족")

    user = User.query.filter_by(id=room_book.user_id).one()

    log = create_log(
        user,
        None,
        "admin.cancel",
        {
            "room_book_id": room_book.id,
            "room_book": str(room_book.publics_to_dict()),
            "reason": reason,
            "admin_id": admin_id,
        },
    )

    db.session.add(log)
    db.session.commit()

    room_book.reason = reason
    room_book.status = RoomBook.STATUS_CANCELED
    db.session.commit()

    return {
        "message": "삭제 성공",
    }


def get_book(book_id: int):
    room_book = RoomBook.query.filter_by(id=book_id).first()

    if not room_book:
        raise NotFound("해당 예약을 찾을 수 없습니다.", f"book_id={book_id}")

    room = Room.query.filter_by(id=room_book.room_id).first()
    user = User.query.filter_by(id=room_book.user_id).first()

    room_book = room_book.publics_to_dict()
    room_book["room"] = room.publics_to_dict()
    room_book["user"] = user.publics_to_dict()
    room_book["user"]["valid"] = user.valid
    del room_book["room_id"]
    del room_book["user_id"]
    del room_book["room"]["room_id"]
    del room_book["user"]["delete_que"]
    del room_book["user"]["tg_name"]
    del room_book["user"]["sms"]
    return room_book

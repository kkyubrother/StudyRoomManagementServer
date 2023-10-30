import datetime as dt
from typing import Tuple, Optional, NamedTuple, List

from flask import Blueprint, request

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from .lib.book import raise_for_duplication
from ..model import Room, RoomBook, db, Pay


class BlockBook(NamedTuple):
    room_type: int
    room_no: int
    block_purpose: str
    weekdays: Tuple[int, int, int, int, int, int, int]
    start_time_second: int
    end_time_second: int
    block_obj: str

    @property
    def start_time(self) -> dt.time:
        return dt.time(self.start_time_second // 60, self.start_time_second % 60)

    @property
    def end_time(self) -> dt.time:
        return dt.time(self.end_time_second // 60, self.end_time_second % 60)


BLOCK_LIST: List[BlockBook] = [
    BlockBook(1, 5, "근무자 전용", (1, 1, 1, 1, 1, 1, 1), 0, 1440, "근무자 전용"),
]


def _create_block_pay_row(user_id: int, book: RoomBook, cashier: str, pay_type: str, paid: int, comment: str):
    db.session.add(Pay(
        user_id=user_id,
        book_id=book.id,
        cashier=cashier,
        pay_type=pay_type,
        paid=paid,
        comment=comment,
        status=Pay.STATUS_CONFIRM
    ))
    db.session.commit()


def _create_block_book_row(d: dict) -> Optional[RoomBook]:
    """생성될시 True"""
    if not RoomBook.query.filter_by(**d).first():
        book = RoomBook(**d)
        db.session.add(book)
        db.session.commit()
        return book


def create_book_from_block():
    """예약 방지에서 예약 정보 구성"""
    status = 400
    people_no = 1
    user_id = 1
    cashier = "server.block"
    pay_type = "etc"
    paid = 0
    comment = "서버 자동 생성"
    now = dt.datetime.utcnow() + dt.timedelta(hours=9)

    d = {
        "status": status,
        "people_no": people_no,
        "user_id": user_id,
        "start_time_second": 0,
        "end_time_second": 23 * 60,
        "department": None,
        "purpose": "행사",
        "obj": "행사",
        "reason": None,
    }

    for i in range(31):
        date = (dt.datetime.now() + dt.timedelta(days=i)).date()

        for block in BLOCK_LIST:
            if not block.weekdays[date.weekday()]:
                continue

            room_id = Room.query.filter_by(type=block.room_type, no=block.room_no).first().id
            end_time_second = block.end_time_second if block.end_time_second != 1440 else block.end_time_second
            d['room_id'] = room_id
            d['start_time_second'] = block.start_time_second
            d['end_time_second'] = end_time_second
            d['purpose'] = block.block_purpose
            d['obj'] = block.block_obj

            d["book_date"] = date
            book = _create_block_book_row(d)
            if book:
                _create_block_pay_row(user_id, book, cashier, pay_type, paid, comment)

    db.session.commit()


bp = Blueprint("room", __name__, url_prefix="/api/rooms")
BLOCK_ROOM = {
    "always": [
        {"type": 1, "no": 5, "reason": "근무자 전용"},
        {"type": 1, "no": 6, "reason": "사용 불가"},
        {"type": 1, "no": 8, "reason": "사용 불가"},
    ],
    "weekdays": {
        0: [],  # Monday
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
    },
}


def is_room_available(
        room_type: int, room_no: int, date: dt.date
) -> Tuple[bool, Optional[str]]:
    for always_block_room in BLOCK_ROOM["always"]:
        if (
                room_type == always_block_room["type"]
                and room_no == always_block_room["no"]
        ):
            return False, always_block_room["reason"]

    for weekday_block_room in BLOCK_ROOM["weekdays"][date.weekday()]:
        if (
                room_type == weekday_block_room["type"]
                and room_no == weekday_block_room["no"]
        ):
            return False, weekday_block_room["reason"]

    return True, None


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_rooms():
    try:
        date = dt.date.fromisoformat(request.args.get("date", type=str))
    except (TypeError, ValueError):
        return {"message": "Not iso format", "reason": "Not iso format"}, 400
    q = Room.query
    rooms = []
    try:
        if "start_time" in request.args and "end_time" in request.args:
            start_time = dt.time.fromisoformat(request.args.get("start_time", type=str))
            end_time = dt.time.fromisoformat(request.args.get("end_time", type=str))

            for room in Room.query.all():
                try:
                    raise_for_duplication(room.id, date, start_time, end_time)
                    rooms.append(room.publics_to_dict())
                except Exception as e:
                    print(e)
                    continue
        else:
            rooms = [r.publics_to_dict() for r in q.all()]
    except Exception as e:
        print(e)
        return {"message": "Not iso format", "reason": "Not iso format"}, 400

    for room in rooms:
        room["available"], room["reason"] = is_room_available(
            room["type"], room["no"], date
        )

    return {"message": "ok", "rooms": rooms}


@bp.route("", methods=("POST",))
@check_user_from_cookie_authorization
def post_room():
    """룸 등록"""
    name = request.json.get("name")
    type_ = request.json.get("type")
    no = request.json.get("no")

    if not name or not type_ or not no:
        return {"message": "Bad Request"}, 400

    room = Room(name=name, type=type_, no=no)
    db.session.add(room)
    db.session.commit()

    return {"message": "create new room", "room": room.publics_to_dict()}

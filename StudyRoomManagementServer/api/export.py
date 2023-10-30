import datetime as dt
from collections import defaultdict
from io import BytesIO
from typing import Tuple, Union, List, Any

from flask import (
    Blueprint,
    request,
    send_file,
)
from openpyxl import Workbook
from werkzeug.datastructures import ImmutableMultiDict

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization, get_user_from_cookie_authorization
from ..model import Log, db, RoomBook, User, Room, Pay, SavedMoney

bp = Blueprint("exports", __name__, url_prefix="/api/exports")


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
# @need_authorization
def get_exports():
    user = get_user_from_cookie_authorization()
    print("get_export", user)
    s = dt.datetime.now()
    category = request.args.get("category", type=str)
    data = []
    if category == "log.auth":
        data.extend(_export_log_auth(request.args))
    elif category == "user.all":
        pass
    elif category == "user.grade.vip":
        data.extend(_export_log_user(request.args, types="grade.vip"))
    elif category == "user.created":
        pass
    elif category == "user.latest_auth":
        pass
    elif category == "user.invalid":
        pass
    elif category == "log.all":
        pass
    elif category == "log.tg":
        pass
    elif category == "log.error":
        pass
    elif category == "log.study.usage":
        data.extend(_export_log_study(request.args))
    elif category == "log.study.usage.only_success":
        data.extend(_export_log_study(request.args, types="success"))
    elif category == "log.donation":
        data.extend(_export_log_donation(request.args))
    elif category == "log.donation.only_success":
        data.extend(_export_log_donation(request.args, types="success"))

    e = dt.datetime.now()
    print(e - s)
    if data:
        return _export_xlsx(data, category)
    return {"message": "올바르지 않은 요청입니다."}, 400


def _export_log_user(data: ImmutableMultiDict, types: str = "all") -> List[Tuple[str, Union[str, int]]]:
    """사용자 출력"""
    temp_data = []
    if types == "grade.vip":
        users: list[User] = User.query.filter_by(grade=10).all()
        temp_data.append(["사용자 ID", "사용자 이름", "전화번호"])
        temp_data.extend([(u.id, u.username, u.num,) for u in users])
    return temp_data


def _export_log_donation(data: ImmutableMultiDict, types: str = "all") -> List[Tuple[str, Union[str, int]]]:
    start_date = data.get("start_date", type=str)
    end_date = data.get("end_date", type=str)
    column = ["후원 ID", "후원 일자", "시간", "후원자 이름", "전화번호", "후원자 지역", "후원 방법", "후원 금액", "상태", "기타"]

    pays = Pay.query.filter(Pay.pay_type.like("donation%"))\
        .filter(db.and_(db.func.date(Pay.created) >= start_date, db.func.date(Pay.created) <= end_date))

    if "all" in types:
        pass
    elif "success" in types:
        pays = pays.filter(Pay.status==Pay.STATUS_CONFIRM)

    pays = [pay.publics_to_dict() for pay in pays.all()]

    temp_data = defaultdict(list)
    for pay in pays:
        u: User = User.query.filter_by(id=pay["user_id"]).first()
        sm: SavedMoney = SavedMoney.query.filter_by(id=pay["saved_money_id"]).first()

        data = [
            *(dt.datetime.fromisoformat(pay["created"]) + dt.timedelta(hours=9)).isoformat().split('T'),
            u.username,
            u.num,
            sm.name if sm else "--정보없음--",
            pay["pay_type_str"] if pay is not None else "정보없음",
            pay["paid"],
            pay["status_str"],
            pay["comment"],
        ]
        temp_data[pay["pay_id"]] = data

    keys = sorted(temp_data.keys(), key=lambda k: temp_data[k][0])

    return [column] + [(k, *temp_data[k]) for k in keys]


def _export_log_auth(data: ImmutableMultiDict) -> List[Tuple[str, Union[str, int]]]:
    start_date = data.get("start_date", type=str)
    end_date = data.get("end_date", type=str)
    column = ["날짜", "인증 횟수"]

    logs = Log.query.filter(db.and_(db.func.date(Log.created) >= start_date,
                                    db.func.date(Log.created) <= end_date))

    temp_auth_qr = defaultdict(set)
    for log in logs.all():
        temp_auth_qr[log.created.date().isoformat()].add(log.user_id)

    rt = [column] + [(k, len(v),) for k, v in temp_auth_qr.items()]
    return rt


def _export_log_study(data: ImmutableMultiDict, types: str = "all") -> List[Tuple[str, Union[str, int]]]:
    start_date = data.get("start_date", type=str)
    end_date = data.get("end_date", type=str)
    column = ["예약 ID", "사용자 이름", "사용인원", "방이름", "일자", "입장 시간", "퇴실 시간", "결제 수단", "결제 지역", "기타"]

    books = RoomBook.query\
        .filter(db.and_(db.func.date(RoomBook.book_date) >= start_date, db.func.date(RoomBook.book_date) <= end_date))

    if "all" in types:
        pass
    elif "success" in types:
        books = books.filter(RoomBook.reason == db.null())

    temp_data = defaultdict(list)
    for book in books.all():
        book: RoomBook
        username = User.query.filter_by(id=book.user_id).with_entities(User.username).first()[0]
        room_name = Room.query.filter_by(id=book.room_id).with_entities(Room.name).first()[0]
        p: Pay = Pay.query.filter_by(book_id=book.id).first()

        data = [
            book.id,
            username,
            book.people_no,
            room_name,
            book.book_date.date().isoformat(),
            book.start_time.isoformat(),
            book.end_time.isoformat(),
            p.pay_type_str if p is not None else "정보없음",
            book.department,
            book.reason,
        ]
        temp_data[book.id] = data
    keys = sorted(temp_data.keys(), key=lambda k: temp_data[k][4]+temp_data[k][5])

    rt = [column] + [temp_data[k] for k in keys]
    return rt


def _export_xlsx(data: List[Union[List[str], Tuple[str, int]]], filename: str = "export") -> Any:
    wb = Workbook()
    ws = wb.active
    [ws.append(d) for d in data]

    excel_stream = BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    try:
        return send_file(
            excel_stream,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=f"{filename}.xlsx",
            as_attachment=True,
            max_age=0
        )
    except Exception as e:
        print(e)
        return send_file(
            excel_stream,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            attachment_filename=f"{filename}.xlsx",
            as_attachment=True,
            cache_timeout=0
        )


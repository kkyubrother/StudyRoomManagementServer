import datetime as dt
from string import ascii_uppercase
from typing import Tuple

import gspread
from flask import Flask
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
JSON_CREDENTIAL_FILE_NAME = ""
CREDENTIALS = None
GOOGLE_CLIENT = None
SPREADSHEET_URL = ""
BOOK_SHEETLINK = ""
DOC: gspread.Spreadsheet = None
VIEW_DOC: gspread.Spreadsheet = None

COLOR_BOOK = {"red": 0.8117, "green": 0.8863, "blue": 0.9529}
COLOR_EVENT = {
    "red": 0.9569,
    "green": 0.8,
    "blue": 0.8,
}
COLOR_INTER_CLASS = {
    "red": 1.0,
    "green": 0.9490,
    "blue": 0.8,
}
COLOR_FIELD = {
    "red": 0.8510,
    "green": 0.9176,
    "blue": 0.8275,
}
COLOR_TEMP = {"red": 0.8510, "green": 0.8235, "blue": 0.9137}
COLOR_GRAY = {"red": 0.851, "green": 0.851, "blue": 0.851}
COLOR_WHITE = {
    "red": 1.0,
    "green": 1.0,
    "blue": 1.0,
}


class UserData:
    NORMAL_BOOK = "book"
    EVENT_BOOK = "event"
    INNER_CLASS_BOOK = "inner"
    TEMP_BOOK = "temp"

    def __init__(self, name: str, people_no: int, type: str):
        """예약자 데이터를 설정한다"""
        assert name, "이름이 없습니다"
        assert people_no, "사용 인원이 없습니다"
        assert type and type in (
            self.NORMAL_BOOK,
            self.EVENT_BOOK,
            self.INNER_CLASS_BOOK,
            self.TEMP_BOOK,
        ), "올바르지 않은 예약 타입입니다"

        self.name = name
        self.people_no = people_no
        self.type = type


class BookData:
    def __init__(
        self, date: dt.date, start: dt.time, end: dt.time, room: int, userdata: UserData
    ):
        """예약 데이터를 설정한다"""
        assert date, "날짜가 없습니다"
        assert start, "시작 시간이 없습니다"
        assert end, "마침 시간이 없습니다"
        assert room, "방 번호가 없습니다"
        assert start < end, "시간이 잘못되었습니다"
        assert start.hour >= 9 and end.hour <= 22, "시간을 초과하였습니다"
        assert userdata, "사용자 데이터가 없습니다"

        self.date = date
        self.start = start
        self.end = end
        self.room = room
        self.userdata = userdata


def get_or_create_worksheet(target_sheet_name: str) -> gspread.Worksheet:
    """시트를 가져오거나, 없으면 복제 후 가져온다"""
    try:
        worksheet = DOC.worksheet(target_sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = DOC.duplicate_sheet(
            source_sheet_id=DOC.worksheet("예약기본v2").id,
            insert_sheet_index=None,
            new_sheet_id=None,
            new_sheet_name=target_sheet_name,
        )
    return worksheet


def get_or_create_view_worksheet(target_sheet_name: str) -> gspread.Worksheet:
    """뷰를 위한 시트를 생성하거나 가져온다."""
    try:
        worksheet = VIEW_DOC.worksheet(target_sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = VIEW_DOC.duplicate_sheet(
            source_sheet_id=VIEW_DOC.worksheet("예약기본").id,
            insert_sheet_index=None,
            new_sheet_id=None,
            new_sheet_name=target_sheet_name,
        )
    return worksheet


def update_cell_color(worksheet: gspread.Worksheet, address: str, user: UserData):
    color = None
    if user.type == UserData.NORMAL_BOOK:
        color = COLOR_BOOK
    elif user.type == UserData.EVENT_BOOK:
        color = COLOR_EVENT
    elif user.type == UserData.INNER_CLASS_BOOK:
        color = COLOR_INTER_CLASS
    elif user.type == UserData.TEMP_BOOK:
        color = COLOR_TEMP
    else:
        raise ValueError("알 수 없는 타입입니다")
    worksheet.format(address, {"backgroundColor": color})


def get_row_no(book: BookData) -> Tuple[int, int]:
    """시작과 끝 행 번호 가져오기"""
    first_row = (book.start.hour - 9) * 2 + 4
    last_row = (book.end.hour - 9) * 2 + 4

    if book.start.minute >= 30:
        first_row += 1

    if book.end.minute == 0:
        last_row -= 1

    elif book.end.minute > 30:
        last_row += 1

    return (
        first_row,
        last_row,
    )


def get_column_letter(book: BookData) -> str:
    """방 번호에 따른 열 가져오기"""
    # 1번방==3==c
    if book.room == 101:  # seminar
        column = 13
    elif book.room == 201:  # studio
        column = 14
    elif 1 <= book.room <= 10:
        column = 2 + book.room
    else:
        raise ValueError("룸 정보가 올바르지 않습니다")
    return ascii_uppercase[column - 1]


def del_book(book: BookData):
    target_sheet_name = f"{book.date.month:0>2}/{book.date.day:0>2}"
    worksheet = get_or_create_worksheet(target_sheet_name)

    column_letter = get_column_letter(book)
    first_row, last_row = get_row_no(book)

    if last_row - first_row == 0:
        address = f"{column_letter}{first_row}"
        txt = ""
    else:
        address = f"{column_letter}{first_row}:{column_letter}{last_row}"
        txt = [[""] for _ in range(first_row, last_row + 1)]
    worksheet.update(address, txt)

    worksheet.format(address, {"backgroundColor": COLOR_WHITE})
    get_or_create_view_worksheet(target_sheet_name).format(
        address, {"backgroundColor": COLOR_WHITE}
    )


def add_book(book: BookData):
    """예약을 추가합니다"""
    target_sheet_name = f"{book.date.month:0>2}/{book.date.day:0>2}"
    worksheet = get_or_create_worksheet(target_sheet_name)

    column_letter = get_column_letter(book)
    first_row, last_row = get_row_no(book)

    user = book.userdata
    txt_username = f"{user.name}"
    txt_people_no = f"{user.people_no}명"
    usage_hour = (book.end.hour - book.start.hour) + (
        (book.end.minute - book.start.minute) / 60
    )
    txt_usage_hour = f"{usage_hour}시간"

    if last_row - first_row == 0:
        address = f"{column_letter}{first_row}"
        txt = f"{txt_username}, {txt_people_no}, {txt_usage_hour}"

    elif last_row - first_row == 1:
        address = f"{column_letter}{first_row}:{column_letter}{last_row}"
        txt = [[f"{txt_username}"], [f"{txt_people_no}, {txt_usage_hour}"]]
        worksheet.update(address, txt)

    else:
        address = f"{column_letter}{first_row}:{column_letter}{last_row}"
        txt = [[f"{txt_username}"], [f"{txt_people_no}"], [f"{txt_usage_hour}"]]

    worksheet.update(address, txt)
    update_cell_color(worksheet, address, user)

    update_cell_color(get_or_create_view_worksheet(target_sheet_name), address, user)


def init_app(app: Flask):
    global JSON_CREDENTIAL_FILE_NAME
    global CREDENTIALS
    global GOOGLE_CLIENT
    global SPREADSHEET_URL
    global BOOK_SHEETLINK
    global DOC
    global VIEW_DOC

    JSON_CREDENTIAL_FILE_NAME = app.config.get("GOOGLE_JSON_CREDENTIAL_FILE_NAME")
    CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(
        JSON_CREDENTIAL_FILE_NAME, SCOPE
    )
    GOOGLE_CLIENT = gspread.authorize(CREDENTIALS)
    SPREADSHEET_URL = app.config.get("SPREADSHEET_URL")
    BOOK_SHEETLINK = app.config.get("BOOK_SHEETLINK")

    # 스프레스시트 문서 가져오기
    DOC = GOOGLE_CLIENT.open_by_url(SPREADSHEET_URL)
    VIEW_DOC = GOOGLE_CLIENT.open_by_url(BOOK_SHEETLINK)

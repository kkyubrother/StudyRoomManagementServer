import datetime
import json
import os
from typing import Union, Set, Dict, List, Any, Tuple

from flask import Flask, g


def trans_str_to_time(data: Union[str, datetime.time]) -> datetime.time:
    try:
        if isinstance(data, str):
            return datetime.time.fromisoformat(data)
        return data
    except (ValueError, TypeError):
        return data


def trans_str_to_datetime(data: Union[str, datetime.datetime]) -> datetime.datetime:
    try:
        if isinstance(data, str):
            return datetime.datetime.fromisoformat(data)
        return data
    except (ValueError, TypeError):
        return data


class ConfigEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, (datetime.date, datetime.time, datetime.datetime,)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class Config:
    __data: dict
    __path: str

    def __init__(self, path: str):
        self.__data = {}
        self.__path = path
        self.load()

    def save(self):
        with open(self.__path, 'w') as f:
            json.dump(self.__data, f, ensure_ascii=False, indent=2, cls=ConfigEncoder)

    def load(self):
        if os.path.isfile(self.__path):
            with open(self.__path) as f:
                try:
                    self.__data = json.load(f)
                except:
                    pass

    @property
    def tg_developer_id(self) -> Set[int]:
        res = self.__data.get('tg_developer_id', set())
        if not isinstance(res, set):
            self.tg_developer_id = res
        return self.__data.get('tg_developer_id', set())

    @tg_developer_id.setter
    def tg_developer_id(self, tg_developer_id: Union[List[Union[int, str]], Set[Union[int, str]]]):
        assert isinstance(tg_developer_id, (list, set,))
        assert (set([isinstance(i, (int, str)) for i in tg_developer_id]) - {True}) == set()
        self.__data['tg_developer_id'] = set(tg_developer_id)

    @property
    def tg_manager_group_id(self) -> int:
        res = self.__data.get('tg_manager_group_id', -1)
        if not isinstance(res, int):
            self.tg_manager_group_id = res
        return self.__data.get('tg_manager_group_id', -1)

    @tg_manager_group_id.setter
    def tg_manager_group_id(self, tg_manager_group_id: int):
        assert isinstance(tg_manager_group_id, int)
        self.__data['tg_manager_group_id'] = tg_manager_group_id

    @property
    def notice_send_time(self) -> datetime.time:
        res = self.__data.get('notice_send_time', datetime.time(3))
        if not isinstance(res, datetime.time):
            self.notice_send_time = res
        return self.__data.get('notice_send_time', datetime.time(3))

    @notice_send_time.setter
    def notice_send_time(self, notice_send_time: datetime.time):
        notice_send_time = trans_str_to_time(notice_send_time)
        assert isinstance(notice_send_time, datetime.time)
        self.__data['notice_send_time'] = notice_send_time

    @property
    def cafe_is_close(self) -> bool:
        res = self.__data.get('cafe_is_close', False)
        if not isinstance(res, bool):
            self.cafe_is_close = res
        return self.__data.get('cafe_is_close', False)

    @cafe_is_close.setter
    def cafe_is_close(self, is_close: bool):
        assert isinstance(is_close, bool)
        self.__data['cafe_is_close'] = is_close

    @property
    def cafe_close_date(self) -> Set[datetime.date]:
        res = self.__data.get('cafe_close_date', set())
        if not isinstance(res, set):
            self.cafe_close_date = res
        return self.__data.get('cafe_close_date', set())

    @cafe_close_date.setter
    def cafe_close_date(self, cafe_close_date: Union[List[datetime.date], Set[datetime.date]]):
        assert isinstance(cafe_close_date, (list, set))
        cafe_close_date = [trans_str_to_datetime(d).date() for d in cafe_close_date]
        self.__data['cafe_close_date'] = set(cafe_close_date)

    @property
    def cafe_weekdays_open(self) -> datetime.time:
        res = self.__data.get('cafe_weekdays_open', datetime.time(11, 30))
        if not isinstance(res, datetime.time):
            self.cafe_weekdays_open = res
        return self.__data.get('cafe_weekdays_open', datetime.time(11, 30))

    @cafe_weekdays_open.setter
    def cafe_weekdays_open(self, weekdays_open: datetime.time):
        weekdays_open = trans_str_to_time(weekdays_open)
        assert isinstance(weekdays_open, datetime.time)
        self.__data['cafe_weekdays_open'] = weekdays_open

    @property
    def cafe_weekdays_close(self) -> datetime.time:
        res = self.__data.get('cafe_weekdays_close', datetime.time(22))
        if not isinstance(res, datetime.time):
            self.cafe_weekdays_close = res
        return self.__data.get('cafe_weekdays_close', datetime.time(22))

    @cafe_weekdays_close.setter
    def cafe_weekdays_close(self, weekdays_close: datetime.time):
        weekdays_close = trans_str_to_time(weekdays_close)
        assert isinstance(weekdays_close, datetime.time)
        self.__data['cafe_weekdays_close'] = weekdays_close

    @property
    def cafe_weekend_open(self) -> datetime.time:
        res = self.__data.get('cafe_weekend_open', datetime.time(11, 30))
        if not isinstance(res, datetime.time):
            self.cafe_weekend_open = res
        return self.__data.get('cafe_weekend_open', datetime.time(11, 30))

    @cafe_weekend_open.setter
    def cafe_weekend_open(self, weekend_open: datetime.time):
        weekend_open = trans_str_to_time(weekend_open)
        assert isinstance(weekend_open, datetime.time)
        self.__data['cafe_weekend_open'] = weekend_open

    @property
    def cafe_weekend_close(self) -> datetime.time:
        res = self.__data.get('cafe_weekend_close', datetime.time(22))
        if not isinstance(res, datetime.time):
            self.cafe_weekend_close = res
        return self.__data.get('cafe_weekend_close', datetime.time(22))

    @cafe_weekend_close.setter
    def cafe_weekend_close(self, weekend_close: datetime.time):
        weekend_close = trans_str_to_time(weekend_close)
        assert isinstance(weekend_close, datetime.time)
        self.__data['cafe_weekend_close'] = weekend_close

    @property
    def room(self) -> List[Dict[str, Union[int, str]]]:
        return self.__data.get('room', [
            {
                "name": "스터디룸 1번방",
                "type": 1,
                "no": 1,
            },
            {
                "name": "스터디룸 2번방",
                "type": 1,
                "no": 2,
            },
            {
                "name": "스터디룸 3번방",
                "type": 1,
                "no": 3,
            },
            {
                "name": "스터디룸 4번방",
                "type": 1,
                "no": 4,
            },
            {
                "name": "스터디룸 5번방",
                "type": 1,
                "no": 5,
            },
            {
                "name": "스터디룸 6번방",
                "type": 1,
                "no": 6,
            },
            {
                "name": "스터디룸 7번방",
                "type": 1,
                "no": 7,
            },
            {
                "name": "스터디룸 8번방",
                "type": 1,
                "no": 8,
            },
            {
                "name": "스터디룸 9번방",
                "type": 1,
                "no": 9,
            },
            {
                "name": "스터디룸 10번방",
                "type": 1,
                "no": 10,
            },
        ])

    @property
    def book_room_limit_time(self) -> datetime.time:
        res = self.__data.get('book_room_limit_time', datetime.time(4))
        if not isinstance(res, datetime.time):
            self.book_room_limit_time = res
        return self.__data.get('book_room_limit_time', datetime.time(4))

    @book_room_limit_time.setter
    def book_room_limit_time(self, limit: datetime.time):
        limit = trans_str_to_time(limit)
        assert isinstance(limit, datetime.time)
        self.__data['book_room_limit_time'] = limit

    @property
    def book_room_weekdays_open(self) -> datetime.time:
        res = self.__data.get('book_room_weekdays_open', self.cafe_weekdays_open)
        if not isinstance(res, datetime.time):
            self.book_room_weekdays_open = res
        return self.__data.get('book_room_weekdays_open', self.cafe_weekdays_open)

    @property
    def book_room_weekdays_close(self) -> datetime.time:
        res = self.__data.get('book_room_weekdays_close', self.cafe_weekdays_close)
        if not isinstance(res, datetime.time):
            self.book_room_weekdays_close = res
        return self.__data.get('book_room_weekdays_close', self.cafe_weekdays_close)

    @property
    def book_room_weekend_open(self) -> datetime.time:
        res = self.__data.get('book_room_weekend_open', self.cafe_weekend_open)
        if not isinstance(res, datetime.time):
            self.book_room_weekend_open = res
        return self.__data.get('book_room_weekend_open', self.cafe_weekend_open)

    @property
    def book_room_weekend_close(self) -> datetime.time:
        res = self.__data.get('book_room_weekend_close', self.cafe_weekend_close)
        if not isinstance(res, datetime.time):
            self.book_room_weekend_close = res
        return self.__data.get('book_room_weekend_close', self.cafe_weekend_close)

    @book_room_weekdays_open.setter
    def book_room_weekdays_open(self, weekdays_open: datetime.time):
        weekdays_open = trans_str_to_time(weekdays_open)
        assert isinstance(weekdays_open, datetime.time)
        self.__data['book_room_weekdays_open'] = weekdays_open

    @book_room_weekdays_close.setter
    def book_room_weekdays_close(self, weekdays_close: datetime.time):
        weekdays_close = trans_str_to_time(weekdays_close)
        assert isinstance(weekdays_close, datetime.time)
        self.__data['book_room_weekdays_close'] = weekdays_close

    @book_room_weekend_open.setter
    def book_room_weekend_open(self, weekend_open: datetime.time):
        weekend_open = trans_str_to_time(weekend_open)
        assert isinstance(weekend_open, datetime.time)
        self.__data['book_room_weekend_open'] = weekend_open

    @book_room_weekend_close.setter
    def book_room_weekend_close(self, weekdays_close: datetime.time):
        weekdays_close = trans_str_to_time(weekdays_close)
        assert isinstance(weekdays_close, datetime.time)
        self.__data['book_room_weekend_close'] = weekdays_close

    @property
    def book_room_study_people_no_max(self) -> int:
        return self.__data.get('book_room_study_people_no_max', 4)

    @book_room_study_people_no_max.setter
    def book_room_study_people_no_max(self, people_no: int):
        assert isinstance(people_no, int)
        assert people_no > 0
        self.__data['book_room_study_people_no_max'] = people_no

    @property
    def book_room_study_people_no_min(self) -> int:
        return self.__data.get('book_room_study_people_no_min', 1)

    @book_room_study_people_no_min.setter
    def book_room_study_people_no_min(self, people_no: int):
        assert isinstance(people_no, int)
        assert people_no > 0
        self.__data['book_room_study_people_no_min'] = people_no

    @property
    def book_room_seminar_people_no_max(self) -> int:
        return self.__data.get('book_room_seminar_people_no_max', 10)

    @book_room_seminar_people_no_max.setter
    def book_room_seminar_people_no_max(self, people_no: int):
        assert isinstance(people_no, int)
        assert people_no > 0
        self.__data['book_room_seminar_people_no_max'] = people_no

    @property
    def book_room_seminar_people_no_min(self) -> int:
        return self.__data.get('book_room_seminar_people_no_min', 1)

    @book_room_seminar_people_no_min.setter
    def book_room_seminar_people_no_min(self, people_no: int):
        assert isinstance(people_no, int)
        assert people_no > 0
        self.__data['book_room_seminar_people_no_min'] = people_no

    @property
    def google_spreadsheet_admin_url(self) -> str:
        return self.__data.get('google_spreadsheet_admin_url', '')

    @google_spreadsheet_admin_url.setter
    def google_spreadsheet_admin_url(self, url: str):
        assert isinstance(url, str)
        self.__data['google_spreadsheet_admin_url'] = url

    @property
    def google_spreadsheet_guest_url(self) -> str:
        return self.__data.get('google_spreadsheet_guest_url', '')

    @google_spreadsheet_guest_url.setter
    def google_spreadsheet_guest_url(self, url: str):
        assert isinstance(url, str)
        self.__data['google_spreadsheet_guest_url'] = url

    @property
    def google_spreadsheet_pay_url(self) -> str:
        return self.__data.get('google_spreadsheet_pay_url', '')

    @google_spreadsheet_pay_url.setter
    def google_spreadsheet_pay_url(self, url: str):
        assert isinstance(url, str)
        self.__data['google_spreadsheet_pay_url'] = url

    @property
    def google_spreadsheet_pay_record_url(self) -> str:
        return self.__data.get('google_spreadsheet_pay_record_url', '')

    @google_spreadsheet_pay_record_url.setter
    def google_spreadsheet_pay_record_url(self, url: str):
        assert isinstance(url, str)
        self.__data['google_spreadsheet_pay_record_url'] = url

    @property
    def google_form_pay_url(self) -> str:
        return self.__data.get('google_form_pay_url', '')

    @google_form_pay_url.setter
    def google_form_pay_url(self, url: str):
        assert isinstance(url, str)
        self.__data['google_form_pay_url'] = url

    @property
    def sms_id(self) -> str:
        return self.__data.get('sms_id', '')

    @sms_id.setter
    def sms_id(self, sms_id: str):
        assert isinstance(sms_id, str)
        self.__data['sms_id'] = sms_id

    @property
    def sms_token(self) -> str:
        return self.__data.get('sms_token', '')

    @sms_token.setter
    def sms_token(self, sms_token: str):
        assert isinstance(sms_token, str)
        self.__data['sms_token'] = sms_token

    @property
    def sms_num(self) -> str:
        return self.__data.get('sms_num', '')

    @sms_num.setter
    def sms_num(self, sms_num: str):
        assert isinstance(sms_num, str)
        self.__data['sms_num'] = sms_num

    @property
    def user_membership_normal_file(self) -> str:
        return self.__data.get('user_membership_normal_file')

    @user_membership_normal_file.setter
    def user_membership_normal_file(self, user_membership_normal_file: str):
        assert isinstance(user_membership_normal_file, str)
        self.__data['user_membership_normal_file'] = user_membership_normal_file

    @property
    def user_membership_vip_file(self) -> str:
        return self.__data.get('user_membership_vip_file')

    @user_membership_vip_file.setter
    def user_membership_vip_file(self, user_membership_vip_file: str):
        assert isinstance(user_membership_vip_file, str)
        self.__data['user_membership_vip_file'] = user_membership_vip_file

    @property
    def user_membership_normal_qr_box(self) -> Tuple[int, int, int, int]:
        return tuple(self.__data.get('user_membership_normal_qr_box', (153, 268, 645, 760,)))

    @user_membership_normal_qr_box.setter
    def user_membership_normal_qr_box(self, user_membership_normal_qr_box: Tuple[int, int, int, int]):
        assert isinstance(user_membership_normal_qr_box, tuple)
        assert len(user_membership_normal_qr_box) == 4
        assert isinstance(user_membership_normal_qr_box[0], int)
        assert isinstance(user_membership_normal_qr_box[1], int)
        assert isinstance(user_membership_normal_qr_box[2], int)
        assert isinstance(user_membership_normal_qr_box[3], int)
        self.__data['user_membership_normal_qr_box'] = list(user_membership_normal_qr_box)

    @property
    def user_membership_vip_qr_box(self) -> Tuple[int, int, int, int]:
        return tuple(self.__data.get('user_membership_vip_qr_box', (153, 262, 644, 753,)))

    @user_membership_vip_qr_box.setter
    def user_membership_vip_qr_box(self, user_membership_vip_qr_box: Tuple[int, int, int, int]):
        assert isinstance(user_membership_vip_qr_box, tuple)
        assert len(user_membership_vip_qr_box) == 4
        assert isinstance(user_membership_vip_qr_box[0], int)
        assert isinstance(user_membership_vip_qr_box[1], int)
        assert isinstance(user_membership_vip_qr_box[2], int)
        assert isinstance(user_membership_vip_qr_box[3], int)
        self.__data['user_membership_vip_qr_box'] = list(user_membership_vip_qr_box)

    @property
    def user_membership_normal_text_box(self) -> Tuple[int, int]:
        return tuple(self.__data.get('user_membership_normal_text_box', (645, 845,)))

    @user_membership_normal_text_box.setter
    def user_membership_normal_text_box(self, user_membership_normal_text_box: Tuple[int, int]):
        assert isinstance(user_membership_normal_text_box, tuple), f"{user_membership_normal_text_box}"
        assert len(user_membership_normal_text_box) == 2, f"{user_membership_normal_text_box}"
        assert isinstance(user_membership_normal_text_box[0], int), f"{user_membership_normal_text_box}"
        assert isinstance(user_membership_normal_text_box[1], int), f"{user_membership_normal_text_box}"
        self.__data['user_membership_normal_text_box'] = list(user_membership_normal_text_box)

    @property
    def user_membership_vip_text_box(self) -> Tuple[int, int]:
        return tuple(self.__data.get('user_membership_vip_text_box', (634, 846,)))

    @user_membership_vip_text_box.setter
    def user_membership_vip_text_box(self, user_membership_vip_text_box: Tuple[int, int]):
        assert isinstance(user_membership_vip_text_box, tuple), f"{user_membership_vip_text_box}"
        assert len(user_membership_vip_text_box) == 2, f"{user_membership_vip_text_box}"
        assert isinstance(user_membership_vip_text_box[0], int), f"{user_membership_vip_text_box}"
        assert isinstance(user_membership_vip_text_box[1], int), f"{user_membership_vip_text_box}"
        self.__data['user_membership_vip_text_box'] = list(user_membership_vip_text_box)

    @property
    def cafe_open_time_text(self) -> str:
        return self.__data.get("cafe_open_time_text", "00:00")

    @cafe_open_time_text.setter
    def cafe_open_time_text(self, cafe_open_time_text: str):
        assert isinstance(cafe_open_time_text, str), f"{cafe_open_time_text}"
        self.__data["cafe_open_time_text"] = cafe_open_time_text

    @property
    def cafe_close_time_text(self) -> str:
        return self.__data.get("cafe_close_time_text", "00:00")

    @cafe_close_time_text.setter
    def cafe_close_time_text(self, cafe_close_time_text: str):
        assert isinstance(cafe_close_time_text, str), f"{cafe_close_time_text}"
        self.__data["cafe_close_time_text"] = cafe_close_time_text


config: Config


def init_app(app: Flask):
    global config
    config = Config(app.config.get('CONFIG_PATH'))


def get_config() -> Config:
    if 'config' not in g:
        g.config = config

    return g.config

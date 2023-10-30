import datetime as dt
import json
from enum import auto

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.ext.hybrid import hybrid_property

from .constants.message_state import MessageState
from .security import dec_v1, enc_v1
from .util.enum_base import StrEnum

db = SQLAlchemy()


def publics_to_dict(self) -> dict:
    dict_ = {}
    for key in self.__mapper__.c.keys():
        if not key.startswith("_"):
            dict_[key] = getattr(self, key)

    for key, prop in inspect(self.__class__).all_orm_descriptors.items():
        if isinstance(prop, hybrid_property):
            dict_[key] = getattr(self, key)

    return dict_


class Room(db.Model):
    __tablename__ = "room"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    type = db.Column(db.Integer)
    no = db.Column(db.Integer)

    def __repr__(self):
        return (
            f'<Room(id={self.id}, name="{self.name}", type={self.type}, no={self.no})>'
        )

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)
        dict_["room_id"] = dict_["id"]
        del dict_["id"]
        return dict_


class RoomBook(db.Model):
    __tablename__ = "room_book"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}
    STATUS_WAITING = 100
    STATUS_BOOKED = 200
    STATUS_CANCELED = 300
    STATUS_BLOCKED = 400

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    status = db.Column(db.Integer)
    people_no = db.Column(db.Integer)
    book_date = db.Column(db.DateTime)
    start_time_second = db.Column(db.Integer)
    end_time_second = db.Column(db.Integer)
    department = db.Column(db.String(64))
    purpose = db.Column(db.String(512))
    obj = db.Column(db.String(2048))
    reason = db.Column(db.Text)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    modified = db.Column(
        db.DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    @property
    def start_time(self) -> dt.time:
        if self.start_time_second == 1440:
            return dt.time(23, 59)
        return dt.time(
            hour=int(self.start_time_second / 60),
            minute=int(self.start_time_second % 60),
        )

    @start_time.setter
    def start_time(self, start_time: dt.time):
        self.start_time_second = start_time.hour * 60 + start_time.minute

    @property
    def end_time(self) -> dt.time:
        if self.end_time_second == 1440:
            return dt.time(23, 59)
        return dt.time(
            hour=int(self.end_time_second / 60),
            minute=int(self.end_time_second % 60),
        )

    @end_time.setter
    def end_time(self, end_time: dt.time):
        self.end_time_second = end_time.hour * 60 + end_time.minute

    def __repr__(self):
        return f"<RoomBook(id={self.id}, status={self.status}, room_id={self.room_id}, user_id={self.user_id}, book_date={self.book_date})>"

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)

        dict_["book_id"] = dict_["id"]
        dict_["book_date"] = dict_["book_date"].date().isoformat()

        dict_["start_time_second"] = 1439 if dict_["start_time_second"] == 1440 else dict_["start_time_second"]
        dict_["start_time"] = dt.time(
            hour=int(dict_["start_time_second"] / 60),
            minute=int(dict_["start_time_second"] % 60),
        ).isoformat()

        dict_["end_time_second"] = 1439 if dict_["end_time_second"] == 1440 else dict_["end_time_second"]
        dict_["end_time"] = dt.time(
            hour=int(dict_["end_time_second"] / 60),
            minute=int(dict_["end_time_second"] % 60),
        ).isoformat()

        dict_["created"] = dict_["created"].isoformat()
        dict_["modified"] = dict_["modified"].isoformat()

        del dict_["id"]
        del dict_["start_time_second"]
        del dict_["end_time_second"]
        return dict_


class User(db.Model):
    __tablename__ = "user"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(
        db.Integer, primary_key=True, unique=True, autoincrement=True
    )  # primary key for event table
    chat_id = db.Column(BIGINT(unsigned=False), unique=True)
    tg_name = db.Column(db.String(64))

    username = db.Column(db.String(32))
    birthday = db.Column(db.String(8))
    age = db.Column(db.Integer)
    gender = db.Column(db.Integer)
    encrypted_num = db.Column(db.String(128))
    status = db.Column(db.Integer)
    grade = db.Column(db.Integer, nullable=False, default=0)
    department = db.Column(db.String(32))
    sms = db.Column(db.Integer)

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    modified = db.Column(
        db.DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    delete_que = db.Column(db.Text)
    qr = db.relationship("QR", backref="user", lazy=True)

    @hybrid_property
    def num(self) -> str:
        return dec_v1(self.encrypted_num)

    @num.setter
    def num(self, new_num: str) -> None:
        self.encrypted_num = enc_v1(new_num)

    @hybrid_property
    def valid(self) -> bool:
        return self.sms == 1

    def __repr__(self) -> str:
        return f"<User({self.id}, {self.username}, {self.birthday}, {self.gender}, {self.num}>"

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)

        dict_["created"] = dict_["created"].isoformat()
        if "modified" in dict_ and isinstance(dict_["modified"], dt.datetime):
            dict_["modified"] = dict_["modified"].isoformat()
        dict_["user_id"] = dict_["id"]
        del dict_["encrypted_num"]
        del dict_["id"]
        return dict_


class QR(db.Model):
    __tablename__ = "qr"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    skey = db.Column(db.String(128))
    revision = db.Column(db.Integer)
    created = db.Column(db.DateTime(timezone=True), default=func.now())

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)
        return dict_


class Log(db.Model):
    __tablename__ = "log"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    chat_id = db.Column(BIGINT(unsigned=False))
    tg_name = db.Column(db.String(64))

    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(32))
    birthday = db.Column(db.String(8))
    age = db.Column(db.Integer)
    gender = db.Column(db.Integer)
    encrypted_num = db.Column(db.String(128))
    grade = db.Column(db.Integer, nullable=False, default=0)
    department = db.Column(db.String(32))
    sms = db.Column(db.Integer)

    log_type = db.Column(db.String(64))
    extra_data_str = db.Column(db.Text(1024 * 1024))
    created = db.Column(db.DateTime(timezone=True), default=func.now())

    @hybrid_property
    def extra_data(self) -> dict:
        if self.extra_data_str:
            return json.loads(self.extra_data_str)
        else:
            return {}

    @extra_data.setter
    def extra_data(self, extra_data: str) -> None:
        if extra_data:
            self.extra_data_str = json.dumps(extra_data, ensure_ascii=False)
        else:
            self.extra_data_str = None

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)

        dict_["created"] = dict_["created"].isoformat()

        return dict_


class Message(db.Model):
    __tablename__ = "message"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}
    STATE_SELECT_ALL = MessageState.SELECT_ALL
    STATE_ALREADY_SEND = MessageState.ALREADY_SEND
    STATE_NEED_SEND = MessageState.NEED_SEND
    STATE_MSG_DELETED = MessageState.MSG_DELETED
    STATE_RECEIPT_SEND = MessageState.RECEIPT_SEND

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    message_id = db.Column(BIGINT(unsigned=False))
    chat_id = db.Column(BIGINT(unsigned=False))
    tg_name = db.Column(db.String(64))
    user_id = db.Column(db.Integer)
    data = db.Column(db.Text(1024))
    states = db.Column(db.Integer)

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)
        return dict_


class Pay(db.Model):
    __tablename__ = "pay"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    STATUS_WAITING = "waiting"
    STATUS_CONFIRM = "confirm"
    STATUS_REJECT = "reject"

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("room_book.id"), nullable=True)
    saved_money_id = db.Column(db.Integer, db.ForeignKey("saved_money.id"), nullable=True)
    cashier = db.Column(db.String(32))
    pay_type = db.Column(db.String(32))
    paid = db.Column(db.Integer)
    comment = db.Column(db.String(64))
    status = db.Column(db.String(32), default="waiting")

    created = db.Column(db.DateTime(timezone=True), default=func.now())

    @hybrid_property
    def pay_type_str(self) -> str:
        if self.pay_type.startswith("card"):
            return "카드"
        elif self.pay_type.startswith("saved_money.d"):
            return "지역적립금"
        elif self.pay_type.startswith("donation.card"):
            return "후원(카드)"
        elif self.pay_type.startswith("donation.transfer"):
            return "후원(이체)"
        elif self.pay_type.startswith("donation.cash"):
            return "후원(현금)"
        elif self.pay_type.startswith("transfer"):
            return "계좌이체"
        elif self.pay_type.startswith("cash"):
            return "현금"
        elif self.pay_type.startswith("saved_money.p"):
            return "개인적립금"
        elif self.pay_type.startswith("etc"):
            return f"기타({self.comment})"
        else:
            return ".".join(self.pay_type.split('.')[:-1])

    @hybrid_property
    def status_str(self) -> str:
        if self.status == self.STATUS_WAITING:
            return "대기중"
        elif self.status == self.STATUS_CONFIRM:
            return "결제 성공"
        elif self.status == self.STATUS_REJECT:
            return "결제 거절"
        else:
            return "오류 상태"

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)

        dict_["pay_id"] = dict_["id"]
        dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]
        return dict_


class Transaction(db.Model):
    """결제 관련 정보 저장"""
    __tablename__ = "transaction"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    STUDY_CAT_ID = 2267976
    TYPE_NONE = 0
    TYPE_CARD_REQUEST = 100
    TYPE_CARD_FALLBACK_REQUEST = 101
    TYPE_CARD_CANCEL_REQUEST = 102

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pay_id = db.Column(db.Integer, db.ForeignKey("pay.id"), nullable=False)
    client_name = db.Column(db.String(128))

    type = db.Column(db.Integer)
    money = db.Column(db.Integer)
    tax = db.Column(db.Integer)
    bongsa = db.Column(db.Integer, default=0)
    halbu = db.Column(db.Integer, default=0)
    agree_num = db.Column(db.BIGINT)
    agree_date = db.Column(db.BIGINT)
    cat_id = db.Column(db.BIGINT)
    myunse = db.Column(db.Integer, default=0)
    message = db.Column(db.String(256))

    response_original = db.Column(db.String(1024))
    transaction_classification = db.Column(db.String(32))
    transaction_type = db.Column(db.String(32))
    response_code = db.Column(db.String(32))
    transaction_amount = db.Column(db.String(32))
    VAT = db.Column(db.String(32))
    service_charge = db.Column(db.String(32))
    installment_month = db.Column(db.String(32))
    authorization_number = db.Column(db.String(32))
    approval_datetime = db.Column(db.String(32))
    issuer_code = db.Column(db.String(32))
    issuer_name = db.Column(db.String(64))
    acquisition_code = db.Column(db.String(32))
    acquisition_company_name = db.Column(db.String(64))
    merchant_number = db.Column(db.String(32))
    accept_cat_id = db.Column(db.String(32))
    balance = db.Column(db.String(32))
    response_message = db.Column(db.String(128))
    card_bin = db.Column(db.String(64))
    card_classification = db.Column(db.String(32))
    professional_management_number = db.Column(db.String(32))
    transaction_serial_number = db.Column(db.String(32))

    created = db.Column(db.DateTime(timezone=True), default=func.now())

    @staticmethod
    def create_transaction_request_card(user_id: int, pay_id: int, client_name: str, money: int):
        return Transaction(
            user_id=user_id, pay_id=pay_id, client_name=client_name, type=Transaction.TYPE_CARD_REQUEST,
            money=money, tax=money - (money / 1.1), halbu=0, cat_id=Transaction.STUDY_CAT_ID
        )

    def publics_to_dict(self) -> dict:
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key.startswith("_"):
                dict_[key] = getattr(self, key)

        for key, prop in inspect(self.__class__).all_orm_descriptors.items():
            if isinstance(prop, hybrid_property):
                dict_[key] = getattr(self, key)

        dict_["transaction_id"] = dict_["id"]
        dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]
        return dict_


class SavedMoney(db.Model):
    """적립금 관련 정보 저장"""
    __tablename__ = "saved_money"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    TYPE_PERSONAL = 1
    TYPE_DEPARTMENT = 2

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    type = db.Column(db.Integer)
    name = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    money = db.Column(db.Integer, nullable=False, default=0)
    comment = db.Column(db.String(64))


class Locker(db.Model):
    """사물함 관련 정보 저장"""
    __tablename__ = "locker"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    locker_num = db.Column(db.Integer, nullable=False, default=0)
    unavailable = db.Column(db.BOOLEAN, nullable=False, default=False)
    location_group = db.Column(db.Integer, nullable=False, default=1)
    location_x = db.Column(db.Integer, nullable=False, default=1)
    location_y = db.Column(db.Integer, nullable=False, default=1)
    main_key = db.Column(db.Integer, nullable=False, default=0)
    spare_key = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["locker_id"] = dict_["id"]
        del dict_["id"]
        return dict_


class LockerRental(db.Model):
    """사물함 대여 관련 정보 저장"""
    __tablename__ = "locker_rental"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    locker_id = db.Column(db.Integer, db.ForeignKey("locker.id"), nullable=False)
    department = db.Column(db.String(64))
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    deadline = db.Column(db.DateTime(timezone=True))
    payment_required = db.Column(db.Boolean, nullable=False, default=True)
    deposit = db.Column(db.Integer, nullable=True)
    vitalization = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["locker_rental_id"] = dict_["id"]
        if "created" in dict_:
            dict_["created"] = dict_["created"].isoformat()
        if "deadline" in dict_:
            dict_["deadline"] = dict_["deadline"].isoformat()
        del dict_["id"]
        return dict_


class LockerPayment(db.Model):
    """사물함 결제 관련 정보 저장"""
    __tablename__ = "locker_payment"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    ADMISSION_READY = 0
    ADMISSION_ACCEPT = 1
    ADMISSION_REJECT = 2

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    locker_id = db.Column(db.Integer, db.ForeignKey("locker.id"), nullable=False)
    locker_rental_id = db.Column(db.Integer, db.ForeignKey("locker_rental.id"), nullable=False)
    licenser_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    id_picture = db.Column(db.String(256))
    period = db.Column(db.Integer)
    payment = db.Column(db.Integer)
    admission = db.Column(db.Integer, default=0)
    reason = db.Column(db.String(64))

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["locker_payment_id"] = dict_["id"]
        if "created" in dict_:
            dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]
        return dict_


class Coupon(db.Model):
    """사물함 결제 관련 정보 저장"""
    __tablename__ = "coupon"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    class CouponStatus(StrEnum):
        usable = auto()
        used = auto()
        expire = auto()

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    tel = db.Column(db.String(64))
    status = db.Column(db.String(32))
    group_id = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    expire = db.Column(db.DateTime(timezone=True), nullable=True)
    device_id = db.Column(db.Integer)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    reason = db.Column(db.String(64))

    # 조회
    # group by tel -> sum(amount)
    # 적립
    # find tel > insert amount
    # 사용
    # find tel > sum(amount) > insert -amount

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["coupon_id"] = dict_["id"]
        if "created" in dict_:
            dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]
        return dict_


class CommuteBackup(db.Model):
    """근무 관련 정보 저장"""
    __tablename__ = "commute"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    auth_from = db.Column(db.String(64))
    enter_time = db.Column(db.DateTime(timezone=True))
    exit_time = db.Column(db.DateTime(timezone=True), default=None)



class Commute(db.Model):
    """근무 관련 정보 저장"""
    __tablename__ = "commute_v2"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    auth_from = db.Column(db.String(64))
    enter_time = db.Column(db.DateTime(timezone=True))
    exit_time = db.Column(db.DateTime(timezone=True), default=None)
    record = db.Column(db.String(16), nullable=True)


class Notice(db.Model):
    """사물함 결제 관련 정보 저장"""
    __tablename__ = "notice"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    publish_date = db.Column(db.String(64))
    text = db.Column(db.String(4096))
    picture = db.Column(db.String(4096))

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["notice_id"] = dict_["id"]
        if "created" in dict_:
            dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]

        dict_["picture"] = json.loads(dict_["picture"])
        return dict_


class NoticeTarget(db.Model):
    """사물함 결제 관련 정보 저장"""
    __tablename__ = "notice_target"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}

    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notice.id"), nullable=True)
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    result = db.Column(db.String(4096))
    setting = db.Column(db.String(4096))

    def to_dict(self) -> dict:
        dict_ = publics_to_dict(self)
        dict_["notice_target_id"] = dict_["id"]
        if "created" in dict_:
            dict_["created"] = dict_["created"].isoformat()
        del dict_["id"]

        return dict_

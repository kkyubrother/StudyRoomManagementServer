from flask import (
    Blueprint,
)

from .lib import user as checker
from ..model import User, db

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _create_dummy_user() -> User:
    return User(
        id=1,
        chat_id=-1,
        username="웹사이트",
        sms=1,
        grade=20
    )


@bp.route("/calculate-age")
def calculate_age():
    print("api.admin.calculate_age")
    users = User.query.all()

    for user in users:
        if not user.birthday:
            continue

        age = checker.get_age(checker.get_birthday(user.birthday)[0])
        if user.age != age:
            user.age = age

    db.session.commit()
    return {"message": "okay"}


@bp.route("/create-dummy-user")
def create_dummy_user():
    print("api.admin.create_dummy_user")
    dummy_user = User.query.filter_by(id=1).first()
    if not dummy_user:
        dummy_user = _create_dummy_user()
        db.session.add(dummy_user)
        db.session.commit()

    return dummy_user.publics_to_dict()

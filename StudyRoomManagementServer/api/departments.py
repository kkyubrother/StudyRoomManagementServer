from typing import Dict, Tuple, Union, Optional

from flask import (
    Blueprint,
    request,
)
from werkzeug.datastructures import ImmutableMultiDict

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from .lib.user import DEPARTMENT_DATA, get_department
from ..model import SavedMoney

bp = Blueprint("departments", __name__, url_prefix="/api/departments")


@bp.route("", methods=("GET",))
@check_user_from_cookie_authorization
def get_departments():
    if not request.args:
        return {
            "message": "ok",
            "departments": DEPARTMENT_DATA
        }

    data = request.args
    action = data.get("action", type=str)
    if action == "find.department":
        return _action_find_department(data)

    return {"message": "올바르지 않은 요청입니다."}, 400


def _action_find_department(data: ImmutableMultiDict) -> Union[Dict[str, str], Tuple[Dict[str, str], int]]:
    """ 지역을 찾아 반환합니다. 없으면 404 """
    result = get_department(data.get("name", type=str))
    if isinstance(result, dict):
        saved_money: Optional[SavedMoney] = SavedMoney.query.filter_by(name=result['key']).first()
        return {
            "message": "ok",
            "key": result['key'],
            "name": result['name'],
            "saved_money": saved_money.money if saved_money else 0,
        }
    return {"message": "해당 지역을 찾을 수 없습니다."}, 404

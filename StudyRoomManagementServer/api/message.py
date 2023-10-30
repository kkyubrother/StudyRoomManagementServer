from flask import (
    Blueprint,
    request,
)

from StudyRoomManagementServer.auth_decorator import check_bot_authorization
from StudyRoomManagementServer.constants.message_state import MessageState
from ..access import chat_id_required
from ..model import db, Message

bp = Blueprint("message", __name__, url_prefix="/api/message")


def view_message(msg: Message) -> dict:
    return {
        "id": msg.id,
        "message_id": msg.message_id,
        "user_id": msg.user_id,
        "tg_name": msg.tg_name,
        "chat_id": msg.chat_id,
        "data": msg.data,
        "states": msg.states,
    }


@bp.route(
    "",
    methods=[
        "GET",
    ],
)
# @token_required
@check_bot_authorization
def get_messages():
    """전체 메시지 반환"""
    q = Message.query

    if request.args.get("chat_id", type=int):
        q = q.filter_by(chat_id=request.args.get("chat_id", type=int))

    states = request.args.get("states", type=int)
    if states is not None and states != MessageState.SELECT_ALL:
        q = q.filter_by(states=states)
    else:
        q = q.filter(Message.states != MessageState.MSG_DELETED)

    return {"data": [view_message(m) for m in q.all()]}


@bp.route(
    "",
    methods=[
        "POST",
    ],
)
# @token_required
@check_bot_authorization
@chat_id_required
def post_message(chat_id: int):
    """메세지 등록"""
    msg = Message(
        chat_id=chat_id,
        message_id=request.form.get("message_id", type=int),
        tg_name=request.form.get("tg_name", type=str),
        user_id=request.form.get("user_id", type=int),
        data=request.form.get("data", type=str),
        states=request.form.get("states", type=int),
    )
    db.session.add(msg)
    db.session.commit()
    return {"message": "ok", "data": view_message(msg)}


@bp.route(
    "",
    methods=[
        "PUT",
    ],
)
# @token_required
@check_bot_authorization
def update_messages():
    msg_id = request.form.get("msg_id", type=int)
    message_id = request.form.get("message_id", type=int)
    states = request.form.get("states", type=int)

    msg = Message.query.filter_by(id=msg_id).first()
    if msg:
        msg.states = states
    msg.message_id = message_id

    db.session.commit()
    return {"message": "ok", "data": view_message(msg)}

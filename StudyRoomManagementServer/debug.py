from flask import (
    Blueprint,
)
from flask.globals import current_app

from .model import QR, db, User, RoomBook
from .model import Room

bp = Blueprint('debug', __name__, url_prefix='/debug')

@bp.route('/<int:user_id>', methods=('DELETE',))
def del_user_info_for_debug(user_id: int):
    if not current_app.debug:
        return ''

    user = User.query.filter_by(id=user_id).first()
    if user:
        for qr in QR.query.filter_by(user_id=user_id).all():
            db.session.delete(qr)
        db.session.delete(user)
        db.session.commit()
        return {'message': 'deleted'}
    else:
        return {'message', 'no data'}, 404

@bp.route('', methods=('DELETE',))
def del_all_user_info_for_debug():
    if not current_app.debug:
        return ''

    for book in RoomBook.query.all():
        db.session.delete(book)
    db.session.commit()

    for room in Room.query.all():
        db.session.delete(room)
    db.session.commit()

    for user in User.query.all():
        for qr in QR.query.filter_by(user_id=user.id).all():
            db.session.delete(qr)
        
        db.session.commit()
        db.session.delete(user)
    db.session.commit()
    return {'message': 'deleted'}

def _init():
    for i in range(10):
        room = Room(
            name='스터디룸',
            type=1,
            no=i+1
        )
        db.session.add(room)
    room = Room(
        name='세미나룸',
        type=2,
        no=1
    )
    db.session.add(room)
    room = Room(
        name='스튜디오',
        type=3,
        no=1
    )
    db.session.add(room)
    db.session.commit()

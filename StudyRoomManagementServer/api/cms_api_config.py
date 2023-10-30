import base64
import datetime
import hashlib
import json
import os
import re
from typing import Tuple

from flask import (
    Blueprint,
    request,
)
from flask import current_app
from flask import send_file

from StudyRoomManagementServer.auth_decorator import check_user_from_cookie_authorization
from StudyRoomManagementServer.util.qr_img import __create_membership_image
from ..cms_config import get_config as get_config_obj

TEST_REGEX = re.compile(r"\w+\.\w{1,5}")
SAMPLE_USER_ID = 0
SAMPLE_REVISION = 1
SAMPLE_QR_CODE = "JA3cSIasxDnly54OcKA_Zq3Nn6J3Oa8HykQWBGsakT0CVcECfI-IFCHnYMdtduab_ZXRhxaH9iycfxCHyUOSRg"


bp = Blueprint("config", __name__, url_prefix="/api/config")


@bp.route("/cafe_open_time_text")
def get_config_cafe_open_time_text():
    config_key = "cafe_open_time_text"
    config = get_config_obj()
    if hasattr(config, config_key):
        config_data = getattr(config, config_key)
        return {config_key: config_data}
    return {'error': 'no_config'}, 400


@bp.route("/cafe_close_time_text")
def get_config_cafe_close_time_text():
    config_key = "cafe_close_time_text"
    config = get_config_obj()
    if hasattr(config, config_key):
        config_data = getattr(config, config_key)
        return {config_key: config_data}
    return {'error': 'no_config'}, 400


@bp.route('/<string:config_key>')
@check_user_from_cookie_authorization
def get_config(config_key: str):
    config = get_config_obj()
    if hasattr(config, config_key):
        config_data = getattr(config, config_key)
        if isinstance(config_data, set):
            config_data = list(config_data)
        elif isinstance(config_data, tuple):
            config_data = list(config_data)
        elif isinstance(config_data, (datetime.time, datetime.date, datetime.datetime,)):
            config_data = config_data.isoformat()

        if isinstance(config_data, list):
            if len(config_data) > 0 and isinstance(config_data[0], datetime.date):
                config_data = [f'{d.year}-{d.month:0>2}-{d.day:0>2}' for d in config_data]
            elif len(config_data) > 0 and isinstance(config_data[0], datetime.time):
                config_data = [f'{d.hour:0>2}:{d.minute:0>2}:{d.second:0>2}' for d in config_data]
        return {config_key: config_data}
    return {'error': 'no_config'}, 400


@bp.route('/<string:config_key>', methods=['POST'])
@check_user_from_cookie_authorization
def post_config(config_key: str):
    config = get_config_obj()
    type_ = request.form.get('type')
    data = request.form.get('data')
    if type_ == 'int':
        data = int(data)
    elif type_ == 'date':
        data = datetime.date.fromisoformat(data)
    elif type_ == 'time':
        data = datetime.time.fromisoformat(data)
    elif type_ == 'datetime':
        data = datetime.datetime.fromisoformat(data)
    elif type_ == 'json':
        data = json.loads(data)
    elif type_ == 'bool':
        data = (data == 'true')
    elif type_ == 'tuple':
        data = tuple(data.split(","))
    elif type_ == 'tuple/int':
        data = tuple(map(int, data.split(",")))

    if hasattr(config, config_key):
        try:
            setattr(config, config_key, data)
            config.save()
            return get_config(config_key)
        except AttributeError:
            return {'error': 'can not set'}, 400

    return {'error': 'no_config'}, 400


def __temporary_get_image(fn: str) -> str:
    if "file_name" in request.args:
        file_name: str = request.args.get('file_name')
        if TEST_REGEX.match(file_name):
            file_path = os.path.join(current_app.config["INSTANCE"], file_name)
            if os.path.isfile(file_path):
                return file_path

    file_path = os.path.join(current_app.config["INSTANCE"], fn)
    if os.path.isfile(file_path):
        return file_path

    return os.path.join(current_app.root_path, "static", "img",  fn)


def __temporary_get_qr_box(default: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if "qr_box" not in request.args:
        return default

    qr_box: str = request.args.get('qr_box')
    if not qr_box:
        return default

    qr_box = qr_box.split(",")
    if len(qr_box) != 4:
        return default

    for s in qr_box:
        if not s.isdigit():
            return default

    x1, y1, x2, y2 = list(map(int, qr_box))
    if x1 >= x2 or y1 >= y2:
        return default

    return x1, y1, x2, y2,


def __temporary_get_text_location(default: Tuple[int, int]) -> Tuple[int, int]:
    if "text_location" not in request.args:
        return default

    text_location: str = request.args.get('text_location')
    if not text_location:
        return default

    text_location = text_location.split(",")
    if len(text_location) != 2:
        return default

    for s in text_location:
        if not s.isdigit():
            return default

    return tuple(map(int, text_location))


@bp.route('/dummy/upload', methods=["POST"])
@check_user_from_cookie_authorization
def post_dummy_membership_img():
    data = request.form.get('data')
    file_mime, file_data = data.split(",")
    file_ext = file_mime.lstrip("data:image/").rstrip(";base64")
    file_data = base64.b64decode(file_data)
    file_name = hashlib.sha1(file_data).hexdigest() + '.' + file_ext
    file_path = os.path.join(current_app.config["INSTANCE"], file_name)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return {"message": "ok", "file_name": file_name}


@bp.route('/dummy/sample.png')
@check_user_from_cookie_authorization
def get_sample_img():
    try:
        file_path = __temporary_get_image(get_config_obj().user_membership_normal_file)
    except Exception as e:
        # print(e)
        file_path = __temporary_get_image("membership_bg.png")
    qr_box = __temporary_get_qr_box(get_config_obj().user_membership_normal_qr_box)
    text_location = __temporary_get_text_location(get_config_obj().user_membership_normal_text_box)

    f = __create_membership_image(SAMPLE_USER_ID, SAMPLE_REVISION, SAMPLE_QR_CODE, file_path, qr_box, text_location)
    try:
        return send_file(f, mimetype="image/png", cache_timeout=0)
    except:
        return send_file(f, mimetype="image/png", max_age=0)


@bp.route('/dummy/sample.vip.png')
@check_user_from_cookie_authorization
def get_vip_sample_img():
    try:
        file_path = __temporary_get_image(get_config_obj().user_membership_vip_file)
    except Exception as e:
        print(e)
        file_path = __temporary_get_image("vip_membership_bg.png")
    qr_box = __temporary_get_qr_box(get_config_obj().user_membership_normal_qr_box)
    text_location = __temporary_get_text_location(get_config_obj().user_membership_normal_text_box)

    f = __create_membership_image(SAMPLE_USER_ID, SAMPLE_REVISION, SAMPLE_QR_CODE, file_path, qr_box, text_location)
    try:
        return send_file(f, mimetype="image/png", cache_timeout=0)
    except:
        return send_file(f, mimetype="image/png", max_age=0)

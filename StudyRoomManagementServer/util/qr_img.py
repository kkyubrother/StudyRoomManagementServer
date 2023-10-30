import os
from io import BytesIO
from traceback import print_stack

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from flask import current_app
from qrcode import QRCode
from qrcode.image.base import BaseImage

from StudyRoomManagementServer.cms_config import get_config
from StudyRoomManagementServer.model import User, QR
from .grade import is_vip

GRADE_VIP = 5

__FONT_PATH = ""


def __create_membership_image(user_id, revision, code, background_img, qr_box, text_location) -> BytesIO:
    """실제 QR 이미지 생성"""
    qr = QRCode()
    qr.add_data(f"{revision}0{user_id:04x}{code}")
    qr.make()

    img_qr = qr.make_image(image_factory=PilImage)

    bio = BytesIO()
    bio.name = "membership.png"
    try:
        img_qr = img_qr.resize((qr_box[2] - qr_box[0], qr_box[3] - qr_box[1],))
        font = ImageFont.truetype(__FONT_PATH, 45)

        with Image.open(background_img) as img_bg:
            img_bg.paste(img_qr, qr_box)

            draw = ImageDraw.Draw(img_bg)
            draw.text(text_location, f"V{revision}_{user_id}", (255, 255, 255), font)
            img_bg.save(bio, "PNG")

    except IOError as ioe:
        print(ioe)
        print_stack()
        img_qr.save(bio, "PNG")
    bio.seek(0)
    return bio


def __create_normal_membership_image(user_id, revision, code) -> BytesIO:
    """일반 회원권 생성"""

    if get_config().user_membership_normal_file:
        qr_img_path = os.path.join(current_app.config["INSTANCE"], get_config().user_membership_normal_file)
    else:
        qr_img_path = os.path.join(current_app.root_path, "static", "img",  "membership_bg.png")
    qr_box = get_config().user_membership_normal_qr_box
    text_location = get_config().user_membership_normal_text_box
    return __create_membership_image(user_id, revision, code, qr_img_path, qr_box, text_location)


def __create_vip_membership_image(user_id, revision, code) -> BytesIO:
    """원장 회원권 생성"""
    if get_config().user_membership_vip_file:
        qr_img_path = os.path.join(current_app.config["INSTANCE"], get_config().user_membership_vip_file)
    else:
        qr_img_path = os.path.join(current_app.root_path, "static", "img",  "vip_membership_bg.png")
    qr_box = get_config().user_membership_vip_qr_box
    text_location = get_config().user_membership_vip_text_box
    return __create_membership_image(user_id, revision, code, qr_img_path, qr_box, text_location)


def create_qr_image(user: User, qr: QR) -> BytesIO:
    """새로운 QR 이미지 생성"""

    user_id: int = user.id
    revision: int = qr.revision
    code: str = qr.skey

    if is_vip(user):
        return __create_vip_membership_image(user_id, revision, code)

    return __create_normal_membership_image(user_id, revision, code)


class PilImage(BaseImage):
    """
    PIL image builder, default format is PNG.
    """

    kind = "PNG"

    def new_image(self, **kwargs):
        back_color = kwargs.get("back_color", "white")
        fill_color = kwargs.get("fill_color", "black")

        if fill_color.lower() != "black" or back_color.lower() != "white":
            if back_color.lower() == "transparent":
                mode = "RGBA"
                back_color = (0, 0, 0, 0,)
            else:
                mode = "RGB"
        else:
            mode = "1"
            # L mode (1 mode) color = (r*299 + g*587 + b*114)//1000
            if fill_color.lower() == "black":
                fill_color = 0
            if back_color.lower() == "white":
                back_color = 255

        img = Image.new(mode, (self.pixel_size, self.pixel_size), back_color)
        self.fill_color = fill_color
        self._idr = ImageDraw.Draw(img)
        return img

    def drawrect(self, row, col):
        box = self.pixel_box(row, col)
        self._idr.rectangle(box, fill=self.fill_color)

    def save(self, stream, format=None, **kwargs):
        kind = kwargs.pop("kind", self.kind)
        if format is None:
            format = kind
        self._img.save(stream, format=format, **kwargs)

    def __getattr__(self, name):
        return getattr(self._img, name)


def init_app(app):
    global __FONT_PATH
    __FONT_PATH = os.path.join(app.root_path, "static", "font", "NanumBarunpenB.ttf")

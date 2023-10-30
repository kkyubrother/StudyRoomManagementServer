"""영수증 생성기"""
import datetime as dt
import os
from io import BytesIO
from typing import NamedTuple, Tuple, Union, List

from PIL import Image, ImageDraw, ImageFont

TITLE_FONT: ImageFont.FreeTypeFont  # = ImageFont.truetype("NotoSansKR-Bold.otf", size=20, encoding="utf-8")
BODY_FONT: ImageFont.FreeTypeFont  # = ImageFont.truetype("NotoSansKR-Regular.otf", size=12, encoding="utf-8")
WATERMARK_IMG: Image.Image  # = ImageFont.truetype("NotoSansKR-Regular.otf", size=12, encoding="utf-8")

W_0 = 5
W_1 = 119
W_2 = W_1 + 69
W_3 = W_2 + 42
W_4 = W_3 + 64
WIDTH = W_4 + 5
HEIGHT = 1000


class Store(NamedTuple):
    """가계 정보"""
    name: str
    address: str
    representative: str
    business_license: str
    phone: str


class CreditCard(NamedTuple):
    """결제 카드 정보"""
    name: str
    number: str
    installment: int
    accept_number: int
    purchase_company: str


class SavedMoney(NamedTuple):
    """결제 지역적립금 정보"""
    name: str
    number: str
    installment: int
    accept_number: int
    purchase_company: str


class Menu(NamedTuple):
    """메뉴 정보"""
    name: str
    unit_price: int
    count: int


class Receipt(NamedTuple):
    """영수증 정보"""
    no: int
    datetime: dt.datetime
    menu: Union[Tuple[Menu], List[Menu]]
    store: Store
    payment: Union[None, CreditCard]


def _change_image_size(max_width: int, max_height: int, image: Image.Image) -> Image.Image:
    width_ratio = max_width / image.size[0]
    height_ratio = max_height / image.size[1]

    new_width = int(width_ratio * image.size[0])
    new_height = int(height_ratio * image.size[1])

    new_image = image.resize((new_width, new_height))
    return new_image


def _draw_title(draw: ImageDraw, text: str, size: Tuple[int, int]) -> Tuple[int, int]:
    """제목을 그려라"""
    tw, th = draw.textsize(text, font=TITLE_FONT)
    draw.text(((WIDTH - tw) / 2, size[1],), text, font=TITLE_FONT, fill="black")
    return tw, th


def _draw_text(draw: ImageDraw, text: str, size: Tuple[int, int], align_right: bool = False) -> Tuple[int, int]:
    """텍스트를 그려라"""
    tw, th = draw.textsize(text, font=BODY_FONT)
    if align_right:
        size = size[0] - tw, size[1]
    draw.text(size, text, font=BODY_FONT, fill="black")
    return tw, th


def _draw_text_line(draw: ImageDraw, text: str, min_height: int) -> int:
    """한줄 텍스트를 그려라"""
    return _draw_text(draw, text, (W_0, min_height))[1]


def _draw_blank_line(draw: ImageDraw, min_height: int) -> int:
    """빈 줄을 그려라"""
    return _draw_text(draw, " ", (W_0, min_height))[1]


def _sum_size(min_width: int, min_height: int, size: Tuple[int, int]) -> Tuple[int, int]:
    """사이즈 더하기"""
    res_width, res_height = size
    return min_width + res_width, min_height + res_height


def make_receipt_image_file(receipt: Receipt) -> BytesIO:
    """영수증 이미지 파일을 생성한다"""
    img = make_receipt_image(receipt)
    bio = BytesIO()
    bio.name = "receipt.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


def _draw_payment_none(draw: ImageDraw, min_height: int) -> int:
    """결제 정보가 없음을 그려라"""
    min_width, min_height = _sum_size(0, min_height, _draw_title(draw, "결제 실패", (0, min_height)))
    return min_height


def _draw_store(draw: ImageDraw, store: Store, min_height: int) -> int:
    """상점 정보를 그려라"""
    min_height += _draw_text_line(draw, f"상호: {store.name}", min_height)
    min_height += _draw_text_line(draw, f"주소: {store.address}", min_height)
    min_height += _draw_text_line(draw, f"대표자: {store.representative}", min_height)
    min_height += _draw_text_line(draw, f"사업자 번호: {store.business_license}", min_height)
    return min_height


def _draw_payment_credit_card(draw: ImageDraw, payment: CreditCard, min_height: int) -> int:
    """신용 승인 정보를 그려라"""
    min_width, min_height = _sum_size(0, min_height, _draw_title(draw, "신용승인", (0, min_height)))

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "카드명칭", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, payment.name, (W_4, line_height), True))

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "카드번호", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height,
                                      _draw_text(draw, payment.number, (W_4, line_height), True))

    line_height = min_height
    text = "일시불" if payment.installment == 0 else f"{payment.installment}"
    _, _ = _sum_size(0, line_height, _draw_text(draw, "할부기간", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, text, (W_4, line_height), True))

    line_height = min_height
    text = f"{payment.accept_number}"
    _, _ = _sum_size(0, line_height, _draw_text(draw, "승인번호", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, text, (W_4, line_height), True))

    line_height = min_height
    text = f"{payment.purchase_company}"
    _, _ = _sum_size(0, line_height, _draw_text(draw, "매입사", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, text, (W_4, line_height), True))
    return min_height


def make_receipt_image(receipt: Receipt) -> Image:
    """영수증 이미지를 생성한다"""
    min_width = 0
    min_height = 0
    now_dt = (dt.datetime.utcnow() + dt.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')

    img = Image.new(mode="RGBA", size=(WIDTH, HEIGHT,), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    min_width, min_height = _sum_size(min_width, min_height, _draw_title(draw, "영수증", (min_width, min_height)))
    min_height = _draw_store(draw, receipt.store, min_height)

    min_height += _draw_text_line(draw, f"일시: {receipt.datetime.strftime('%Y년 %m월 %d일')}", min_height)
    min_height += _draw_text_line(draw, f"발행일시: {now_dt}", min_height)
    min_height += _draw_text_line(draw, f"No: {receipt.no}", min_height)

    min_height += _draw_blank_line(draw, min_height)

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "메뉴명", (W_0, line_height)))
    _, _ = _sum_size(0, line_height, _draw_text(draw, "단가", (W_1, line_height)))
    _, _ = _sum_size(0, line_height, _draw_text(draw, "수량", (W_2, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, "금액", (W_3, line_height)))

    for menu in receipt.menu:
        line_height = min_height
        _, _ = _sum_size(0, line_height, _draw_text(draw, menu.name, (W_0, line_height)))
        _, _ = _sum_size(0, line_height, _draw_text(draw, format(menu.unit_price, ","), (W_2, line_height), True))
        _, _ = _sum_size(0, line_height, _draw_text(draw, format(menu.count, ","), (W_3, line_height), True))
        text = format(menu.unit_price * menu.count, ",")
        min_width, min_height = _sum_size(0, line_height, _draw_text(draw, text, (W_4, line_height), True))

    min_height += _draw_blank_line(draw, min_height)
    min_height += _draw_blank_line(draw, min_height)

    line_height = min_height
    total_price = sum([menu.unit_price * menu.count for menu in receipt.menu])
    _, _ = _sum_size(0, line_height, _draw_text(draw, "판매금액", (W_0, line_height)))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, format(total_price, ","), (W_4, line_height), True))

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "과세공급가액", (W_3, line_height), True))
    tax_free_price = round(total_price / 1.1)
    tax = total_price - tax_free_price
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, format(tax_free_price, ","), (W_4, line_height), True))

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "부가세액", (W_3, line_height), True))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, format(tax, ","), (W_4, line_height), True))

    line_height = min_height
    _, _ = _sum_size(0, line_height, _draw_text(draw, "총 결제 금액", (W_3, line_height), True))
    min_width, min_height = _sum_size(0, line_height, _draw_text(draw, format(total_price, ","), (W_4, line_height), True))

    min_height += _draw_blank_line(draw, min_height)

    if isinstance(receipt.payment, CreditCard):
        min_height = _draw_payment_credit_card(draw, receipt.payment, min_height)
    elif receipt.payment is None:
        min_height = _draw_payment_none(draw, min_height)

    return img.crop((0, 0, WIDTH, min_height + 10))


def init_app(app):
    global TITLE_FONT
    TITLE_FONT = ImageFont.truetype(
        os.path.join(app.root_path, "static", "font", "NotoSansKR-Bold.otf")
        , size=20, encoding="utf-8")

    global BODY_FONT
    BODY_FONT = ImageFont.truetype(
        os.path.join(app.root_path, "static", "font", "NotoSansKR-Regular.otf")
        , size=12, encoding="utf-8")

    global WATERMARK_IMG
    WATERMARK_IMG = Image.open(
        os.path.join(app.root_path, "static", "img", "logo-plin.png")
    )

from base64 import b64decode, b64encode
from typing import Tuple

from Cryptodome.Cipher import AES
from flask import Flask

SECURE_KEY: bytes = None
SECURE_AAD: bytes = None
SECURE_NONCE: bytes = None


def init_app(app: Flask):
    init_key(app.config["SECURE_KEY"], app.config["SECURE_AAD"], app.config["SECURE_NONCE"])


def init_key(secure_key: str, secure_aad: str, secure_nonce: str):
    global SECURE_KEY
    global SECURE_AAD
    global SECURE_NONCE
    SECURE_KEY = secure_key
    SECURE_AAD = secure_aad
    SECURE_NONCE = secure_nonce


# 암호화 함수
def enc(key: bytes, aad: bytes, nonce: bytes, plain_data: bytes) -> Tuple[bytes, bytes]:
    # AES GCM으로 암호화 라이브러리 생성
    cipher = AES.new(key, AES.MODE_GCM, nonce)

    # aad(Associated Data) 추가
    cipher.update(aad)

    # 암호!!!
    cipher_data = cipher.encrypt(plain_data)
    mac = cipher.digest()

    # 암호 데이터와 mac 리턴
    return cipher_data, mac


# 복호화 함수
def dec(key: bytes, aad: bytes, nonce: bytes, cipher_data, mac) -> bytes or None:
    # 암호화 라이브러리 생성
    cipher = AES.new(key, AES.MODE_GCM, nonce)
    # aad(Associated Data) 추가
    cipher.update(aad)

    try:
        # 복호화!!!
        plain_data = cipher.decrypt_and_verify(cipher_data, mac)
        # 복호화 된 값 리턴
        return plain_data

    except ValueError:
        # 복호화 실패
        return None


__VERSION_1 = "V1"


def enc_v1(plain_text: str) -> str:
    if not isinstance(plain_text, str):
        return plain_text
    plain_data = plain_text.encode("utf-8")

    enc_data, mac = enc(SECURE_KEY, SECURE_AAD, SECURE_NONCE, plain_data)
    return (
        __VERSION_1
        + "|"
        + b64encode(enc_data).decode("utf-8")
        + "|"
        + b64encode(mac).decode("utf-8")
    )


def dec_v1(encrypt_data: str) -> str:
    if not isinstance(encrypt_data, str):
        return encrypt_data

    elif not encrypt_data.strip():
        return encrypt_data

    if len(encrypt_data.split("|")) == 2:
        enc_txt, enc_mac = encrypt_data.split("|")
    else:
        enc_ver, enc_txt, enc_mac = encrypt_data.split("|")
        if __VERSION_1 != enc_ver:
            raise ValueError()

    enc_data = b64decode(enc_txt.encode("utf-8"))
    mac = b64decode(enc_mac.encode("utf-8"))

    plain_data = dec(SECURE_KEY, SECURE_AAD, SECURE_NONCE, enc_data, mac)

    if plain_data is not None:
        return plain_data.decode("utf-8")

    raise ValueError()

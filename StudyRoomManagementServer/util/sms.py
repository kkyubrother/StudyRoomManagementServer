from logging import Logger

from flask import Flask
from phps_sms_module.lms import LMS
from phps_sms_module.sms import SMS

# from phps_sms.sms import SMS, SMSError

SMS_ID = ""
SMS_TOKEN = ""
SMS_NUM = ""
_SMS_MODULE: SMS = None

logger: Logger = None


def init_app(app: Flask):
    global SMS_ID
    global SMS_TOKEN
    global SMS_NUM
    global _SMS_MODULE
    global logger
    SMS_ID = app.config.get("SMS_ID")
    SMS_TOKEN = app.config.get("SMS_TOKEN")
    SMS_NUM = app.config.get("SMS_NUM")
    logger = app.logger
    SMS.set_print_debug_message(True)
    SMS.set_logger(app.logger)
    _SMS_MODULE = SMS(SMS_ID, SMS_TOKEN, SMS_NUM)


def send(to_num: str, text: str):
    try:
        if len(text) < 50:
            result = _SMS_MODULE.send_msg(to_num, text)
        else:
            result = LMS.send(SMS_ID, SMS_TOKEN, SMS_NUM, to_num, text, None)

        return result
    except Exception as e:
        logger.error(f"to_num: {to_num}, text: {text}")
        logger.error(e)
        print(f"to_num: {to_num}, text: {text}")
        print(e)
        raise e


def send_v2(from_tel: str, to_tel: str, text: str):
    try:
        _SMS_MODULE = SMS(SMS_ID, SMS_TOKEN, from_tel)
        if len(text) < 50:
            result = _SMS_MODULE.send_msg(to_tel, text)
        else:
            result = LMS.send(SMS_ID, SMS_TOKEN, from_tel, to_tel, text, None)

        return result
    except Exception as e:
        logger.error(f"from_tel: {from_tel}, to_tel: {to_tel}, text: {text}")
        logger.error(e)
        raise e

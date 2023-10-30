import traceback
from typing import Dict


def __mk_res(message: str, status_code: int) -> [Dict, int]:
    return {"message": message}, status_code


class CafeManagementError(Exception):
    debug_message: str
    status_code: int
    message: str

    def __init__(self, status_code: int, message: str, debug_message: str = None):
        self.status_code = status_code
        self.message = message
        self.debug_message = debug_message

    def __str__(self):
        return f"<CafeManagementError('{self.status_code}', '{self.message}', '{self.debug_message}')>"


class Unauthorized(CafeManagementError):
    def __init__(self, message: str, debug_message: str = None):
        super().__init__(401, message, debug_message)


class BadRequest(CafeManagementError):
    def __init__(self, message: str, debug_message: str = None):
        super().__init__(400, message, debug_message)


class Forbidden(CafeManagementError):
    def __init__(self, message: str, debug_message: str = None):
        super().__init__(403, message, debug_message)


class NotFound(CafeManagementError):
    def __init__(self, message: str = "Not Found", debug_message: str = None):
        super().__init__(404, message, debug_message)


class Conflict(CafeManagementError):
    def __init__(self, message: str, debug_message: str = None):
        super().__init__(409, message, debug_message)


def error_handle(app):
    """에러 핸들러

    에러 처리하는 함수

    Args:
        app  : __init__.py에서 파라미터로 app을 전달 받은 값
    Returns:
        json : error_response() 함수로 에러 메시지를 전달해서 반환 받고 return
    """

    @app.errorhandler(AttributeError)
    def handle_error(e):
        traceback.print_exc()
        return __mk_res("Server Error", 500)

    @app.errorhandler(KeyError)
    def handle_key_error(e):
        traceback.print_exc()
        return __mk_res("Server Error", 500)

    @app.errorhandler(TypeError)
    def handle_type_error(e):
        traceback.print_exc()
        return __mk_res("Server Error", 500)

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        traceback.print_exc()
        return __mk_res("Server Error", 500)

    @app.errorhandler(CafeManagementError)
    def handle_error(e):
        traceback.print_exc()
        print(e)
        return __mk_res(e.message, e.status_code)

    @app.errorhandler(Exception)
    def handle_error(e):
        traceback.print_exc()
        return __mk_res("Server Error", 500)

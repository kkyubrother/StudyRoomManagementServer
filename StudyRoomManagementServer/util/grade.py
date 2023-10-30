from ..model import User


GRADE_NORMAL = 0
GRADE_VIP = 10
GRADE_MANAGER = 15
GRADE_ADMIN = 20
GRADE_WARNING = -10
GRADE_ENEMY = -20


def is_normal(user: User) -> bool:
    """회원인가?"""
    return user.grade >= GRADE_NORMAL


def is_vip(user: User) -> bool:
    """원장인가?"""
    return user.grade >= GRADE_VIP


def is_manager(user: User) -> bool:
    """플린이인가?"""
    return user.grade >= GRADE_MANAGER


def is_admin(user: User) -> bool:
    """관리자인가?"""
    return user.grade >= GRADE_ADMIN


def is_warning(user: User) -> bool:
    """경고인가?"""
    return user.grade <= GRADE_WARNING


def is_enemy(user: User) -> bool:
    """차단인가?"""
    return user.grade <= GRADE_ENEMY

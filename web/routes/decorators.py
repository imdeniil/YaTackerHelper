"""Декораторы для маршрутов"""

from functools import wraps
from fasthtml.common import RedirectResponse


def require_auth(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    async def wrapper(sess, *args, **kwargs):
        user_id = sess.get('user_id')
        if not user_id:
            return RedirectResponse('/login', status_code=303)
        return await f(sess, *args, **kwargs)
    return wrapper


def require_role(*allowed_roles):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        async def wrapper(sess, *args, **kwargs):
            role = sess.get('role')
            if role not in allowed_roles:
                return RedirectResponse('/dashboard', status_code=303)
            return await f(sess, *args, **kwargs)
        return wrapper
    return decorator

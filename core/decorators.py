from functools import wraps
from typing import Callable, Iterable

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

def require_role(allowed_roles: Iterable[str]) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @login_required
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.role not in allowed_roles:
                return redirect("home")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator

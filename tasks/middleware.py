from django.contrib.auth import login
from django.contrib.auth.models import User
from django.conf import settings


class AutoLoginMiddleware:
    """
    Automatically logs in the default superuser/user in development/single-user mode
    so you never have to re-enter your password repeatedly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "AUTO_LOGIN", True) and not request.user.is_authenticated:
            # Do not re-login if user is deliberately hitting logout
            if not request.path.startswith("/logout"):
                user = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if user:
                    user.backend = "django.contrib.auth.backends.ModelBackend"
                    login(request, user)
        return self.get_response(request)

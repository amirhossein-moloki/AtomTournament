# tournament_project/asgi.py

import os
from django.core.asgi import get_asgi_application
# import های مربوط به Channels را هم برای خوانایی بهتر اینجا می‌آوریم
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# این خط باید اولین دستور مربوط به جنگو باشد
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tournament_project.settings")

# !! مهم: ابتدا این تابع را فراخوانی می‌کنیم تا جنگو پیکربندی شود
django_asgi_app = get_asgi_application()

# حالا که جنگو آماده است، می‌توانیم routing های خود را import کنیم
import chat.routing
import notifications.routing

# در نهایت، application را با استفاده از متغیری که ساختیم تعریف می‌کنیم
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
                + notifications.routing.websocket_urlpatterns
            )
        ),
    }
)

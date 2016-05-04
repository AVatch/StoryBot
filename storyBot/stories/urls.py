from django.conf.urls import url
from .views import BotWebHookHandler

# API endpoints
urlpatterns = [
    url(r'^messenger$',
        BotWebHookHandler.as_view(),
        name='messenger')
]

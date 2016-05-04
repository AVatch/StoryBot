from django.conf.urls import url
from .views import BotWebHookHandler, HomePageView

# API endpoints
urlpatterns = [
    url(r'^$',
        HomePageView.as_view(),
        name='home'),
    
    url(r'^api/v1/messenger$',
        BotWebHookHandler.as_view(),
        name='messenger'),
    
    
    
]

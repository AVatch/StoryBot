from django.conf.urls import url
from .views import BotWebHookHandler, HomePageView, StoryDetailView

# API endpoints
urlpatterns = [
    url(r'^$',
        HomePageView.as_view(),
        name='home'),
    
    url(r'^stories/(?P<pk>[0-9]+)$',
        StoryDetailView.as_view(),
        name='story'),
    
    url(r'^api/v1/messenger$',
        BotWebHookHandler.as_view(),
        name='messenger'),
     
]

from django.conf.urls import url
from django.views.generic import TemplateView
from .views import BotWebHookHandler, CleanupView, HomePageView, StoryDetailView, AboutPageView

# API endpoints
urlpatterns = [
    url(r'^$',
        HomePageView.as_view(),
        name='home'),
    
    url(r'^about$',
         AboutPageView.as_view(),),
    
    url(r'^stories/(?P<pk>[0-9]+)$',
        StoryDetailView.as_view(),
        name='story'),
    
    url(r'^api/v1/messenger$',
        BotWebHookHandler.as_view(),
        name='messenger'),
    
    url(r'^api/v1/cleanup$',
         CleanupView.as_view(),
         name='cleanup'),
     
]

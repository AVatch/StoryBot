import os
import json
import random
import datetime

import requests

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.template.defaulttags import register
from django.conf import settings
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

import bot
import dispatchers
from .keywords import *
from .fb_chat_buttons import *
from .models import Contributor, Fragment, Story
from .alias_generator import generate_alias, generate_title, generate_random_gif
from .story_utilities import checkForStaleContributors, kickStaleContributor

FB_WEBHOOK_CHALLENGE = os.environ.get("FB_WEBHOOK_CHALLENGE")
FB_APP_ID = os.environ.get("FB_APP_ID")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_TOKEN = os.environ.get("FB_TOKEN")


def get_user_fb_info(fb_id):
    """returns the users fb info
    ref: https://developers.facebook.com/docs/messenger-platform/send-api-reference#user_profile_request
    """
    r = requests.get('https://graph.facebook.com/v2.6/' + str(fb_id),
                     params={
                         'fields': 'first_name,last_name,profile_pic,locale,timezone,gender',
                         'access_token': FB_TOKEN
                     })
    return r.json()



@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    else:
        return None

"""Primary webhook endpoint where the bot logic resides
"""
class BotWebHookHandler(APIView):
    def get(self, request, format=None):
        """Endpoint to verify webhook with Facebook service
        """
        if request.query_params.get('hub.verify_token') == FB_WEBHOOK_CHALLENGE:
            return Response( int(request.query_params.get('hub.challenge')) )  
        return Response( status=status.HTTP_200_OK )
    

    def post(self, request, format=None):
        """Main entry point for Messenger conversations
        """
        
    
        messenger_events = request.data.get('entry')[0].get('messaging')
    
        for event in messenger_events:
            
            contributor, created = Contributor.objects.get_or_create(social_identifier=str( event.get('sender').get('id') ) )
            contributor.last_active = timezone.now()
            contributor.save()
                        
            if created:
                fb_info = get_user_fb_info( contributor.social_identifier )
                
                contributor.profile_pic = fb_info.get('profile_pic')
                contributor.first_name = fb_info.get('first_name')
                contributor.last_name = fb_info.get('last_name')
                contributor.locale = fb_info.get('locale')
                contributor.gender = fb_info.get('gender')
                contributor.timezone = fb_info.get('timezone')
                contributor.save()
                
                dispatchers.sendBotMessage(contributor.social_identifier, "Thanks for joining StoryBot!")
                dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "Let's get started.",
                                                [BUTTON_JOIN, BUTTON_BROWSE])
                break  # we want to let the user input a choice            
        
            if event.get('postback') and event.get('postback').get('payload'):
                """Handle PB postback style messages
                """
                bot.process_postback_message( contributor, event.get('postback').get('payload') )
            
            if event.get('message') and event.get('message').get('text'):
                """Handle messages with text
                """
                bot.process_raw_message( contributor, event.get('message').get('text') )
           
        """Return a 200 to the messenger provider 
        """
        return Response( status=status.HTTP_200_OK )


"""Calls the cleanup function which identified any stale contributors and
drops them
"""
class CleanupView(APIView):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        stale_contributors = checkForStaleContributors()
        print "STALE CONTRIBUTORS"
        print stale_contributors
        for contributor in stale_contributors:
            if contributor.stale:
                # this is the 2nd time we are asking them to write
                # so kick them
                print "KICK"*50
                kickStaleContributor( contributor )
                dispatchers.notifyKickedContributor( contributor )
                
            else:
                # notify them to act
                print "NOTIFY"
                dispatchers.remindInactiveContributor( contributor )
                # mark them stale for next time
                contributor.mark_stale()
        return Response( { }, status=status.HTTP_200_OK )


"""Renders the landing page, which is just a random story
"""
class HomePageView(View):
    def get(self, request):
        # pick a random story and render it
        story = Story.objects.filter(complete=True).order_by('?').first()
        
        if story:
            contributors = {}
            context = {
                "story": story,
                "fragments": [],
                "description": "",
                "story_url_path": settings.BASE_URL + "/stories/" + str(story.id),
                "cover": generate_random_gif(),
                "contributors": contributors,
                "FB_APP_ID": FB_APP_ID,
                "FB_PAGE_ID": FB_PAGE_ID
            }

            context["fragments"] = Fragment.objects.filter(story=story).order_by('position')
            context["description"] = context["fragments"][0].fragment[:130] + "..." 
            
            for contributor in story.contributors.all():
                color = "#%06x" % random.randint(0, 0xFFFFFF)
                context["contributors"][contributor.id] = {
                    "color": color,
                    "alias": ""
                }
                fragment = story.fragment_set.filter(contributor=contributor).first()
                if fragment:
                    context["contributors"][contributor.id]["alias"] = fragment.alias
            
        else:
            # DB is empty and there are no stories
            context = {
                "story": None,
                "fragments": [],
                "description": "",
                "story_url_path": settings.BASE_URL,
                "cover": generate_random_gif(),
                "contributors": [],
                "FB_APP_ID": FB_APP_ID,
                "FB_PAGE_ID": FB_PAGE_ID
            }
        return render(request, 'stories/stories.html', context)

"""Renders the story details page, which is just one story as
designated by its id
"""
class StoryDetailView(View):
    def get(self, request, pk):
        
        story = get_object_or_404(Story, pk=pk)
        
        contributors = {}
        context = {
            "story": story,
            "fragments": [],
            "description": "",
            "story_url_path": settings.BASE_URL + "/stories/" + str(story.id),
            "cover": generate_random_gif(),
            "contributors": contributors,
            "FB_APP_ID": FB_APP_ID,
            "FB_PAGE_ID": FB_PAGE_ID
        }

        context["fragments"] = Fragment.objects.filter(story=story).order_by('position')
        context["description"] = context["fragments"][0].fragment[:130] + "..."
        
        for contributor in story.contributors.all():
            color = "#%06x" % random.randint(0, 0xFFFFFF)
            context["contributors"][contributor.id] = {
                "color": color,
                "alias": ""
            }
            fragment = story.fragment_set.filter(contributor=contributor).first()
            if fragment:
                context["contributors"][contributor.id]["alias"] = fragment.alias
    
            
    
        return render(request, 'stories/stories.html', context)

"""Renders the about page
"""
class AboutPageView(View):
    def get(self, request):
        context = {
            "FB_APP_ID": FB_APP_ID,
            "FB_PAGE_ID": FB_PAGE_ID
        }
        return render(request, 'about.html', context)
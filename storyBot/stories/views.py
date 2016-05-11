import os
import json
import random
import datetime

import requests

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

import bot
import dispatchers
from .keywords import *
from .fb_chat_buttons import *
from .models import Contributor, Fragment, Story
from .alias_generator import generate_alias, generate_title

FB_WEBHOOK_CHALLENGE = os.environ.get("FB_WEBHOOK_CHALLENGE")
FB_APP_ID = os.environ.get("FB_APP_ID")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")

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
        
        print "POSTING HERE"

        messenger_events = request.data.get('entry')[0].get('messaging')
        
        for event in messenger_events:
            
            contributor, created = Contributor.objects.get_or_create(social_identifier=str( event.get('sender').get('id') ) )
            
            if created:
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


"""Renders the landing page, which is just a random story
"""
class HomePageView(View):
    def get(self, request):
        # pick a random story and render it
        story = Story.objects.filter(complete=True).order_by('?').first()
        
        context = {
            "story": story,
            "fragments": [],
            "FB_APP_ID": FB_APP_ID,
            "FB_PAGE_ID": FB_PAGE_ID
        }
        
        if story:
            story_fragments = Fragment.objects.filter(story=story).order_by('position')                
            
            context["fragments"] = story_fragments
        
        return render(request, 'stories/stories.html', context)

"""Renders the story details page, which is just one story as
designated by its id
"""
class StoryDetailView(View):
    def get(self, request, pk):
        
        story = get_object_or_404(Story, pk=pk)
        
        context = {
            "story": story,
            "fragments": [],
            "FB_APP_ID": FB_APP_ID,
            "FB_PAGE_ID": FB_PAGE_ID
        }
        
        if story:
            story_fragments = Fragment.objects.filter(story=story).order_by('position')                
            
            context["fragments"] = story_fragments
        
        return render(request, 'stories/stories.html', context)


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

from .models import Contributor, Fragment, Story
from .alias_generator import generate_alias, generate_title


FB_WEBHOOK_CHALLENGE = os.environ.get("FB_WEBHOOK_CHALLENGE")
FB_TOKEN = os.environ.get("FB_TOKEN")
FB_URL = os.environ.get("FB_URL")
FB_APP_ID = os.environ.get("FB_APP_ID")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")

KEYWORD_START = '\start'
KEYWORD_CONTINUE = '\continue'
KEYWORD_READ = '\\read'
KEYWORD_ERASE = '\erase'
KEYWORD_DONE = '\done'
KEYWORD_DISCARD = '\discard'

KEYWORD_BROWSE = '\\browse'

KEYWORD_HISTORY = '\history'
KEYWORD_HELP = '\help'


FRAGMENT_MAPPING = {
                        0: 'Begining',
                        1: 'Middle',
                        2: 'End'
                    } 


def hasNumber(string):
    """check if a string contains a number
    """
    return any( char.isdigit() for char in string )

def chunkString(string, length):
    """Given a string break it down into 
    chunks of size length
    """
    return [string[i:i+length] for i in range(0, len(string), length)]


def sendBotMessage(recipient, message):
    """A script to send a facebook message to recipient
    """
    responseBody = { 
                        'recipient': { 
                            'id': recipient
                        }, 
                        'message': {
                            'text': message
                        } 
                    } 
    
    requests.post(FB_URL, 
                  params = { 'access_token': FB_TOKEN },
                  headers = {'content-type': 'application/json'},
                  data = json.dumps(responseBody) )

def readBackStory( contributor, story ):
    """Reads the story back and makes sure it chunks it appropriately
    """
    sendBotMessage(contributor.social_identifier, story.title)
    story_fragments = Fragment.objects.filter(story=story).order_by('position')
    for fragment in story_fragments:
        complete = "COMPLETE" if fragment.complete else "INCOMPLETE"
        sendBotMessage(contributor.social_identifier, "[" + complete + "] " + FRAGMENT_MAPPING.get(fragment.position) + " by " + fragment.alias)
        fragment_chunks = chunkString(fragment.fragment, 180)
        for chunk in fragment_chunks:
            sendBotMessage(contributor.social_identifier, chunk)

def sendHelpMessage( contributor ):
    """Sends a help message with the instructions on how to use the bot
    """
    sendBotMessage( contributor.social_identifier, "To read a random story just send \"\\browse\"" )
    sendBotMessage( contributor.social_identifier, "to start a story just send \"\start\"" )
    sendBotMessage( contributor.social_identifier, "to read the story you are working on just send \"\\read\"" )
    sendBotMessage( contributor.social_identifier, "to continue a story just send \"\continue\"" )
    sendBotMessage( contributor.social_identifier, "to see a history of your stories just send \"history\"" )

def createStory( contributor ):
    story = Story.objects.create( title=generate_title("") )
    # create a new fragment for the story
    fragment = Fragment.objects.create(story=story, 
                                       fragment="", 
                                       alias=generate_alias(),
                                       position=0, 
                                       contributor=contributor)
                        
    # update the state of the contributor
    contributor.state = "writing"
    contributor.save()  
    # the story and fragment are created, so tell the user to start the story
    sendBotMessage(contributor.social_identifier, "You're starting a new story, you can start it!")

def joinStory(contributor, story):
    # create a fragment for the story
    fragment = Fragment.objects.create(story=story, 
                                       fragment="",
                                       alias=generate_alias(), 
                                       position= story.fragment_set.count(), 
                                       contributor=contributor)
    
    # update the state of the contributor
    contributor.state = "writing"
    contributor.save()
    # notify the user what they will be writing
    sendBotMessage(contributor.social_identifier, "We found a story for you to join, you will be writing the " + FRAGMENT_MAPPING.get(fragment.position))


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
            
            if created:
                sendBotMessage(contributor.social_identifier, "Thanks for joining StoryBot! Here are some tips.")
                sendHelpMessage( contributor )
                break  # we want to let the user input a choice
                
                
            
            if event.get('message') and event.get('message').get('text'):
                """Handle messages with text
                """
                
                message_text = event.get('message').get('text')
                
                
                if KEYWORD_START in message_text.lower():
                    """Handle the case that the user is attempting to start a new story 
                    """
                    # first let's check to make sure the user is not currently working on a Story
                    # a user can only work on one story at a time.
                    if Fragment.objects.filter(contributor=contributor).filter(complete=False).count() > 0:
                        sendBotMessage(contributor.social_identifier, "Looks like you are already writing a story. Finish that first, or discard it to start a new one")
                        
                    else:
                        sendBotMessage(contributor.social_identifier, "Great, let's find a story for you to join!")
                        
                        if Story.objects.filter(complete=False).count() > 0:
                            # there are some stories that are not complete 
                            stories = Story.objects.filter(complete=False).order_by('time_created')
                            
                            # get the first story (earliest) the user is already not a contributor to
                            for story in stories: 
                                if story.fragment_set.all().filter(contributor=contributor).count() == 0:
                                    # the contributor has not authored any of these story fragments 
                                    # so let's add them to it
                                    joinStory( contributor, story)
                                    # since the user is joining a story that already has some content
                                    # we should read it back to the user
                                    readBackStory( contributor, story)
                                    break # short circuit the for loop, no need to look for more 
                                    
                            if contributor.state != "writing":
                                # none of the incomplete stories had availible slots for the user, so we are going 
                                # to create a new story for the user
                                createStory( contributor )
                        else:
                            # all stories are complete, so we should create a new one
                            createStory( contributor )
                            
                
                elif KEYWORD_DONE in message_text.lower():
                    """Handle the case that the user is attempting to finish a story fragment 
                    """
                    # the user should only have one incomplete fragment at a time, so 
                    # let's get it and update it
                    fragment = contributor.fragment_set.all().filter(complete=False).first()
                    
                    if fragment:
                        story = fragment.story
                        
                        # Mark the contributor specific fragment done
                        fragment.complete = True
                        fragment.save()
                        
                        # Update the contributor state
                        contributor.state = "browsing"
                        contributor.save()
                        
                        sendBotMessage( contributor.social_identifier, "Thanks! We will notify you when the story is done" )
                        
                        # Check if all the fragments are done
                        if Fragment.objects.filter(story=story).filter(complete=True).count() == 3:
                            # all the fragments are done, so let's mark the story done
                            story.complete = True
                            story.save()
                            # notify all the participants their story is done
                            story_fragments = Fragment.objects.filter(story=story)
                            # Notify the contributors the story is done and send them a message with it
                            for fragment in story_fragments:
                                sendBotMessage( fragment.contributor.social_identifier, "One of your stories is complete! Respond with \\read " + str(story.id) + " to see it" )
                                
                
                elif KEYWORD_READ in message_text.lower():
                    """Handle the case that the user is attempting to read a specific story 
                    """
                    # check if the message also had an id for the story
                    if hasNumber(message_text):
                        try:
                            story_id = int(message_text.split(' ')[1])
                            story = Story.objects.get(id=story_id)
                            readBackStory( contributor, story )
                        except Exception as e:
                            sendBotMessage( contributor.social_identifier, "Sorry we could not find that story" )
                            
                    else:
                        # if not, read back the story the user is working on
                        fragment = contributor.fragment_set.all().order_by('time_created').last()
                        story = fragment.story
                        sendBotMessage( contributor.social_identifier, "This is the last story you worked on" )
                        readBackStory(contributor, story)
                        
                
                elif KEYWORD_CONTINUE in message_text.lower() or contributor.state == 'writing':
                    """Handle the case that the user is attempting to continue a story 
                    """ 
                    if KEYWORD_CONTINUE in message_text.lower():
                        # If the user just says \continue we should read back the story
                        # to them to remind them where they are at.
                        
                        # the user should only have one incomplete fragment at a time, so 
                        # let's get it and update it
                        fragment = contributor.fragment_set.all().filter(complete=False).first()
                        if fragment:
                            sendBotMessage(contributor.social_identifier, "Here is the story so far...")
                            story = fragment.story
                            readBackStory(contributor, story)
                        else:
                            sendBotMessage(contributor.social_identifier, "It doesn't seem you are working on a story. Send \"\start\" to join a new story")
                            
                    else:
                        # the user is just inputing text, while in the 'writing' state
                        # so let's add it to the focused fragment
                        
                        # the user should only have one incomplete fragment at a time, so 
                        # let's get it and update it
                        fragment = contributor.fragment_set.all().filter(complete=False).first()
                        if fragment:
                            fragment.fragment = fragment.fragment + " " + message_text
                            fragment.save()
                            sendBotMessage(contributor.social_identifier, "Adding that to your part of the story, \"\\done\" to finish.")
                            
                
                elif KEYWORD_HISTORY in message_text.lower():
                    """Handle the case that the user is attempting to see a history of their writing 
                    """
                    sendBotMessage(contributor.social_identifier, "Here is a history of your stories. Send \"\\read <story id>\" to read a story")
                    
                    fragments = Fragment.objects.filter(contributor=contributor).order_by('time_created')
                    stories = []
                    for fragment in fragments:
                        stories.append( fragment.story )
                        
                    for story in stories:
                        complete = "COMPLETE" if story.complete else "INCOMPLETE"
                        sendBotMessage(contributor.social_identifier,  "["+complete+"] Story id: " + str(story.id))    
                        
                
                elif KEYWORD_DISCARD in message_text.lower():
                    """Handle the case that the user is attempting to discard his fragment 
                    """
                    fragment = Fragment.objects.filter(contributor=contributor).filter(complete=False).first()
                    if fragment:
                        # erase the contents of the fragment
                        fragment.fragment = ""
                        fragment.save()
                        sendBotMessage(contributor.social_identifier,  "Your story fragment has been erased, you can start writing it again")
                        sendBotMessage(contributor.social_identifier,  "Here is the story so far")
                        readBackStory(contributor, fragment.story)
                    else:
                        sendBotMessage(contributor.social_identifier,  "You have no story drafts to discard")
                        
                        
                
                elif KEYWORD_BROWSE in message_text.lower():
                    """Handle the case that the user is attempting to read a random story 
                    """
                    contributor.state = 'browsing'
                    contributor.save()
                    
                    # get a random story
                    story = Story.objects.order_by('?').first()
                    
                    if story:
                        sendBotMessage(contributor.social_identifier, "Here is a random story")
                        readBackStory(contributor, story)
                    else:
                        sendBotMessage(contributor.social_identifier, "Looks like we can't find any stories right now. Send \"\\start\" to start one!")
                        
                
                elif KEYWORD_HELP in message_text.lower():
                    """Handle the case that the user is attempting to get help 
                    """
                    sendHelpMessage( contributor )
                
                else:
                    """Handle the case that we hanvt thought about 
                    """
                    sendBotMessage(contributor.social_identifier, "Sorry, I didn't get that :( Here are some tips!")
                    sendHelpMessage( contributor )
                    
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


import os
import json
import requests

from django.conf import settings

from .fb_chat_buttons import *
from .keywords import *
from .helpers import *
from .models import Contributor, Story, Fragment, WRITING

import content_generators

FB_TOKEN = os.environ.get("FB_TOKEN")
FB_URL = os.environ.get("FB_URL")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")



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
    
    r = requests.post(FB_URL, 
                      params = { 'access_token': FB_TOKEN },
                      headers = {'content-type': 'application/json'},
                      data = json.dumps(responseBody) )


def sendBotStructuredImageMessage(recipient, img_url):
    """Send a facebook structured image message
    Use this for prompts and navigation
    """
    responseBody = {
        'recipient': { 
            'id': recipient
        },
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url":img_url
                }
            }
        }         
    }

    r = requests.post(FB_URL, 
                  params = { 'access_token': FB_TOKEN },
                  headers = {'content-type': 'application/json'},
                  data = json.dumps(responseBody) )
    
def sendBotStructuredButtonMessage(recipient, text, buttons=[]):
    """Send a facebook structured button message
    Use this for prompts and navigation
    """
    responseBody = {
        'recipient': { 
            'id': recipient
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text":text,
                    "buttons":buttons
                }
            }
        }
         
    }
    
    r = requests.post(FB_URL, 
                  params = { 'access_token': FB_TOKEN },
                  headers = {'content-type': 'application/json'},
                  data = json.dumps(responseBody) )

def sendHelpMessage( contributor ):
    """Sends a help message with the instructions on how to use the bot
    """
    sendBotMessage( contributor.social_identifier, "To read a random story just send \"\\browse\"" )
    sendBotMessage( contributor.social_identifier, "to start a story just send \"\start\"" )
    sendBotMessage( contributor.social_identifier, "to read the story you are working on just send \"\\read\"" )
    sendBotMessage( contributor.social_identifier, "to continue a story just send \"\continue\"" )
    sendBotMessage( contributor.social_identifier, "to see a history of your stories just send \"history\"" )
    

def readBackFragment( contributor, fragment ):
    """read back a fragment and properly chunks it up where necessary
    """
    if fragment:
        text = ""
        text += fragment.fragment if fragment.fragment is not "" else "[Nothing has been written yet]" 
        fragment_chunks = chunkString(text, 180)
        for chunk in fragment_chunks:
            sendBotMessage(contributor.social_identifier, "<(\") " + "\"" + chunk + "\"")

def readBackStory( contributor, story ):
    """Reads the story back and makes sure it chunks it appropriately
    """

    story_fragments = Fragment.objects.filter(story=story).order_by('position')[:5]
    
    story_snippet = ""
    for f in story_fragments:
        story_snippet += f.fragment if f.fragment is not "" else "[Nothing has been written yet]"
    
    story_snippet = "<(\") \"" + story_snippet[:100] + "...\""
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                   story_snippet,
                                   [{
                                        "type": "web_url",
                                        "title": "Read the story",
                                        "url": settings.BASE_URL + "/stories/" + str(story.id)
                                    }])

def notifyOnStoryCompletion( story ):
    # we want to get the contributors from the fragments 
    # rather than the story since ppl may have left, and we want 
    # to notify them as well
    contributors = []
    fragments = story.fragment_set.all().order_by('position')
    for fragment in fragments:
        if fragment.contributor not in contributors:
            contributors.append(fragment.contributor)
    
    for contributor in contributors:
        contributor.reset_temp_alias()
        contributor.set_active_story(0)
        sendBotStructuredButtonMessage(contributor.social_identifier,
                                       ":|] Looks like one of your stories is complete!",
                                       [{
                                            "type": "web_url",
                                            "title": "Read the story",
                                            "url": settings.BASE_URL + "/stories/" + str(story.id)
                                        }, 
                                        BUTTON_JOIN, 
                                        BUTTON_BROWSE])   
    
    # post to facebook as well
    # TBD - update the fb token
    # postStoryToFacebook( story ) 
    

def notifyOnStoryUpdate( story ):
    """notify everyone that the story was just updated
    """
    contributors = story.contributors.all()
    last_complete_fragment = story.get_last_complete_fragment()
    if last_complete_fragment:
        for contributor in contributors:
            if contributor == last_complete_fragment.contributor:
                sendBotMessage(contributor.social_identifier, ":|] We will notify you when it is your turn again!" )
            else:
                sendBotMessage(contributor.social_identifier, ":|] Story Updated by " + last_complete_fragment.alias)
                readBackFragment(contributor, last_complete_fragment)
        
def remindInactiveContributor( contributor ):
    """notifies a contributor who has been inactive for a while
    and gives them an opportunity to leave or finish their story
    """
    last_fragment = contributor.get_last_fragment()
    last_story = last_fragment.story
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                       ":|] Hey, it's still your turn! Don't keep the others waiting.",
                                       [{
                                            "type": "web_url",
                                            "title": "Read the story",
                                            "url": settings.BASE_URL + "/stories/" + str(last_story.id)
                                        },  
                                        BUTTON_DONE,
                                        BUTTON_LEAVE])

def notifyKickedContributor( contributor ):
    """notifies a contributor that they are dropped from the story
    """
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                       ":|] Hey, you've been inactive for too long, so we've removed you from the story. You still will be notified when the story is done!",
                                       [BUTTON_JOIN,
                                        BUTTON_READ,
                                        BUTTON_HISTORY])        


def postStoryToFacebook( story ):
    """Posts story snippet to the facebook page
    ref: https://developers.facebook.com/docs/graph-api/reference/v2.6/page/feed#publish
    """
    r = requests.post("https://graph.facebook.com/v2.6/" + FB_PAGE_ID + "/feed", 
                  params = { 'access_token': FB_TOKEN },
                  headers = {'content-type': 'application/json'},
                  data = json.dumps({
                      "message": "Hello world"
                  }) )
    print r.json()


def notifyContributorOnTurn( contributor, story, short=True ):
    """Send a notification to the user that it is their turn
    """
    n = story.calculate_remaining_number_of_turns( contributor )
    msg = "It's your turn, you have %d turns left" % (n, )
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(story.id)
                },
               BUTTON_OPTIONS]
               
    if short:
        sendBotMessage(contributor.social_identifier, msg)
    else:
        sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)


"""
Flare
"""
def flareOnSearch( contributor ):
    """
    """
    print "flareOnSearch()"
    img_url = content_generators.generate_search_img()
    sendBotStructuredImageMessage( contributor.social_identifier, img_url)

def flareOnRead( contributor ):
    """
    """
    print "flareOnRead()"
    img_url = content_generators.generate_read_img()
    sendBotStructuredImageMessage( contributor.social_identifier, img_url)

def flareOnDone( contributor ):
    """
    """
    print "flareOnDone()"
    img_url = content_generators.generate_done_img()
    sendBotStructuredImageMessage( contributor.social_identifier, img_url)

"""
Call to Actions
"""

def ctaOnAccountCreation( contributor ):
    """Call to Action on first time using the bot
    """
    print "ctaOnAccountCreation()"
    sendBotMessage(contributor.social_identifier, "Thanks for joining StoryBot %s!" % contributor.first_name)
    sendBotMessage(contributor.social_identifier, "Welcome! StoryBot is a writing game, where you get paired up with another random participant and take turns writing a story through messenger. We start you off with a writing prompt and will notify you every time it is your turn by sending you a friendly message.")
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                    "Let's get started",
                                    [BUTTON_JOIN, BUTTON_BROWSE])

def ctaOptionsMenu( contributor ):
    """Call to Action menu for general options
    """
    print "ctaOptionsMenu()"
    msg = "What would you like to do?"
    buttons = []
    if contributor.state == WRITING:
        buttons.append(BUTTON_LEAVE)
    else:
        buttons.append(BUTTON_JOIN)
    buttons.append(BUTTON_READ)
    buttons.append(BUTTON_HISTORY)
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons )

def ctaNewStoryOnCreation( contributor, story ):
    """Call To Action for succesfully joining a story by being the first
    """
    print "ctaNewStoryOnCreation()"
    n = story.calculate_remaining_number_of_turns( contributor )
    prompt = story.prompt
    alias = contributor.temp_alias
    msg = "Here is a story for you to start off, you will have %d turns and be called \"%s\"! Here is the prompt: \"%s\"" % (n, alias, prompt,)
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(story.id)
                },
               BUTTON_SKIP, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons ) 

def ctaNewStoryOnJoin( contributor, story ):
    """Call to Action for succesfully joining a story that has already been started
    """
    print "ctaNewStoryOnJoin()"
    n = story.calculate_remaining_number_of_turns( contributor )
    alias = contributor.temp_alias
    msg = "Here is a story for you to join, you will have %d turns and be called \"%s\"! I'll message you when it's your turn." % (n, alias, )
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(story.id)
                },
               BUTTON_SKIP, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons )

def ctaNewStoryOnBusy( contributor, story ):
    """Call To Action for not joining a story because the
    contributor is already writing another story
    """
    print "ctaNewStoryOnBusy()"
    msg = ""
    buttons = []
    
    last_fragment = contributor.get_last_fragment()
    
    if last_fragment:
        n = story.calculate_remaining_number_of_turns( contributor )
        alias = contributor.temp_alias
        msg += "Seems like you are already working on another story under the alias \"%s\" and have %d turns left. Finish or leave the story before starting a new one." % (alias, n)
        buttons.append({
                           "type": "web_url",
                           "title": "Read the story",
                           "url": settings.BASE_URL + "/stories/" + str(story.id)
                        })
        buttons.append(BUTTON_LEAVE)
    else:
        msg += "Something broke, sorry."
    
    buttons.append(BUTTON_OPTIONS)
        
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons )




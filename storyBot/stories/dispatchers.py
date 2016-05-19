import os
import json
import requests

from django.conf import settings

from .fb_chat_buttons import *
from .keywords import *
from .helpers import *
from .models import Contributor, Story, Fragment


FB_TOKEN = os.environ.get("FB_TOKEN")
FB_URL = os.environ.get("FB_URL")

def sendBotMessage(recipient, message, first_person=False):
    """A script to send a facebook message to recipient
    """
    
    if first_person:
        message = "[StoryBot] " + message
    
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

def sendBotStructuredGenericMessage(recipient, title, item_url=None, image_url=None, subtitle=None, buttons=[]):
    """ref: https://developers.facebook.com/docs/messenger-platform/send-api-reference#welcome_message_configuration
            https://developers.facebook.com/docs/messenger-platform/send-api-reference#guidelines 
    
    Regarding buttons:
        {
            "type":"web_url",
            "title":"View Website",
            "url":"https://www.petersbowlerhats.com"
        },
        {
            "type":"postback",
            "title":"Start Chatting",
            "payload":"DEVELOPER_DEFINED_PAYLOAD"
        }
    """
    
    responseBody = {
        'recipient': { 
            'id': recipient
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": title,
                            "item_url": item_url,
                            "image_url": image_url,
                            "subtitle": subtitle,
                            "buttons": buttons
                        }
                    ]
                }
            }
        }
         
    }
    
    requests.post(FB_URL, 
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
    contributors = story.contributors.all()
    for contributor in contributors:
        contributor.reset_temp_alias()
        sendBotStructuredButtonMessage(contributor.social_identifier,
                                       ":|] Looks like one of your stories is complete!",
                                       [{
                                            "type": "web_url",
                                            "title": "Read the story",
                                            "url": settings.BASE_URL + "/stories/" + str(story.id)
                                        }, 
                                        BUTTON_JOIN, 
                                        BUTTON_BROWSE])   

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

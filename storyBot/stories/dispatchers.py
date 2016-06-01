import os
import json
import requests

from django.conf import settings

from .fb_chat_buttons import *
from .keywords import *
from .models import Contributor, Story, Fragment, WRITING

import content_generators
import helpers

FB_TOKEN = os.environ.get("FB_TOKEN")
FB_URL = os.environ.get("FB_URL")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")


"""
-----FaceBook Interface
"""

def sendBotMessage(recipient, message):
    """A script to send a facebook message to recipient
    """
    request_data = { 
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
                      data = json.dumps(request_data) )
    # print r.json()

def sendBotStructuredImageMessage(recipient, img_url):
    """Send a facebook structured image message
    Use this for prompts and navigation
    """
    # print "sendBotStructuredImageMessage()"
    request_data = {
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
                  data = json.dumps(request_data) )
    # print r.json()

def sendBotStructuredButtonMessage(recipient, text, buttons=[]):
    """Send a facebook structured button message
    Use this for prompts and navigation
    """
    # print "sendBotStructuredButtonMessage()"
    request_data = {
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
                  data = json.dumps(request_data) )    
    # print r.json()
    
    
"""
-----Flare
"""
def flareOnSearch( contributor ):
    """
    """
    # print "flareOnSearch()"
    img_url = content_generators.generate_search_img()
    sendBotStructuredImageMessage( contributor.social_identifier, img_url)

def flareOnRead( contributor ):
    """
    """
    # print "flareOnRead()"
    img_url = content_generators.generate_read_img()
    # sendBotStructuredImageMessage( contributor.social_identifier, img_url)

def flareOnDone( contributor ):
    """
    """
    # print "flareOnDone()"
    img_url = content_generators.generate_done_img()
    sendBotStructuredImageMessage( contributor.social_identifier, img_url)
    

"""
-----Read Story
"""

def readBackFragment( contributor, fragment ):
    """read back a fragment and properly chunks it up where necessary
    """
    # print "readBackFragment()"
    if fragment:
        text = ""
        text += fragment.fragment if fragment.fragment is not "" else "[ Nothing has been written yet ]" 
        fragment_chunks = helpers.chunkString(text, 180)
        for chunk in fragment_chunks:
            sendBotMessage(contributor.social_identifier, "<(\") " + "\"" + chunk + "\"")

def readBackStory( contributor, story ):
    """Reads the story back and makes sure it chunks it appropriately
    """
    # print "readBackStory()"
    story_fragments = Fragment.objects.filter(story=story).order_by('position')[:5]
    
    story_snippet = ""
    for f in story_fragments:
        story_snippet += f.fragment if f.fragment is not "" else "[ Nothing has been written yet ]"
    
    story_snippet = "<(\") \"" + story_snippet[:100] + "...\""
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                   story_snippet,
                                   [{
                                        "type": "web_url",
                                        "title": "Read the story",
                                        "url": settings.BASE_URL + "/stories/" + str(story.id)
                                    }])

def readBackContributorHistory( contributor ):
    """
    """
    # print "readBackContributorHistory()"
    stories = Story.objects.filter(contributors__in=[contributor])
    chunk_size = 3 #fb allows only 3 buttons at a time
    story_chunks = [stories[i:i + chunk_size] for i in range(0, len(stories), chunk_size)]
    
    # print story_chunks
    
    sendBotMessage( contributor.social_identifier, ":|] Here is a history of your stories") 
    for i, story_chunk in enumerate(story_chunks):
        buttons = []
        for story in story_chunk:
            # print story
            msg = "[%d/%d]" % ( (i+1), len(story_chunks) )
            buttons.append({
                                "type": "web_url",
                                "title": story.prompt[:15] + "...",
                                "url": settings.BASE_URL + "/stories/" + str(story.id)
                            })
        sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)
    
    msg = ":|] What would you like to do now?"
    buttons = [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)

"""
-----Notifications
"""

def notifyOnStoryCompletion( story ):
    # we want to get the contributors from the fragments 
    # rather than the story since ppl may have left, and we want 
    # to notify them as well
    # print "notifyOnStoryCompletion()"
    contributors = []
    fragments = story.fragment_set.all().order_by('position')
    for fragment in fragments:
        if fragment.contributor not in contributors:
            contributors.append(fragment.contributor)
    
    for contributor in contributors:
        contributor.reset_temp_alias()
        contributor.set_active_story(0)
        
        flareOnDone( contributor )
        
        msg = ":|] Looks like one of your stories is complete!"
        buttons = [{
                        "type": "web_url",
                        "title": "Read the story",
                        "url": settings.BASE_URL + "/stories/" + str(story.id)
                    }, 
                    BUTTON_JOIN, 
                    BUTTON_OPTIONS]
        sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)

def notifyOnStoryUpdate( story ):
    """notify everyone that the story was just updated
    """
    # print "notifyOnStoryUpdate()"
    contributors = story.contributors.all()
    # print contributors
    last_complete_fragment = story.get_last_complete_fragment()
    if last_complete_fragment:
        for contributor in contributors:
            if contributor == last_complete_fragment.contributor:
                sendBotMessage(contributor.social_identifier, ":|] I'll notify you when it is your turn again!" )
            else:
                sendBotMessage(contributor.social_identifier, ":|] Story Updated by " + last_complete_fragment.alias)
                readBackFragment(contributor, last_complete_fragment)

def notifyNextContributor( contributor, story ):
    """notify the next contributor its their turn
    """
    # print "notifyNextContributor()"
    n = story.calculate_remaining_number_of_turns( contributor )
    msg = ":|] It's your turn and you have %d turns left. (just send us a message and we'll add it to your story's part)" % n
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(story.id)
                }, BUTTON_OPTIONS] 
    # check if this is the last fragment
    last = story.fragment_set.all().order_by('position').last() == contributor.get_last_fragment()           
    if last:
        msg += " This will be the end of the story!"
    sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)
    
def remindInactiveContributor( contributor ):
    """notifies a contributor who has been inactive for a while
    and gives them an opportunity to leave or finish their story
    """
    # print "remindInactiveContributor()"
    last_fragment = contributor.get_last_fragment()
    last_story = last_fragment.story
    msg = ":|] Hey, it's still your turn! Don't keep the others waiting."
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(last_story.id)
                }, BUTTON_DONE, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)

def notifyKickedContributor( contributor ):
    """notifies a contributor that they are dropped from the story
    """
    # print "notifyKickedContributor()"
    msg = ":|] Hey, you've been inactive for too long, so we've removed you from the story. You still will be notified when the story is done!"
    buttons = [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY]
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                       msg,
                                       )        

def notifyContributorOnTurn( contributor, story, short=True ):
    """Send a notification to the user that it is their turn
    """
    # print "notifyContributorOnTurn()"
    n = story.calculate_remaining_number_of_turns( contributor )
    msg = ":|] It's your turn, you have %d turns left" % (n, )
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
-----Call to Actions
"""

def ctaOnAccountCreation( contributor ):
    """Call to Action on first time using the bot
    """
    # print "ctaOnAccountCreation()"
    sendBotMessage(contributor.social_identifier, ":|] Thanks for joining StoryBot %s!" % contributor.first_name)
    sendBotMessage(contributor.social_identifier, ":|] StoryBot is a writing game, where you get paired up with another random participant and take turns writing a story through messenger. We start you off with a writing prompt and will notify you every time it is your turn by sending you a friendly message.")
    sendBotStructuredButtonMessage(contributor.social_identifier,
                                    ":|] Let's get started!",
                                    [BUTTON_JOIN, BUTTON_BROWSE])

def ctaOptionsMenu( contributor ):
    """Call to Action menu for general options
    """
    # print "ctaOptionsMenu()"
    msg = ":|] What would you like to do now?"
    buttons = []
    if contributor.is_busy():
        buttons.append(BUTTON_LEAVE)
    else:
        buttons.append(BUTTON_JOIN)
    buttons.append(BUTTON_BROWSE)
    buttons.append(BUTTON_HISTORY)
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons )

def ctaNewStoryOnCreation( contributor, story ):
    """Call To Action for succesfully joining a story by being the first
    """
    # print "ctaNewStoryOnCreation()"
    n = story.calculate_remaining_number_of_turns( contributor )
    prompt = story.prompt
    alias = contributor.temp_alias
    msg = ":|] Here is a story for you to start off, you will have %d turns and be called \"%s\"! Here is the prompt: \"%s\"" % (n, alias, prompt,)
    if len(msg) > 300:
        # we should chunk it
        chunks = helpers.chunkString(msg, 300)
        msg = ":|] Ready?"
        for chunk in chunks:
            sendBotMessage(contributor.social_identifier, chunk)
    buttons = [{
                    "type": "web_url",
                    "title": "Read the story",
                    "url": settings.BASE_URL + "/stories/" + str(story.id)
                },
               BUTTON_SKIP, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons )
    sendBotMessage( contributor.social_identifier, ":|] Just message me and I'll add your message to the story!" ) 

def ctaNewStoryOnJoin( contributor, story ):
    """Call to Action for succesfully joining a story that has already been started
    """
    # print "ctaNewStoryOnJoin()"
    n = story.calculate_remaining_number_of_turns( contributor )
    alias = contributor.temp_alias
    msg = ":|] Here is a story for you to join, you will have %d turns and be called \"%s\"! I'll message you when it's your turn." % (n, alias, )
    if len(msg) > 300:
        # we should chunk it
        chunks = helpers.chunkString(msg, 300)
        msg = "Ready?"
        for chunk in chunks:
            sendBotMessage(contributor.social_identifier, chunk)
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
    # print "ctaNewStoryOnBusy()"
    msg = ""
    buttons = []
    
    last_fragment = contributor.get_last_fragment()
    
    if last_fragment:
        n = story.calculate_remaining_number_of_turns( contributor )
        alias = contributor.temp_alias
        msg += ":|] Seems like you are already working on another story under the alias \"%s\" and have %d turns left. Finish or leave the story before starting a new one." % (alias, n)
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

def ctaLeftStory( contributor ):
    """Call To Action for when a user leaves a story
    """
    msg = ":|] You've left the story. We'll keep your submitted work for this story and notify you when the story is complete"
    buttons = [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY]    
    sendBotStructuredButtonMessage( contributor.social_identifier, msg, buttons)

def ctaConfirmEdit( contributor ):
    """
    """
    msg = ":|] Got it! You can tell me more or finish your turn."
    buttons = [BUTTON_DONE, BUTTON_UNDO, BUTTON_OPTIONS]
    sendBotStructuredButtonMessage(contributor.social_identifier, msg, buttons)


"""
-----Other
"""
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
    # print r.json()


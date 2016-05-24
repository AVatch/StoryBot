import random
import math

import os
import json
import requests

from django.db.models import Count
from django.conf import settings

from .keywords import *
from .fb_chat_buttons import *
from .helpers import *
from .content_generators import generate_alias
from .models import Contributor, Story, Fragment
from .models import BROWSING, WRITING, NAMING, SPEAKING
  
import story_utilities
import dispatchers


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


def handle_join( contributor ):
    """Join a story
    """
    # First let's check to make sure the user is not currently working on
    # a story
    
    if contributor.is_busy():
        fragment = contributor.get_last_fragment()
        if fragment:
            # remind the user what they are working on
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] Looks like you are in the middle of a story! Finish or leave it before starting another one.")
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                    ":|] Your alias for this story is " + fragment.alias,
                                                    [{
                                                            "type": "web_url",
                                                            "title": "Read the story",
                                                            "url": settings.BASE_URL + "/stories/" + str(fragment.story.id)
                                                        }, BUTTON_LEAVE])
        else:
            print "FAILED TO GET LAST FRAGMENT"
    else:
        available_story = Story.objects.filter(complete=False) \
                                       .filter(full=False) \
                                       .exclude(contributors__in=[contributor]) \
                                       .order_by('?') \
                                       .first()
        
        if available_story:
            # join the story
            story = story_utilities.joinStory(contributor, available_story)
            contributor.temp_alias = generate_alias()
            contributor.save()

            # tell the user they are paired up
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                        ":|] We've found a story for you to join! For this story you will be called " + contributor.temp_alias,
                                                        [{
                                                                "type": "web_url",
                                                                "title": "Read the story",
                                                                "url": settings.BASE_URL + "/stories/" + str(story.id)
                                                            }, BUTTON_LEAVE])
            
            # check if the other people are done and it is your turn
            if story.are_all_populated_fragments_done():
                # Associate the next story fragment with the contributor
                story.associate_fragment_with_contributor(contributor)
                dispatchers.sendBotMessage(contributor.social_identifier, ":|] It's your turn, you have " + str(story.calculate_remaining_number_of_turns(contributor )) + " turns left, send us a message to add it to the story!")
            else:            
                dispatchers.sendBotMessage(contributor.social_identifier, ":|] We'll let you know when it's your turn!")
            
        else:
            # create a new one
            s, f = story_utilities.createStory(contributor)
            # the story and fragment are created, so tell the user to start the story
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] You're starting a new story!")
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] Your alias for this story will be' " + f.alias + " and will have " + str( s.calculate_remaining_number_of_turns( contributor ) ) + " turns.")

            dispatchers.sendBotMessage(contributor.social_identifier, ":|] Here is some inspiration if you need it!")
            dispatchers.sendBotMessage(contributor.social_identifier, "o.O " + s.prompt)
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] You can start writing.")
            

def handle_done( contributor ):
    """handles the case when a user says they are done with their fragment
    """
    # get the last fragment the user was working on
    fragment = contributor.get_last_fragment()
    
    if story_utilities.markFragmentAsDone( fragment ):
        # fragment is done
        
        story = fragment.story
        if story.is_story_done():
            # the story is done, mark it complete
            story.mark_complete()
            # update everyone that story is done
            dispatchers.notifyOnStoryCompletion(story)
        else:
            # the story is not done, so update everyone about the latest update
            dispatchers.notifyOnStoryUpdate(story)
            # now figure out the next person who is up
            next_contributor = story.get_next_contributor()
            
            if next_contributor and next_contributor.id != contributor.id:
                next_fragment = story.associate_fragment_with_contributor(next_contributor)
                
                if next_fragment:
                    # notify the next contributor it's their turn
                    dispatchers.sendBotStructuredButtonMessage(next_contributor.social_identifier,
                                                        ":|] It's your turn, you have " + str( story.calculate_remaining_number_of_turns( next_contributor ) ) + " turns left. (just send us a message and we'll add it to your story's part)",
                                                        [{
                                                            "type": "web_url",
                                                            "title": "Read the story",
                                                            "url": settings.BASE_URL + "/stories/" + str(story.id)
                                                        }])
                else:
                    print "FAILED TO CREATE NEXT FRAGMENT"
                
            else:
                print "FAILED TO GET THE NEXT CONTRIBUTOR"
    
    else:
        # fragment did not exist or was not written
        dispatchers.sendBotMessage(contributor.social_identifier, ":|] Looks like you havn't written anything!")
    

def handle_undo( contributor ):
    if contributor.state == WRITING:
        fragment = contributor.get_last_fragment()
        
        if fragment and fragment.last_edit:
            f = story_utilities.undoLastEdit( contributor )
            dispatchers.sendBotMessage( contributor.social_identifier, ":|] Undo done, here is what you have so far" )
            dispatchers.readBackFragment( contributor, f )
        else:
            dispatchers.sendBotMessage( contributor.social_identifier, ":|] Sorry, I can't undo this.")
        
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   ":|] What would you like to do now?",
                                                   [BUTTON_DONE, {
                                                        "type": "web_url",
                                                        "title": "Read the story",
                                                        "url": settings.BASE_URL + "/stories/" + str(f.story.id)
                                                    }])
                                                   
    else:
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   ":|] It doesn't look like you are writing anything at the moment",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_leave( contributor ):
    """Handle the case that the user is attempting to leave the story
    """
    active_story = contributor.active_story
    if active_story:
        active_story = Story.objects.get(id=active_story)
        active_story.remove_contributor( contributor )
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   ":|] You just left the story",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])
    else:
        dispatchers.sendBotMessage(contributor.social_identifier,  "You are not working on any story")
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   ":|] What would you like to do?",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])



def handle_browse( contributor ):
    """Handle the case that the user is attempting to read a random story 
    """    
    # get a random story
    story = Story.objects.filter(complete=True).order_by('?').first()
    if story:
        dispatchers.sendBotMessage(contributor.social_identifier,  ":|] Here is a random story")
        dispatchers.readBackStory( contributor, story )
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                            ":|] What would you like to do now?",
                                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])
    else:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                            ":|] Well this is embarassing, we can't find any stories",
                                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_history( contributor ):
    """Handle the case that the user is attempting to see a history of their writing 
    """
    dispatchers.sendBotMessage(contributor.social_identifier, ":|] Here is a history of your stories")

    stories = Story.objects.filter(contributors__in=[contributor])
    
    chunk_size = 3 # fb lets us put only 3 buttons at a time
    story_chunks = [stories[i:i + chunk_size] for i in range(0, len(stories), chunk_size)]
    
    for i, story_chunk in enumerate(story_chunks):
        buttons = []
        for story in story_chunk:
            buttons.append({
                                "type": "web_url",
                                "title": "Story " + str(story.id),
                                "url": settings.BASE_URL + "/stories/" + str(story.id)
                            })
    
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[" + str(i+1) + "/" + str(len(story_chunks)) +  "]",
                                                buttons)
        
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                            ":|] What would you like to do now?",
                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])
    

def handle_help( contributor, detail_level=3 ):
    """Send a message to the user with all availble options
    the bot supports.
    """
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                            ":|] Here are the basics",
                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])


def handle_create( contributor):
    """
    """
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


"""Define the bot action handlers to their mapped keywords
"""
BOT_HANDLER_MAPPING = {
    KEYWORD_JOIN: handle_join,
    KEYWORD_DONE: handle_done,
    KEYWORD_UNDO: handle_undo,
    KEYWORD_LEAVE: handle_leave,
    KEYWORD_BROWSE: handle_browse,
    KEYWORD_HISTORY: handle_history,
    KEYWORD_HELP: handle_help,
    KEYWORD_CREATE: handle_create
}

def process_postback_message( contributor, payload ):
    """FB provides postbacks where we can designate
    arbitrary data. For this bot, we are providing
    the processed triggers
    The payload should map directly to our keywords
    since we defined the values
    """
    
    if hasNumber(payload):
        story_id = int(payload.split(' ')[1])
        BOT_HANDLER_MAPPING[ KEYWORD_READ ]( contributor, story_id )
    else:
        print '*'*50
        print payload
        BOT_HANDLER_MAPPING[ payload ]( contributor )

def process_raw_message( contributor, payload ):
    """In the event the user sends us a message, 
    handle it here.
    We first need to parse it and normalize it
    The order of the if elif else matters here as higher
    cases will be given higher precident
    """
    processed_payload = payload.lower()
    if KEYWORD_HELP in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_HELP]( contributor )
    elif KEYWORD_JOIN in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_JOIN]( contributor )
    elif KEYWORD_DONE in processed_payload:
        BOT_HANDLER_MAPPING[ KEYWORD_DONE ]( contributor ) 
    elif KEYWORD_LEAVE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_LEAVE]( contributor )
    elif KEYWORD_HISTORY in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_HISTORY]( contributor )
    elif KEYWORD_BROWSE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_BROWSE]( contributor )
    else:
        if contributor.state == WRITING:
            fragment = story_utilities.updateStory( contributor, payload )
            story = fragment.story
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                       ":|] Got it! You can tell me more or finish your turn.",
                                                       [BUTTON_DONE, BUTTON_UNDO])
        else:
            # we didn't understand the input so show user all
            # availible options
            BOT_HANDLER_MAPPING[KEYWORD_HELP]( contributor )

def process_img_message( contributor, payload ):
    """In the event the user sends us some rich
    media message. At this moment, story bot will
    simply respond with a cute message as we do not 
    have any support for media in these stories
    """
    pass


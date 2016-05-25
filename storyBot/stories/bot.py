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




def handle_options( contributor ):
    """Handle the case for a general menu of options
    """
    dispatchers.ctaOptionsMenu( contributor )


def handle_join( contributor, ignore_story_ids=None ):
    """Join a story
    """
    # send some flare
    dispatchers.flareOnSearch( contributor )
    
    if contributor.is_busy():
        """ the contributor is currently busy so they need to
        finish or leave their current story before starting a new one
        """
        try:
            active_story = Story.objects.get( id=contributor.active_story )
        except Story.DoesNotExist:
            active_story = None
        
        if active_story:
            dispatchers.ctaNewStoryOnBusy( contributor, active_story )
        else:
            dispatchers.sendBotMessage( contributor.social_identifier, ":|] You broke me, sorry!" )
            dispatchers.ctaOptionsMenu( contributor )
        
    else:
        """ the contributor is availible to start/join a new story
        """
        available_story = Story.objects.filter(complete=False) \
                                       .filter(full=False) \
                                       .exclude(contributors__in=[contributor])
        if ignore_story_ids:
            available_story = available_story.exclude(id__in=ignore_story_ids)

        # pick a random story from the set of stories
        available_story = available_story.order_by('?').first()
        
        if available_story:
            # join the story
            story_utilities.joinStory(contributor, available_story)            
        else:
            # create a new one
            story_utilities.createStory(contributor)

def handle_done( contributor ):
    """handles the case when a user says they are done with their fragment
    """
    print "handle_done()"
    # get the last fragment the user was working on
    fragment = contributor.get_last_fragment()
    if fragment and story_utilities.markFragmentAsDone( fragment ):
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
            # now figure out who the next person is
            next_contributor = story.get_next_contributor()

            if next_contributor and next_contributor.id != contributor.id:
                next_fragment = story.associate_fragment_with_contributor(next_contributor)
                
                if next_fragment:
                    # notify the next contributor it's their turn
                    dispatchers.notifyNextContributor( next_contributor, story )
                else:
                    # the next fragment does not exist
                    pass
                
            else:
                # the next contributor is the current contributor
                pass
    
    else:
        # fragment did not exist or was not written
        dispatchers.sendBotMessage( contributor.social_identifier, ":|] Looks like you havn't written anything!" )
        dispatchers.ctaOptionsMenu( contributor )
    

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
                                                    }, BUTTON_OPTIONS])
                                                   
    else:
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   ":|] It doesn't look like you are writing anything at the moment",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_OPTIONS])

def handle_leave( contributor ):
    """Handle the case that the user is attempting to leave the story
    """
    print "handle_leave()"
    story = story_utilities.leaveStory( contributor )
    if story:
        # succesfully left story
        dispatchers.ctaLeftStory( contributor )
    else:
        # there was an issue leaving the story
        dispatchers.sendBotMessage( contributor.social_identifier,  ":|] It looks like you are not working on a story at the moment." )
        dispatchers.ctaOptionsMenu( contributor )

def handle_skip( contributor ):
    """Handles the case of a user skipping a pormpt    
    A skip, is a participant leaving a story
    """
    print "handle_skip()"
    story_id = story_utilities.leaveStory( contributor )
 
    if story_id:
        # succesfully left story
        dispatchers.sendBotMessage(contributor.social_identifier, ":|] Ok, let's try again")
        handle_join(contributor, ignore_story_ids=[story_id])
    else:
        # there was an issue leaving the story
        dispatchers.sendBotMessage( contributor.social_identifier,  ":|] It looks like you are not working on a story at the moment." )
        dispatchers.ctaOptionsMenu( contributor )

def handle_browse( contributor ):
    """Handle the case that the user is attempting to read a random story 
    """
    print "handle_browse()"
    # get a random story
    story = Story.objects.filter(complete=True).order_by('?').first()
    if story:
        dispatchers.sendBotMessage(contributor.social_identifier,  ":|] Here is a random story")
        dispatchers.readBackStory( contributor, story )
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                            ":|] What would you like to do now?",
                                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_OPTIONS])
    else:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                            ":|] Well this is embarassing, I can't find any stories",
                                                            [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_OPTIONS])
def handle_history( contributor ):
    """Handle the case that the user is attempting to see a history of their writing 
    """
    print "handle_history()"
    dispatchers.readBackContributorHistory( contributor )    


def handle_help( contributor, detail_level=3 ):
    """Send a message to the user with all availble options
    the bot supports.
    """
    print "handle_help()"
    dispatchers.ctaOptionsMenu( contributor )


def handle_create( contributor):
    """Handles the creation of an account.
    Gets basic facebook user info and populates the contributor object
    """
    print "handle_create()"
    # get the user's facebook info
    fb_info = get_user_fb_info( contributor.social_identifier )

    # populate the contributor object
    contributor.profile_pic = fb_info.get('profile_pic')
    contributor.first_name = fb_info.get('first_name')
    contributor.last_name = fb_info.get('last_name')
    contributor.locale = fb_info.get('locale')
    contributor.gender = fb_info.get('gender')
    contributor.timezone = fb_info.get('timezone')
    contributor.save()

    # send a cta    
    dispatchers.ctaOnAccountCreation( contributor )


"""Define the bot action handlers to their mapped keywords
"""
BOT_HANDLER_MAPPING = {
    KEYWORD_JOIN: handle_join,
    KEYWORD_DONE: handle_done,
    KEYWORD_UNDO: handle_undo,
    KEYWORD_LEAVE: handle_leave,
    KEYWORD_SKIP: handle_skip,
    KEYWORD_BROWSE: handle_browse,
    KEYWORD_HISTORY: handle_history,
    KEYWORD_HELP: handle_help,
    KEYWORD_CREATE: handle_create,
    KEYWORD_OPTIONS: handle_options
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
    elif KEYWORD_SKIP in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_SKIP]( contributor )
    elif KEYWORD_HISTORY in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_HISTORY]( contributor )
    elif KEYWORD_BROWSE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_BROWSE]( contributor )    
    else:
        if contributor.state == WRITING:
            fragment = story_utilities.updateStory( contributor, payload )
            dispatchers.ctaConfirmEdit( contributor )
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


import random

from .keywords import *
from .fb_chat_buttons import *
from .models import Contributor, Story, Fragment

import helpers
import dispatchers



def handle_join( contributor ):
    """Join a story
    """
    # First let's check to make sure the user is not currently working on
    # a story
    if Fragment.objects.filter(contributor=contributor).filter(complete=False).count() > 0:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   "Looks like you are already writing a story!",
                                                   [BUTTON_CONTINUE, BUTTON_DISCARD, BUTTON_LEAVE])
            
    else:
        dispatchers.sendBotMessage(contributor.social_identifier, "Great, let's find a story for you to join!")

        if Story.objects.filter( complete=False ).count( ) > 0:
            # there are some stories that are not complete 
            stories = Story.objects.filter( complete=False ).order_by( 'time_created' )
            
            # get the first story (earliest) the user is already not a contributor to
            for story in stories: 
                if story.fragment_set.all( ).filter( contributor=contributor ).count( ) == 0:
                    # the contributor has not authored any of these story fragments 
                    # so let's add them to it
                    helpers.joinStory( contributor, story )
                    # notify the user what they will be writing
                    fragment = contributor.fragment_set.all().order_by('-time_created').first()
                    dispatchers.sendBotMessage(contributor.social_identifier, "We found a story for you to join, you will be writing the " + FRAGMENT_MAPPING.get(fragment.position))
                    # since the user is joining a story that already has some content
                    # we should read it back to the user
                    dispatchers.readBackStory( contributor, story )
                    break # short circuit the for loop, no need to look for more 
                    
            if contributor.state != "writing":
                # none of the incomplete stories had availible slots for the user, so we are going 
                # to create a new story for the user
                helpers.createStory( contributor )
                # the story and fragment are created, so tell the user to start the story
                dispatchers.sendBotMessage(contributor.social_identifier, "You're starting a new story, you can start it!")
        else:
            # all stories are complete, so we should create a new one
            helpers.createStory( contributor )
            # the story and fragment are created, so tell the user to start the story
            dispatchers.sendBotMessage(contributor.social_identifier, "You're starting a new story, you can start it!")

def handle_continue( contributor ):
    """Handle the case that the user is attempting to continue a story 
    """ 
    # the user should only have one incomplete fragment at a time, so 
    # let's get it and update it
    fragment = contributor.fragment_set.all( ).filter( complete=False ).first( )
    if fragment:
        story = fragment.story
        dispatchers.sendBotMessage(contributor.social_identifier, "Here is the story so far...")
        dispatchers.readBackStory(contributor, story)
    else:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "Looks like you aren't working on any story right now. What would you like to do?",
                                                [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_read( contributor, id=None ):
    if id:
        story = Story.objects.get(id=id)
        dispatchers.readBackStory( contributor, story )
    else:
        # get the last story the user wrote
        fragment = contributor.fragment_set.all().order_by('time_created').last()
        story = fragment.story
        dispatchers.sendBotMessage( contributor.social_identifier, "This is the last story you worked on" )
        dispatchers.readBackStory( contributor, story )
        dispatchers.sendBotStructuredButtonMessage(fragment.contributor.social_identifier,
                                                           "What would you like to do now?",
                                                           [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_undo( contributor ):
    fragment = contributor.fragment_set.all().order_by('time_created').last()
    if fragment.last_edit:
        helpers.undoLastEdit( contributor )
        dispatchers.sendBotMessage( contributor.social_identifier, "Undo done, here is what you have so far" )
        dispatchers.readBackFragment(contributor, fragment)
    else:
        dispatchers.sendBotMessage( contributor.social_identifier, "I'm only starting to learn how to go back in time, so undo is limited to one edit at a time" )

def handle_discard( contributor ):
    pass

def handle_leave( contributor ):
    pass

def handle_done( contributor ):
    """
    """
    fragment = contributor.fragment_set.all().filter(complete=False).first()
            
    if fragment and fragment.fragment:
        story = fragment.story
        
        # Mark the contributor specific fragment done
        fragment.complete = True
        fragment.save()
        
        # Update the contributor state
        contributor.state = "browsing"
        contributor.save()
        
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   "Draft submitted, awesome!",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])
        
        # Check if all the fragments are done
        if Fragment.objects.filter(story=story).filter(complete=True).count() == 3:
            # all the fragments are done, so let's mark the story done
            story.complete = True
            story.save()
            # notify all the participants their story is done
            story_fragments = Fragment.objects.filter(story=story)
            # Notify the contributors the story is done and send them a message with it
            for fragment in story_fragments:
                dispatchers.sendBotStructuredButtonMessage(fragment.contributor.social_identifier,
                                                           "One of your stories is done!",
                                                           [{
                                                                "type": "postback",
                                                                "title": "Read the story",
                                                                "payload": "/read " + str(story.id)
                                                            }])
    else:
        dispatchers.sendBotMessage( contributor.social_identifier, "You need to write something" )


def handle_browse( contributor ):
    """Handle the case that the user is attempting to read a random story 
    """
    contributor.state = 'browsing'
    contributor.save()
    
    # get a random story
    story = Story.objects.order_by('?').first()
    dispatchers.readBackStory( contributor, story )
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                           "What would you like to do now?",
                                                           [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])


def handle_history( contributor ):
    pass

def handle_help( contributor, detail_level=3 ):
    """Send a message to the user with all availble options
    the bot supports.
    """
    if detail_level >= 1:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "Here are the basics",
                                                [BUTTON_JOIN, BUTTON_CONTINUE, BUTTON_BROWSE])
    if detail_level >= 2:                                                
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "Here is how you can edit your drafts",
                                                [BUTTON_UNDO, BUTTON_DISCARD, BUTTON_DONE])
    if detail_level >= 3:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "Here are a few other helpful features",
                                                [BUTTON_READ, BUTTON_HISTORY, BUTTON_LEAVE])


BOT_HANDLER_MAPPING = {
    KEYWORD_JOIN: handle_join,
    KEYWORD_CONTINUE: handle_continue,
    KEYWORD_READ: handle_read,
    KEYWORD_UNDO: handle_undo,
    KEYWORD_DISCARD: handle_discard,
    KEYWORD_LEAVE: handle_leave,
    KEYWORD_DONE: handle_done, 
    KEYWORD_BROWSE: handle_browse,
    KEYWORD_HISTORY: handle_history,
    KEYWORD_HELP: handle_help
}




def process_postback_message( contributor, payload ):
    """FB provides postbacks where we can designate
    arbitrary data. For this bot, we are providing
    the processed triggers
    The payload should map directly to our keywords
    since we defined the values
    """
    
    if helpers.hasNumber(payload):
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
    elif KEYWORD_READ in processed_payload:
        if helpers.hasNumber(payload):
            story_id = int(payload.split(' ')[1])
            BOT_HANDLER_MAPPING[ KEYWORD_READ ]( contributor, story_id )
        else:
            BOT_HANDLER_MAPPING[ KEYWORD_READ ]( contributor ) 
    elif KEYWORD_DISCARD in processed_payload:
        pass
    elif KEYWORD_LEAVE in processed_payload:
        pass
    elif KEYWORD_CONTINUE in processed_payload:
        pass
    elif KEYWORD_HISTORY in processed_payload:
        pass
    elif KEYWORD_BROWSE in processed_payload:
        pass
    else:
        if contributor.state == 'writing':
            helpers.updateStory( contributor, payload )
            
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                       "Story updated",
                                                       [BUTTON_UNDO, BUTTON_READ, BUTTON_DONE])
            
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


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

        if Story.objects.filter(complete=False).count() > 0:
            # there are some stories that are not complete 
            stories = Story.objects.filter(complete=False).order_by('time_created')
            
            # get the first story (earliest) the user is already not a contributor to
            for story in stories: 
                if story.fragment_set.all().filter(contributor=contributor).count() == 0:
                    # the contributor has not authored any of these story fragments 
                    # so let's add them to it
                    helpers.joinStory( contributor, story)
                    # since the user is joining a story that already has some content
                    # we should read it back to the user
                    dispatchers.readBackStory( contributor, story)
                    break # short circuit the for loop, no need to look for more 
                    
            if contributor.state != "writing":
                # none of the incomplete stories had availible slots for the user, so we are going 
                # to create a new story for the user
                helpers.createStory( contributor )
        else:
            # all stories are complete, so we should create a new one
            helpers.createStory( contributor )

def handle_continue( contributor ):
    pass

def handle_read( contributor ):
    pass

def handle_undo( contributor ):
    pass

def handle_discard( contributor ):
    pass

def handle_leave( contributor ):
    pass

def handle_done( contributor ):
    pass

def handle_browse( contributor ):
    pass

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
        pass
    elif KEYWORD_DONE in processed_payload:
        pass
    elif KEYWORD_READ in processed_payload:
        pass
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
        # we didn't understand the input so show user all
        # availible options
        BOT_HANDLER_MAPPING[KEYWORD_HELP]( contributor )

def process_imsg_message( contributor, payload ):
    """In the event the user sends us some rich
    media message. At this moment, story bot will
    simply respond with a cute message as we do not 
    have any support for media in these stories
    """
    pass


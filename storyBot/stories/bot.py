import random

from .keywords import *
from .models import Contributor, Story, Fragment

import helpers
import dispatchers



def handle_join( contributor ):
    pass

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

def handle_help( contributor ):
    """Send a message to the user with all availble options
    the bot supports
    """
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                               "Here are the basics",
                                               [{
                                                   "type": "postback",
                                                   "title": "Join a story",
                                                   "payload": KEYWORD_JOIN
                                               },{
                                                   "type": "postback",
                                                   "title": "Continue last draft",
                                                   "payload": KEYWORD_CONTINUE
                                               },{
                                                   "type": "postback",
                                                   "title": "Read a random story",
                                                   "payload": KEYWORD_BROWSE
                                               }])
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                               "Here is how you can edit your drafts",
                                               [{
                                                   "type": "postback",
                                                   "title": "Undo your last edit",
                                                   "payload": KEYWORD_UNDO
                                               },{
                                                   "type": "postback",
                                                   "title": "Discard your draft",
                                                   "payload": KEYWORD_DISCARD
                                               },{
                                                   "type": "postback",
                                                   "title": "Finish draft",
                                                   "payload": KEYWORD_DONE
                                               }])
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                               "Here are a few other helpful features",
                                               [{
                                                   "type": "postback",
                                                   "title": "Read a story",
                                                   "payload": KEYWORD_READ
                                               },{
                                                   "type": "postback",
                                                   "title": "View past stories",
                                                   "payload": KEYWORD_HISTORY
                                               },{
                                                   "type": "postback",
                                                   "title": "Leave the story",
                                                   "payload": KEYWORD_LEAVE
                                               }])


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


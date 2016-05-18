import random
import math

from django.db.models import Count
from django.conf import settings

from .keywords import *
from .fb_chat_buttons import *
from .alias_generator import generate_alias
from .models import Contributor, Story, Fragment
from .models import BROWSING, WRITING, NAMING, SPEAKING
from .models import NUM_STORY_CONTRIBUTORS, NUM_TURNS_PER_CONTRIBUTOR
  
import helpers
import dispatchers


def handle_join( contributor ):
    """Join a story
    """
    # First let's check to make sure the user is not currently working on
    # a story
    if contributor.state == WRITING:
        fragment = contributor.get_last_fragment(complete=False)
        
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
        available_story = Story.objects.filter(complete=False) \
                                       .filter(full=False) \
                                       .exclude(contributors__in=[contributor]) \
                                       .order_by('time_created') \
                                       .first()
        
        if available_story:
            # join the story
            story = helpers.joinStory(contributor, available_story)
            
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
            if story.fragment_set.all().filter(contributor__isnull=False).filter(complete=False).count() == 0:
                contributor.state = WRITING
                contributor.save()
                
                fragment = story.fragment_set.all().filter(contributor__isnull=True).order_by('position').first()
                fragment.contributor = contributor
                fragment.alias = contributor.temp_alias
                fragment.save()
                
                dispatchers.sendBotMessage(contributor.social_identifier, ":|] It's your turn, send us a message to add it to the story!")
            else:
                dispatchers.sendBotMessage(contributor.social_identifier, ":|] We'll let you know when it's your turn!")
            
        else:
            # create a new one
            s = helpers.createStory(contributor)
            f = s.fragment_set.all().order_by('position').first()
            # the story and fragment are created, so tell the user to start the story
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] You're starting a new story!")
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] You're alias for this story will be' " + f.alias + " and will have " + str(NUM_TURNS_PER_CONTRIBUTOR) + " turns.")
                        
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] Here is some inspiration if you need it!")
            dispatchers.sendBotMessage(contributor.social_identifier, "o.O " + s.prompt)
            dispatchers.sendBotMessage(contributor.social_identifier, ":|] You can start writing.")
            

def handle_done( contributor ):
    """handles the case when a user says they are done with their fragment
    """
    # get the last fragment the user was working on
    fragment = contributor.get_last_fragment(complete=False)
    
    if fragment and fragment.fragment:
        story = fragment.story    
        
        # mark the fragment as done
        fragment.complete = True
        fragment.save()
        
        # update contributor state
        contributor.state = BROWSING
        contributor.save()
        
        # get a list of the story conrtibutors
        story_contributors = story.contributors.all()
        
        # check if the story has reached termination conditions
        if story.fragment_set.all().filter(complete=True).count() == story.num_of_turns:
            # mark story as done
            story.complete = True
            story.save()

            # update everyone that the story is complete
            for c in story_contributors:
                c.temp_alias = "" # reset the temp alias
                c.save()
                dispatchers.sendBotStructuredButtonMessage(c.social_identifier,
                                                           ":|] Looks like one of your stories is complete!",
                                                           [{
                                                                "type": "web_url",
                                                                "title": "Read the story",
                                                                "url": settings.BASE_URL + "/stories/" + str(story.id)
                                                            }, 
                                                            BUTTON_JOIN, 
                                                            BUTTON_BROWSE])
        
        else:
            # the story is not done, 
            
            # broadcast the latest update to the rest and notify the next person whose turn it is
            for c in story_contributors:
                if c == contributor:
                    # tell the contributor he'll be messeged when its his turn
                    contributor_completed_fragments_count = story.fragment_set.all().filter(contributor=c).filter(complete=True).count()
                    
                    if contributor_completed_fragments_count == story.num_of_turns / story.num_of_contributors:
                        dispatchers.sendBotMessage(contributor.social_identifier, ":|] We will notify you when the story is done!" )
                    else:
                        dispatchers.sendBotMessage(contributor.social_identifier, ":|] We will notify you when it is your turn again!" )
                else:
                    # notify the update in the story
                    dispatchers.sendBotMessage(c.social_identifier, ":|] Story Updated by " + c.temp_alias)
                    dispatchers.readBackFragment( c, fragment )
        
        
        
        
            # figure out who the next person is in the story
            contributor_index = list(story_contributors).index(contributor)
            next_contributor = story_contributors[ contributor_index + 1 ] if contributor_index + 1 < len(story_contributors) else story_contributors[0]

            if contributor != next_contributor:
                # create a fragment for that person
                next_story_fragment = story.fragment_set.all().filter(contributor__isnull=True).order_by('position').first()
                if next_story_fragment:
                    next_story_fragment.alias = next_contributor.temp_alias
                    next_story_fragment.contributor = next_contributor
                    next_story_fragment.save()
                    
                    next_contributor.state = WRITING
                    next_contributor.save()
                    
                    # notify them it's their turn
                    turns_left = NUM_TURNS_PER_CONTRIBUTOR - story.fragment_set.all().filter(complete=True).filter(contributor=next_contributor).count()
                    dispatchers.sendBotStructuredButtonMessage(next_contributor.social_identifier,
                                                        ":|] It's your turn, you have " + str(turns_left) + " turns left. (just send us a message and we'll add it to your story's part)",
                                                        [{
                                                            "type": "web_url",
                                                            "title": "Read the story",
                                                            "url": settings.BASE_URL + "/stories/" + str(story.id)
                                                        }])
    else:
        dispatchers.sendBotMessage(contributor.social_identifier, ":|] Looks like you havn't written anything!")
        

def handle_undo( contributor ):
    if contributor.state == WRITING:
        fragment = contributor.fragment_set.all().order_by('time_created').last()
        if fragment and fragment.last_edit:
            f = helpers.undoLastEdit( contributor )
            dispatchers.sendBotMessage( contributor.social_identifier, ":|] Undo done, here is what you have so far" )
            dispatchers.readBackFragment( contributor, f )
        else:
            dispatchers.sendBotMessage( contributor.social_identifier, ":|] I'm only starting to learn how to go back in time, so undo is limited to one edit at a time")
        
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
    fragment = Fragment.objects.filter(contributor=contributor).filter(complete=False).first()
    if fragment:
        # erase the contents of the fragment
        fragment.delete()
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
    contributor.state = BROWSING
    contributor.save()
    
    # get a random story
    story = Story.objects.order_by('?').first()
    dispatchers.sendBotMessage(contributor.social_identifier,  ":|] Here is a random story")
    dispatchers.readBackStory( contributor, story )
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                           ":|] What would you like to do now?",
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


BOT_HANDLER_MAPPING = {
    KEYWORD_JOIN: handle_join,
    KEYWORD_DONE: handle_done,
    KEYWORD_UNDO: handle_undo,
    KEYWORD_LEAVE: handle_leave,
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
    elif KEYWORD_LEAVE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_LEAVE]( contributor )
    elif KEYWORD_HISTORY in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_HISTORY]( contributor )
    elif KEYWORD_BROWSE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_BROWSE]( contributor )
    else:
        if contributor.state == WRITING:
            fragment = helpers.updateStory( contributor, payload )
            story = fragment.story      
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                       ":|] Story updated! (You can keep writing by sending more messages)",
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


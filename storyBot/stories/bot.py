import random

from django.db.models import Count

from .keywords import *
from .fb_chat_buttons import *
from .models import Contributor, Story, Fragment

import helpers
import dispatchers


BASE_URL = "https://5b9e4890.ngrok.io"
MAX_STORY_CONTRIBUTORS = 3
MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR = 5


def handle_join( contributor ):
    """Join a story
    """
    # First let's check to make sure the user is not currently working on
    # a story
    if Fragment.objects.filter(contributor=contributor).filter(complete=False).count() > 0:
        print "JOIN - USER IS WRITING ALREADY"
    
        contributor.state = 'writing'
        contributor.save()
        fragment = Fragment.objects.filter(contributor=contributor).filter(complete=False).first()
        dispatchers.sendBotMessage(contributor.social_identifier, "Looks like you are in the middle of a story!")
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   "Your alias is " + fragment.alias,
                                                   [{
                                                        "type": "web_url",
                                                        "title": "Read the story",
                                                        "url": BASE_URL + "/stories/" + str(fragment.story.id)
                                                    }, BUTTON_LEAVE])
            
    else:
        print "JOIN - USER IS NOT WRITING ALREADY"
        dispatchers.sendBotMessage(contributor.social_identifier, "Great, let's find a story for you to join!")
        availible_story = Story.objects.annotate(num_contributors=Count('contributors')) \
                                       .filter(num_contributors__lte=MAX_STORY_CONTRIBUTORS-1) \
                                       .filter(complete=False) \
                                       .exclude(contributors__in=[contributor]) \
                                       .order_by('time_created').first()
        
        if availible_story:
            print "JOIN - FOUND A GOOD STORY"
            print availible_story
            
            # join the story
            s, f = helpers.joinStory(contributor, availible_story)
            # tell the user they are paired up
            dispatchers.sendBotMessage(contributor.social_identifier, "We found a story for you to join!")
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                        "Your alias will be " + f.alias,
                                                        [{
                                                                "type": "web_url",
                                                                "title": "Read the story",
                                                                "url": BASE_URL + "/stories/" + str(s.id)
                                                            }, BUTTON_LEAVE])
                                                            
            dispatchers.sendBotMessage(contributor.social_identifier, "You will have " + str(MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR) + " turns in this story!")
            
            # check if everything else is complete. if so you are up!
            if s.fragment_set.all().filter(complete=True).count() == s.fragment_set.all().count() - 1:
                print "JOIN - YOUR TURN"
                contributor.state = "writing"
                contributor.save()
                dispatchers.sendBotMessage(contributor.social_identifier, "It looks like it is your turn!")
            else:
                if s.fragment_set.all().filter(contributor=contributor).count() == MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR:
                    dispatchers.sendBotMessage(contributor.social_identifier, "You've used up all your turns! We'll let you know when the story is done!")
                else:
                    dispatchers.sendBotMessage(contributor.social_identifier, "We will notify you when updates are made and when it is your turn!")
            
        else:
            print "JOIN - COULD NOT FIND A STORY STARTING A NEW ONE"
            # create a new one
            s, f = helpers.createStory(contributor)
            # the story and fragment are created, so tell the user to start the story
            dispatchers.sendBotMessage(contributor.social_identifier, "You're starting a new story, you can start it!")
            dispatchers.sendBotMessage(contributor.social_identifier, "For this we'll call you " + f.alias)
            dispatchers.sendBotMessage(contributor.social_identifier, "Here is some inspiration if you need it!")
            dispatchers.sendBotMessage(contributor.social_identifier, s.prompt)
            
            dispatchers.sendBotMessage(contributor.social_identifier, "You will have " + str(MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR) + " turns in this story!")
            dispatchers.sendBotMessage(contributor.social_identifier, "Start writing")
            

def handle_done( contributor ):
    """
    """
    # get the last fragment the user was working on
    fragment = contributor.fragment_set.all().filter(complete=False).first()
    
    if fragment and fragment.fragment:
        print "DONE - USER HAS WRITTEN SOME STUFF"
        story = fragment.story
        
        # mark the fragment as done
        fragment.complete = True
        fragment.save()
        
        # update contributor state
        contributor.state = "browsing"
        contributor.save()
        
        story_contributors = story.contributors.all()
        
        # check if the story has reached termination conditions
        if story.fragment_set.all().filter(complete=True).count() == MAX_STORY_CONTRIBUTORS * MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR:
            # story has N fragments marked as complete
            print "|"*50
            print "STORY DONE"
            
            story.complete = True
            story.save()
            
            for c in story_contributors:
                dispatchers.sendBotStructuredButtonMessage(c.social_identifier,
                                                           "Looks like one of your stories is complete!",
                                                           [{
                                                                "type": "web_url",
                                                                "title": "Read the story",
                                                                "url": BASE_URL + "/stories/" + str(story.id)
                                                            }, BUTTON_JOIN])
        
        else:
            # the story is not done, so broadcast the latest update to the rest and notify the next person 
            # whose turn it is
            print "|"*50
            print "STORY NOT DONE"
            
            for c in story_contributors:
                if c == contributor:
                    # tell the contributor he'll be messeged when its his turn
                    contributor_fragments_count = story.fragment_set.all().filter(contributor=contributor).count()
                    dispatchers.sendBotMessage(contributor.social_identifier, "You have used " + str( min(contributor_fragments_count, MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR) ) + " out of " + str(MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR) + " turns" )
                    dispatchers.sendBotMessage(contributor.social_identifier, "We will notify you when it is your turn again!" )
                else:
                    # notify the update in the story
                    dispatchers.sendBotMessage(c.social_identifier, "Story Updated")
                    dispatchers.readBackFragment( c, fragment )
        
            # notify the next person that it is their turn
            contributor_index = list(story_contributors).index(contributor)
            next_contributor = story_contributors[ contributor_index + 1 ] if contributor_index + 1 < len(story_contributors) else story_contributors[0]
            if next_contributor != contributor:
                print "Updating the next contributor"
                alias = story.fragment_set.all().filter(contributor=next_contributor).first().alias
                s, f = helpers.joinStory(next_contributor, story, alias)
                next_contributor.state = "writing"
                next_contributor.save()

                dispatchers.sendBotMessage(next_contributor.social_identifier, "It's your turn!")
            
    else:
        dispatchers.sendBotMessage(contributor.social_identifier, "Looks like you havn't written anything!")
    
    # fragment = contributor.fragment_set.all().filter(complete=False).first()
            
    # if fragment and fragment.fragment:
    #     story = fragment.story
        
    #     # Mark the contributor specific fragment done
    #     fragment.complete = True
    #     fragment.save()
        
    #     # Update the contributor state
    #     if story.fragment_set.all().filter(contributor=contributor).count() > MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR:
    #         contributor.state = "browsing"
    #         contributor.save()
    #         dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
    #                                                 "Looks like you've submitted all your parts, we'll notify you when the story is done!",
    #                                                 [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])
    #     else:
    #         # Check who's turn is next
    #         if story.contributors.all().count() > 1:
    #             story_contributors = story.contributors.all()
    #             contributor_index = list(story_contributors).index(contributor)
    #             next_contributor = story_contributors[contributor_index+1] if contributor_index+1 < len(story_contributors) else story_contributors[0]
                
    #             print "*"*50
    #             print story_contributors
                
    #             print contributor
    #             print next_contributor
                
    #             dispatchers.sendBotMessage(next_contributor.social_identifier, "Hey, it's your turn to write for the story!")
    #             dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
    #                                                 "Thanks!, We'll notify you when it's your turn to write more",
    #                                                 [{
    #                                                     "type": "web_url",
    #                                                     "title": "Read the story so far",
    #                                                     "payload": BASE_URL + "/stories/ " + str(story.id)
    #                                                 }])
            
    #         dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
    #                                                 "Thanks!, We'll notify you when it's your turn to write more",
    #                                                 [BUTTON_BROWSE, BUTTON_HISTORY])
        
    #     # Check if all the fragments are done
    #     if Fragment.objects.filter(story=story).filter(complete=True).count() == MAX_STORY_CONTRIBUTORS * MAX_STORY_FRAGMENTS_PER_CONTRIBUTOR:
    #         # all the fragments are done, so let's mark the story done
    #         story.complete = True
    #         story.save()
    #         # notify all the participants their story is done
    #         story_contributors = story.contributors.all()
    #         # Notify the contributors the story is done and send them a message with it
    #         for contributor in story_contributors:
    #             dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
    #                                                        "One of your stories is done, check it out!",
    #                                                        [{
    #                                                             "type": "postback",
    #                                                             "title": "Read the story",
    #                                                             "payload": "/read " + str(story.id)
    #                                                         }])
    # else:
    #     dispatchers.sendBotMessage( contributor.social_identifier, "You need to write something" )





def handle_continue( contributor ):
    """Handle the case that the user is attempting to continue a story 
    """ 
    # the user should only have one incomplete fragment at a time, so 
    # let's get it and update it
    fragment = contributor.fragment_set.all( ).filter( complete=False ).first( )
    if fragment:
        story = fragment.story
        dispatchers.sendBotMessage(contributor.social_identifier, "Here is the story so far...", True)
        dispatchers.readBackStory(contributor, story)
    else:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[StoryBot] Looks like you aren't working on any story right now. What would you like to do?",
                                                [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_read( contributor, id=None ):
    if id:
        story = Story.objects.get(id=id)
        dispatchers.readBackStory( contributor, story )
        
    else:
        # get the last story the user wrote
        fragment = contributor.fragment_set.all().order_by('time_created').last()
        story = fragment.story
        dispatchers.sendBotMessage( contributor.social_identifier, "This is the last story you worked on", True )
        dispatchers.readBackStory( contributor, story )
    
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                               "[StoryBot] What would you like to do now?",
                                               [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])

def handle_undo( contributor ):
    fragment = contributor.fragment_set.all().order_by('time_created').last()
    if fragment.last_edit:
        fragment = helpers.undoLastEdit( contributor )
        dispatchers.sendBotMessage( contributor.social_identifier, "Undo done, here is what you have so far", True )
        dispatchers.readBackFragment(contributor, fragment)
    else:
        dispatchers.sendBotMessage( contributor.social_identifier, "I'm only starting to learn how to go back in time, so undo is limited to one edit at a time", True )

def handle_discard( contributor ):
    """Handle the case that the user is attempting to discard his fragment 
    """
    fragment = Fragment.objects.filter(contributor=contributor).filter(complete=False).first()
    if fragment:
        # erase the contents of the fragment
        fragment.fragment = ""
        fragment.last_edit = ""
        fragment.save()
        dispatchers.sendBotMessage(contributor.social_identifier,  "Your draft has been discarded, you can start writing it again", True)
        dispatchers.sendBotMessage(contributor.social_identifier,  "Here is the story so far", True)
        dispatchers.readBackStory(contributor, fragment.story)
    else:
        dispatchers.sendBotMessage(contributor.social_identifier,  "You have no story drafts to discard", True)
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   "[StoryBot] What would you like to do?",
                                                   [BUTTON_CONTINUE, BUTTON_DISCARD, BUTTON_LEAVE])

def handle_leave( contributor ):
    """Handle the case that the user is attempting to leave the story
    """
    fragment = Fragment.objects.filter(contributor=contributor).filter(complete=False).first()
    if fragment:
        # erase the contents of the fragment
        fragment.destroy()
        dispatchers.sendBotMessage(contributor.social_identifier,  "Your story fragment has been erased, and you have left the story. Send \"\start\" to join a new story")
    else:
        dispatchers.sendBotMessage(contributor.social_identifier,  "You are not working on any story", True)
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                   "[StoryBot] What would you like to do?",
                                                   [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])



def handle_browse( contributor ):
    """Handle the case that the user is attempting to read a random story 
    """
    contributor.state = 'browsing'
    contributor.save()
    
    # get a random story
    story = Story.objects.order_by('?').first()
    dispatchers.readBackStory( contributor, story )
    dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                           "[StoryBot] What would you like to do now?",
                                                           [BUTTON_JOIN, BUTTON_BROWSE, BUTTON_HISTORY])


def handle_history( contributor ):
    """Handle the case that the user is attempting to see a history of their writing 
    """
    dispatchers.sendBotMessage(contributor.social_identifier, "Here is a history of your stories", True)
    
    fragments = Fragment.objects.filter(contributor=contributor).order_by('time_created')
    stories = []
    for fragment in fragments:
        stories.append( fragment.story )
    
    chunk_size = 3 # fb lets us put only 3 buttons at a time
    story_chunks = [stories[i:i + chunk_size] for i in range(0, len(stories), chunk_size)]
    
    for i, story_chunk in enumerate(story_chunks):
        buttons = []
        for story in story_chunk:
            buttons.append({
                                "type": "postback",
                                "title": "Story " + str(story.id),
                                "payload": "/read " + str(story.id)
                            })
    
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[" + str(i+1) + "/" + str(len(story_chunks)) +  "]",
                                                buttons)

    

def handle_help( contributor, detail_level=3 ):
    """Send a message to the user with all availble options
    the bot supports.
    """
    if detail_level >= 1:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[StoryBot] Here are the basics",
                                                [BUTTON_JOIN, BUTTON_CONTINUE, BUTTON_BROWSE])
    if detail_level >= 2:                                                
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[StoryBot] Here is how you can edit your drafts",
                                                [BUTTON_UNDO, BUTTON_DISCARD, BUTTON_DONE])
    if detail_level >= 3:
        dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                "[StoryBot] Here are a few other helpful features",
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
        BOT_HANDLER_MAPPING[KEYWORD_DISCARD]( contributor )
    elif KEYWORD_LEAVE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_LEAVE]( contributor )
    elif KEYWORD_CONTINUE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_CONTINUE]( contributor )
    elif KEYWORD_HISTORY in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_HISTORY]( contributor )
    elif KEYWORD_BROWSE in processed_payload:
        BOT_HANDLER_MAPPING[KEYWORD_BROWSE]( contributor )
    else:
        if contributor.state == "writing":
            print "UPDATING THE FRAGMENT"
            print payload 
            print contributor.state
            
            fragment = helpers.updateStory( contributor, payload )
            
            dispatchers.sendBotStructuredButtonMessage(contributor.social_identifier,
                                                       "Story updated!",
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


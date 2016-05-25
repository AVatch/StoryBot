from datetime import timedelta

from django.utils import timezone

from .fb_chat_buttons import *
from .models import Contributor, Story, Fragment, WRITING

import dispatchers
import content_generators

def createStory( contributor ):
    """create a story with an initial contributor and 
    a set of fragments
    """
    print "createStory()"
    # generate a prompt
    generated_prompt = content_generators.generate_prompt()
    
    # create the story
    story = Story.objects.create( prompt=generated_prompt['prompt'], prompt_link=generated_prompt['link'] )
    story.populate_with_fragments( )
    story.add_contributor( contributor )
    fragment = story.associate_fragment_with_contributor( contributor )
    
    dispatchers.ctaNewStoryOnCreation( contributor, story )
    
def joinStory(contributor, story):
    """given a contributor and a story, it finds the next available slot for
    the contributor to fill in
    """
    print "joinStory()"
    # update the story contributors
    story.add_contributor( contributor )
    dispatchers.ctaNewStoryOnJoin( contributor, story )
    
    # check to see if the newly joined contributor is up next
    if story.are_all_populated_fragments_done():
        # associate the contributor with the next fragment in the story
        story.associate_fragment_with_contributor( contributor )
        dispatchers.notifyContributorOnTurn( contributor, story )

def leaveStory(contributor):
    """Have the user leave their active story
    """
    print "leaveStory()"
    if contributor.active_story != 0:
        try:
            active_story = Story.objects.get(id=contributor.active_story)
        except Story.DoesNotExist:
            active_story = None
        
        if active_story:
            active_story_id = active_story.id
            active_story.remove_contributor( contributor )
            return active_story_id
        else:
            return None
        
    else:
        return None
        

def markFragmentAsDone(fragment):
    """
    """
    print "markFragmentAsDone()"
    story = fragment.story
    contributor = fragment.contributor

    if fragment and fragment.fragment:
        fragment.mark_complete()
        return True
    else:
        return None

def updateStory(contributor, content):
    """Update the fragment
    """
    print "updateStory()"
    fragment = contributor.get_last_fragment()
    if fragment and not fragment.complete:
        fragment.edit(content)
    return fragment

def undoLastEdit(contributor):
    """Undo the last edit made by the person
    """
    fragment = contributor.get_last_fragment()
    if fragment and not fragment.complete:
        fragment.undo_edit()
    return fragment 

def checkForStaleContributors( ):
    """checks stories for any contributors which have not been active
    for a period of time and prompts them to act
    """
    print "checkForStaleContributors()"
    TIME_DELTA = timedelta(hours=3)
    now = timezone.now()
    
    contributors_to_message = []
    writing_contributors = Contributor.objects.all().filter(state=WRITING).order_by('last_active')

    for contributor in writing_contributors:
        if ( now - contributor.last_active ) > TIME_DELTA:
            contributors_to_message.append( contributor )            
    return contributors_to_message

def kickStaleContributor( contributor ):
    """kicks a contributor from the story since they have been inactive
    """
    print "kickStaleContributor()"
    if contributor.active_story:
    
        try:
            active_story = Story.objects.get(id=contributor.active_story)
        except Story.DoesNotExist:
            active_story = None

        if active_story:
            # remove the contributor from the story 
            active_story.remove_contributor( contributor )
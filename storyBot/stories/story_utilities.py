from datetime import timedelta

from django.utils import timezone

from .fb_chat_buttons import *
from .content_generators import *
from .models import Contributor, Story, Fragment

def createStory( contributor ):
    """create a story with an initial contributor and 
    a set of fragments
    """
    # generate a prompt
    generated_prompt = generate_prompt()
    
    # create the story
    story = Story.objects.create( prompt=generated_prompt['prompt'], prompt_link=generated_prompt['link'] )
    story.populate_with_fragments( )
    story.add_contributor( contributor )
    fragment = story.associate_fragment_with_contributor( contributor )
    
    return story, fragment
    
def joinStory(contributor, story):
    """given a contributor and a story, it finds the next available slot for
    the contributor to fill in
    """
    # update the story contributors
    story.add_contributor( contributor )
    return story

def markFragmentAsDone(fragment):
    """
    """
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
    fragment = contributor.get_last_fragment(complete=False)
    if fragment:
        fragment.edit(content)
    return fragment

def undoLastEdit(contributor):
    """Undo the last edit made by the person
    """
    fragment = contributor.get_last_fragment(complete=False)
    if fragment:
        fragment.undo_edit()
    return fragment 


def checkForStaleContributors( ):
    """checks stories for any contributors which have not been active
    for a period of time and prompts them to act
    """
    TIME_DELTA = timedelta(hours=2)
    now = timezone.now()
    
    unfinished_stories = Story.objects.all().filter(complete=False).order_by('time_created')
    contributors_to_message = []
    
    for story in unfinished_stories:
        # get the last fragment in the story
        last_incomplete_fragment = story.get_last_incomplete_fragment()
        if last_incomplete_fragment:
            # check if the user has been active
            contributor_last_active = last_incomplete_fragment.contributor.last_active  
            if ( now - contributor_last_active ) > TIME_DELTA:
                contributors_to_message.append( contributor_last_active )
                
    return contributors_to_message

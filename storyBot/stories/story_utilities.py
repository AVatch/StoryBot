from datetime import timedelta

from django.utils import timezone

from .fb_chat_buttons import *
from .content_generators import *
from .models import Contributor, Story, Fragment, WRITING

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
    TIME_DELTA = timedelta(hours=1)
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
    if contributor.active_story:
        active_story = Story.objects.get(id=contributor.active_story)
        if active_story:
            # remove the contributor from the story 
            active_story.remove_contributor( contributor )
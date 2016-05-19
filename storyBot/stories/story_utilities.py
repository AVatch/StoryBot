import datetime 
from .fb_chat_buttons import *
from .alias_generator import *
from .models import Contributor, Story, Fragment

def hasNumber(string):
    """check if a string contains a number
    """
    return any( char.isdigit() for char in string )

def chunkString(string, length):
    """Given a string break it down into 
    chunks of size length
    """
    return [string[i:i+length] for i in range(0, len(string), length)]



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

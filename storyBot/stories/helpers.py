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
    """
    """
    story = Story.objects.create( title=generate_title("") )
    # create a new fragment for the story
    fragment = Fragment.objects.create(story=story, 
                                       fragment="", 
                                       alias=generate_alias(),
                                       position=0, 
                                       contributor=contributor)
                        
    # update the state of the contributor
    contributor.state = "writing"
    contributor.save()  
    

def joinStory(contributor, story):
    """
    """
    # create a fragment for the story
    fragment = Fragment.objects.create(story=story, 
                                       fragment="",
                                       alias=generate_alias(), 
                                       position= story.fragment_set.count(), 
                                       contributor=contributor)
    # update the state of the contributor
    contributor.state = "writing"
    contributor.save()
    

def leaveStory(contributor, story):
    """
    """
    pass


def updateStory(contributor, content):
    """
    """
    fragment = contributor.fragment_set.all().filter(complete=False).first()
    if fragment:
        fragment.fragment += content
        fragment.last_edit = content
        fragment.save()

def undoLastEdit(contributor):
    """
    """
    fragment = contributor.fragment_set.all().filter(complete=False).first()
    if fragment:
        fragment.fragment = fragment.fragment[:-len(fragment.last_edit)]
        fragment.last_edit = ""
        fragment.save()
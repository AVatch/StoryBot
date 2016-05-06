import dispatchers

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
    # the story and fragment are created, so tell the user to start the story
    dispatchers.sendBotMessage(contributor.social_identifier, "You're starting a new story, you can start it!")

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
    # notify the user what they will be writing
    dispatchers.sendBotMessage(contributor.social_identifier, "We found a story for you to join, you will be writing the " + FRAGMENT_MAPPING.get(fragment.position))

def leaveStory(contributor, story):
    """
    """
    pass

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
    prompt=generate_prompt()
    story = Story.objects.create( title=generate_title(""), prompt=prompt['prompt'], prompt_link=prompt['link'] )
    story.contributors.add(contributor)
    story.save()
    
    # create a new fragment for the story
    fragment = Fragment.objects.create(story=story, 
                                       fragment="",
                                       alias=generate_alias(),
                                       position=0, 
                                       contributor=contributor)
                        
    # update the state of the contributor
    contributor.state = "writing"
    contributor.save()  
    
    return story, fragment
    

def joinStory(contributor, story, alias=None):
    """
    """
    # create a fragment for the story
    
    if alias is None:
        alias = generate_alias()
    
    fragment = Fragment.objects.create(story=story, 
                                       fragment="",
                                       alias=alias, 
                                       position=story.fragment_set.count(), 
                                       contributor=contributor)
    # update the state of the contributor
    contributor.state = "browsing"
    contributor.save()
    
    # update the story contributors
    if contributor not in story.contributors.all():
        story.contributors.add(contributor)
        story.save()
    
    return story, fragment
    

def leaveStory(contributor, story):
    """
    """
    pass


def updateStory(contributor, content):
    """
    """
    fragment = contributor.fragment_set.all().filter(complete=False).first()
    if fragment:
        fragment.fragment = fragment.fragment + " " + content
        fragment.last_edit = content
        fragment.save()
    return fragment
    


def undoLastEdit(contributor):
    """
    """
    fragment = contributor.fragment_set.all().filter(complete=False).first()
    if fragment:
        fragment.fragment = fragment.fragment[:-len(fragment.last_edit)]
        fragment.last_edit = ""
        fragment.save()
        
    return fragment 
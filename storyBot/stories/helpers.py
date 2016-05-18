from .fb_chat_buttons import *
from .alias_generator import *
from .models import Contributor, Story, Fragment
from .models import BROWSING, WRITING, NAMING, SPEAKING

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
    story.contributors.add(contributor)
    story.save()
    
    # fill it up with fragments
    for i in range( story.num_of_turns):
        f = Fragment.objects.create(story=story,
                                    position=i)
        if i == 0:
            # give the contributor starting the story, the first
            # part
            f.contributor = contributor
            f.alias = generate_alias()
            f.save()
            # update the state of the contributor
            contributor.state = WRITING
            contributor.temp_alias = f.alias
            contributor.save()

    return story
    

def joinStory(contributor, story):
    """given a contributor and a story, it finds the next available slot for
    the contributor to fill in
    """
            
    # update the state of the contributor
    contributor.state = BROWSING
    contributor.save()
    
    # update the story contributors
    if contributor not in story.contributors.all():
        story.contributors.add(contributor)
        story.save()
    
    # check if the story should be set to full
    if story.contributors.all().count() == story.num_of_contributors:
        story.full = True
        story.save()
    
    return story


def completeFragment(contributor, story):
    """
    """
    pass

def prepareNextStoryFragment(contributor, story):
    """
    """
    pass



def leaveStory(contributor, story):
    """
    """
    pass


def updateStory(contributor, content):
    """
    """
    print "UPDATING"*10
    fragment = contributor.get_last_fragment(complete=False)
    print fragment
    if fragment:
        fragment.fragment = fragment.fragment + " " + content
        fragment.last_edit = content
        fragment.save()
    else:
        pass
    return fragment
    


def undoLastEdit(contributor):
    """
    """
    fragment = contributor.get_last_fragment(complete=False)
    if fragment:
        fragment.fragment = fragment.fragment[:-len(fragment.last_edit)]
        fragment.last_edit = ""
        fragment.save()
        
    return fragment 
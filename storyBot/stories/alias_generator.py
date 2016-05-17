import os
import random
import json
from django.conf import settings

def generate_alias():
    """generates an alias
    """
    adjective = random.choice(open(os.path.join(settings.BASE_DIR, 'stories/data/adjectives.txt')).readlines())
    animal = random.choice(open(os.path.join(settings.BASE_DIR, 'stories/data/animals.txt')).readlines())
    alias = adjective.strip().capitalize() + ' ' + animal.strip().capitalize()
    return alias
    
def generate_title(contents):
    """generates a story title based off of the 
    content
    """
    return "An amazing story in search of a title"

def generate_prompt( ):
    """generates a story prompt
    """
    prompt =  json.loads( random.choice(open(os.path.join(settings.BASE_DIR, 'stories/data/prompts.json')).readlines()) )
    return prompt

    
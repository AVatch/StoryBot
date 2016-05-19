import os
import random
import json
import requests
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
    prompt = random.choice(
            open(
                os.path.join(
                    settings.BASE_DIR, 'stories/data/prompts.json'
                )
            ).readlines()
        ).strip()[:-1]
    prompt = json.loads(prompt)
    return prompt

def generate_random_gif():
    """get random gif from giphy
    """
    gif = ""
    r = requests.get("http://api.giphy.com/v1/stickers/random?api_key=dc6zaTOxFJmzC", 
                      headers = {'content-type': 'application/json'})
    gif = r.json()["data"]["url"]
    return gif
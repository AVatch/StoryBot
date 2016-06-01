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


PLACEHOLDER_IMG = "http://placehold.it/350x150"
def generate_search_img():
    options = [
        "https://media.giphy.com/media/3oEjHKUfzCuFB7eIYE/giphy.gif",# blue
        "https://media.giphy.com/media/l41YAr1UylnZqtyO4/giphy.gif", # green
        "https://media.giphy.com/media/3oEjHGmKWXUMmDHRV6/giphy.gif",# purple
        "https://media.giphy.com/media/l41YgKtSiuBjyBlII/giphy.gif", # red
        "https://media.giphy.com/media/3oEjHDcq0pDj5P4kZW/giphy.gif" # yellow
    ]
    return random.choice(options)

def generate_read_img():
    return PLACEHOLDER_IMG
    
def generate_done_img():
    options = [
        "https://media.giphy.com/media/3oEjI9tsMtzEPU5rS8/giphy.gif",# blue
        "https://media.giphy.com/media/l41YkY1sqD4z7GRgc/giphy.gif", # green
        "https://media.giphy.com/media/l41YqAhms22IKucog/giphy.gif", # purple
        "https://media.giphy.com/media/l41YejvefEvwNA0uc/giphy.gif", # red
        "https://media.giphy.com/media/3oEjHVBZS5ijxbKrjq/giphy.gif" # yellow
    ]
    return random.choice(options)

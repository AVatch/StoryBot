import random
import os
from django.conf import settings

def generate_alias():
    """generates an alias
    """
    adjective = random.choice(open(os.path.join(settings.BASE_DIR, 'stories/data/adjectives.txt')).readlines())
    animal = random.choice(open(os.path.join(settings.BASE_DIR, 'stories/data/animals.txt')).readlines())
    alias = adjective.strip().capitalize() + ' ' + animal.strip().capitalize()
    return alias
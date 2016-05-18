from __future__ import unicode_literals

from django.db import models

DEFAULT_STORY_TITLE = "An amazing story in search of a title"

BROWSING = 'BR'
WRITING = 'WR'
NAMING = 'NM'
SPEAKING = 'SP'

CONTRIBUTOR_STATES = (
    ('BR', BROWSING),
    ('WR', WRITING),
    ('NM', NAMING),
    ('SP', SPEAKING),
)
class Contributor(models.Model):
    social_identifier = models.CharField(max_length=200)
    
    profile_pic = models.URLField(blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    locale = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=100, blank=True)
    timezone = models.IntegerField(blank=True)
    
    state = models.CharField(max_length=2, choices=CONTRIBUTOR_STATES, default=BROWSING)

    last_active = models.DateTimeField(auto_now_add=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( self.first_name, self.last_name )


class Story(models.Model):
    complete = models.BooleanField(default=False)
    
    title = models.CharField(max_length=100, default=DEFAULT_STORY_TITLE)
    prompt = models.CharField(max_length=250, blank=True)
    prompt_link = models.URLField(blank=True)
    
    contributors = models.ManyToManyField(Contributor)
    
    num_of_spots = models.IntegerField(default=2)
    num_of_turns = models.IntegerField(default=4)
    
    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( self.title, str(self.pk), )
    
    class Meta:
        verbose_name_plural = "stories"
    
    def get_number_of_fragments(self):
        return self.fragment_set.all().count()
    get_number_of_fragments.short_description = 'Number of Fragments'
    
    def get_number_of_contributors(self):
        return self.contributors.all().count()
    get_number_of_contributors.short_description = 'Number of Contributors'
        

class Fragment(models.Model):
    story = models.ForeignKey(Story)

    fragment = models.TextField(blank=True)
    position = models.IntegerField()
    
    last_edit = models.TextField(blank=True)
    complete = models.BooleanField(default=False)

    contributor = models.ForeignKey(Contributor)
    alias = models.CharField(max_length=100)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( str(self.id), self.fragment )


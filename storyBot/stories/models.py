from __future__ import unicode_literals

from django.db import models

DEFAULT_STORY_TITLE = "An amazing story in search of a title"

NUM_STORY_CONTRIBUTORS = 2
NUM_TURNS_PER_CONTRIBUTOR = 4

BROWSING = 'BR'
WRITING = 'WR'
NAMING = 'NM'
SPEAKING = 'SP'

CONTRIBUTOR_STATES = (
    (BROWSING, 'Browsing'),
    (WRITING, 'Writing'),
    (NAMING, 'Naming'),
    (SPEAKING, 'Speaking'),
)
class Contributor(models.Model):
    social_identifier = models.CharField(max_length=200)
    
    profile_pic = models.URLField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    locale = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.IntegerField(blank=True, null=True)
    
    state = models.CharField(max_length=2, choices=CONTRIBUTOR_STATES, default=BROWSING)

    last_active = models.DateTimeField(auto_now_add=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( self.first_name, self.last_name )
    
    def get_last_fragment(self, complete=False):
        return Fragment.objects.filter(contributor=self).filter(complete=complete).order_by('time_modified').first()

class Story(models.Model):
    complete = models.BooleanField(default=False)
    full = models.BooleanField(default=False)
    
    title = models.CharField(max_length=100, default=DEFAULT_STORY_TITLE)
    prompt = models.CharField(max_length=250, blank=True)
    prompt_link = models.URLField(blank=True)
    
    contributors = models.ManyToManyField(Contributor)
    
    num_of_contributors = models.IntegerField(default=NUM_STORY_CONTRIBUTORS)
    num_of_turns = models.IntegerField(default=NUM_STORY_CONTRIBUTORS*NUM_TURNS_PER_CONTRIBUTOR)
    
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

    contributor = models.ForeignKey(Contributor, blank=True, null=True)
    alias = models.CharField(max_length=100, blank=True, null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( str(self.id), self.fragment )


from __future__ import unicode_literals
import math
from random import choice

from django.db import models
from django.utils import timezone

from content_generators import generate_alias

DEFAULT_STORY_TITLE = "An amazing story in search for a title"
NUM_STORY_CONTRIBUTORS = 2

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

def calculate_num_of_turns( ):
    """calculates an number of turns for the story
    """
    LOWER_BOUND = 4
    UPPER_BOUND = 8
    return choice(range(LOWER_BOUND, UPPER_BOUND, 2)) # ensure its even


class Contributor(models.Model):
    social_identifier = models.CharField(max_length=200)
    
    profile_pic = models.URLField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    locale = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.IntegerField(blank=True, null=True)
    
    state = models.CharField(max_length=2, choices=CONTRIBUTOR_STATES, default=BROWSING)
    temp_alias = models.CharField(max_length=100, blank=True, null=True)
    last_active = models.DateTimeField(null=True, blank=True)
    stale = models.BooleanField(default=False)
    active_story = models.IntegerField(blank=True, null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def mark_last_active_time(self):
        self.last_active = timezone.now()
        self.save()
    
    def mark_stale(self):
        self.stale = True
        self.save()
    
    def mark_active(self):
        self.stale = False
        self.save()
    
    def update_state(self, state):
        self.state = state
        self.save()
    
    def reset_temp_alias(self):
        self.temp_alias = ""
        self.save()

    def get_last_fragment(self):
        return Fragment.objects.filter(contributor=self).order_by('time_modified').last()
    
    def set_active_story(self, id):
        self.active_story = id
        self.save()
    
    def get_active_story(self):
        if self.last_story:
            return Story.objects.get(id = self.active_story)
        else:
            return None
    
    def is_busy(self):
        """determine if the contributor is currently writing or part of a story
        that is not done
        """
        last_fragment = self.get_last_fragment()
        if last_fragment:
            last_story = last_fragment.story
            return (self.state is WRITING) or (not last_fragment.complete)
        else:
            return False
             
        
    def __str__(self):
        return '%s: %s' % ( self.first_name, self.last_name )

class Story(models.Model):
    complete = models.BooleanField(default=False)
    full = models.BooleanField(default=False)
    
    title = models.CharField(max_length=100, default=DEFAULT_STORY_TITLE)
    prompt = models.CharField(max_length=250, blank=True)
    prompt_link = models.URLField(blank=True)
    
    contributors = models.ManyToManyField(Contributor)
    
    num_of_contributors = models.IntegerField(default=NUM_STORY_CONTRIBUTORS)
    num_of_turns = models.IntegerField(default=calculate_num_of_turns())
    
    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def is_story_done(self):
        return self.fragment_set.filter(complete=True).count() == self.num_of_turns
    
    def mark_complete(self):
        self.complete = True
        self.save()
    
    def are_all_populated_fragments_done(self):
        return self.fragment_set.all().filter(contributor__isnull=False).filter(complete=False).count() == 0
    
    def add_contributor(self, contributor):
        if contributor not in self.contributors.all():
            self.contributors.add(contributor)
            
            # check if story is full
            if self.contributors.all().count() == self.num_of_contributors:
                self.full = True
            
            # commit the change
            self.save()
            
            # update the contributor
            contributor.set_active_story(self.id)
    
    def remove_contributor(self, contributor):
        if contributor in self.contributors.all():
            # remove from the active contributors
            self.contributors.remove(contributor)
            # a person left, so the story is not full
            self.full = False
            # commit the change
            self.save()
            
            # update the contributor
            contributor.mark_active()
            contributor.update_state(BROWSING)
            contributor.reset_temp_alias()
            contributor.set_active_story(0)
            
            # remove the fragment as it is no longer valid
            fragment = contributor.get_last_fragment()
            fragment.empty_fragment()
            
            # if everyone left, scrap the story
            if self.contributors.count() == 0:
                self.delete()
    
    def populate_with_fragments(self):
        for i in range(self.num_of_turns):
            fragment = Fragment.objects.create(story=self, position=i) 
    
    def associate_fragment_with_contributor(self, contributor):
        availible_story_fragments = self.fragment_set.filter(contributor__isnull=True).order_by('position')
        if availible_story_fragments:
            # update the next story fragment
            next_availible_story_fragment = availible_story_fragments.first()
            next_availible_story_fragment.contributor = contributor
            next_availible_story_fragment.alias = contributor.temp_alias if contributor.temp_alias else generate_alias()
            next_availible_story_fragment.save()

            contributor.mark_active()
            contributor.update_state(WRITING)

            return next_availible_story_fragment
        else:
            return None
    
    def get_last_incomplete_fragment(self):
        return self.fragment_set.filter(complete=False).order_by('position').first()
    
    def get_last_complete_fragment(self):
        return self.fragment_set.filter(complete=True).order_by('position').last()
    
    def get_next_contributor(self):
        last_complete_fragment = self.get_last_complete_fragment()
        story_contributors = self.contributors.all()
        if last_complete_fragment:
            last_contributor = last_complete_fragment.contributor
            last_contributor_index = list(story_contributors).index(last_contributor)
            next_contributor = story_contributors[ last_contributor_index + 1 ] if last_contributor_index + 1 < len(story_contributors) else story_contributors.first()
            
            return next_contributor
        else:
            return None
    
    def calculate_remaining_number_of_turns(self, contributor):
        """given a contributor returns how many turns that person has left in this story
        """
        num_empty_fragments = self.fragment_set.filter(contributor__isnull=True).count() + 1 # add one for the current user
        
        return int( math.ceil( 1.0 * num_empty_fragments / self.num_of_contributors ) )
   
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

    def mark_complete(self):
        self.complete = True
        self.save()
        # update the contributor
        contributor.mark_active()
        self.contributor.update_state(BROWSING)

    def edit(self, content):
        self.fragment = " ".join([self.fragment, content]).strip()
        self.last_edit = content
        self.save()
    
    def undo_edit(self):
        self.fragment = self.fragment[:-len(self.last_edit)].strip()
        self.last_edit = ""
        self.save()

    def empty_fragment(self):
        self.fragment = ""
        self.complete = False
        self.contributor = None
        self.alias = ""
        self.save()

    def __str__(self):
        return '%s: %s' % ( str(self.id), self.fragment )

        
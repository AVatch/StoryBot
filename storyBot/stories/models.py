from __future__ import unicode_literals

from django.db import models


class Contributor(models.Model):
    social_identifier = models.CharField(max_length=200)
    
    """
    the state keeps track of where the user is
    
    browsing -> user is not engaged with any story
    writing -> user is writing a fragment
    """
    state = models.CharField(max_length=20, default="browsing")

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( self.social_identifier, self.state )


class Story(models.Model):
    complete = models.BooleanField(default=False)
    title = models.CharField(max_length=100, default="An amazing story in search of a title")
    prompt = models.CharField(max_length=250, default="")
    prompt_link = models.URLField(blank=True)
    contributors = models.ManyToManyField(Contributor)
    
    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return 'Story ID - %s' % ( str(self.pk) )
    
    class Meta:
        verbose_name_plural = "stories"
        

class Fragment(models.Model):
    story = models.ForeignKey(Story)
    last_edit = models.TextField(default="") 
    fragment = models.TextField()
    position = models.IntegerField()
    alias = models.CharField(max_length=100)
    complete = models.BooleanField(default=False)

    contributor = models.ForeignKey(Contributor)

    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return '%s: %s' % ( str(self.id), self.fragment )


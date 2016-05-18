from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Error(models.Model):
    time_stamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    
    def __str__(self):
        return '%s: %s: %s' % ( str(self.id), str(self.time_stamp), self.message ) 
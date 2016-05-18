from django.contrib import admin

from .models import Error

# Register your models here.
class ErrorAdmin(admin.ModelAdmin):
    model = Error
admin.site.register(Error, ErrorAdmin)
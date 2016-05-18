from django.contrib import admin

from .models import Contributor, Fragment, Story


class ContributorAdmin(admin.ModelAdmin):
    model = Contributor
    list_display = ('social_identifier', 'state', 'first_name', 'last_name', 'locale', 'gender', 'timezone')
admin.site.register(Contributor, ContributorAdmin)


class FragmentInline(admin.TabularInline):
    model = Fragment
    extra = 1

class StoryAdmin(admin.ModelAdmin):
    model = Story
    inlines = [
        FragmentInline,
    ]
    list_display = ('complete', 'id', 'prompt', 'get_number_of_fragments', 'get_number_of_contributors', 'full', 'time_created', 'time_modified')

admin.site.register(Story, StoryAdmin)


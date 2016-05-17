from django.contrib import admin

from .models import Contributor, Fragment, Story


class ContributorAdmin(admin.ModelAdmin):
    model = Contributor
admin.site.register(Contributor, ContributorAdmin)


class FragmentInline(admin.TabularInline):
    model = Fragment
    extra = 1

class StoryAdmin(admin.ModelAdmin):
    model = Story
    inlines = [
        FragmentInline,
    ]
admin.site.register(Story, StoryAdmin)


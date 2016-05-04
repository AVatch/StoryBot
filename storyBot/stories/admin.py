from django.contrib import admin

from .models import Contributor, Fragment, Story


class ContributorAdmin(admin.ModelAdmin):
    model = Contributor
admin.site.register(Contributor, ContributorAdmin)


class FragmentAdmin(admin.ModelAdmin):
    model = Fragment
admin.site.register(Fragment, FragmentAdmin)


class StoryAdmin(admin.ModelAdmin):
    model = Story
admin.site.register(Story, StoryAdmin)

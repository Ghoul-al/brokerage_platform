from django.contrib import admin
from .models import Profile

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'username', 'phone_number', 'dob', 'gender', 'created', 'updated')
    search_fields = ('user__username', 'Name', 'username')
    list_filter = ('gender', 'created', 'updated')
    ordering = ('-created',)

admin.site.register(Profile, ProfileAdmin)


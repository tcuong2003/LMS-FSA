from import_export import resources
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Chat

class ChatResource(resources.ModelResource):
    class Meta:
        model = Chat
        fields = ('id', 'sender', 'receiver', 'message', 'timestamp')  # Add fields you want to import/export




@admin.register(Chat)
class ChatAdmin(ImportExportModelAdmin):
    resource_class = ChatResource
    list_display = ('sender', 'receiver', 'message', 'timestamp')  # Adjust the fields displayed in the admin
    search_fields = ('sender__username', 'receiver__username', 'message')  # Search fields for the admin

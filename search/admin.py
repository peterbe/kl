# django
from django.contrib import admin

# app
from models import Word, Search

class WordAdmin(admin.ModelAdmin):

    list_display = ('word', 'length', 'part_of_speech')
    #list_filter = ['word','length', 'part_of_speech']
    #ordering = ('word', 'length')
    
    def save_model(self, request, obj, form, change):
        print obj.length
        obj.save()    
    
    
admin.site.register(Word, WordAdmin)

class SearchAdmin(admin.ModelAdmin):
    list_display = ('search_word', 'ip_address', 'language', 'add_date')
    list_filter = ('language',)
    ordering = ('-add_date',)
    

admin.site.register(Search, SearchAdmin)
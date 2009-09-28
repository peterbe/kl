import os
import glob
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = 'Adds a new word the database'
    
    def handle_noargs(self, **options):

        from search.views import ALL_LANGUAGE_OPTIONS, _get_word_definition, \
          _get_word_definition_scrape, add_word_definition
        
        word = unicode(raw_input("Word: ").strip(), 'utf8')
        length = len(word)
        print repr(word), length
        
        
        langs = []
        for option in ALL_LANGUAGE_OPTIONS:
            answer = raw_input('\t%s [y/N] ' % option['label'].encode('latin1'))
            if answer.lower() in ('y','yes'):
                langs.append(option['code'].lower())
                
        # insert them finally!
        from search.models import Word
        
        definition = ''
        
        for lang in langs:
            word_object = Word.objects.create(word=word, language=lang, length=length)
            cache_key = '_find_alternatives_%s_%s' % (word, lang)
            cache.delete(cache_key)
            
            if not definition:
                try:
                    definition = _get_word_definition(word, language=lang)
                except AttributeError:
                    # sometimes you get a weird AttributeError in nltk
                    pass
                
                if not definition:
                    _get_word_definition_scrape(word, language=lang)
                
            if definition:
                add_word_definition(word, definition, language=lang)


from pprint import pprint
import datetime
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from collections import defaultdict
from search.views import _get_word_definition, _get_word_definition_scrape
from search.data import add_word_definition
from search.models import Search

SEARCH_SUMMARY_SKIPS = \
('crossword','korsord','fuck','peter','motherfucker',
 )



class Command(BaseCommand):
    help = """Lookup definitions"""
    
    
    def handle(self, *args, **options):
        #if not args:
        #    raise CommandError("USAGE: ./manage.py %s <word> <lang> [save]" % \
        #                       os.path.basename(__file__).split('.')[0])
        
        max_ = 2
        
        today = datetime.date.today()
        today=datetime.date(2009,4,1)#HACK!
        since = datetime.date(today.year, today.month, 1)
        
        definitions = {}
        

        searches = Search.objects.filter(add_date__gte=since,
                                              found_word__isnull=False,
                                              found_word__definition__isnull=True)

        searches = searches.exclude(found_word__word__in=list(SEARCH_SUMMARY_SKIPS))
        
        # because I know I have no way to look up Swedish words, no point finding them
        searches = searches.exclude(language='sv')
    
        found_words = defaultdict(list)
        definitions = {}
        for each in searches:
            found_words[each.language].append(each.found_word.word)
    
            if each.language not in definitions:
                definitions[each.found_word.language] = {}
            #if each.found_word.definition:
            #    definitions[each.found_word.language][each.found_word.word.lower()]\
            #    = each.found_word.definition.splitlines()
                
        found_words = dict(found_words)
        #pprint(found_words)
        #return
        
        atleast_count = 2
        found_words_repeats = {}
        for language, words in found_words.items():
            counts = defaultdict(int)
            for word in words:
                if len(word) < 2:
                    # don't want to find single character words
                    # It's a bug that they're even in there
                    continue
                counts[word.lower()] += 1
                found_words_repeats[language] = sorted([k for (k,v)
                                                        in counts.items() if v >= atleast_count],
                                                       lambda x,y: cmp(y[1], x[1]))
            #pprint(found_words_repeats)
            pprint(dict(counts))
        return 
        count = 0    
        for lang, words in found_words_repeats.items():
            for word in words:
                try:
                    definitions[lang][word]
                except KeyError:
                    if lang in ('en-us','en-gb'):
                        # wordnet
                        definition = _get_word_definition(word, language=lang)
                    else:
                        definition = None

                    if not definition:
                        definition = _get_word_definition_scrape(word, language=lang)
                    if definition:
                        add_word_definition(word, definition, language=lang)
                        
                    count += 1
                    
                    if count >= max_:
                        break
                    

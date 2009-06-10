from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from search.views import _get_word_definition_scrape
from search.models import Word

class Command(BaseCommand):
    help = """Lookup definitions"""
    
    
    def handle(self, *args, **options):
        if not args:
            raise CommandError("USAGE: ./manage.py %s <word> <lang> [save]" % \
                               os.path.basename(__file__).split('.')[0])
            
        args = list(args)
        save = False
        if 'save' in args:
            save = True
            args.remove('save')
            
        word = args[0]
        
        try:
            language = args[1]
        except IndexError:
            language = 'en'
            
        definition = _get_word_definition_scrape(word, language)
        
        if save and definition:
            try:
                word_obj = Word.objects.get(language=language, word__iexact=word)
                word_obj.definition = definition
                word_obj.save()
            except Word.DoesNotExist:
                pass
        
        for each in definition.splitlines():
            print "*\t", repr(each)
            print
            
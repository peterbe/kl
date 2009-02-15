# python
import datetime
try:
    import simplejson
except ImportError:
    from django.utils import simplejson

# django
from django.test.client import Client
from django.test import TestCase

# project
from search.views import _get_search_stats
from search.models import Word, Search

class ViewTestCase(TestCase):
    """
    Testing views
    """
    
    def test_solve_errors(self):
        """ test sending rubbish to solve() """
        client = Client()
        response = client.get('/los/?l=x')
        # redirects means it's unhappy
        assert response.status_code == 302, response.status_code
        
        response = client.get('/los/?l=3&s=a')
        assert response.status_code == 302, response.status_code
        
        
    def _add_word(self, word, language, part_of_speech=u'', name=False):
        Word.objects.create(word=word, length=len(word),
                            part_of_speech=part_of_speech,
                            language=language,
                            name=name)
        
    def test_solve_json(self):
        """ do an actual search """
        # add some that will help the search
        self._add_word(u'abc', 'sv')
        self._add_word(u'abd', 'sv')
        self._add_word(u'acd', 'sv')
        
        client = Client()
        response = client.get('/los/json/?l=3&s=a&s=b&s=&lang=sv')
        
        struct = simplejson.loads(response.content)
        assert not struct['alternatives_truncated']
        assert struct['word_count'] == 2
        assert struct['match_points'] == [1,1,0]
        assert struct['words'] == ['abc','abd']
        assert struct['search'] == 'ab '
        
        recorded_search = Search.objects.get(search_word='ab ')
        # because multiples were found, it doesn't refer to a word
        assert recorded_search.found_word is None
        
        # do another search were we find exactly one result
        response = client.get('/los/json/?l=3&s=&s=c&s=d')
        
        struct = simplejson.loads(response.content)
        assert struct['word_count'] == 1
        assert struct['match_points'] == [0,1,1]
        assert struct['words'] == ['acd']
        assert struct['search'] == ' cd'
        
        recorded_search = Search.objects.get(search_word=' cd')
        word_instance = recorded_search.found_word
        assert word_instance is not None
        assert word_instance.word == u'acd'
        
        
    def test__get_search_stats(self):
        """ test the private method _get_search_stats() """
        res = _get_search_stats()
        assert res['no_total_words'] == 0
        assert res['no_searches_today'] == 0
        assert res['no_searches_yesterday'] == 0
        assert res['no_searches_this_week'] == 0
        assert res['no_searches_this_month'] == 0
        assert res['no_searches_this_year'] == 0
        
        self._add_word(u'abc', 'sv')
        self._add_word(u'abd', 'sv')
        self._add_word(u'acd', 'sv')
        
        res = _get_search_stats()
        assert res['no_total_words'] == 3
        assert res['no_searches_today'] == 0
        assert res['no_searches_yesterday'] == 0
        assert res['no_searches_this_week'] == 0
        assert res['no_searches_this_month'] == 0
        assert res['no_searches_this_year'] == 0        

        # do a search "today"
        client = Client()
        client.get('/los/json/?l=3&s=a&s=b&s=&lang=sv')
        
        res = _get_search_stats()
        assert res['no_total_words'] == 3
        assert res['no_searches_today'] == 1

        # do another search and then manually nudge it's add_date
        client.get('/los/json/?l=3&s=x&s=x&s=x')
        s = Search.objects.get(search_word=u'xxx')
        s.add_date = datetime.datetime.today() - datetime.timedelta(days=1)
        s.save()
        
        res = _get_search_stats()
        assert res['no_total_words'] == 3
        assert res['no_searches_yesterday'] == 1
        
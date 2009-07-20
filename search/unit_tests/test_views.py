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
from search.views import get_search_stats, _get_variations, _find_alternatives
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
        
        self.assertEquals(struct['words'],
                          [{'word':'abc'}, {'word':'abd'}])
        assert struct['search'] == 'ab '
        
        recorded_search = Search.objects.get(search_word='ab ')
        # because multiples were found, it doesn't refer to a word
        assert recorded_search.found_word is None
        
        # do another search were we find exactly one result
        response = client.get('/los/json/?l=3&s=&s=c&s=d&lang=sv')
        struct = simplejson.loads(response.content)
        self.assertEquals(struct['word_count'], 1)
        self.assertEquals(struct['match_points'], [0,1,1])
        self.assertEquals(struct['words'], 
                          [{'word':'acd'}])
        self.assertEquals(struct['search'], ' cd')
        
        recorded_search = Search.objects.get(search_word=' cd')
        word_instance = recorded_search.found_word
        assert word_instance is not None
        assert word_instance.word == u'acd'
        
        
    def test_get_search_stats(self):
        """ test the get_search_stats() """
        func = lambda l: get_search_stats(l, use_cache=False)
        
        res = func('sv')
        assert res['no_total_words'] == 0
        assert res['no_searches_today'] == 0
        assert res['no_searches_yesterday'] == 0
        assert res['no_searches_this_week'] == 0
        assert res['no_searches_this_month'] == 0
        assert res['no_searches_this_year'] == 0
        
        self._add_word(u'abc', 'sv')
        self._add_word(u'abd', 'sv')
        self._add_word(u'acd', 'sv')
        
        res = func('sv')
        self.assertEquals(res['no_total_words'], 3)
        assert res['no_searches_today'] == 0
        assert res['no_searches_yesterday'] == 0
        assert res['no_searches_this_week'] == 0
        assert res['no_searches_this_month'] == 0
        assert res['no_searches_this_year'] == 0        

        # do a search "today"
        client = Client()
        response = client.get('/los/json/?l=3&s=a&s=b&s=&lang=sv')
        
        res = func('sv')
        assert res['no_total_words'] == 3
        self.assertEquals(res['no_searches_today'], 1)

        # do another search and then manually nudge it's add_date
        client.get('/los/json/?l=3&s=x&s=x&s=x&lang=sv')
        s = Search.objects.get(search_word=u'xxx')
        self.assertEquals(s.language, u'sv')
        s.add_date = datetime.datetime.today() - datetime.timedelta(days=1)
        s.save()
        
        res = func('sv')
        self.assertEquals(res['no_total_words'], 3)
        self.assertEquals(res['no_searches_yesterday'], 1)
        
        
    def test_search_with_clue(self):
        """test if wordnet is installed """
        from search.views import wordnet
        if wordnet is None:
            return

        client = Client()
        # surface, 7 letters
        from urllib import urlencode
        qs = urlencode(dict(l=7, s=list('surfac_'), lang='en-gb', clues='floor'), 
                       doseq=True)
        response = client.get('/los/json/?' + qs.replace('_',''))
        struct = simplejson.loads(response.content)
        # Incomplete test!
        #print struct
        
        
    def test__get_variations_simple(self):
        """ test the private method _get_variations() """
        from search.views import wordnet
        if wordnet is None:
            return

        r= _get_variations(u'partying')
        self.assertTrue(u'partying' not in r)
        self.assertTrue(u'party' in r)
        self.assertTrue(u'parties' in r)
        self.assertTrue(u'celebrate' in r)
        self.assertTrue(u'celebrates' in r)
        
        r = _get_variations(u'party')
        self.assertTrue(u'party' not in r)
        self.assertTrue(u'partying' in r)
        self.assertTrue(u'parties' in r)
        
        
    def test__get_variations_name(self):
        """ test the private method _get_variations() """
        from search.views import wordnet
        if wordnet is None:
            return

        r= _get_variations(u'Peter')
        self.assertTrue(not bool(r))
        
        
    def test_regression__general_search(self):
        """stupidity test that checks that _E_E_A_ matches
        'GENERAL'
        """
        #Word.objects.create(word='peter', language='en-us')
        #response = self.client.get('/simple/?slots=_E_E_&language=en-us')
        #print response.content
        
        Word.objects.create(word='general', language='en-us')
        response = self.client.get('/simple/?slots=_E_E_A_&language=en-us')
        #print response.content
        self.assertTrue('1 match found' in response.content)

        # hack to reset the cache for this search
        cache_key = '_find_alternatives__e_e_a__en-us'
        from django.core.cache import cache
        cache.delete(cache_key)
        
        Word.objects.create(word='federal', language='en-us')
        response = self.client.get('/simple/?slots=_E_E_A_&language=en-us')
        #print response.content
        self.assertTrue('2 matches found' in response.content)

        
    def test__find_alternatives(self):
        """return the right alternatives"""
        slots = [u' ', u' ', u' ', u'T', u'A', u'M', u' ', u' ', u'T']
        language = 'fr'
        
        # add a word we expect to find
        t1 = Word.objects.create(word=u'testament', language='fr')
        func = _find_alternatives
        
        self.assertEqual(func(slots, language), [t1])
        
        



        
        

        
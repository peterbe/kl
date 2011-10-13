import datetime
from urlparse import urlparse, urljoin
from urllib import urlencode, quote
import urllib2
import re
from pprint import pprint
from cStringIO import StringIO
import logging
from time import time, mktime, sleep
from random import randint, shuffle
try:
    import simplejson
except ImportError:
    from django.utils import simplejson

from lxml.html import parse
from lxml import etree
from lxml.cssselect import CSSSelector

# Create your views here.
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect,  Http404
from django.template import RequestContext
from django.core.cache import cache
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError
from django.utils.translation import ugettext as _
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.views.decorators.cache import cache_page, never_cache
from django.conf import settings
from models import Word, Search
from forms import DSSOUploadForm, FeedbackForm, WordlistUploadForm, SimpleSolveForm, QUIZZES
from forms import WordWhompForm, AddWordForm
from utils import uniqify, any_true, ValidEmailAddress, stats, niceboolean, print_sql
from morph_en import variations as morph_variations
from data import add_word_definition, ip_to_coordinates, save_ip_lookup
from data import get_searches_rate
from googlecharts import get_search_types_pie, get_languages_pie, get_lengths_bar, \
  get_definitionlookups_bar

from utils import ONE_HOUR, ONE_DAY, ONE_WEEK, ONE_MONTH
from search.googlecharts import get_sparklines_cached

def _render_json(data):
    return HttpResponse(simplejson.dumps(data),
                        mimetype='application/javascript')

def _render(template, data, request):
    return render_to_response(template, data,
                              context_instance=RequestContext(request))

def set_cookie(response, key, value, expire=None):
    # http://www.djangosnippets.org/snippets/40/
    if expire is None:
        max_age = 365*24*60*60  #one year
    else:
        max_age = expire
    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + \
      datetime.timedelta(seconds=max_age), "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie(key, value, max_age=max_age, expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        secure=settings.SESSION_COOKIE_SECURE or None)


ONE_DAY = 60 * 60 * 24 # one day in seconds

STOPWORDS = (
             "a", "and", "are", "as", "at", "be", "but", "by",
             "for", "if", "in", "into", "is", "it",
             "no", "not", "of", "on", "or", "such",
             "that", "the", "their", "then", "there", "these",
             "they", "this", "to", "was", "will", "with",
            )



ALL_LANGUAGE_OPTIONS = (
        {'code':'sv', 'label':'Svenska', 'domain':'krysstips.se'},
        {'code':'en-US', 'label':'English (US)', 'domain':'en-us.crosstips.org',
         'title':"American English"},
        {'code':'en-GB', 'label':'English (GB)', 'domain':'en-us.crosstips.org',
         'title':"British English"},
        {'code':'fr', 'label':u'Fran\xe7ais', 'domain':'fr.crosstips.org'},
)

SEARCH_SUMMARY_SKIPS = \
('crossword','korsord','fuck','peter','motherfucker',
 )


class SearchResult(object):
    def __init__(self, word, definition=u'', by_clue=None):
        self.word = word
        self.definition = definition
        self.by_clue = by_clue


from view_cache_utils import cache_page_with_prefix
def _base_key_prefixer(request):
    if request.GET.keys():
        # really worried
        return None

    # ultimately get_cache_key() will just contain an md5 hash of the
    # request.path but we want it to depend on the host used to
    # e.g. crosstips.org should be different from fr.crosstips.org

    key = request.get_host().split(':')[0]
    if request.mobile:
        key += 'mobile'
    if request.iphone:
        key += 'iphone'

    return key

def _sensitive_key_prefixer(request):
    if request.session.get('has_searched'):
        # if they have done a search they might expect the counter
        # to go up
        return None

    return _base_key_prefixer(request)

def _less_sensitive_key_prefixer(request):
    # do cache like normal even if you have done a search
    return _base_key_prefixer(request)



@cache_page_with_prefix(ONE_HOUR, _sensitive_key_prefixer)
def solve(request, json=False, record_search=True):
    # By default we are set to record the search in our stats
    # This can be overwritten by a CGI variable called 'r'
    # E.g. r=0 or r=no
    if request.GET.get('r'):
        record_search = niceboolean(request.GET.get('r'))

    if request.GET.get('l'):
        try:
            length = int(request.GET.get('l'))
        except ValueError:
            return HttpResponseRedirect('/?error=length')
        slots = request.GET.getlist('s')
        if not type(slots) is list:
            return HttpResponseRedirect('/?error=slots')

        notletters = request.GET.get('notletters', u'').upper()
        notletters = [x.strip() for x in notletters.split(',')
                      if len(x.strip()) == 1 and not x.strip().isdigit()]

        if not len(slots) >= length:
            return HttpResponseRedirect('/?error=slots&error=length')

        if not [x for x in slots if x.strip()]:
            # all blank
            return HttpResponseRedirect('/?error=slots')

        clues = request.GET.get('clues', u'')
        if clues and ' ' in clues and ',' not in clues:
            clues = clues.replace(' ',', ')
        clues = [x.strip() for x in clues.split(',')
                 if x.strip() and x.strip().lower() not in STOPWORDS and not x.count(' ')]

        language = request.GET.get('lang', request.LANGUAGE_CODE).lower()

        search_results = [] # the final simple list that is sent back

        for clue in clues:
            alternatives = _find_alternative_synonyms(clue, slots[:length], language,
                                                      notletters=notletters,
                                                      request=request)
            search_results.extend([SearchResult(x, by_clue=clue) for x in alternatives])

        # find some alternatives
        search = ''.join([x and x.lower() or ' ' for x in slots[:length]])
        cache_key = '_find_alternatives_%s_%s' % (search, language)
        if notletters:
            cache_key += '__not' + u''.join(notletters)
        cache_key = cache_key.replace(' ','_')
        if re.findall('\s', cache_key):
            raise ValueError("invalid cache_key search=%r, language=%r" % (search, language))

        alternatives = cache.get(cache_key)
        if alternatives is None:
            alternatives = _find_alternatives(slots[:length], language, notletters=notletters)
            cache.set(cache_key, alternatives, ONE_DAY)

        alternatives_count = len(alternatives)
        alternatives_truncated = False
        if alternatives_count > 100:
            alternatives = alternatives[:100]
            alternatives_truncated = True

        result = dict(length=length,
                      search=search,
                      word_count=alternatives_count,
                      alternatives_truncated=alternatives_truncated,
                     )
        already_found = [x.word for x in search_results]
        search_results.extend([SearchResult(each.word,
                                            definition=each.definition)
                               for each in alternatives
                               if each.word not in already_found])
        match_points = None
        match_points = []
        if search_results:
            first_word = search_results[0].word
            for i, letter in enumerate(first_word):
                if letter.lower() == search[i]:
                    match_points.append(1)
                else:
                    match_points.append(0)
            result['match_points'] = match_points

        result['words'] = []
        for search_result in search_results:
            v = dict(word=search_result.word)
            if search_result.definition:
                v['definition'] = search_result.definition
            if search_result.by_clue:
                v['by_clue'] = search_result.by_clue
            result['words'].append(v)


        if alternatives_count == 1:
            result['match_text'] = _("1 match found")
        elif alternatives_count:
            if alternatives_truncated:
                result['match_text'] = _("%(count)s matches found but only showing first 100")\
                  % dict(count=alternatives_count)
            else:
                result['match_text'] = _("%(count)s matches found") % \
                  dict(count=alternatives_count)
        else:
            result['match_text'] = _("No matches found unfortunately :(")

        found_word = None
        if len(search_results) == 1:
            try:
                found_word = Word.objects.get(word=search_results[0].word,
                                              language=language)
            except Word.DoesNotExist:
                # this it was probably not from the database but
                # from the wordnet stuff
                found_word = None

        if record_search:

            _record_search(search,
                           user_agent=request.META.get('HTTP_USER_AGENT',''),
                           ip_address=request.META.get('REMOTE_ADDR',''),
                           found_word=found_word,
                           language=language)

        request.session['has_searched'] = True

        if json:
            return _render_json(result)

    else:
        length = '' # default

    show_example_search = not bool(request.session.get('has_searched'))
    if not show_example_search:
        most_recent_search_word = _get_recent_search_word(request)

    accept_clues = wordnet is not None and \
      request.LANGUAGE_CODE.lower() in ('en', 'en-gb', 'en-us')

    ad_widget_template = 'kwisslewidget.html'
    if language in ('en-gb', 'fr'):
        ad_widget_template = 'minriverteawidget.html'

    data = locals()
    return _render('solve.html', data, request)

def _get_recent_search_word(request):
    _today = datetime.datetime.today()
    _since = datetime.datetime(_today.year, _today.month, 1)

    _extra_exclude = dict(found_word__word__in=list(SEARCH_SUMMARY_SKIPS))
    if request.META.get('HTTP_USER_AGENT'):
        _extra_exclude['user_agent'] = request.META.get('HTTP_USER_AGENT')
    if request.META.get('REMOTE_ADDR'):
        _extra_exclude['ip_address'] = request.META.get('REMOTE_ADDR')

    _extra_filter = dict()
    # Special hack! Since the search summary has a cache of 1 hour,
    # don't include things that are too recent
    _extra_filter['add_date__lt'] = _today - datetime.timedelta(hours=1)

    return _find_recent_search_word(request.LANGUAGE_CODE,
                                    since=_since,
                                    random=True,
                                    extra_exclude=_extra_exclude,
                                    **_extra_filter)


def _find_recent_search_word(language, since=None, random=False, extra_exclude={}, **extra_filter):
    searches = Search.objects.filter(language=language, found_word__isnull=False,
                                     **extra_filter).select_related('found_word')

    if since:
        searches = searches.filter(add_date__gte=since)
    searches = searches.exclude(**extra_exclude)

    if random:
        # For some bizzare reason it seems that even if the exclude above
        # has found_word__word__in=SEARCH_SUMMARY_SKIPS it still returns
        # words from that list!!!!
        # Hence this list comprehension.
        found_words = [x.found_word for x in searches
                       if x.found_word.word not in SEARCH_SUMMARY_SKIPS]
        shuffle(found_words)
        try:
            return found_words[0]
        except IndexError:
            return None
    else:
        searches = searches.order_by('-add_date')
        return searches[0].found_word
    return None



def _record_search(search_word, user_agent=u'', ip_address=u'',
                   found_word=None,
                   language=None,
                   search_type=u''):
    if len(user_agent) > 200:
        user_agent = user_agent[:200]
    if len(ip_address) > 15:
        import warnings
        warnings.warn("ip_address too long (%r)" % ip_address)
        ip_address = u''
    elif ip_address == '127.0.0.1' and settings.DEBUG:
        # because 127.0.0.1 can't be looked up, use a random other one
        examples = '125.239.15.42,114.199.97.224,68.190.165.25,208.75.100.212,'\
                   '61.29.84.154,72.49.16.234,66.57.228.64,196.25.255.250,'\
                   '141.117.6.97,85.68.18.183,90.157.186.202'.split(',')
        shuffle(examples)
        ip_address = examples[0]


    Search.objects.create(search_word=search_word,
                          user_agent=user_agent.strip(),
                          ip_address=ip_address.strip(),
                          found_word=found_word,
                          language=language,
                          search_type=search_type,
                          )

def get_search_stats(language):
    """ wrapper on _get_search_stats() that uses a cache instead """
    res = _get_search_stats(language)
    return res


def _get_search_stats(language):
    # Total no words in our database
    cache_key = 'no_total_words_%s' % language
    no_total_words = cache.get(cache_key)
    if no_total_words is None:
        no_total_words = Word.objects.filter(language=language).count()
        cache.set(cache_key, no_total_words, ONE_MONTH)


    today = datetime.datetime.today()

    # Searches today
    today_midnight = datetime.datetime(today.year, today.month,
                                       today.day, 0, 0, 0)
    cache_key = 'no_searches_today_%s' % language
    no_searches_today = cache.get(cache_key)
    if no_searches_today is None:
        no_searches_today = Search.objects.filter(language=language,
                                                  add_date__gte=today_midnight).count()
        cache.set(cache_key, no_searches_today, ONE_DAY)


    # Searches yesterday
    cache_key = 'no_searches_yesterday_%s' % language
    no_searches_yesterday = cache.get(cache_key)
    if no_searches_yesterday is None:
        yesterday_midnight = today_midnight - datetime.timedelta(days=1)
        no_searches_yesterday = Search.objects.filter(language=language,
                add_date__range=(yesterday_midnight, today_midnight)).count()
        cache.set(cache_key, no_searches_yesterday, ONE_DAY)

    # Searches this week
    cache_key = 'no_searches_this_week_%s' % language
    no_searches_this_week = cache.get(cache_key)
    if no_searches_this_week is None:
        # find the first monday
        monday_midnight = today_midnight
        while monday_midnight.strftime('%A') != 'Monday':
            monday_midnight = monday_midnight - datetime.timedelta(days=1)

        no_searches_this_week = Search.objects.filter(
                                            language=language,
                                            add_date__gt=monday_midnight).count()
        cache.set(cache_key, no_searches_this_week, ONE_DAY)

    # Searches this month
    cache_key = 'no_searches_this_month_%s' % language
    no_searches_this_month = cache.get(cache_key)
    if no_searches_this_month is None:
        first_day_month = datetime.datetime(today.year, today.month, 1, 0, 0, 0)
        no_searches_this_month = Search.objects.filter(language=language,
                                                       add_date__gte=first_day_month).count()
        cache.set(cache_key, no_searches_this_month, ONE_HOUR)

    # Searches this year
    cache_key = 'no_searches_this_year_%s' % language
    no_searches_this_year = cache.get(cache_key)
    if no_searches_this_year is None:
        first_day_year = datetime.datetime(today.year, 1, 1, 0, 0, 0)
        no_searches_this_year = Search.objects.filter(language=language,
                                           add_date__gte=first_day_year).count()
        cache.set(cache_key, no_searches_this_year, ONE_HOUR)

    del cache_key

    return locals()

def get_saved_cookies(request):
    cookie__name = request.COOKIES.get('kl__name')
    cookie__email = request.COOKIES.get('kl__email')
    return dict([(k,v) for (k,v) in locals().items() if v is not None])

try:
    from nltk.corpus import wordnet
except ImportError:
    wordnet = None


def XXX_find_alternative_synonyms(word, slots, language):
    if wordnet is None:
        return []

    length = len(slots)

    slots = [x and x.lower() or ' ' for x in slots]
    search = ''.join(slots)
    start = ''
    end = ''
    try:
        start = re.findall('^\w+', search)[0]
    except IndexError:
        pass

    try:
        end = re.findall('\w+$', search)[0]
    except IndexError:
        pass


    def filter_match(word):

        if end and not word.endswith(end):
            # Don't even bother
            return False
        elif start and not word.startswith(start):
            # Don't even bother
            return False

        if end:
            matchable_string = search[len(start):-len(end)]
            found_string = word[len(start):-len(end)]
        else:
            matchable_string = search[len(start):]
            found_string = word[len(start):]
        assert len(matchable_string) == len(found_string)
        for i, each in enumerate(matchable_string):
            if each != u' ' and each != found_string[i]:
                # can't be match
                return False
        return True



    def test(word, pos, pluralize=True):
        if len(word) == length:
            return filter_match(word)
        elif pluralize and pos == wordnet.NOUN:
            # still here,
            # getting desperate!
            as_plural = plural(word)
            if as_plural != word:
                return test(as_plural, pos, pluralize=False)


    def plural(word):
        if word.endswith('y'):
            return word[:-1] + 'ies'
        elif word[-1] in 'sx' or word[-2:] in ['sh', 'ch']:
            return word + 'es'
        elif word.endswith('an'):
            return word[:-2] + 'en'
        return word + 's'


    tested_words = []

    matched_words = []
    for synset in wordnet.synsets(word):
        s_word = synset.name.split('.')[0]
        if synset.definition:
            try:
                add_word_definition(s_word, synset.definition, language=language)
            except Word.DoesNotExist:
                pass
        if s_word not in tested_words and not s_word.count('_'):
            tested_words.append(s_word)
            if test(s_word, synset.pos):
                matched_words.append(s_word)

            for variation in morph_variations(s_word):
                if len(variation) == length and variation not in tested_words:
                    tested_words.append(variation)
                    test(variation, None)

        for sub_synset in wordnet.synset(synset.name).hypernyms():
            s_word = sub_synset.name.split('.')[0]
            if sub_synset.definition:
                try:
                    add_word_definition(s_word, sub_synset.definition, language=language)
                except Word.DoesNotExist:
                    pass
            if s_word not in tested_words and not s_word.count('_'):
                tested_words.append(s_word)
                if test(s_word, sub_synset.pos):
                    matched_words.append(s_word)

                for variation in morph_variations(s_word):
                    if len(variation) == length and variation not in tested_words:
                        tested_words.append(variation)
                        test(variation, None)

    tested_words.sort()

    del tested_words

    return matched_words


def _find_alternative_synonyms(word, slots, language, notletters=[], request=None):
    length = len(slots)

    slots = [x and x.lower() or ' ' for x in slots]
    search = ''.join(slots)
    start = ''
    end = ''
    try:
        start = re.findall('^\w+', search)[0]
    except IndexError:
        pass

    try:
        end = re.findall('\w+$', search)[0]
    except IndexError:
        pass

    def filter_match(word):

        if end and not word.endswith(end):
            # Don't even bother
            return False
        elif start and not word.startswith(start):
            # Don't even bother
            return False

        if end:
            matchable_string = search[len(start):-len(end)]
            found_string = word[len(start):-len(end)]
        else:
            matchable_string = search[len(start):]
            found_string = word[len(start):]
        assert len(matchable_string) == len(found_string)
        for i, each in enumerate(matchable_string):
            if each != u' ' and each != found_string[i]:
                # can't be match
                return False
        return True

    def test(word):
        if len(word) == length:
            if not notletters:
                for letter in word:
                    if letter.upper() in notletters:
                        return False
            return filter_match(word)

    for variation in _get_variations(word, greedy=True, request=request):
        if test(variation):
            yield variation



def variationstester(request):
    if request.GET.get('words'):
        words = request.GET.get('words')
        greedy = request.GET.get('greedy')
        if words.count(','):
            splitted = words.split(',')
        else:
            splitted = words.split()
        all_words = [x.strip() for x in splitted if x.strip()]
        variations = []
        for word in all_words:
            block = _get_variations(word,
                                    greedy=greedy,
                                    store_definitions=request.GET.get('store_definitions'),
                                    request=request)
            block.sort()
            variations.append(block)

    return _render('variationstester.html', locals(), request)

def word_definition_lookup(request):
    if request.GET.get('word'):
        filter_ = dict(word__iexact=request.GET.get('word'))
        if request.GET.get('language'):
            filter_ = dict(filter_, language=request.GET.get('language'))

        try:
            word_object = Word.objects.get(**filter_)
        except Word.DoesNotExist:
            word_object = None
            unrecognized_word = True

        if word_object is not None:
            definition = word_object.definition

            if not definition:
                definition = _get_word_definition(word_object.word,
                                                  language=word_object.language)
                if not definition:
                    definition = _get_word_definition_scrape(word_object.word,
                                                             language=word_object.language)

                if definition:
                    add_word_definition(word_object.word,
                                        definition,
                                        language=word_object.language)


    return _render('word_definition_lookup.html', locals(), request)

def _get_word_definition(word, language=None):
    if language.lower() in ('en-us', 'en-gb'):
        for synset in wordnet.synsets(word):
            if synset.name.split('.')[0] == word:
                return synset.definition

def _get_word_definition_scrape(word, language=None):
    if language.lower() not in ('en-us','en-gb','fr'):
        return

    if language == 'fr':
        url = "http://www.le-dictionnaire.com/definition.php"
        query = {'mot':word.encode('utf-8'),
                }
        url += '?%s' % urlencode(query)

        cache_key = 'ledictionnaire_download_%s' % \
          smart_str(url.replace('http://',''))

        extractor = _extract_definitions_le_dictionnaire

    else:
        url = "http://www.google.com/search"#?hl=en&client=firefox-a&rls=com.ubuntu%3Aen-GB%3Aunofficial&q=define%3Abanyans&btnG=Search&meta=
        if language.lower() == 'en-gb':
            url = url.replace('.com', '.co.uk')
        query = {'hl': language.lower().split('-')[0],
                'q': 'define:%s' % word.encode('utf-8'),
                'ie': 'utf-8',
                'oe': 'utf-8'
                }
        url += '?%s' % urlencode(query)

        cache_key = 'google_define_download_%s' % url.replace('http://','')

        extractor = _extract_definitions_google


    # take a random search from Searches to
    request_meta = {}
    request_meta['HTTP_USER_AGENT'] = _get_random_used_user_agent()
    logging.info("cache_key=%r" % cache_key)
    try:
        html = cache.get(cache_key)
    except DjangoUnicodeDecodeError:
        html = None

    if html is None:
        print "URL", url
        html = _download_url(url, request_meta)
        sleep(2) # to not piss off Google/le-dictionnaire.com
        print "Downloaded", len(html), "bytes"
        print
        cache.set(cache_key, html)

    # happens on Google
    if "No definitions of" in html and "were found in English" in html:
        return

    definitions = extractor(html)
    if definitions:
        # perhaps combined it becomes larger than 245 characters
        # (actually 250 but worried about line breaks)
        while sum([len(x) for x in definitions]) > 245:
            definitions = definitions[:-1]
            if len(definitions) == 1 and len(definitions[0]) > 245:
                definitions = [definitions[0][:245]]
                break

        # 250 characters is the max
        return '\n'.join([x.strip() for x in definitions if x.strip()])[:250]


def _extract_definitions_le_dictionnaire(html, max_definitions=3):
    if isinstance(html, unicode):
        html = html.encode('utf8')
    parser = etree.HTMLParser()
    tree = etree.parse(StringIO(html), parser)
    page = tree.getroot()
    assert page is not None, "root is None!"
    sel = CSSSelector('td.arial-12-gris')
    sel2 = CSSSelector('span')

    definitions = []

    #tables = list(CSSSelector('table')(page))
    #for i, table in enumerate(tables):
     #   #print dir(table)
     #   print i
     #   print repr(etree.tostring(table))
     #   print "\n"

    tables = list(CSSSelector('table')(page))[4:8]
    for table in tables:
        #print etree.tostring(table)
        for td in sel(table):
            definition = []
            for span in sel2(td):
                s = span.attrib.get('style')
                if s in ('color: #ABABAB;', 'cursor: pointer;'):
                    if span.text:
                        definition.append(span.text)

            definitions.append(' '.join(definition))
        if len(definitions) >= max_definitions:
            break

    return definitions

    #raise ValueError

def _extract_definitions_google(html, max_definitions=3):
    definitions = []

    if isinstance(html, unicode):
        html = html.encode('utf8')
    parser = etree.HTMLParser()
    tree = etree.parse(StringIO(html), parser)
    page = tree.getroot()
    assert page is not None, "root is None!"
    sel = CSSSelector('ul.std li')

    for li in sel(page):
        if li.text:
            definitions.append(li.text.strip())
        if len(definitions) > max_definitions:
            break

    return definitions


def _get_random_used_user_agent(span=20):
    from random import choice
    user_agents = [x.user_agent for x in
                   Search.objects.all().order_by('-add_date')[:span]]
    return choice(user_agents)



def plural(word):
    if word.endswith('y'):
        return word[:-1] + 'ies'
    elif word[-1] in 'sx' or word[-2:] in ['sh', 'ch']:
        return word + 'es'
    elif word.endswith('an'):
        return word[:-2] + 'en'
    return word + 's'


def _get_variations(word, greedy=False,
                    store_definitions=True,
                    request=None):
    a = _get_variations_wordnet(word, greedy=greedy,
                                store_definitions=store_definitions)

    b = _get_variations_synonym_dot_com(word, greedy=greedy,
                                        store_definitions=store_definitions,
                                        request=request)
    return a + b
    return a


versus_synonym_string = re.compile('(\w+) \(vs\. \w+\)')
def _get_variations_synonym_dot_com(word, greedy=False,
                                    store_definitions=True,
                                    request=None):
    from lxml.html import parse
    from lxml import etree

    from lxml.cssselect import CSSSelector
    assert not word.count(' '), "Word can not have a space in it"

    url = 'http://www.synonym.com/synonyms/%s/' % word
    if request is None:
        page = parse(url).getroot()
    else:
        cache_key = 'syndotcom_download_%s' % url.replace('http://','')
        html = cache.get(cache_key)
        if html is None:
            html = _download_url(url, request.META)
            cache.set(cache_key, html)
        assert len(html) > 1000, "HTML too short %r" % html
        if isinstance(html, unicode):
            html = html.encode('utf8')
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(html), parser)
        page = tree.getroot()
        assert page is not None, "root is None!"

    sel = CSSSelector('span.equals')

    all = set()
    for span in sel(page):
        synonyms = span.text
        for synonym in [x.strip().lower() for x in synonyms.split(',') if x.strip()]:
            if '(' in synonym:
                synonym = versus_synonym_string.sub(r'\1', synonym)
            if ' ' not in synonym:
                all.add(synonym)

            if greedy:
                #all.add(plural(synonym))# unsure this helps much
                for morph in morph_variations(synonym):
                    morphed_back = wordnet.morphy(morph)
                    if morphed_back:
                        if ' ' not in morphed_back:
                            all.add(morphed_back)

    return list(all)

def _download_url(url, request_meta):

    headers = {}
    if request_meta.get('HTTP_USER_AGENT'):
        headers['User-Agent'] = request_meta.get('HTTP_USER_AGENT')
    if request_meta.get('HTTP_ACCEPT_LANGUAGE'):
        headers['Accept-Language'] = request_meta.get('HTTP_ACCEPT_LANGUAGE')
    if request_meta.get('HTTP_ACCEPT'):
        headers['Accept-Encoding'] = request_meta.get('HTTP_ACCEPT')

    req = urllib2.Request(url, None, headers)
    u = urllib2.urlopen(req)
    headers = u.info()
    return u.read()


def _get_variations_wordnet(word, greedy=False,
                            store_definitions=True):
    """return a list of words if possible.
    If greedy, return a
    """
    all = []

    def ok_word(w):
        return not w.count('_') and w != word and not w.count(' ')

    for each in morph_variations(word):
        if each in all:
            # a crap variation
            continue

        # check that each variation is a word
        if not wordnet.morphy(each):
            # then it's probably not a word
            continue
            # then it's a word
        if not ok_word(each):
            # e.g. 'horizontal_surface'
            continue

        all.append(each)
        if not greedy:
            continue

        for synset in wordnet.synsets(each):
            for synonym_synset in synset.hypernyms():
                synonym = synonym_synset.name.split('.')[0]
                if not ok_word(synonym):
                    continue


                for synonym_variation in morph_variations(synonym):
                    if not wordnet.morphy(synonym_variation):
                        # then it's not a word
                        continue

                    if synonym_variation in all:
                        # already seen this variation
                        continue

                    all.append(synonym_variation)

                    synonym_variation_plural = plural(synonym_variation)
                    if synonym_variation_plural and synonym_variation_plural != synonym_variation:
                        if wordnet.morphy(synonym_variation_plural) and ok_word(synonym_variation_plural):
                            all.append(synonym_variation_plural)

    return all


def _find_alternatives(slots, language, notletters=[]):
    length = len(slots)

    if length == 1:
        return Word.objects.filter(length=1, word=slots[0], language=language)

    filter_ = dict(length=length, language=language)
    slots = [x and x.lower() or ' ' for x in slots]
    search = ''.join(slots)
    start = ''
    end = ''
    try:
        start = re.findall('^\w+', search)[0]
        filter_['word__istartswith'] = start
    except IndexError:
        pass

    try:
        end = re.findall('\w+$', search)[0]
        filter_['word__iendswith'] = end
    except IndexError:
        pass


    def filter_match(match):
        if end:
            matchable_string = search[len(start):-len(end)]
            found_string = match.word[len(start):-len(end)]
        else:
            matchable_string = search[len(start):]
            found_string = match.word[len(start):]

        assert len(matchable_string) == len(found_string), \
        "matchable_string=%r, found_string=%r" % (matchable_string, found_string)

        for i, each in enumerate(matchable_string):
            if each != u' ' and each != found_string[i]:
                # can't be match
                return False
        return True

    search_base = Word.objects
    limit = 10000
    # if the filter is really vague and the length is high we're going to get
    # too many objects and we need to cut our losses.
    if filter_['length'] > 5:
        if filter_.get('word__istartswith') and filter_.get('word__iendswith'):
            # It's long but has a startswith and an endswith, increase the limit
            limit = 5000
        elif filter_.get('word__istartswith') or filter_.get('word__iendswith'):
            # we're going to get less than above but still many
            limit = 2500
        else:
            limit = 1000
    # if there's neither a start or a end (e.g. '_E_E_A_') it will get all words
    # that are of that length then end truncate the result set then filter them
    # as a string operation. Then there's a chance it might not ever test word we
    # are looking for.
    if not start and not end:
        # must come up with some other crazy icontains filter
        # Look for the longest lump of letter. For example in '_E_ERA_' 'era' is
        # the longest lump
        #lumps = re.findall('\w+', search)
        lumps = search.split()

        longest = sorted(lumps, lambda x,y: cmp(len(y), len(x)))[0]
        if len(longest) > 1:
            filter_['word__icontains'] = longest
        else:
            for each in uniqify(lumps):
                search_base = search_base.filter(word__icontains=each)

            limit = search_base.filter(**filter_).order_by('word').count()
    elif (start and len(start) <= 2) or (end and len(end) <= 2):
        # If you search for somethin like "___TAM__T"
        # We so far only know it's 9 characters long (french as 21k 9 characters long
        # words).
        # We also have one tiny little 't' at the end but there's still
        # 4086 options
        for lump in re.findall(r'\s(\w+)\s', search):
            filter_['word__icontains'] = lump

    search_qs = search_base.filter(**filter_)
    for notletter in notletters:
        search_qs = search_qs.exclude(word__icontains=notletter)
    all_matches = [x for x in search_qs.order_by('word')[:limit]
                   if filter_match(x)]
    return uniqify(all_matches,
                   lambda x: x.word.lower())


@login_required
def upload_wordlist(request):
    if request.method == "POST":
        file_ = request.FILES['file']
        skip_ownership_s = bool(request.POST.get('skip_ownership_s'))
        titled_is_name = bool(request.POST.get('titled_is_name'))
        language = request.POST.get('language')
        encoding = request.POST.get('encoding', 'utf8')
        assert language, "no language :("
        count = 0

        # save the file to /tmp then reopen it with codecs.open
        # so we can use xreadlines on it
        from tempfile import mkdtemp
        temp_file_path = mkdtemp()+'.txt'
        open(temp_file_path,'w').write(file_.read())
        import codecs
        for line in codecs.open(temp_file_path, 'r', encoding).xreadlines():
            line = unicode(line, encoding).strip()
            print repr(line)
            if line.startswith('#') or not line.strip():
                continue
            if skip_ownership_s and line.strip().endswith("'s"):
                continue

            #line = unicode(line, 'iso-8859-1').strip()

            if len(line) == 1:
                continue

            name = False
            if titled_is_name:
                if line[0].isupper():
                    name = True

            part_of_speech = ''

            count += 1
            if count > 10000000:
                break

            # let's add it!
            _add_word(line, part_of_speech, language, name)

        return HttpResponseRedirect('/upload-wordlist/')

    form = WordlistUploadForm()
    return _render('upload_wordlist.html', locals(), request)


@login_required
def upload_dsso(request):
    if request.method == "POST":
        file_ = request.FILES['file']

        simple_line = re.compile('\d+r\d+<(?P<part>[\w\s]+)>(?P<words>[\w\-:!,\s]+)$', re.U)
        count = 0

        for line in file_.xreadlines():
            if line.startswith('#') or not line.strip():
                continue

            if any_true(line.startswith,
                        ('COMPOUND', 'CUSTOM:', 'DEFINITION', 'BASEWORDS:','STATUS:',
                         'USTOM:')):
                continue

            #if randint(1,5) != 1:
            #    continue

            line = unicode(line, 'iso-8859-1')

            found = simple_line.findall(line)
            if found and len(found[0]) == 2:
                part, words = found[0]
                words = [x.split(',')[0].strip() for x in words.split(':')
                         if x.strip() and x.strip() not in list('!')]
                for word in uniqify(words):
                    _add_word(word, part, 'sv', part=='egennamn')
            else:
                print repr(line)

            count += 1
            if count > 10000*9999:
                break

        return HttpResponseRedirect('/upload-dsso/')

    form = DSSOUploadForm()
    return _render('upload_dsso.html', locals(), request)

def _add_word(word, part_of_speech, language, name):
    #pass
    length = len(word)
    try:
        Word.objects.get(word=word, length=length, language=language)
    except Word.DoesNotExist:
        # add it
        Word.objects.create(word=word, length=length, part_of_speech=part_of_speech,
                            language=language,
                            name=name)


def send_feedback(request):

    if not request.method == "POST":
        return HttpResponseRedirect('/?error=feedback')

    feedbackform = FeedbackForm(data=request.POST)
    if feedbackform.is_valid():
        name = feedbackform.cleaned_data.get('name')
        email = feedbackform.cleaned_data.get('email')
        render_form_ts = feedbackform.cleaned_data.get('render_form_ts')
        render_now_ts = int(time())
        geo = request.META.get('GEO')

        _send_feedback(feedbackform.cleaned_data.get('text'),
                       name=name,
                       email=email,
                       render_form_ts=int(render_form_ts),
                       render_now_ts=render_now_ts,
                       geo=geo)

        response = _render('feedback_sent.html', locals(), request)
        if name is not None:
            if type(name) is unicode:
                name = name.encode('utf8')
            set_cookie(response, 'kl__name', name)
        if email is not None:
            if type(email) is unicode:
                email = email.encode('utf8')
            set_cookie(response, 'kl__email', email)
        return response
    else:
        print feedbackform.errors

    return _render('solve.html', locals(), request)

def _send_feedback(text, name=u'', email=u'', fail_silently=False,
                   geo=None, render_form_ts=None, render_now_ts=None):

    recipient_list = [mail_tuple[1] for mail_tuple in settings.MANAGERS]

    if email and ValidEmailAddress(email):
        from_email = email
    else:
        try:
            from_email = settings.DEFAULT_FROM_EMAIL
        except:
            from_email = 'feedbackform@' + Site.objects.get_current().domain

    message = "Feedback\n========\n"
    if name:
        message += "From: %s\n" % name
    if email:
        message += "Email: %s\n" % email
    if geo:
        message += "GEO: %s\n" % geo
    #if render_form_ts and render_now_ts:
    #    message += "render_form_ts:%s  render_now_ts:%s  diff:%s\n" % \
    #      (render_form_ts, render_now_ts, render_now_ts-render_form_ts)

    message += "\n" + text
    message += '\n\n\n--\nkl'

    send_mail(fail_silently=fail_silently,
              from_email=from_email,
              recipient_list=recipient_list,
              subject=_("Feedback on Crosstips"),
              message=message,
             )

def get_language_options(request, be_clever=True):
    current_language = request.LANGUAGE_CODE
    all_options = ALL_LANGUAGE_OPTIONS

    # if your browser says 'en-GB' then hide the US option and relabel
    # 'English (GB)' as just 'English' so that british and US users don't
    # have to worry about the difference
    #print "GEO", repr(request.META.get('GEO'))
    #http_lang = request.META.get('LANG')
    #if http_lang:
    #    logging.info("LANG=%r" % http_lang)
    #else:
    #    print [k for k in request.META.keys() if k.count('LANG')]
    #    print request.META.get('HTTP_ACCEPT_LANGUAGE')
    #print "LANG=%r" % http_lang


    language_domans = settings.LANGUAGE_DOMAINS

    options = []
    for option in all_options:
        if option['code'].lower() == current_language.lower():
            option['on'] = True
        else:
            option['on'] = False

        # we must create a key called 'href'
        if option['code'].lower() in language_domans:
            option['href'] = 'http://%s' % language_domans[option['code'].lower()]
        else:
            option['href'] = '/change-language/to/%s/' % option['code']

        if be_clever and request.META.get('GEO') == 'GB':
            # ditch the en-US option and change the label
            # from "English (GB)" to "English"
            if option['code'] == 'en-US':
                continue
            elif option['label'] == 'English (GB)':
                option['label'] = 'English'

        options.append(option)

    return options

def change_language(request, language=None):
    if language:
        autosubmit = True
    else:
        autosubmit = False
    next = '/'
    return _render('change_language.html', locals(), request)


from calendar import HTMLCalendar
from collections import defaultdict

# copied from http://journal.redflavor.com/creating-a-flexible-monthly-calendar-in-django
class StatsCalendar(HTMLCalendar):

    def __init__(self, stats):
        super(StatsCalendar, self).__init__()
        self.stats = stats

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if datetime.date.today() == datetime.date(self.year, self.month, day):
                cssclass += ' today'

            if day in self.stats:
                cssclass += ' filled'
                body = self.stats[day]
                return self.day_cell(cssclass, '%d <p class="count">%s</p>' % (day, body))
            return self.day_cell(cssclass, day)
        return self.day_cell('noday', '&nbsp;')

    def formatmonth(self, year, month):
        self.year, self.month = year, month
        return super(StatsCalendar, self).formatmonth(year, month)

    def group_by_day(self, stats):
        field = lambda search: search.add_date.day
        return dict(
            [(day, len(list(items))) for day, items in groupby(stats, field)]
        )

    def day_cell(self, cssclass, body):
        return '<td class="%s">%s</td>' % (cssclass, body)

@cache_page_with_prefix(ONE_HOUR, _less_sensitive_key_prefixer)
def statistics_calendar(request):
    languages = request.GET.getlist('languages')

    month = request.GET.get('month')
    if not month:
        month = datetime.date.today().month
    else:
        month = int(month)

    year = request.GET.get('year')
    if not year:
        year = datetime.date.today().year
    else:
        year = int(year)

    stats = _get_searches_stats(month=month,
                                year=year,
                                languages=languages,
                                calendar_stats=True)

    language_options = get_language_options(request, be_clever=False)
    for each in language_options:
        each['checked'] = each['code'].lower() in [x.lower() for x in languages]
    #language_options.append(dict(code='en', label='English (both)'))
    calendar = StatsCalendar(stats)
    html_calendar = calendar.formatmonth(year, month)
    return _render('statistics_calendar.html', locals(), request)


def _get_searches_stats(month=None, year=None, languages=[],
                        calendar_stats=False,
                        **extra_filter):

    if year:
        year = int(year)
        if year < 2008 or year > 2020:
            raise ValueError("Year out of range month")
    #else:
    #    year = datetime.date.today().year

    if month:
        if not year:
            year = datetime.date.today().year
        month = int(month)
        if month < 1 or month > 12:
            raise ValueError("Invalid month")
    #else:
    #    month = datetime.date.today().month

    searches = Search.objects.all()
    if year:
        searches = searches.filter(add_date__year=year)
    if month:
        searches = searches.filter(add_date__month=month)

    if extra_filter:
        searches = searches.filter(**extra_filter)

    if languages:
        languages = [x.lower() for x in languages]
        if 'en' in languages:
            searches = searches.filter(language__istartswith='en')
            languages.remove('en')
        if languages:
            searches = searches.filter(language__in=languages)

    stats = defaultdict(int)
    for s in searches:
        if calendar_stats:
            key = s.add_date.day
        else:
            key = datetime.date(s.add_date.year,
                                s.add_date.month,
                                s.add_date.day)
            key = int(mktime(key.timetuple())) * 1000

        stats[key] += 1

    if calendar_stats:
        if stats.keys():
            max_day = max(stats.keys())
        else:
            max_day = 1
        for i in range(1, max_day):
            if i not in stats:
                stats[i] = 0

    return dict(stats)

daterange_iso_regex = re.compile('(?P<yy>\d{4})/(?P<mm>\d{2})/(?P<dd>\d{2}) - (?P<yy2>\d{4})/(?P<mm2>\d{2})/(?P<dd2>\d{2})')
daterange_us_regex = re.compile('(?P<mm>\d{2})/(?P<dd>\d{2})/(?P<yy>\d{4}) - (?P<mm2>\d{2})/(?P<dd2>\d{2})/(?P<yy2>\d{4})')


@cache_page_with_prefix(ONE_DAY, _less_sensitive_key_prefixer)
def statistics_graph(request):
    languages = request.GET.getlist('languages')

    date1 = date2 = None
    extra_filter = {}
    if request.GET.get('daterange'):

        daterange = request.GET.get('daterange')
        match = None

        if daterange_iso_regex.findall(daterange):
            match = daterange_iso_regex.match(daterange)

        elif daterange_us_regex.findall(daterange):
            match = daterange_us_regex.match(daterange)

        if match:
            date1 = datetime.date(int(match.group('yy')),
                                  int(match.group('mm')),
                                  int(match.group('dd')))

            date2 = datetime.date(int(match.group('yy2')),
                                  int(match.group('mm2')),
                                  int(match.group('dd2')))


        if date1:
            extra_filter['add_date__gte'] = date1
        if date2:
            extra_filter['add_date__lt'] = date2

    stats = _get_searches_stats(languages=languages,
                                **extra_filter)

    # turn this into a sorted list
    stats = [[k, v] for (k,v) in stats.items()]
    stats.sort()
    stats_json = simplejson.dumps(stats)

    datepicker2_options = {}
    # 'earliestDate':

    datepicker_options = {}
    if request.META.get('GEO') == 'US':
        datepicker2_options['dateFormat'] = 'mm/dd/yy'
    else:
        datepicker_options['firstDay'] = 1
        datepicker2_options['dateFormat'] = 'yy/mm/dd'

    if datepicker_options:
        datepicker2_options['datepickerOptions'] = datepicker_options

    # finally, for the locals() below, change the variable 'datepicker_options'
    # to mean the overall one which embeds the jQuery UI Datepicker options
    datepicker_options = datepicker2_options
    datepicker_options_json = simplejson.dumps(datepicker_options)

    language_options = get_language_options(request, be_clever=False)
    for each in language_options:
        each['checked'] = each['code'].lower() in [x.lower() for x in languages]

    if date1 and date2:
        fmt1 = '%d %b'
        fmt2 = '%d %b %Y'
        if date1.strftime('%Y') == date2.strftime('%Y'):
            if date1.strftime('%b') == date2.strftime('%b'):
                fmt1 = '%d'
        else:
            fmt1 = '%d %b %Y'

        html_title = _(u"Statistics graph between %(date1)s and %(date2)s") %\
                      dict(date1=date1.strftime(fmt1), date2=date2.strftime(fmt2))
    elif date1:
        html_title = _(u"Statistics graph since %(date1)s") % \
                      dict(date1=date1.strftime('%d %b %Y'))
    elif date2:
        html_title = _(u"Statistics graph up until %(date2)s") % \
                      dict(date2=date2.strftime('%d %b %Y'))

    qs = Search.objects.filter(**extra_filter)

    # don't do this on the example searches
    qs = qs.exclude(search_word__in=('c o    rd', 'p t r', 'ko  o d'))

    PIE_WIDTH = 500; PIE_HEIGHT = 170
    BAR_WIDTH = 500; BAR_HEIGHT = 170

    # figure out what the different types of search_type there are
    #print_sql(qs.values('search_type').distinct('search_type'))
    search_types = [x['search_type'] for x
                    in qs\
                      .values('search_type').distinct('search_type')]

    if len(search_types) > 1:
        search_types_pie = get_search_types_pie(qs, search_types,
                                                PIE_WIDTH, PIE_HEIGHT)

    # figure out what languages people use to search
    languages = [x['language'] for x
                    in qs\
                      .values('language').distinct('language')]
    if len(languages) > 1:
        search_languages_pie = get_languages_pie(qs, languages,
                                                 PIE_WIDTH, PIE_HEIGHT)


    #lengths = [x for x in
    lengths = [x['L'] for x in
               qs.extra(select={'L':'length(search_word)'})\
                 .distinct('L').values('L')][1:-1]
    if len(lengths) > 1:
        search_lengths_bar = get_lengths_bar(qs, lengths,
                                             BAR_WIDTH,
                                             BAR_HEIGHT)


    #languages = [(_(u"English"), ('en-us','en-gb')),
    #             (_(u"French"), ('fr',)),
    #             ]
    languages = [(u"English", ('en-us','en-gb')),
                 (u"French", ('fr',)),
                 ]
    definitionlookups_bar = get_definitionlookups_bar(languages,
                                                      BAR_WIDTH,
                                                      100)
    return _render('statistics_graph.html', locals(), request)


def solve_simple(request, record_search=True,
                 template='simple.html',
                 json=False,
                 search_type="simple"):
    if request.GET.get('slots'):

        # By default we are set to record the search in our stats
        # This can be overwritten by a CGI variable called 'r'
        # E.g. r=0 or r=no
        if request.GET.get('r'):
            record_search = niceboolean(request.GET.get('r'))

        form = SimpleSolveForm(request.GET)
        if form.is_valid():

            language = form.cleaned_data.get('language')
            if not language:
                language = request.LANGUAGE_CODE

            slots = form.cleaned_data['slots']
            slots = slots.replace('.', ' ').replace('*', ' ').replace('_',' ')
            slots = list(slots)
            clues = form.cleaned_data.get('clues', [])
            length = len(slots)

            search_results = [] # the final simple list that is sent back

            assert length == len(slots)
            for clue in clues:
                alternatives = _find_alternative_synonyms(clue, slots, language,
                                                        request=request)
                search_results.extend([SearchResult(x, by_clue=clue) for x in alternatives])

            # find some alternatives
            search = ''.join([x and x.lower() or ' ' for x in slots[:length]])
            cache_key = '_find_alternatives_%s_%s' % (search, language)
            cache_key = cache_key.replace(' ','_')
            if re.findall('\s', cache_key):
                raise ValueError("invalid cache_key search=%r, language=%r" % (search, language))

            alternatives = cache.get(cache_key)
            if alternatives is None:
                alternatives = _find_alternatives(slots[:length], language)
                cache.set(cache_key, alternatives, ONE_DAY)

            alternatives_count = len(alternatives)
            alternatives_truncated = False
            if alternatives_count > 100:
                alternatives = alternatives[:100]
                alternatives_truncated = True

            result = dict(length=length,
                        search=search,
                        word_count=alternatives_count,
                        alternatives_truncated=alternatives_truncated,
                        )
            already_found = [x.word for x in search_results]
            search_results.extend([SearchResult(each.word,
                                                definition=each.definition)
                                for each in alternatives
                                if each.word not in already_found])
            match_points = None
            match_points = []
            if search_results:
                first_word = search_results[0].word
                for i, letter in enumerate(first_word):
                    if letter.lower() == search[i]:
                        match_points.append(1)
                    else:
                        match_points.append(0)
                result['match_points'] = match_points

            result['words'] = []
            for search_result in search_results:
                v = dict(word=search_result.word)
                if search_result.definition:
                    v['definition'] = search_result.definition
                if search_result.by_clue:
                    v['by_clue'] = search_result.by_clue
                result['words'].append(v)


            if alternatives_count == 1:
                result['match_text'] = _("1 match found")
            elif alternatives_count:
                if alternatives_truncated:
                    result['match_text'] = _("%(count)s matches found but only showing first 100")\
                    % dict(count=alternatives_count)
                else:
                    result['match_text'] = _("%(count)s matches found") % \
                    dict(count=alternatives_count)
            else:
                result['match_text'] = _("No matches found unfortunately :(")

            found_word = None
            if len(search_results) == 1:
                try:
                    found_word = Word.objects.get(word=search_results[0].word,
                                                language=language)
                except Word.DoesNotExist:
                    # this it was probably not from the database but
                    # from the wordnet stuff
                    found_word = None

            if record_search:
                _record_search(search,
                            user_agent=request.META.get('HTTP_USER_AGENT',''),
                            ip_address=request.META.get('REMOTE_ADDR',''),
                            found_word=found_word,
                            language=language,
                            search_type=search_type)

            request.session['has_searched'] = True

            if json:
                return _render_json(result)

    else:
        language = request.LANGUAGE_CODE
        form = SimpleSolveForm(initial={'language':language})

        show_example_search = not bool(request.session.get('has_searched'))

    #ad_widget_template = 'kwisslewidget.html'
    ad_widget_template = 'minriverteawidget.html'

    return _render(template, locals(), request)




def statistics_uniqueness(request):
    today = datetime.datetime.today()
    since = datetime.datetime(today.year, today.month, 1)

    cache_key = 'statistics_uniqueness_' + since.strftime('%Y%m%d')
    data = cache.get(cache_key)
    if data is None:
        data = _get_statistics_uniquess_numbers(since)
        cache.set(cache_key, data, ONE_DAY)

    return _render('statistics_uniqueness.html', data, request)


def _get_statistics_uniquess_numbers(since):
    hashes = defaultdict(int)

    for search in Search.objects.filter(add_date__gte=since):
        string = search.user_agent + search.ip_address
        hashed = hash(string)
        hashes[hashed] += 1

    no_one_search = len([x for x in hashes.values() if x ==1])
    no_searchers = len(hashes)
    no_searches = sum(hashes.values())

    median, average, std, min_, max_ = stats([float(x) for x in hashes.values()])
    return locals()


MONTH_NAMES = []
for i in range(1, 13):
    d = datetime.date(2009, i, 1)
    MONTH_NAMES.append(d.strftime('%B'))

#@login_required
def searches_summary_lookup_definitions(request, year, month, atleast_count=1):
    """wrapper on searches_summary(lookup_definitions=True)"""
    from django.utils.cache import get_cache_key
    cache_key = get_cache_key(request)
    return searches_summary(request, year, month, atleast_count=atleast_count,
                            lookup_definitions=True)

@cache_page_with_prefix(ONE_DAY, _sensitive_key_prefixer)
def searches_summary(request, year, month, atleast_count=2,
                     lookup_definitions=False):

    first_search_date = Search.objects.all().order_by('add_date')[0].add_date
    last_search_date = Search.objects.all().order_by('-add_date')[0].add_date

    year = int(year)
    try:
        month_nr = [x.lower() for x in MONTH_NAMES].index(month.lower()) + 1
    except ValueError:
        raise Http404("Unrecognized month name")
    # turn that into a date
    since = datetime.date(year, month_nr, 1)

    if (month_nr + 1) > 12:
        since_month_later = datetime.date(year+1, 1, 1)
    else:
        since_month_later = datetime.date(year, month_nr+1, 1)

    since_month_later_datetime = datetime.datetime(since_month_later.year,
                                                   since_month_later.month,
                                                   since_month_later.day)

    if since_month_later_datetime < first_search_date:
        raise Http404("Too far back in time")
    if since_month_later_datetime < last_search_date:
        next_month_link = since_month_later.strftime("/searches/%Y/%B/")

    since_datetime = datetime.datetime(since.year, since.month, since.day)

    if since_datetime > last_search_date:
        raise Http404("Too far into the future")
    elif since_datetime > first_search_date:
        if (month_nr - 1) < 1:
            since_month_earlier = datetime.date(year-1, 12, 1)
        else:
            since_month_earlier = datetime.date(year, month_nr-1, 1)

        previous_month_link = since_month_earlier.strftime("/searches/%Y/%B/")

    base_searches = Search.objects.filter(add_date__gte=since,
                                          add_date__lt=since_month_later)

    found_searches = base_searches.exclude(found_word=None)\
                                  .select_related('found_word')\
                                  .exclude(found_word__word__in=list(SEARCH_SUMMARY_SKIPS))

    found_words = defaultdict(list)
    definitions = {}
    for each in found_searches:
        found_words[each.language].append(each.found_word.word)

        if each.language not in definitions:
            definitions[each.found_word.language] = {}
        if each.found_word.definition:
            definitions[each.found_word.language][each.found_word.word.lower()]\
              = each.found_word.definition.splitlines()


    found_words = dict(found_words)

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


    if lookup_definitions:
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

    # bake the definitions into found_words_repeats
    for lang, words in found_words_repeats.items():
        for i, word in enumerate(words):
            words_dict = dict(word=word)
            if lang in definitions:
                if word in definitions[lang]:
                    words_dict = dict(words_dict, definitions=definitions[lang][word])
            found_words_repeats[lang][i] = words_dict

    all_words_plain = set()
    for records in found_words_repeats.values():
        for record in records:
            all_words_plain.add(record['word'].lower())
    all_words_plain = list(all_words_plain)

    return _render('searches_summary.html', locals(), request)



def get_canonical_url(url):
    scheme, netloc, path, params, query, fragment = urlparse(url)
    if netloc in settings.CANONICAL_DOMAINS:
        return url.replace(netloc,
                           settings.CANONICAL_DOMAINS[netloc])



@cache_page_with_prefix(ONE_HOUR, _sensitive_key_prefixer)
def word_whomp(request, record_search=False):
    if request.GET.get('slots'):

        # By default we are set to record the search in our stats
        # This can be overwritten by a CGI variable called 'r'
        # E.g. r=0 or r=no
        if request.GET.get('r'):
            record_search = niceboolean(request.GET.get('r'))

        form = WordWhompForm(request.GET)
        if form.is_valid():

            language = form.cleaned_data.get('language')
            if not language:
                language = request.LANGUAGE_CODE

            slots = form.cleaned_data['slots']
            slots = slots.replace('.', ' ').replace('*', ' ').replace('_',' ')
            slots = list(slots)
            length = len(slots)

            search_results = [] # the final simple list that is sent back

            assert length == len(slots)

            # find some alternatives
            search = ''.join([x and x.lower() or ' ' for x in slots[:length]])
            cache_key = '_word_whomp_%s_%s' % (search, language)
            cache_key = cache_key.replace(' ','_')

            alternatives = cache.get(cache_key)
            if alternatives is None:
                alternatives = _find_word_whomps(slots[:length], language)
                cache.set(cache_key, alternatives, ONE_DAY)

            alternatives_count = len(alternatives)
            alternatives_truncated = False

            result = dict(length=length,
                        search=search,
                        word_count=alternatives_count,
                        alternatives_truncated=alternatives_truncated,
                        )
            search_results.extend([SearchResult(each.word,
                                                definition=each.definition)
                                for each in alternatives])

            match_points = None
            match_points = []

            result['words'] = []
            for search_result in search_results:
                v = dict(word=search_result.word)
                if search_result.definition:
                    v['definition'] = search_result.definition
                result['words'].append(v)

            result['groups'] = []
            for length in list(set([len(x['word']) for x in result['words']])):
                group = []
                result['groups'].append((length,
                                         [x for x in result['words']
                                          if len(x['word'])==length
                                         ]))
            #for length in (3,4,5,6):


            if alternatives_count == 1:
                result['match_text'] = _("1 match found")
            elif alternatives_count:
                if alternatives_truncated:
                    result['match_text'] = _("%(count)s matches found but only showing first 100")\
                    % dict(count=alternatives_count)
                else:
                    result['match_text'] = _("%(count)s matches found") % \
                    dict(count=alternatives_count)
            else:
                result['match_text'] = _("No matches found unfortunately :(")

            found_word = None
            if len(search_results) == 1:
                try:
                    found_word = Word.objects.get(word=search_results[0].word,
                                                language=language)
                except Word.DoesNotExist:
                    # this it was probably not from the database but
                    # from the wordnet stuff
                    found_word = None

            if record_search:
                _record_search(search,
                            user_agent=request.META.get('HTTP_USER_AGENT',''),
                            ip_address=request.META.get('REMOTE_ADDR',''),
                            found_word=found_word,
                            language=language,
                            search_type="simple")

            request.session['has_searched'] = True


    else:
        language = request.LANGUAGE_CODE
        form = WordWhompForm(initial={'language':language})

        show_example_search = not bool(request.session.get('has_searched'))

    return _render('word-whomp.html', locals(), request)

def is_list_subset(subset, all):
    for each in subset:
        if each in all:
            all.remove(each)
        else:
            return False
    return True

def _find_word_whomps(letters, language, skip_names=True):
    keep = []
    letters = [x.lower() for x in letters]
    for length in (3, 4, 5, 6):
        for word in Word.objects.filter(length=length, language=language):
            # if the word is a name, skip it
            if skip_names and word.word[0].isupper() and word.word[1:].islower():
                continue
            these_letters = list(word.word.lower())

            if is_list_subset(these_letters, letters[:]):
                keep.append(word)

    return keep

@login_required
def add_word(request):
    if request.method == "POST":
        form = AddWordForm(request.POST)
        if form.is_valid():
            word = form.cleaned_data.get('word')
            languages = form.cleaned_data.get('languages')
            languages = [x.lower() for x in languages]
            for language in languages:
                Word.objects.create(word=word, language=language,
                                   )

            return HttpResponseRedirect('/add-word/?done=1&word=%s' % word.encode('utf8'))

    else:
        initial_languages = []
        for code, label in settings.LANGUAGES:
            if code.lower() == request.LANGUAGE_CODE.lower():
                initial_languages.append(code)
        word = request.GET.get('word', u'')
        form = AddWordForm(initial={'languages':initial_languages,
                                    'word': word})

    done = request.GET.get('done', False)

    return _render('add-word.html', locals(), request)


@cache_page_with_prefix(ONE_DAY, _sensitive_key_prefixer)
def crossing_the_world(request):
    now = datetime.datetime.now()
    # 10 min ago
    since = now - datetime.timedelta(minutes=10)

    searches = _get_recent_located_searches(since=since)
    GOOGLEMAPS_API_KEY = settings.GOOGLEMAPS_API_KEY

    return _render('crossing-the-world.html', locals(), request)

def crossing_the_world_json(request):
    how_many = request.GET.get('how_many', 10)
    since = int(request.GET.get('since', time()*1000))
    since = datetime.datetime.fromtimestamp(float(since)/1000)
    languages = request.GET.getlist('languages')

    items = list(_get_recent_located_searches(languages=languages,
                                             since=since,
                                             how_many=int(how_many)))

    data = dict(items=items, count=len(items))
    data['search_rate'] = round(get_searches_rate(past_hours=0.5), 2)

    return _render_json(data)



def _set_text_html(item):
    """set a key called 'text_html' that describes what the search was as a
    html string.
    This is what is shown in the .openInfoWindowHtml() popup window.
    """
    text = ""
    text += "Searched for %s letter word:<br/>" % len(item['search_word'])
    text += "'<code>%s</code>'" % item['search_word'].upper().replace(' ','_')
    if item.get('found_word'):
        text += "<br/>and found '<a href=\"/word/%s/%s/\" target=\"_blank\"><code>%s</code></a>'!" % \
          (item['found_word'], item['language'], item['found_word'].upper())
        if item.get('found_word_definition'):
            def_html = item.get('found_word_definition')
            if len(def_html) > 50:
                def_html = def_html[:50] + \
                  u'<a href="/word/%s/" target="_blank">...</a>' % item['found_word']
            text += '<br/>which means: <small><em>%s</em></small>' % def_html

    item['text_html'] = text

def _set_title_text(item, location):
    """set a key called title which can be put in the <title> tag temporarily
    like when Gmail chat updates the title"""
    if location.get('country_name') and location.get('place_name'):
        item['title'] = _(u"In %(place_name)s, %(country_name)s someone searched "\
                          u"for a %(length)s letter word: '%(search_word)s'") % \
                        dict(place_name=location['place_name'],
                             country_name=location['country_name'],
                             length=len(item['search_word']),
                             search_word=item['search_word'].upper().replace(' ','_'))



def _get_recent_located_searches(languages=None, how_many=10, since=None):
    qs = Search.objects.all()
    if languages:
        qs = qs.filter(language__in=languages)
    if since:
        qs = qs.filter(add_date__gt=since)

    yield_count = 0
    for search in qs.order_by('-add_date'):
        if search.user_agent.count('Googlebot'):
            continue
        else:
            print search.user_agent

        location = ip_to_coordinates(search.ip_address)
        if location:
            if location.get('country_code') == 'XX':
                continue
            if location.get('coordinates'):
                item = dict(location,
                            language=search.language,
                            search_word=search.search_word,
                           )
                if search.found_word:
                    item = dict(item, found_word=search.found_word.word)
                    if search.found_word.definition:
                        item = dict(item, found_word_definition=search.found_word.definition)
                    else:
                        definition = _get_word_definition(search.found_word.word,
                                                          language=search.found_word.language)
                        if not definition:
                            definition = _get_word_definition_scrape(search.found_word.word,
                                                                     language=search.found_word.language)
                        if definition:
                            add_word_definition(search.found_word.word, definition,
                                                search.found_word.language)
                            item = dict(item, found_word_definition=definition)
                _set_text_html(item)
                _set_title_text(item, location)

                yield_count += 1
                if yield_count >= how_many:
                    break

                yield item



def word(request, word_string, language=None):
    word_string = word_string.strip()
    if len(word_string) < 2:
        raise Http404("word too short")

    if not language:
        language = request.LANGUAGE_CODE
    try:
        word = Word.objects.get(language=language.lower(),
                                word=word_string,
                                length=len(word_string))
    except Word.DoesNotExist:
        return _render('word.html', locals(), request)

    statistics = {}
    no_found_word = Search.objects.filter(language=language.lower(),
                                          found_word=word).count()
    statistics['no_found_word'] = no_found_word
    if word.definition:
        definition_splitted = word.definition.splitlines()

    if language.lower() in ('en','en-us','en-gb'):
        synonyms = [x for x in _get_variations_synonym_dot_com(word_string, request=request)
                    if not x.count('(')]
        synonyms.sort()
        synonyms = [dict(word=x, url=u'/word/%s/%s/' % (x, language.lower()))
                    for x in synonyms]


    return _render('word.html', locals(), request)


def solve_iphone(request, record_search=True):
    # almost a wrapper on solve_simple()

    return solve_simple(request,
                        record_search=record_search,
                        template='iphone.html',
                        search_type="iphone")


def quiz_answer(request):
    data = {}
    question = request.POST.get('question', request.GET.get('question'))
    if question:
        question = question.split('=')[0].strip()
        answer = QUIZZES.get(question)
        if answer:
            data['answer'] = answer

    return _render_json(data)


def get_sparklines_json(request):

    data = {}

    today = datetime.datetime.today()
    first_date = datetime.datetime(today.year, today.month, 1)
    data['href'] = '/statistics/graph/?daterange='+\
                            quote(first_date.strftime('%Y/%m/%d')) +\
                            quote(' - ') +\
                            quote(today.strftime('%Y/%m/%d'))

    data['src'] = get_sparklines_cached(150, 100)
    data['alt'] = _("Searches this month")

    return _render_json(data)


def dumb_test_page(request):
    return _render('dumb_test_page.html', locals(), request)

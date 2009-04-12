import datetime
import urllib2
import re
from pprint import pprint
from cStringIO import StringIO
import logging
from time import time, mktime
from random import randint
try:
    import simplejson
except ImportError:
    from django.utils import simplejson

# Create your views here.
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect,  Http404
from django.template import RequestContext
from django.core.cache import cache
from django.utils.translation import ugettext as _
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.conf import settings

from models import Word, Search
from forms import DSSOUploadForm, FeedbackForm, WordlistUploadForm, SimpleSolveForm
from utils import uniqify, any_true, ValidEmailAddress, stats
from morph_en import variations as morph_variations

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
        domain=settings.SESSION_COOKIE_DOMAIN, secure=settings.SESSION_COOKIE_SECURE or None)


ONE_DAY = 60 * 60 * 24 # one day in seconds

class SearchResult(object):
    def __init__(self, word, definition=u'', by_clue=None):
        self.word = word
        self.definition = definition
        self.by_clue = by_clue
        
        
def solve(request, json=False):
    if request.GET.get('l'):
        try:
            length = int(request.GET.get('l'))
        except ValueError:
            return HttpResponseRedirect('/los/?error=length')
        slots = request.GET.getlist('s')
        if not type(slots) is list:
            return HttpResponseRedirect('/los/?error=slots')
        
        if not len(slots) >= length:
            return HttpResponseRedirect('/los/?error=slots&error=length')
        
        clues = request.GET.get('clues', u'')
        clues = [x.strip() for x in clues.split(',') if x.strip()]
        
        language = request.GET.get('lang', request.LANGUAGE_CODE).lower()
        
        search_results = [] # the final simple list that is sent back
        
        for clue in clues:
            alternatives = _find_alternative_synonyms(clue, slots[:length], language, 
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
            result['match_text'] = _("1 found")
        elif alternatives_count:
            if alternatives_truncated:
                result['match_text'] = _("%(count)s found but only showing first 100")\
                  % dict(count=alternatives_count)
            else:
                result['match_text'] = _("%(count)s found") % \
                  dict(count=alternatives_count)
        else:
            result['match_text'] = _("None found unfortunately :(")
            
        found_word = None
        if len(search_results) == 1:
            try:
                found_word = Word.objects.get(word=search_results[0].word, 
                                              language=language)
            except Word.DoesNotExist:
                # this it was probably not from the database but
                # from the wordnet stuff
                found_word = None
        
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
    
    accept_clues = wordnet is not None and \
      request.LANGUAGE_CODE.lower() in ('en', 'en-gb', 'en-us')
    #accept_clues=False# disabled for the time being

    data = locals()

    return _render('solve.html', data, request)

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
    
    Search.objects.create(search_word=search_word,
                          user_agent=user_agent.strip(),
                          ip_address=ip_address.strip(),
                          found_word=found_word,
                          language=language,
                          search_type=search_type,
                          )

def get_search_stats(language, refresh_today_stats=True, use_cache=True):
    """ wrapper on _get_search_stats() that uses a cache instead """
    
    today = datetime.datetime.today()
    today_midnight = datetime.datetime(today.year, today.month,
                                       today.day, 0, 0, 0)
    
    if use_cache:
        cache_key = '_get_search_stats' + language
        if re.findall('\s', cache_key):
            raise ValueError("invalid cache_key language=%r" % language)
        res = cache.get(cache_key)
    else:
        res = None

    if res is None:
        #t0=time()
        res = _get_search_stats(language)
        #print time()-t0, "to generate stats"
        if use_cache:
            seconds_since_midnight = (today - today_midnight).seconds
            cache.set(cache_key, res, seconds_since_midnight)
        
    if refresh_today_stats:
        # exception
        res['no_searches_today'] = Search.objects.filter(add_date__gte=today_midnight,
                                                         language=language
                                                        ).count()
    return res

def _get_search_stats(language):
    
    no_total_words = Word.objects.filter(language=language).count()
        
    today = datetime.datetime.today()
    
    today_midnight = datetime.datetime(today.year, today.month, 
                                       today.day, 0, 0, 0)
    no_searches_today = Search.objects.filter(language=language,
                                              add_date__gte=today_midnight).count()
    
    yesterday_midnight = today_midnight - datetime.timedelta(days=1)
    no_searches_yesterday = Search.objects.filter(
                    language=language,
                    add_date__range=(yesterday_midnight, today_midnight)).count()
    
    # find the first monday
    monday_midnight = today_midnight
    while monday_midnight.strftime('%A') != 'Monday':
        monday_midnight = monday_midnight - datetime.timedelta(days=1)
        
    no_searches_this_week = Search.objects.filter(
                                            language=language,
                                            add_date__gt=monday_midnight).count()

    first_day_month = datetime.datetime(today.year, today.month, 1, 0, 0, 0)
    no_searches_this_month = Search.objects.filter(language=language,
                                           add_date__gte=first_day_month).count()

    first_day_year = datetime.datetime(today.year, 1, 1, 0, 0, 0)
    no_searches_this_year = Search.objects.filter(language=language,
                                           add_date__gte=first_day_year).count()
    
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
                _add_word_definition(s_word, synset.definition, language=language)
            except Word.DoesNotExist:
                pass
        print "s", repr(s_word)
        if s_word not in tested_words and not s_word.count('_'):
            tested_words.append(s_word)
            if test(s_word, synset.pos):
                matched_words.append(s_word)
                
            for variation in morph_variations(s_word):
                if len(variation) == length and variation not in tested_words:
                    tested_words.append(variation)
                    test(variation, None)
        
        for sub_synset in wordnet.synset(synset.name).hypernyms():
            print "\ts", repr(s_word)
            s_word = sub_synset.name.split('.')[0]
            if sub_synset.definition:
                try:
                    _add_word_definition(s_word, sub_synset.definition, language=language)
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


def _find_alternative_synonyms(word, slots, language, request=None):
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
        parser = etree.HTMLParser()
        if isinstance(html, unicode):
            html = html.encode('utf8')
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
    

def _find_alternatives(slots, language):
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
        assert len(matchable_string) == len(found_string)
        for i, each in enumerate(matchable_string):
            if each != u' ' and each != found_string[i]:
                # can't be match
                return False
        return True
    
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

    all_matches = [x for x in Word.objects.filter(**filter_).order_by('word')[:limit]
                   if filter_match(x)]
    return uniqify(all_matches,
                   lambda x: x.word.lower())


def _add_word_definition(word, definition, language=None):
    filter_ = dict(word=word)
    if language:
        filter_ = dict(filter_, language=language)
        
    w = Word.objects.get(**filter_)
    w.definition = definition.strip()
    w.save()

@login_required
def upload_wordlist(request):
    if request.method == "POST":
        file_ = request.FILES['file']
        skip_ownership_s = bool(request.POST.get('skip_ownership_s'))
        titled_is_name = bool(request.POST.get('titled_is_name'))
        language = request.POST.get('language')
        assert language, "no language :("
        count = 0
        for line in file_.xreadlines():
            if line.startswith('#') or not line.strip():
                continue
            if skip_ownership_s and line.strip().endswith("'s"):
                continue
            
            
            line = unicode(line, 'iso-8859-1').strip()
            
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
    print "\t", repr(word), language
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
        geo = request.META.get('GEO')

        _send_feedback(feedbackform.cleaned_data.get('text'),
                       name=name,
                       email=email,
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
    
    return _render('solve.html', locals(), request)
        
def _send_feedback(text, name=u'', email=u'', fail_silently=False,
                   geo=None):
    
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
    all_options = (
        {'code':'sv', 'label':'Svenska', 'domain':'krysstips.se'},
        {'code':'en-US', 'label':'English (US)', 'domain':'en-us.crosstips.org',
         'title':"American English"},
        {'code':'en-GB', 'label':'English (GB)', 'domain':'en-us.crosstips.org',
         'title':"BritishEnglish"},
    )
    
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

def statistics_calendar(request):
    languages = request.GET.getlist('languages')
    
    month = request.GET.get('month')
    if not month:
        month = datetime.date.today().month
        
    year = request.GET.get('year')
    if not year:
        year = datetime.date.today().year
        
    stats = _get_searches_stats(month=month,
                                year=year,
                                languages=languages,
                                calendar_stats=True)
    

    language_options = get_language_options(request, be_clever=False)
    for each in language_options:
        each['checked'] = each['code'].lower() in languages
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
def statistics_graph(request):
    languages = request.GET.getlist('languages')
    
    extra_filter = {}
    if request.GET.get('daterange'):
        
        daterange = request.GET.get('daterange')
        date1 = date2 = None
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
    
    return _render('statistics_graph.html', locals(), request)


def solve_simple(request):
    if request.GET.get('slots'):
        
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
                result['match_text'] = _("1 found")
            elif alternatives_count:
                if alternatives_truncated:
                    result['match_text'] = _("%(count)s found but only showing first 100")\
                    % dict(count=alternatives_count)
                else:
                    result['match_text'] = _("%(count)s found") % \
                    dict(count=alternatives_count)
            else:
                result['match_text'] = _("None found unfortunately :(")
                
            found_word = None
            if len(search_results) == 1:
                try:
                    found_word = Word.objects.get(word=search_results[0].word, 
                                                language=language)
                except Word.DoesNotExist:
                    # this it was probably not from the database but
                    # from the wordnet stuff
                    found_word = None
            
            _record_search(search,
                           user_agent=request.META.get('HTTP_USER_AGENT',''),
                           ip_address=request.META.get('REMOTE_ADDR',''),
                           found_word=found_word,
                           language=language,
                           search_type="simple")
            
            request.session['has_searched'] = True
    
        
    else:
        language = request.LANGUAGE_CODE
        form = SimpleSolveForm(initial={'language':language})
        
        show_example_search = not bool(request.session.get('has_searched'))
        
    return _render('simple.html', locals(), request)
    
    


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
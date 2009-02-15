import datetime
import re
from pprint import pprint
import logging
from time import time
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
from forms import DSSOUploadForm, FeedbackForm, WordlistUploadForm
from utils import uniqify, any_true, ValidEmailAddress

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
        
        language = request.GET.get('lang', request.LANGUAGE_CODE).lower()

        # find some alternatives
        alternatives = _find_alternatives(slots[:length], language=language)
        search = ''.join([x and x.lower() or ' ' for x in slots[:length]]);
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
        words = [each.word for each in alternatives]
        match_points = None
        match_points = []
        if words:
            for i, letter in enumerate(words[0]):
                if letter.lower() == search[i]:
                    match_points.append(1)
                else:
                    match_points.append(0)
            result['match_points'] = match_points
        result['words'] = words
        
        found_word = None
        if len(words) == 1:
            found_word = Word.objects.get(word=words[0], language=language)
        
        _record_search(search,
                       user_agent=request.META.get('HTTP_USER_AGENT',''),
                       ip_address=request.META.get('REMOTE_ADDR',''),
                       found_word=found_word)

        if json:
            return _render_json(result)
        
    else:
        length = '' # default
        
    data = locals()
    

    return _render('solve.html', data, request)

def _record_search(search_word, user_agent=u'', ip_address=u'',
                   found_word=None):
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
                          )

def get_search_stats(language, refresh_today_stats=True):
    """ wrapper on _get_search_stats() that uses a cache instead """
    cache_key = '_get_search_stats' + language
    res = cache.get(cache_key)
    today = datetime.datetime.today()
    today_midnight = datetime.datetime(today.year, today.month,
                                       today.day, 0, 0, 0)
    if res is None:
        #t0=time()
        res = _get_search_stats(language)
        #print time()-t0, "to generate stats"
        seconds_since_midnight = (today - today_midnight).seconds
        
        cache.set(cache_key, res, seconds_since_midnight)
        
    if refresh_today_stats:
        # exception
        
        res['no_searches_today'] = Search.objects.filter(
                                           add_date__gte=today_midnight).count()
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

def _find_alternatives(slots, language):
    length = len(slots)
    
    if length == 1:
        return Word.objects.filter(length=1, word=slots[0], language=language)
    
    #print language, repr(''.join([x==u'' and u'_' or x for x in slots]))
    
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
    
    return [x for x in Word.objects.filter(**filter_).order_by('word')[:limit]
            if filter_match(x)]
    

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
    
    form = FeedbackForm(data=request.POST)
    if form.is_valid():
        name = form.cleaned_data.get('name')
        email = form.cleaned_data.get('email')
        _send_feedback(form.cleaned_data.get('text'),
                       name=name,
                       email=email)
        
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
        
def _send_feedback(text, name=u'', email=u'', fail_silently=False):
    
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
    message += "\n" + text
    message += '\n\n\n--\nkl'
    
    send_mail(fail_silently=fail_silently, 
              from_email=from_email,
              recipient_list=recipient_list,
              subject=_("Feedback on Crosstips"),
              message=message,
             )

def get_language_options(request):
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
    http_lang = request.META.get('LANG')
    if http_lang:
        logging.info("LANG=%r" % http_lang)
    else:
        print [k for k in request.META.keys() if k.count('LANG')]
        print request.META.get('HTTP_ACCEPT_LANGUAGE')
    print "LANG=%r" % http_lang
        
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
            
        options.append(option)
        
    return options
    
def change_language(request, language):
    if language:
        autosubmit = True
    else:
        autosubmit = False
    next = '/'
    return _render('change_language.html', locals(), request)
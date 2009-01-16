import re
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


from models import Word
from forms import DSSOUploadForm
from utils import uniqify, any_true

def _render_json(data):
    return HttpResponse(simplejson.dumps(data),
                        mimetype='application/javascript')

def _render(template, data, request):
    return render_to_response(template, data,
                              context_instance=RequestContext(request))

        
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
        
        # find some alternatives
        alternatives = _find_alternatives(slots[:length])
        search = ''.join([x and x.lower() or ' ' for x in slots[:length]]);
        alternatives_count = len(alternatives)
        alternatives_truncated = False
        if alternatives_count > 100:
            alternatives = alternatives[:100]
            alternatives_truncated = True
        
        if json:
            data = dict(length=length,
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
                data['match_points'] = match_points
            data['words'] = words
                
            return _render_json(data)
        
    else:
        length = '' # default
        
    data = locals()
    
    data.update(_get_search_stats())

    return _render('solve.html', data, request)

def _get_search_stats():
    
    no_total_words = 70140
    no_searches_today = 5
    no_searches_yesterday = 4
    
    no_searches_this_week = 15
    no_searches_this_month = 44
    
    no_searches_this_year = 109
    
    return locals()

def _find_alternatives(slots):
    length = len(slots)
    
    if length == 1:
        return Word.objects.filter(length=1, word=slots[0])
    
    filter_ = dict(length=length)
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
                    _add_word(word, part)
            else:
                print repr(line)
                    
            count += 1
            if count > 10000*9999:
                break
        
        return HttpResponseRedirect('/upload-dsso/')
    
    form = DSSOUploadForm()
    return _render('upload_dsso.html', locals(), request)
        
def _add_word(word, part_of_speech):
    #pass
    print "\t", repr(part_of_speech), repr(word)
    length = len(word)
    try:
        Word.objects.get(word=word, length=length)
    except Word.DoesNotExist:
        # add it
        Word.objects.create(word=word, length=length, part_of_speech=part_of_speech)
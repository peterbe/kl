import re
from random import randint

# Create your views here.
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect,  Http404

from models import Word
from forms import DSSOUploadForm
from utils import uniqify, any_true


def solve(request):
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
        
    else:
        length = '' # default
        
    return render_to_response('solve.html', locals())

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
        
    return [x for x in Word.objects.filter(**filter_).order_by('word')
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
    return render_to_response('upload_dsso.html', locals())
        
def _add_word(word, part_of_speech):
    #pass
    print "\t", repr(part_of_speech), repr(word)
    length = len(word)
    try:
        Word.objects.get(word=word, length=length)
    except Word.DoesNotExist:
        # add it
        Word.objects.create(word=word, length=length, part_of_speech=part_of_speech)
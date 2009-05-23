import re
import time
from django import forms
from django.utils.translation import ugettext as _


class DSSOUploadForm(forms.Form):
    
    file = forms.FileField()

class WordlistUploadForm(forms.Form):
    
    file = forms.FileField()
    language = forms.CharField(max_length=10)
    titled_is_name = forms.BooleanField(required=False, initial=True)
    skip_ownership_s = forms.BooleanField(required=False, initial=True)
    encoding = forms.CharField(max_length=10)
    

    
class FeedbackForm(forms.Form):
    text = forms.CharField()
    name = forms.CharField(max_length=100, required=False)
    email = forms.CharField(max_length=100, required=False)
    url = forms.CharField(max_length=1, required=False)
    your_website_url = forms.CharField(max_length=1, required=False)
    render_form_ts = forms.CharField(max_length=20, required=True)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('url'):
            raise forms.ValidationError("Not empty :(")
        return cleaned_data
    
    def clean_render_form_ts(self):
        v = self.cleaned_data['render_form_ts']
        # the timestamp can't been too old or too recent because then we suspect it's a 
        # bot.
        diff = int(time.time()) - int(v)
        if diff == 0:
            raise forms.ValidationError("Timestamp too short")
        # diff = 60 is 1 minute
        # diff * 60 = 60 is 1 hour
        if diff >  (3600 * 24):
            # form generated too long ago
            raise forms.ValidationError("Timestamp too long")
        return v
    
    def clean_your_website_url(self):
        # this is a honeypot and must be blank 
        if self.cleaned_data['your_website_url']:
            raise forms.ValidationError(u"Please leave this one blank")
        return self.cleaned_data['your_website_url']
    
    def clean_body(self):
        if 'text' in self.cleaned_data and getattr(settings, 'AKISMET_API_KEY', ''):
            from akismet import Akismet
            from django.utils.encoding import smart_str
            akismet_api = Akismet(key=settings.AKISMET_API_KEY,
                                  blog_url='http://%s/' % Site.objects.get_current().domain)
            if akismet_api.verify_key():
                akismet_data = { 'comment_type': 'comment',
                                 'referer': self.request.META.get('HTTP_REFERER', ''),
                                 'user_ip': self.request.META.get('REMOTE_ADDR', ''),
                                 'user_agent': self.request.META.get('HTTP_USER_AGENT', '') }
                if akismet_api.comment_check(smart_str(self.cleaned_data['body']), data=akismet_data, build_data=True):
                    raise forms.ValidationError(u"Akismet thinks this message is spam")
        return self.cleaned_data['body']
    


class SimpleSolveForm(forms.Form):
    slots = forms.CharField(max_length=30,
                            widget=forms.widgets.TextInput(attrs={'size':30}))
    language = forms.CharField(max_length=6, required=False,
                              widget=forms.widgets.HiddenInput())
    
    
    def clean_slots(self):
        slots = self.cleaned_data['slots']
        if re.findall('\d', slots):
            raise forms.ValidationError(_(u"Can not contain numbers"))
        slots = slots.replace('*',' ').replace('.',' ').replace('_', ' ')
        if re.findall('[^\w ]', slots):
            raise forms.ValidationError(_(u"Can only contain alphabetical characters"))
        count_non_blanks = len(slots) - slots.count(' ')
        if not count_non_blanks:
            raise forms.ValidationError(_(u"Must pass at least 1 character"))
        return slots
    
class WordWhompForm(SimpleSolveForm):
    slots = forms.CharField(max_length=6,
                            widget=forms.widgets.TextInput(attrs={'size':8}))
    
    
    def clean_slots(self):
        slots = super(WordWhompForm, self).clean_slots()
        if not len(slots) == 6:
            raise forms.ValidationError(_(u"Must be exactly 6 characters"))
        return slots
    
from django.forms.widgets import SelectMultiple

from django.conf import settings
class AddWordForm(forms.Form):
    word = forms.CharField(max_length=30,
                           widget=forms.widgets.TextInput(attrs={'size':30}))

    languages = forms.MultipleChoiceField(choices=settings.LANGUAGES)
    
    def clean(self):
        from search.models import Word
        cleaned_data = self.cleaned_data
        for language in cleaned_data['languages']:
            try:
                Word.objects.get(word__iexact=cleaned_data['word'], language=language.lower())
                raise forms.ValidationError("Word already exists in %s" % language)
            except Word.DoesNotExist:
                pass # good!
            
        return cleaned_data
        
    
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
                       
    url(r'^upload-dsso/$', upload_dsso),
    url(r'^upload-wordlist/$', upload_wordlist),
    url(r'^change-language/to/(?P<language>[\w\-]+)/$', change_language),
    url(r'^change-language/$', change_language),
    url(r'^los/$', solve),
    url(r'^/?$', solve),
    url(r'^los/json/$', solve, {'json':True}),
    url(r'^feedback/$', send_feedback),
    url(r'^statistics/calendar/$', statistics_calendar),
    url(r'^variationstester/$', variationstester),
                       
)
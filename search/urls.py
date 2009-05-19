from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
                       
    url(r'^upload-dsso/$', upload_dsso),
    url(r'^upload-wordlist/$', upload_wordlist),
    url(r'^change-language/to/(?P<language>[\w\-]+)/$', change_language),
    url(r'^change-language/$', change_language),
    url(r'^los/$', solve),
    url(r'^/?$', solve),
    url(r'^simple/$', solve_simple),
    url(r'^los/json/$', solve, {'json':True}),
    url(r'^feedback/$', send_feedback),
    url(r'^statistics/calendar/$', statistics_calendar),
    url(r'^statistics/graph/$', statistics_graph),
    url(r'^statistics/uniqueness/$', statistics_uniqueness),
    url(r'^variationstester/$', variationstester),
    url(r'^searches/(?P<year>\d{4})/(?P<month>\w+)/$', searches_summary),
    url(r'^searches/(?P<year>\d{4})/(?P<month>\w+)/lookup-definitions/$', 
        searches_summary_lookup_definitions),
    url(r'^word-definition-lookup/$', word_definition_lookup),
    url(r'^word-whomp/$', word_whomp),
    url(r'^add-word/$', add_word),
    
)
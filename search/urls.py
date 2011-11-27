from django.conf.urls.defaults import patterns, url

from views import *

urlpatterns = patterns('',

    url(r'^upload-dsso/$', upload_dsso),
    url(r'^upload-wordlist/$', upload_wordlist),
    url(r'^change-language/to/(?P<language>[\w\-]+)/$', change_language),
    url(r'^change-language/$', change_language),
    url(r'^los/$', solve),
    url(r'^/?$', solve),
    url(r'^simple/$', solve_simple),
    url(r'^iphone/$', solve_iphone),
    url(r'^los/json/$', solve, {'json':True}),
    url(r'^simple/json/$', solve_simple, {'json':True}),
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
    url(r'^crossing-the-world/$', crossing_the_world),
    url(r'^crossing-the-world.json$', crossing_the_world_json),
    url(r'^word/(?P<word_string>\w+)/$', word),
    url(r'^word/(?P<word_string>\w+)/(?P<language>\w+[-\w]+)/$', word),
    url(r'^quiz_answer.json$', quiz_answer),
    url(r'^get_sparklines.json$', get_sparklines_json),

    url(r'^dumb_test_page$', dumb_test_page),
)

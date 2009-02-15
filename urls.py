from django.conf.urls.defaults import *
import django.views.static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from settings import MEDIA_ROOT

urlpatterns = patterns('',
    # Example:
    (r'', include('kl.search.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
                       
    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
                       
    # CSS, Javascript and IMages
    (r'^images/(?P<path>.*)$', django.views.static.serve,
     {'document_root': MEDIA_ROOT + '/images',
       'show_indexes': True}),                       
    (r'^css/(?P<path>.*)$', django.views.static.serve,
      {'document_root': MEDIA_ROOT + '/css',
       'show_indexes': True}),
    (r'^javascript/(?P<path>.*)$', django.views.static.serve,
      {'document_root': MEDIA_ROOT + '/javascript',
       'show_indexes': True}),    
)

from django.conf.urls.defaults import *
import django.views.static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()
from django.conf import settings

#from sitemap import FlatPageSitemap, OtherSitemap, sitemap
from sitemap import FlatPageSitemap, sitemap, CustomSitemap
#from sitemap import CustomSitemap, sitemap

sitemaps = {
    'flatpages': FlatPageSitemap,
    'otherpages': CustomSitemap,
}

urlpatterns = patterns('',
    # Example:
    (r'', include('kl.search.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
                       
    (r'^sitemap.xml$', sitemap,
     {'sitemaps': sitemaps}),
                       

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
                       
    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),

    # CSS, Javascript and IMages
    (r'^sparklines/(?P<path>.*)$', django.views.static.serve,
     {'document_root': settings.MEDIA_ROOT + '/sparklines',
       'show_indexes': settings.DEBUG}),
                       
    # CSS, Javascript and IMages
    (r'^images/(?P<path>.*)$', django.views.static.serve,
     {'document_root': settings.MEDIA_ROOT + '/images',
       'show_indexes': settings.DEBUG}),                       
    (r'^css/(?P<path>.*)$', django.views.static.serve,
      {'document_root': settings.MEDIA_ROOT + '/css',
       'show_indexes': settings.DEBUG}),
    (r'^javascript/(?P<path>.*)$', django.views.static.serve,
      {'document_root': settings.MEDIA_ROOT + '/javascript',
       'show_indexes': settings.DEBUG}),    
)


if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
    )
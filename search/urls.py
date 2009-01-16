from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
                       
    url(r'^upload-dsso/$', upload_dsso),
    url(r'^los/$', solve),
    url(r'^/?$', solve),
    url(r'^los/json/$', solve, {'json':True}),
                       
)
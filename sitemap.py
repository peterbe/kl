from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.contrib.sitemaps import Sitemap as DjangoSitemap
#from django.contrib.sitemaps import FlatPageSitemap


#class FlatPageSitemap(RequestBasedSitemap):
#    pass
    
from django.utils.encoding import smart_str
from django.template import loader
from django.http import HttpResponse, Http404
from django.core.paginator import EmptyPage, PageNotAnInteger

def sitemap(request, sitemaps, section=None):
    maps, urls = [], []
    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps.append(sitemaps[section])
    else:
        maps = sitemaps.values()
    page = request.GET.get("p", 1)
    for site in maps:
        site.request = request
        try:
            if callable(site):
                urls.extend(site().get_urls(page))
            else:
                urls.extend(site.get_urls(page))
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)
    xml = smart_str(loader.render_to_string('sitemap.xml', {'urlset': urls}))
    return HttpResponse(xml, mimetype='application/xml')    

#from django.contrib.sitemaps.views import django_sitemap_view




class Sitemap(DjangoSitemap):

    def get_urls(self, page=1):
        #from django.contrib.sites.models import Site
        #current_site = Site.objects.get_current()
        current_site = RequestSite(self.request)
        urls = []
        for item in self.paginator.page(page).object_list:
            loc = "http://%s%s" % (current_site.domain, self.__get('location', item))
            url_info = {
                'location':   loc,
                'lastmod':    self.__get('lastmod', item, None),
                'changefreq': self.__get('changefreq', item, None),
                'priority':   self.__get('priority', item, None)
            }
            urls.append(url_info)
        return urls


class Page(object):
    
    def __init__(self, location, changefreq=None):
        self.location = location
        self.changefreq = changefreq
    
    def get_absolute_url(self):
        return self.location
    
class CustomSitemap(Sitemap):
    #def location(self, obj):
    #    return obj['location']
    
    def items(self):
        return [
                Page("/",
                     changefreq="daily",
                     ),
                Page("/statistics/calendar/",
                     changefreq="weekly",
                     ),
                
                Page("/statistics/graph/",
                     changefreq="weekly",
                     ),                
                ]


class FlatPageSitemap(Sitemap):
    def items(self):
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.all()

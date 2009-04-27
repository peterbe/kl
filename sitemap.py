import datetime
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

from kl.search.models import Search

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
                'lastmod':    self.__get('lastmod', item, 
                                         getattr(item, 'lastmod', None)),
                'changefreq': self.__get('changefreq', item, 
                                         getattr(item, 'changefreq', None)),
                'priority':   self.__get('priority', item, 
                                         getattr(item, 'priority', None))
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
        all = []
        all += [
                Page("/",
                     changefreq="daily",
                     ),
                Page("/statistics/calendar/",
                     changefreq="weekly",
                     ),
                
                Page("/statistics/graph/",
                     changefreq="weekly",
                     ),
                Page("/statistics/uniqueness/",
                     changefreq="weekly",
                     ),                
                ]
        
        first_search = Search.objects.all().order_by('add_date')[0]
        y = first_search.add_date.year
        m = first_search.add_date.month
        d = 1
            
        last_search = Search.objects.all().order_by('-add_date')[0]
        last_y = last_search.add_date.year
        last_m = last_search.add_date.month
        last_d = 1
        
        while True:
            if m >= last_m and y >= last_y:
                break
            
            m += 1
            if m > 12:
                m = 1
                y += 1
            all.append(Page(datetime.datetime(y, m, 1).strftime('/searches/%Y/%B/'),
                            changefreq="monthly"))
            
        return all


class FlatPageSitemap(Sitemap):
    def items(self):
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.all()

# python
import logging
import os
import datetime
from urllib import urlopen
from random import choice
from string import Template
from cStringIO import StringIO

# django
from django.conf import settings
from django.utils.translation import ugettext as _

# app
from models import Word, IPLookup, Search
from utils import cache as cache_function

def add_word_definition(word, definition, language=None, 
                        clever_english_duplicate=True):
    filter_ = dict(word=word)
    if language:
        language = language.lower()
        filter_ = dict(filter_, language=language)

    try:
        w = Word.objects.get(**filter_)
    except Word.DoesNotExist:
        # slower but necessary
        filter_['word__iexact'] = filter_.pop('word')
        w = Word.objects.get(**filter_)
    w.definition = definition.strip()
    w.save()
    
    if clever_english_duplicate and language and language in ('en-us','en-gb'):
        if language == 'en-us':
            filter_['language'] = 'en-gb'
        else:
            filter_['language'] = 'en-us'
        try:
            w = Word.objects.get(**filter_)
        except Word.DoesNotExist:
            # it simply doesn't exist in the other language
            return
        w.definition = definition.strip()
        w.save()

AMAZON_PRODUCT_LINK_TEMPLATE_UK = Template("""
<iframe
src="http://rcm-uk.amazon.co.uk/e/cm?t=peterbecom-21&o=2&p=8&l=as1&asins=$asins&fc1=$foreground&IS2=1&lt1=_blank&m=amazon&lc1=$linkcolor&bc1=$bordercolor&bg1=$background&f=ifr&nou=1"
style="width:120px;height:240px;" scrolling="no" marginwidth="0"
marginheight="0" frameborder="0"></iframe>
""".strip())

AMAZON_PRODUCT_LINK_TEMPLATE_US = Template("""
<iframe src="http://rcm.amazon.com/e/cm?t=crosstips-20&o=1&p=8&l=as1&asins=$asins&fc1=$foreground&IS2=1&lt1=_blank&m=amazon&lc1=$linkcolor&bc1=$bordercolor&bg1=$background&f=ifr&nou=1" style="width:120px;height:240px;" scrolling="no" marginwidth="0" marginheight="0" frameborder="0"></iframe>
""".strip())

ALL_ASINS_UK = """
0600619729
0007277849
0007277849
0007277849
1402732554
0330464221
0007274645
0486262995
0716022087
0007264518
0713683201
0330488457
0600618587
000726447X
0600619702
0007280866
0007232896
0007198353
0007264488
1402739370
0852651031
0330451863
0330442848
0600618781
033046423X
0769632793
000720874X
0330463993
0140152059
0330489828
0330442813
1598690485
1843544695
0330442821
0330451669
0007210418
0850793173
0600618455
0600618579
0852651023
060061378X
0330320297
0852650582
B000XD9RVM
B00127R8RS
B001LSXPFW
B000W09JL4
B0018BG3G0&
B0002I8VSI
B001UGDM30
B0002A45AY
""".strip().split()

ALL_ASINS_US = """
0877799296
031254636X
1598695363
031236122X
0312316224
0060517573
1593374313
1558507647
0312382790
1402743998
0486294005
0312386257
B001F7AXJ0
B001F7AXJ0
0740770322
1402725914
1603207716
081293122X
1933821027
031230515X
1603207694
0761143866
B001CGMV30
B001CGMV30
B00006IFTO
B0017X1P4E
""".strip().split()


def get_amazon_advert(geo):
    
    if geo in ('GB','IR'):
        asins = choice(ALL_ASINS_UK)
        template = AMAZON_PRODUCT_LINK_TEMPLATE_UK
    elif geo in ('US','CA'):
        asins = choice(ALL_ASINS_US)
        template = AMAZON_PRODUCT_LINK_TEMPLATE_US
    else:
        asins = None

        
    if asins:
        variables = {'foreground':  '000000',
                     'background':  'FFFFFF',
                     'bordercolor': 'FFFFFF',
                     'linkcolor':   '0000FF',
                     
                     'asins': asins,
                    }
        html = template.substitute(variables)
        
        return html

@cache_function(3600) # seconds
def ip_to_coordinates(ip_address):
    """return a dict of information with these possible keys:
    
    * place_name
    * country_name
    * country_code
    * coordinates
    
    """
    
    def decimal2float(x):
        return float(x)
    
    # search for it here first
    try:
        lookup = IPLookup.objects.get(ip=ip_address)
        return dict(place_name=lookup.place_name,
                    country_name=lookup.country_name,
                    country_code=lookup.country_code,
                    coordinates=(decimal2float(lookup.longitude), decimal2float(lookup.latitude)),
                    )
    except IPLookup.DoesNotExist:
        # continue below
        pass
    
    #def _log(m):
    #    open('/tmp/ip_to_coordinates.log','a').write(m)
    #_log("%s: " % ip_address.strip())
    
    ## free one
    #info = __hostip_ip_to_coordinates(ip_address)
    #if info and 'coordinates' in info:
    #    _log("HOSTIP.info!\n")
    #    print "HOSTIP.info!"
    #    return info
    
    info = __geoip_ip_to_coordinates(ip_address)
    if info and 'coordinates' in info:
        save_ip_lookup(ip_address, info)
        return info
    return {}

def __hostip_ip_to_coordinates(ip_address):
    """return a dict of information with these possible keys:
    
    * place_name
    * country_name
    * country_code
    * coordinates
    
    """
    xml = urlopen('http://api.hostip.info/?ip=%s' % ip_address).read()
    
    test_xml="""<HostipLookupResultSet version="1.0.0" xmlns="http://www.hostip.info/api" xmlns:gml="http://www.opengis.net/gml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.hostip.info/api/hostip-1.0.0.xsd">
 <gml:description>This is the Hostip Lookup Service</gml:description>
 <gml:name>hostip</gml:name>
 <gml:boundedBy>
  <gml:Null>inapplicable</gml:Null>
 </gml:boundedBy>
 <gml:featureMember>
  <Hostip>
   <gml:name>Sugar Grove, IL</gml:name>
   <countryName>UNITED STATES</countryName>
   <countryAbbrev>US</countryAbbrev>
   <!-- Co-ordinates are available as lng,lat -->
   <ipLocation>
    <gml:PointProperty>
     <gml:Point srsName="http://www.opengis.net/gml/srs/epsg.xml#4326">
      <gml:coordinates>-88.4588,41.7696</gml:coordinates>
     </gml:Point>
    </gml:PointProperty>
   </ipLocation>
  </Hostip>
 </gml:featureMember>
</HostipLookupResultSet>
    """.strip()
    #'" # jed
    
    if isinstance(xml, unicode):
        xml = xml.encode('utf8')
    
    from lxml import etree
    parser = etree.XMLParser()
    #print xml
    tree = etree.parse(StringIO(xml), parser)
    root = tree.getroot()
    def GML(tag_name):
        return '{http://www.opengis.net/gml}' + tag_name
    def NS(tag_name):
        return '{http://www.hostip.info/api}' + tag_name
    
    info = {}
    
    for item in root.getiterator():
        if item.tag == GML('name'):
            info['place_name'] = item.text
        elif item.tag == NS('countryName'):
            info['country_name'] = item.text.title()
        elif item.tag == NS('countryAbbrev'):
            info['country_code'] = item.text
        elif item.tag == GML('coordinates'):
            info['coordinates'] = [round(float(x), 4) for x in item.text.split(',')]
        #else:
        #    print repr(item.tag)
    
    return info
    
    
def __geoip_ip_to_coordinates(ip_address):
    """return a dict of information with these possible keys:
    
    * place_name
    * country_name
    * country_code
    * coordinates
    
    """
    import GeoIP
    try:
        database_file = settings.GEO_LITE_CITY_DATABASE_FILE
    except AttributeError:
        database_file = os.path.expanduser('~/GeoLiteCity.dat')
        
    if not os.path.isfile(database_file):
        import warnings
        warnings.warn("GeoLiteCity database file %r does not exist" % database_file)
        return {}
    
    gi = GeoIP.open(database_file, GeoIP.GEOIP_STANDARD)
    try:
        data = gi.record_by_addr(ip_address)
    except SystemError:
        logging.error("Unable to lookup %r" % ip_address)
        return {}
    
    def safe_unicodify(str_, encodings=('utf8','latin1')):
        for encoding in encodings:
            try:
                return unicode(str_, encoding)
            except UnicodeDecodeError:
                pass
        raise UnicodeDecodeError('%r is not in %r' % (str_, encodings))
                
    info = {}
    if data.get('country'):
        info['country_name'] = safe_unicodify(data['country'])
    elif data.get('country_name'):
        info['country_name'] = safe_unicodify(data['country_name'])
        
    if data.get('city'):
        info['place_name'] = safe_unicodify(data['city'])
    if 'longitude' in data and 'latitude' in data:
        info['coordinates'] = (data['longitude'], data['latitude'])
    if data.get('country_code'):
        info['country_code'] = data['country_code']
    
    return info
        
        
        
def save_ip_lookup(ip, location_data):
    if isinstance(ip, unicode):
        ip = ip.encode('utf-8')
        
    if not location_data['coordinates']:
        raise ValueError("Must have coordinates")
    
    lookup, created = IPLookup.objects.get_or_create(ip=ip)
        
    if location_data.get('place_name'):
        lookup.place_name = location_data.get('place_name')
    if location_data.get('country_name'):
        lookup.country_name = location_data.get('country_name')
    if location_data.get('country_code'):
        lookup.country_code = location_data.get('country_code')
        
    longitude, latitude = location_data['coordinates']
    lookup.longitude = str(round(longitude, 10))
    lookup.latitude = str(round(latitude, 10))
    
    lookup.save()
    
    
    
@cache_function(60) # 60 seconds = 1 min
def get_searches_rate(languages=None, past_hours=1, formatted=False):
    """return how many searches are done per minute.
    
    If 'formatted', return it as a string with the unit.
    """
    since = datetime.datetime.now() - datetime.timedelta(hours=past_hours)
    qs = Search.objects.filter(add_date__gte=since)
    if languages:
        if isinstance(languages, basestring):
            languages = [languages]
        qs = qs.filter(language__in=list(languages))
        
    no_searches = qs.count()
    minutes = past_hours * 60
    
    rate = float(no_searches) / minutes # searches per minute
    
    if formatted:
        return "%.2f " % rate + _(u"searches/minute")
    else:
        return rate
    


    
    
    
    
    

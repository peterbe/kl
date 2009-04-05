import re

class UserAgent:
    def __init__(self):
        self.vendor = None
        self.model  = None
        self.midp   = None
        self.cldc   = None
        
    def __repr__(self):
        return '{ vendor: ' + repr(self.vendor) + ', model: ' + repr(self.model) + ', midp: ' + repr(self.midp) + ', cldc: ' + repr(self.cldc) + ' } '

_vendorMap = {
    'mot' : 'motorola',
    'sec' : 'samsung',
    'sie' : 'siemens',
    'lge' : 'lg',
    'cdm' : 'audiovox',
    'hci' : 'hyundai',
    'hei' : 'hyundai',
    'telit_mobile_terminals' : 'telit',
    'tsm' : 'vitelcom',
    'hd'  : 'hd', #?
    }

_reStandard = re.compile(r'^(acer|alcatel|audiovox|blackberry|ericsson|lg|motorola|nec|nokia|panasonic|qci|sagem|samsung|sanyo|sendo|sharp|sonyericsson|telit|philips|vitelcom|' + \
                         '|'.join(_vendorMap.keys()) + ')[- /]?([^/\s_]+)')
_reImode = re.compile(r'^(docomo|portalmmm)[/ ]\d+\.\d+[/ ]([a-z]+)([a-z\d]+)')
_reMozilla = re.compile(r'^mozilla/.*(samsung|nokia|sony|symbian os|symbianos|series 60|smartphone|cellphone|mobilephone|windows ce|palmos|palmsource)')
_reOther  = re.compile(r'up\.browser|up\.link|vodafone|netfront|j2me/midp|opera mini|up/4|mmp/')
_reCldc   = re.compile(r'configuration/cldc-(\d\.\d)')
_reMidp   = re.compile(r'profile/midp-(\d\.\d)')

_imodeMap   = {
    'd'  : 'mitsubishi',
    'er' : 'ericsson',
    'f'  : 'fujitsu',
    'ko' : 'kokusai', #Hitachi
    'm'  : 'mitsubishi',
    'p'  : 'panasonic', #Matsushita
    'n'  : 'nec',
    'nm' : 'nokia',
    'r'  : 'japan radio',
    's'  : 'samsung',
    'sh' : 'sharp',
    'so' : 'sony',
    'ts' : 'toshiba',
    }


def _parseCldcMidp(userAgent, outResult):
    cldc = _reCldc.search(userAgent)
    midp = _reMidp.search(userAgent)
    if midp and cldc:
        outResult.midp = midp.group(1)
        outResult.cldc = cldc.group(1)
        return True
    return False

def _parseOther(userAgent, outResult):
    return _reOther.search(userAgent)

def _parseMozilla(userAgent, outResult):
    return _reMozilla.match(userAgent)

def _parseImode(userAgent, outResult):
    mo = _reImode.match(userAgent)
    if mo is None: return False
    groups = mo.groups()
    vendor  = _imodeMap.get(groups[1])
    model   = groups[2]
    outResult.vendor = vendor
    outResult.model  = model
    return True
#return {'vendor':vendor, 'model':model}
    
def _parseStandard(userAgent, outResult):
    mo = _reStandard.match(userAgent)
    if mo is None: return False
    groups = mo.groups()
    vendor  = groups[0]
    model   = groups[1]
    #version = groups[4] if len(groups) > 4 else None
    model = model.rstrip('._')
    
    if vendor == 'cdm':
        model  = 'cdm-' + model
    elif vendor == 'lge':
        model = model.split('-', 1)[0]
    elif vendor == 'tsm':
        model  = 'tsm-' + model
    elif model == 't68_nil': #ericsson
        model = 't68'
    vendor = _vendorMap.get(vendor, vendor)
    outResult.vendor = vendor
    outResult.model  = model
    return True
#return {'vendor':vendor, 'model':model}
    
def parseUserAgent(userAgent):
    userAgent = userAgent.lower()
    result = UserAgent()
    ok1 = _parseCldcMidp(userAgent, result)
    
    ok2 = _parseStandard(userAgent, result) or \
          _parseMozilla(userAgent, result)  or \
          _parseImode(userAgent, result) or \
          _parseOther(userAgent, result)
    
    return result if ok1 or ok2 else None

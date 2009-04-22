import re
import itertools

def niceboolean(value):
    if type(value) is bool:
        return value
    falseness = ('','no','off','false','none','0', 'f')
    return str(value).lower().strip() not in falseness


def uniqify(seq, idfun=None): # Alex Martelli ******* order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        ##if marker in seen: continue
        if seen.has_key(marker): continue
        seen[marker] = 1
        result.append(item)
    return result


def any_true(pred, seq):
    """ http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/212959 """
    return True in itertools.imap(pred,seq)


def _ShouldBeNone(result): return result is not None
def _ShouldNotBeNone(result): return result is None

tests = (
    # Thank you Bruce Eckels for these (some modifications by Peterbe)
  (re.compile("^[0-9a-zA-Z\.\'\+\-\_]+\@[0-9a-zA-Z\.\-\_]+$"),
   _ShouldNotBeNone, "Failed a"),
  (re.compile("^[^0-9a-zA-Z]|[^0-9a-zA-Z]$"),
   _ShouldBeNone, "Failed b"),
  (re.compile("([0-9a-zA-Z\_]{1})\@."),
   _ShouldNotBeNone, "Failed c"),
  (re.compile(".\@([0-9a-zA-Z]{1})"),
   _ShouldNotBeNone, "Failed d"),
  (re.compile(".\.\-.|.\-\..|.\.\..|.\-\-."),
   _ShouldBeNone, "Failed e"),
  (re.compile(".\.\_.|.\-\_.|.\_\..|.\_\-.|.\_\_."),
   _ShouldBeNone, "Failed f"),
  (re.compile(".\.([a-zA-Z]{2,3})$|.\.([a-zA-Z]{2,4})$"),
   _ShouldNotBeNone, "Failed g"),
  # no underscore just left of @ sign or _ after the @
  (re.compile("\_@|@[a-zA-Z0-9\-\.]*\_"),
   _ShouldBeNone, "Failed h"),
)
def ValidEmailAddress(address, debug=None):
    for test in tests:
        if test[1](test[0].search(address)):
            if debug: return test[2]
            return 0
    return 1


def stats(r):
    #returns the median, average, standard deviation, min and max of a sequence
    tot = sum(r)
    avg = tot/len(r)
    sdsq = sum([(i-avg)**2 for i in r])
    s = list(r)
    s.sort()
    return s[len(s)//2], avg, (sdsq/(len(r)-1 or 1))**.5, min(r), max(r)

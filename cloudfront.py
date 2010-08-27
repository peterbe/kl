import re
import os
import boto

from django.conf import settings

_cf_connection = None
_cf_distribution = None

def _upload_to_cloudfront(filepath):
    global _cf_connection
    global _cf_distribution
    
    if _cf_connection is None:
        _cf_connection = boto.connect_cloudfront(settings.AWS_ACCESS_KEY, 
                                                 settings.AWS_ACCESS_SECRET)
                                                         
    if _cf_distribution is None:
        _cf_distribution = _cf_connection.create_distribution(
            origin='%s.s3.amazonaws.com' % settings.AWS_STORAGE_BUCKET_NAME,
            enabled=True,
            comment=settings.AWS_CLOUDFRONT_DISTRIBUTION_COMMENT)
                              
    
    # now we can delete any old versions of the same file that have the 
    # same name but a different timestamp
    basename = os.path.basename(filepath)
    object_regex = re.compile('%s\.(\d+)\.%s' % \
        (re.escape('.'.join(basename.split('.')[:-2])),
         re.escape(basename.split('.')[-1])))
    for obj in _cf_distribution.get_objects():
        match = object_regex.findall(obj.name)
        if match:
            old_timestamp = int(match[0])
            new_timestamp = int(object_regex.findall(basename)[0])
            if new_timestamp == old_timestamp:
                # an exact copy already exists
                return obj.url()
            elif new_timestamp > old_timestamp:
                # we've come across the same file but with an older timestamp
                #print "DELETE!", obj_.name
                obj.delete()
                break
    
    # Still here? That means that the file wasn't already in the distribution
    
    fp = open(filepath)
    
    # Because the name will always contain a timestamp we set faaar future 
    # caching headers. Doesn't matter exactly as long as it's really far future.
    headers = {'Cache-Control':'max-age=315360000, public',
               'Expires': 'Thu, 31 Dec 2037 23:55:55 GMT',
               }
               
    #print "\t\t\tAWS upload(%s)" % basename
    obj = _cf_distribution.add_object(basename, fp, headers=headers)
    return obj.url()


from time import time

class SlowMap(object):
    """
    >>> slow_map = SlowMap(60)
    >>> slow_map[key] = value
    >>> print slow_map.get(key)
    None

    Then 60 seconds goes past:
    >>> slow_map.get(key)
    value

    """
    def __init__(self, timeout_seconds):
        self.timeout = timeout_seconds

        self.guard = dict()
        self.data = dict()

    def get(self, key, default=None):
        value = self.data.get(key)
        if value is not None:
            return value
        
        if key not in self.guard:
            return default
        
        value, expires = self.guard.get(key)
  
        if expires < time():
            # good to release
            self.data[key] = value
            del self.guard[key]
            return value
        else:
            # held back
            return default

    def __setitem__(self, key, value):
        self.guard[key] = (value, time() + self.timeout)
        
# The estimated time it takes AWS CloudFront to create the domain name is
# 1 hour.
DISTRIBUTION_WAIT_TIME = 60 * 60
_conversion_map = SlowMap(DISTRIBUTION_WAIT_TIME)

def file_proxy(uri, new=False, filepath=None, changed=False, **kwargs):
    if filepath and (new or changed):
        if filepath.lower().split('.')[-1] in ('jpg','gif','png'):
            #print "UPLOAD TO CLOUDFRONT", filepath
            _conversion_map[uri] = _upload_to_cloudfront(filepath)
    return _conversion_map.get(uri, uri)

if __name__ == '__main__':
    import sys
    try:
        filepath = sys.argv[1]
        assert os.path.isfile(filepath)
    except (AssertionError, IndexError):
        print "python %s /path/to/a/file" % __file__
        sys.exit(1)
        
    from django.core.management import setup_environ
    import cloudfront_static_settings
    setup_environ(cloudfront_static_settings)

    print _upload_to_cloudfront(filepath)
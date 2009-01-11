# python
import os
import stat
from slimmer import css_slimmer, guessSyntax, html_slimmer, js_slimmer
from pprint import pprint

# django 
from django import template

class SlimContentNode(template.Node):
    def __init__(self, nodelist, format=None):
        self.nodelist = nodelist
        self.format = format
    def render(self, context):
        code = self.nodelist.render(context)
        if self.format == 'css':
            return css_slimmer(code)
        elif self.format in ('js', 'javascript'):
            return js_slimmer(code)
        elif self.format == 'html':
            return html_slimmer(code)
        else:
            format = guessSyntax(code)
            if format:
                self.format = format
                return self.render(context)
            
        return code

    
register = template.Library()
@register.tag(name='slimcontent')
def do_slimcontent(parser, token):
    nodelist = parser.parse(('endslimcontent',))
    parser.delete_first_token()
    
    _split = token.split_contents()
    format = ''
    if len(_split) > 1:
        tag_name, format = _split
        if not (format[0] == format[-1] and format[0] in ('"', "'")):
            raise template.TemplateSyntaxError, \
                          "%r tag's argument should be in quotes" % tag_name
                          
    return SlimContentNode(nodelist, format[1:-1])


@register.tag(name='slimfile')
def slimfile_node(parser, token):
    _split = token.split_contents()
    tag_name = _split[0]
    options = _split[1:]
    try:
        filename = options[0]
        if not (filename[0] == filename[-1] and filename[0] in ('"', "'")):
            raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name
        filename = filename[1:-1]
    except IndexError:
        raise template.TemplateSyntaxError("Filename not specified")
    
    return SlimFileNode(filename)

class SlimFileNode(template.Node):
    def __init__(self, filename):
        self.filename = filename
    def render(self, context):
        return _slimfile(self.filename)

    
_FILE_MAP = {}

def _slimfile(filename):
    from time import time
    t0=time()
    r = _slimfile_timed(filename)
    t1=time()
    print (t1-t0), filename
    return r
        
        
def _slimfile_timed(filename):
    
    from settings import MEDIA_ROOT, DEBUG
    try:
        from settings import DJANGO_SLIMMER
        if not DJANGO_SLIMMER:
            return filename
    except ImportError:
        pass
    
    
    #pprint(_FILE_MAP)
    if not _FILE_MAP:
        print "\n\t_FILE_MAP empty!!\n"
    new_filename, m_time = _FILE_MAP.get(filename, (None, None))
    
    # we might already have done a conversion but the question is
    # if the javascript or css file has changed. This we only want
    # to bother with when in DEBUG mode because it adds one more 
    # unnecessary operation.
    if new_filename:
        if DEBUG:
            # need to check if the original has changed
            old_new_filename = new_filename
            new_filename = None
        else:
            # This is really fast and only happens when NOT in DEBUG mode
            # since it doesn't do any comparison 
            return new_filename
    else:
        # This is important so that we can know that there wasn't an 
        # old file which will help us know we don't need to delete 
        # the old one
        old_new_filename = None

    if not new_filename:
        
        filepath = _filename2filepath(filename, MEDIA_ROOT)
        if not os.path.isfile(filepath):
            import warnings; warnings.warn("Can't file %s" % filepath)
            return filename
        
        new_m_time = os.stat(filepath)[stat.ST_MTIME]
        if m_time:
            # we had the filename in the map
            if m_time != new_m_time:
                # ...but it has changed!
                m_time = None
            else:
                # ...and it hasn't changed!
                return old_new_filename
            
        if not m_time:
            # We did not have the filename in the map OR it has changed
            apart = os.path.splitext(filename)
            new_filename = ''.join([apart[0], 
                                '.%s' % new_m_time,
                                apart[1]])
            
            _FILE_MAP[filename] = (new_filename, new_m_time)
            if old_new_filename:
                os.remove(_filename2filepath(old_new_filename, MEDIA_ROOT))

    new_filepath = _filename2filepath(new_filename, MEDIA_ROOT)
        
    if new_filename.endswith('.js'):
        content = js_slimmer(open(filepath).read())
    elif new_filename.endswith('.css'):
        content = css_slimmer(open(filepath).read())
    open(new_filepath, 'w').write(content)
                                    
    return new_filename

def _filename2filepath(filename, MEDIA_ROOT):
    # The reason we're doing this is because the templates will 
    # look something like this:
    # src="{{ MEDIA_URL }}/css/foo.css"
    # and if (and often happens in dev mode) MEDIA_URL will 
    # just be ''
    
    if filename.startswith('/'):
        return os.path.join(MEDIA_ROOT, filename[1:])
    else:
        return os.path.join(MEDIA_ROOT, filename)
    
    
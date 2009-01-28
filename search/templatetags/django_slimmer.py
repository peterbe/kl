# python
import os
import sys
import stat
from slimmer import css_slimmer, guessSyntax, html_slimmer, js_slimmer
from pprint import pprint

if sys.platform == "win32":
    _CAN_SYMLINK = False
else:
    _CAN_SYMLINK = True
    import subprocess
    
def _symlink(from_, to):
    cmd = 'ln -s "%s" "%s"' % (from_, to)
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    

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
    
    return StaticFileNode(filename, slimmer_if_possible=True)

@register.tag(name='staticfile')
def staticfile_node(parser, token):
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
    
    return StaticFileNode(filename, symlink_if_possible=_CAN_SYMLINK)

class StaticFileNode(template.Node):
    
    def __init__(self, filename, slimmer_if_possible=False, 
                 symlink_if_possible=False):
        self.filename = filename
        self.slimmer_if_possible = slimmer_if_possible
        self.symlink_if_possible = symlink_if_possible
        
    def render(self, context):
        return _static_file(self.filename,
                            slimmer_if_possible=self.slimmer_if_possible,
                            symlink_if_possible=self.symlink_if_possible)
    
    
_FILE_MAP = {}

def _static_file(filename, 
                       slimmer_if_possible=False,
                       symlink_if_possible=False):
    print filename
    print "symlink_if_possible", symlink_if_possible
    print
    from time import time
    t0=time()
    r = _static_file_timed(filename, slimmer_if_possible=slimmer_if_possible,
                          symlink_if_possible=symlink_if_possible)
    t1=time()
    #print (t1-t0), filename
    return r
        
        
def _static_file_timed(filename, 
                       slimmer_if_possible=False, 
                       symlink_if_possible=False):
    
    from settings import MEDIA_ROOT, DEBUG
    try:
        from settings import DJANGO_SLIMMER
        if not DJANGO_SLIMMER:
            return filename
    except ImportError:
        return filename
    
    try:
        from settings import DJANGO_SLIMMER_SAVE_PREFIX
    except ImportError:
        DJANGO_SLIMMER_SAVE_PREFIX = ''
        
    try:
        from settings import DJANGO_SLIMMER_NAME_PREFIX
    except ImportError:
        DJANGO_SLIMMER_NAME_PREFIX = ''
        
    PREFIX = DJANGO_SLIMMER_SAVE_PREFIX and DJANGO_SLIMMER_SAVE_PREFIX or MEDIA_ROOT

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
            import warnings; warnings.warn("Can't find file %s" % filepath)
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
            
            #new_filename = DJANGO_SLIMMER_NAME_PREFIX + new_filename
            
            _FILE_MAP[filename] = (DJANGO_SLIMMER_NAME_PREFIX + new_filename, new_m_time)
            if old_new_filename:
                os.remove(_filename2filepath(old_new_filename.replace(DJANGO_SLIMMER_NAME_PREFIX, ''),
                                             PREFIX))

    new_filepath = _filename2filepath(new_filename, PREFIX)
        
    content = open(filepath).read()
    if slimmer_if_possible:
        if new_filename.endswith('.js'):
            content = js_slimmer(content)
        elif new_filename.endswith('.css'):
            content = css_slimmer(content)
    elif symlink_if_possible:
        _symlink(filepath, new_filepath)
    print "** STORING:", new_filepath
    open(new_filepath, 'w').write(content)
                            
    return DJANGO_SLIMMER_NAME_PREFIX + new_filename


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)
            
def _filename2filepath(filename, MEDIA_ROOT):
    # The reason we're doing this is because the templates will 
    # look something like this:
    # src="{{ MEDIA_URL }}/css/foo.css"
    # and if (and often happens in dev mode) MEDIA_URL will 
    # just be ''
    
    if filename.startswith('/'):
        path = os.path.join(MEDIA_ROOT, filename[1:])
    else:
        path = os.path.join(MEDIA_ROOT, filename)
        
    if not os.path.isdir(os.path.dirname(path)):
        _mkdir(os.path.dirname(path))
        
    return path
    
    
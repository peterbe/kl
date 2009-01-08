from django import template

register = template.Library()

@register.filter()
def highlight_suggestion(word, search):
    assert len(word) == len(search)
    out = []
    for i, letter in enumerate(word):
        if letter.lower() == search[i]:
            out.append(u'<span class="match letter">%s</span>' % letter)
        else:
            out.append(u'<span class="letter">%s</span>' % letter)
    
    return ''.join(out)
    
    
                                        
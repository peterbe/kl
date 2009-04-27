from django import template

from kl.search.views import ALL_LANGUAGE_OPTIONS
register = template.Library()

@register.filter()
def language_switch_href(language_code):
    return 'javascript:this.form.submit();return false'

@register.filter()
def show_language_verbose(language_code):
    for option in ALL_LANGUAGE_OPTIONS:
        if option['code'].lower() == language_code.lower():
            return option['label']
    
    return language_code.title()
from django import template

register = template.Library()

@register.filter()
def language_switch_href(language_code):
    return 'javascript:this.form.submit();return false'
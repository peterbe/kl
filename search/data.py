from random import choice
from string import Template

AMAZON_PRODUCT_LINK_TEMPLATE = Template("""
<iframe
src="http://rcm-uk.amazon.co.uk/e/cm?t=peterbecom-21&o=2&p=8&l=as1&asins=$asins&fc1=$foreground&IS2=1&lt1=_blank&m=amazon&lc1=0000FF&bc1=$bordercolor&bg1=$background&f=ifr&nou=1"
style="width:120px;height:240px;" scrolling="no" marginwidth="0"
marginheight="0" frameborder="0"></iframe>
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
""".split()


def get_amazon_advert(language):
    
    asins = None
    if language == 'en-gb':
        asins = choice(ALL_ASINS_UK)
    if asins:
        variables = {'foreground': '000000',
                    'background': 'FFFFFF',
                    'bordercolor': 'FFFFFF',
                    'asins': asins,
                    }
        html = AMAZON_PRODUCT_LINK_TEMPLATE.substitute(variables)
        
        return html
    
    
    
    
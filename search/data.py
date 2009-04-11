from random import choice
from string import Template

AMAZON_PRODUCT_LINK_TEMPLATE_UK = Template("""
<iframe
src="http://rcm-uk.amazon.co.uk/e/cm?t=peterbecom-21&o=2&p=8&l=as1&asins=$asins&fc1=$foreground&IS2=1&lt1=_blank&m=amazon&lc1=0000FF&bc1=$bordercolor&bg1=$background&f=ifr&nou=1"
style="width:120px;height:240px;" scrolling="no" marginwidth="0"
marginheight="0" frameborder="0"></iframe>
""".strip())

AMAZON_PRODUCT_LINK_TEMPLATE_US = Template("""
<iframe src="http://rcm.amazon.com/e/cm?t=crosstips-20&o=1&p=8&l=as1&asins$asins&fc1=$foreground&IS2=1&lt1=_blank&m=amazon&lc1=0000FF&bc1=$bordercolor&bg1=$background&f=ifr&nou=1"
style="width:120px;height:240px;" scrolling="no" marginwidth="0" marginheight="0" frameborder="0"></iframe>
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
    
    asins = None
    if geo == ('GB','IR'):
        asins = choice(ALL_ASINS_UK)
        template = AMAZON_PRODUCT_LINK_TEMPLATE_UK
    elif geo in ('US','CA'):
        asins = choice(ALL_ASINS_US)
        template = AMAZON_PRODUCT_LINK_TEMPLATE_US
        
    if asins:
        variables = {'foreground': '000000',
                     'background': 'FFFFFF',
                     'bordercolor': 'FFFFFF',
                     'asins': asins,
                    }
        html = templates.substitute(variables)
        
        return html
    
    
    
    
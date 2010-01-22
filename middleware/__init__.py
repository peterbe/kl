
class MobileSecondMiddleware(object):
    """The sole purpose of this middleware is that we can override the
    request.mobile.
    At the moment all it does is looking out for the debugging magic trick of
    listening for ?SIMULATE_MOBILE
    
    Perhaps later we might have a cookie override here.

    It's important that this is set up in MIDDLEWARE_CLASSES *AFTER*
    minidetector.Middleware as this one is supposed to override.
    """

                               
    @staticmethod
    def process_request(request):
        request.iphone = False
        if request.mobile:
            # make it even more clever by checking if it's an iphone
            http_user_agent = request.META.get('HTTP_USER_AGENT', '')
            if 'iPhone' in http_user_agent and 'AppleWebKit' in http_user_agent:
                request.iphone = True
            
        if 'SIMULATE_MOBILE' in request.GET or 'SIMULATE_MOBILE' in request.POST:
            request.mobile = True
        elif 'SIMULATE_IPHONE' in request.GET or 'SIMULATE_IPHONE' in request.POST:
            request.mobile = True
            request.iphone = True
        return None

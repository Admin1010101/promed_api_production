# core/middleware.py (or create a new middleware.py in your project root)

class StripPortFromHostMiddleware:
    """
    Middleware to strip port numbers from the HTTP_HOST header.
    This fixes Azure health check issues where the host includes :8000
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the host header
        host = request.META.get('HTTP_HOST', '')
        
        # Strip port if present (e.g., "169.254.129.3:8000" -> "169.254.129.3")
        if ':' in host:
            request.META['HTTP_HOST'] = host.split(':')[0]
        
        response = self.get_response(request)
        return response
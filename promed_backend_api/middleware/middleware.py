# promed_backend_api/middleware.py
import json
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only log token endpoint requests
        if '/provider/token/' in request.path:
            logger.info("=" * 50)
            logger.info(f"REQUEST TO: {request.path}")
            logger.info(f"METHOD: {request.method}")
            logger.info(f"HEADERS: {dict(request.headers)}")
            logger.info(f"Content-Type: {request.content_type}")
            
            if request.method == 'POST':
                try:
                    # Read the body without consuming it
                    body = request.body
                    logger.info(f"RAW BODY: {body}")
                    if body:
                        decoded = body.decode('utf-8')
                        logger.info(f"DECODED BODY: {decoded}")
                        try:
                            parsed = json.loads(decoded)
                            logger.info(f"PARSED JSON: {parsed}")
                        except:
                            logger.info("Body is not valid JSON")
                except Exception as e:
                    logger.error(f"Error reading body: {e}")
            
            logger.info("=" * 50)
        
        response = self.get_response(request)
        
        # Log response for token endpoint
        if '/provider/token/' in request.path:
            logger.info(f"RESPONSE STATUS: {response.status_code}")
            if hasattr(response, 'data'):
                logger.info(f"RESPONSE DATA: {response.data}")
        
        return response
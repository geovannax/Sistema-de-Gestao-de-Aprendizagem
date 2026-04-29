

class CookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # adicionar cookies
        cookies_to_set = getattr(request, '_set_cookies', {})
        for key, value in cookies_to_set.items():
            response.set_cookie(
                key,
                value,
                max_age=365 * 24 * 3600,
                httponly=True,
                samesite='Lax'
            )

        # remover cookies
        cookies_to_delete = getattr(request, '_delete_cookies', [])
        for key in cookies_to_delete:
            response.delete_cookie(key)

        return response
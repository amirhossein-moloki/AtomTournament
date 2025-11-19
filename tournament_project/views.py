from django.shortcuts import redirect

def page_not_found_view(request, exception):
    """
    Redirects all 404 errors to the specified static 404 page.
    """
    return redirect("https://atom-game.ir/404.html")

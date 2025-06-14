from django.shortcuts import render
from django.http import Http404

def login_view(request):
    post_url = request.GET.get('post', '/')
    magic_value = request.GET.get('magic', '')
    if not post_url or not magic_value:
        raise Http404("Page not found")
        
    return render(request, 'login.html', {'post_url': post_url, 'magic_value': magic_value})

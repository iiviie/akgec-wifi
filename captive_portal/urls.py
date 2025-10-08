from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='index'),
    path('forgot-password/', views.password_reset_request, name='password_reset_request'),
    path('reset-password/<uuid:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('test-login/', views.test_login_view, name='test_login'),
]
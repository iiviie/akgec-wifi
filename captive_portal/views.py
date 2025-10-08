from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import StudentModel, PasswordResetToken
import hashlib

def login_view(request):
    post_url = request.GET.get('post', '/')
    magic_value = request.GET.get('magic', '')
    if not post_url or not magic_value:
        raise Http404("Page not found")
        
    return render(request, 'login.html', {'post_url': post_url, 'magic_value': magic_value})


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Email address is required.')
            return render(request, 'password_reset_form.html')
        
        try:
            student = StudentModel.objects.get(email=email)
            
            # Invalidate any existing tokens for this student
            PasswordResetToken.objects.filter(student=student, used=False).update(used=True)
            
            # Create new reset token
            reset_token = PasswordResetToken.objects.create(student=student)
            
            # Send reset email
            reset_url = f"{settings.SITE_URL}/reset-password/{reset_token.token}/"
            
            subject = 'AKGEC WiFi - Password Reset Request'
            html_message = render_to_string('password_reset_email.html', {
                'student': student,
                'reset_url': reset_url,
                'site_name': 'AKGEC WiFi Portal'
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False,
            )
            
            messages.success(request, 'Password reset email has been sent to your email address.')
            return render(request, 'password_reset_form.html', {'email_sent': True})
            
        except StudentModel.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, 'If an account with that email exists, a password reset email has been sent.')
            return render(request, 'password_reset_form.html', {'email_sent': True})
        except Exception as e:
            messages.error(request, 'An error occurred while sending the email. Please try again.')
            return render(request, 'password_reset_form.html')
    
    return render(request, 'password_reset_form.html')


def password_reset_confirm(request, token):
    reset_token = get_object_or_404(PasswordResetToken, token=token)
    
    if not reset_token.is_valid():
        messages.error(request, 'This password reset link has expired or is invalid.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password or not confirm_password:
            messages.error(request, 'Both password fields are required.')
            return render(request, 'password_reset_confirm.html', {'token': token})
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'password_reset_confirm.html', {'token': token})
        
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'password_reset_confirm.html', {'token': token})
        
        # Update password (let model handle hashing)
        student = reset_token.student
        student.password = new_password
        student.save()
        
        # Mark token as used
        reset_token.used = True
        reset_token.save()
        
        messages.success(request, 'Your password has been reset successfully. You can now login with your new password.')
        return redirect('password_reset_request')
    
    return render(request, 'password_reset_confirm.html', {'token': token})


def test_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Both email and password are required.')
            return render(request, 'test_login.html')
        
        try:
            student = StudentModel.objects.get(email=email)
            password_hash = hashlib.md5(password.encode()).hexdigest()
            
            # Debug information
            print(f"DEBUG - Email: {email}")
            print(f"DEBUG - Entered password: {password}")
            print(f"DEBUG - Generated hash: {password_hash}")
            print(f"DEBUG - Stored hash: {student.password}")
            print(f"DEBUG - Hashes match: {student.password == password_hash}")
            
            if student.password == password_hash:
                messages.success(request, f'Login successful! Welcome {student.username}.')
            else:
                messages.error(request, f'Invalid password. Debug: entered="{password}" hash="{password_hash}" stored="{student.password}"')
        except StudentModel.DoesNotExist:
            messages.error(request, 'No account found with this email.')
    
    return render(request, 'test_login.html')

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.template.response import TemplateResponse


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24)  # Cache for 24 hours
def about_page(request):
    """About page with company information."""
    context = {
        'page_title': 'About Ubongo IQ',
        'page_description': 'Learn about Ubongo IQ and our mission to share knowledge and insights.',
    }
    return TemplateResponse(request, 'pages/about.html', context)


@require_http_methods(["GET", "POST"])
def contact_page(request):
    """Contact page with form."""
    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        if all([name, email, subject, message]):
            # In a real application, you would send the email or save to database
            # For now, we'll just show a success message
            context = {
                'page_title': 'Contact Us',
                'page_description': 'Get in touch with us.',
                'success_message': 'Thank you for your message! We\'ll get back to you soon.',
                'form_data': {'name': name, 'email': email, 'subject': subject, 'message': message}
            }
        else:
            context = {
                'page_title': 'Contact Us',
                'page_description': 'Get in touch with us.',
                'error_message': 'Please fill in all required fields.',
                'form_data': {'name': name, 'email': email, 'subject': subject, 'message': message}
            }
    else:
        context = {
            'page_title': 'Contact Us',
            'page_description': 'Get in touch with us.',
        }
    
    return TemplateResponse(request, 'pages/contact.html', context)
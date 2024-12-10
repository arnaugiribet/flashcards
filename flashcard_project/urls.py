"""
URL configuration for flashcard_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from flashcards import views

# List of prefixes to apply
prefixes = ["", "apm0074851-rnaseq-amer01/ag-scrna/port/8000/"]

# Initialize the urlpatterns list
urlpatterns = [
    path("admin/", admin.site.urls)
]

# Loop through each prefix and append the URL patterns to urlpatterns
for prefix in prefixes:
    urlpatterns.append(path(f'{prefix}', include('flashcards.urls')))  # Routes root path to flashcards app

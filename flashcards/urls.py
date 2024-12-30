from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Root path (e.g., '/')
    path('add_flashcards/', views.add_flashcards, name='add_flashcards'),
    path('decks/', views.user_decks, name='user_decks'),
    path('create_deck/', views.create_deck, name='create_deck'),
    path('study/', views.study, name='study'),
    path('study/review', views.review_card, name='review_card'),
    path('study/no_cards_due', views.no_cards_due, name='no_cards_due'),
    path('add_flashcards/', views.add_flashcards, name='add_flashcards'),
    path('add_flashcards/manual/', views.create_manually, name='create_manually'),
    path('add_flashcards/automatic/', views.create_automatically, name='create_automatically'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # Redirect to home after logout
    path('account/', views.account_settings, name='account_settings'),
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Root path (e.g., '/')
    path('decks/', views.user_decks, name='user_decks'),
    path('documents/', views.user_documents, name='user_documents'),
    path('document/<uuid:document_id>/url/', views.get_document_url, name='get_document_url'),
    path('document/<uuid:document_id>/flashcards/', views.get_document_flashcards, name='get_document_flashcards'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/delete/<uuid:document_id>/', views.delete_document, name='delete_document'),
    path('process-selection/', views.process_selection, name='process_selection'),
    path('manage_cards/', views.manage_cards, name='manage_cards'),    
    path('delete_card/<uuid:card_id>/', views.delete_card, name='delete_card'),
    path('delete_deck/<uuid:deck_id>/', views.delete_deck, name='delete_deck'),
    path('update_card_field/<uuid:card_id>/', views.update_card_field, name='update_card_field'),
    path('create_deck/', views.create_deck, name='create_deck'),
    path('study/', views.study, name='study'),
    path('study/review', views.review_card, name='review_card'),
    path('study/no_cards_due', views.no_cards_due, name='no_cards_due'),
    path('add_flashcards/manual/', views.create_manually, name='create_manually'),
    path('add_flashcards/automatic/', views.create_automatically, name='create_automatically'),
    path('process_file_and_context/', views.process_file_and_context, name='process_file_and_context'),
    path('signup/', views.signup, name='signup'),
    path('resend_activation_email/<int:user_id>/', views.resend_activation_email, name='resend_activation_email'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # Redirect to home after logout
    path('account/settings/', views.account_settings, name='account_settings'),
    path('account/change-username/', views.change_username, name='change_username'),
    path('account/change-password/', views.change_password, name='change_password'),
    path('account/delete/', views.delete_account, name='delete_account'),
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
    path('feedback/', views.feedback_view, name='feedback'),
]

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from django.utils.safestring import mark_safe
from flashcards.models import UserDocument

class DocumentUploadForm(forms.ModelForm):
    document = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Accepted formats: PDF, TXT, DOCX'
    )

    class Meta:
        model = UserDocument
        fields = ['document', 'deck']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['deck'].queryset = Deck.objects.filter(user=user)
            
    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            file_type = document.name.split('.')[-1].lower()
            if file_type not in ['pdf', 'txt', 'docx']:
                raise forms.ValidationError('File type not supported. Please upload PDF, TXT, or DOCX files only.')
            return document


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Enter a valid email address.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        existing_user = User.objects.filter(email=email)
        
        if existing_user.exists():
            user = existing_user.first()
            if not user.is_active:
                # Add a link/button to resend the verification email
                self.add_resend_button_to_error(user)
                raise forms.ValidationError(
                    f"This email is pending verification. Please check your inbox or request a new verification email.\n{self.resend_button}"
                )
            else:
                raise forms.ValidationError("This email is already in use.")
        return email

    def add_resend_button_to_error(self, user):
        """ Adds the button link for resending activation email to the error message """
        # Generate the URL to resend the email
        resend_url = reverse('resend_activation_email', kwargs={'user_id': user.id})
        self.resend_button = mark_safe(f'<a href="{resend_url}" class="btn-resend">Resend Verification Email</a>')

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

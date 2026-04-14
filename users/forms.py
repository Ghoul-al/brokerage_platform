from django import forms
from django.contrib.auth import get_user_model
from .models import PaymentMethod, Profile
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists!")
        return email
    
    
    
class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['payment_type', 'details']
        widgets = {
            'details': forms.Textarea(attrs={
                'placeholder': 'Enter payment details as JSON format',
                'rows': 3
            })
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'email', 'phone_number', 'dob', 'gender', 'profile_image']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }




class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'username', 'email', 'profile_image', 'phone_number']

# class RegistrationForm(UserCreationForm):
#     email = forms.EmailField(required=True)
    
#     class Meta:
#         model = User
#         fields = ["username", "email", "password1", "password2" ]
        
    

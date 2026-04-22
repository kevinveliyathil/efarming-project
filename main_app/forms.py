from django import forms
from django.contrib.auth.models import User
from .models import FarmerProfile, CustomerProfile, Crop

# --- Registration Forms ---
class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match")

class FarmerProfileForm(forms.ModelForm):
    class Meta:
        model = FarmerProfile
        # FIXED: Removed 'aadhar_no', added 'id_proof' to match models.py
        fields = ('phone_no', 'area', 'profile_photo', 'id_proof')
        widgets = {
            'phone_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area / City'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'id_proof': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ('phone_number', 'address', 'state', 'area', 'profile_photo')
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full Address'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City / Area'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

# --- Crop Listing Form ---
class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ('name', 'category', 'price_per_kg', 'quantity_kg', 'image', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Crop Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price_per_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per Kg'}),
            'quantity_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Available Stock (kg)'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# --- Settings Update Forms ---
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class FarmerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = FarmerProfile
        fields = ['profile_photo', 'phone_no', 'area']
        widgets = {
            'phone_no': forms.TextInput(attrs={'class': 'form-control'}),
            'area': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CustomerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['profile_photo', 'phone_number', 'address', 'state', 'area']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'area': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
# main_app/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

class CustomerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['profile_photo', 'phone_number', 'address', 'state', 'area']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'area': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
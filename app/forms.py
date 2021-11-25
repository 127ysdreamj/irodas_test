from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms

class CustomUserCreationForm(UserCreationForm):
    class Meta:
       model = get_user_model()
       fields = ('email',)

class AddToCartForm(forms.Form):
    num = forms.IntegerField( 
        label='数量',
        min_value=1,
        required=True)




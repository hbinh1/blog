from django import forms
from .models import Comment, Contact

class EmailPostForm(forms.Form):
    name = forms.CharField(max_length=25)
    email = forms.EmailField()
    to = forms.EmailField()
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea
    )



class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['name', 'email', 'body']

class SearchForm(forms.Form):
    query = forms.CharField(widget=forms.Textarea, label='')


class Contact(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'body']
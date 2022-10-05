from django.db import models
from django.contrib.auth.models import AbstractUser


from .managers import UserManager

#Custom User CLass for extending
class User(AbstractUser):
    """Already has is_staff and is_superuserin Abstract User class
    uses email for authentication and login
    settings.py needs AUTH_USER_MODEL = (this one)
    Would recommend setting this up at the begging of any django project prior to first migrate cmd
    """
    username = None
    email = models.EmailField('Email Address', unique=True)
    first_name = models.CharField('First Name', max_length=50)
    last_name = models.CharField('Last Name', max_length=50)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    def __str__(self):
        return self.user.get_full_name()

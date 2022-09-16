# tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator  

class TokenGenerator(PasswordResetTokenGenerator):
    # used to replacee settings.PASSWORD_RESET_TIMEOUT, set your length of token here. Currently is 7 days
    timeout = 60 * 60 * 24 * 7
    
    def _make_hash_value(self, user, timestamp):  
        return (  
            text_type(user.pk) + str(timestamp) +  
            text_type(user.is_active)  
        )
    
    def check_token(self, user, token):
        """ Copy + paste from DJango PasswordTokenGenerator to overwrite line 39 for timeout"""
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split("-")
            legacy_token = len(ts_b36) < 4
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        if not constant_time_compare(self._make_token_with_timestamp(user, ts), token):
            if not constant_time_compare(
                self._make_token_with_timestamp(user, ts, legacy=True),
                token,
            ):
                return False
        now = self._now()
        if legacy_token:
            ts *= 24 * 60 * 60
            ts += int((now - datetime.combine(now.date(), time.min)).total_seconds())
        if (self._num_seconds(now) - ts) > self.timeout:
            return False
        return True
        
account_token = TokenGenerator()


# Seperate file
# Example in a view:
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_text 

# Some where in a signup form view:
          message = render_to_string('core/emails/user/user_activation.html', {  
                'user': user,  
                'domain': current_site.domain,  
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),  
                'token': account_activation_token.make_token(user),
            })
          email = EmailMessage(  
                        mail_subject, message, to=[user.email]  
            )  
          email.send() 
      
# Later on simple function baed view:
# url pattern would be like: accounts/activate/<str:uidb64>/<str:token>/
def activate_account(request, uidb64, token):
    try:  
        uid = force_text(urlsafe_base64_decode(uidb64))  
        user = User.objects.get(pk=uid)
        next_url = request.GET.get('next') or reverse_lazy('user')  
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):  
        user = None  
    if user is not None and account_activation_token.check_token(user, token):
        # Handle your stuff here such as account activation, such as:
        # user.is_active = True
        # user.save()

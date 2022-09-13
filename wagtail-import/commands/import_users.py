import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = "Imports from old site via json format"
    """
    Users will need to reset their password on first time login
    """

    def add_arguments(self, parser):
        parser.add_argument('the_file', help='the file to import')


    def handle(self, *args, **options):
        
        with open(options['the_file'], 'r') as f:
            data = json.load(f)

        for user in data['users']:
            user = user['user']
            
            print('Starting: ', user['email']) 
            
            with transaction.atomic():
                new_user, created = User.objects.get_or_create(
                    email=user['email'],
                    first_name=user['first_name'],
                    last_name=user['last_name']
                )
                
                if created:
                    profile, c = UserProfile.objects.get_or_create(
                        user=new_user,
                        org_type='',
                        org_name=user['org_name'],
                        is_private_org=True if user['is_private_org'] == 'Private' else False,
                        job_title=user['job_title'],
                        address=user['address'],
                        city=user['city'],
                        state=user['state'],
                        zip_code=user['zip_code'],
                        phone=user['phone'],
                    )
            profile = locals().get('profile', 'Already Created')
            self.stdout.write(f"Finished: {new_user.email}, {profile}")
            
        f.close()
        self.stdout.write(self.style.SUCCESS('All Done! Success!'))

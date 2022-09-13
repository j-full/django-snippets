import json
import urllib.request, urllib.error
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.validators import validate_slug
from django.core import exceptions
from django.utils.timezone import make_aware
from wagtail.core.models import Collection, Page
from wagtail.images.models import Image
from coderedcms.models.snippet_models import ClassifierTerm
from website.models import ArticlePage, ArticleIndexPage


class Command(BaseCommand):
    help = "Imports from old site via json format"
    """
    Need to have created desired index pages before running this.
    Sample Command: python manage.py import_artcles export.json -t 'Featured Articles'
    Sample JSON to parse:
    pages: [
        0: {
            content: {
                title:	"Health Care Curriculum",
                category:	"Ideas", :classifier_terms:
                cover_image: {
                    src:	"https://oldsite.com/sites/default/files/field/image/article-health-care.jpg",
                    alt:	"",
                    title:	"",
                },
                date_display:	"2015-10-16",
                author_display:	"Author",
                body:	"<p>Recently the National…pal\">profile</a>.</p>\n",
                tags:	"Health Care",
                app_label:	"website",
                model:	"ArticlePage",
                caption:	null,
                slug:	"/article/health-care-guide"
            }
        },
    ]
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = Collection.objects.get(name='prev img')

    def add_arguments(self, parser):
        parser.add_argument('the_file', help='the file to import')
        parser.add_argument('-t', '--type', type=str, help='Article Type, Featured Articles, etc.', )


    def handle(self, *args, **options):
        
        if not options['type']:
            raise CommandError('Plz specify article type, ex: -t Featured')
        
        try:
            parent = ArticleIndexPage.objects.get(title=options['type'])
        except Exception:
            index_options = list(ArticleIndexPage.objects.all().values_list('title', flat=True))
            raise CommandError(
                f"Couldn't find Article Type with name {options['type']}, "
                f"(Note: must be string, spaces allowed, is case sensitive), options are: {index_options}"
            )

        # import article type pages
        with open(options['the_file'], 'r') as f:
            data = json.load(f)

        for page in data['pages']:
            content = page['content']
            
            print('Starting: ', content['title']) 
            
            classifier_term = self.get_classifier_term(content['category'])
            try:
                youtube_link = content['youtube_link'] if content['youtube_link'] else None
            except KeyError:
                youtube_link = None
            
            with transaction.atomic():
                new_page = ArticlePage(
                    title=content['title'],
                    first_published_at=make_aware(datetime.strptime(content['date_display'], "%Y-%m-%d")),
                    date_display=content['date_display'],
                    author_display=content['author_display'] if content['author_display'] else 'The LC Staff',
                    caption=content['caption'] if (content['caption'] and len(content['caption']) < 255) else '',
                    classifier_terms=classifier_term
                )
                slug = self.make_slug(content['slug'], content['title'])
                if slug:
                    new_page.slug=slug

                body_html = self.replace_body_images(content['body'])
                new_body = [{'type': 'html', 'value': body_html}]

                if youtube_link:
                    new_body.append({
                        "type": "embed_video", 
                        "value": {
                            "settings": {"custom_template": "", "custom_css_class": "", "custom_id": ""},
                            "url": f"{youtube_link}"
                        }
                    })

                new_page.body = json.dumps(new_body)
                if content['cover_image']:
                    cover_image = self.get_and_save_image(content['cover_image']['src'])
                    if cover_image:
                        new_page.cover_image = cover_image

                parent.add_child(instance=new_page)

                if content['tags']:
                    tags = content['tags'].split(', ')
                    new_page.tags.add(*tags)
                
                new_page.save()
                new_page.save_revision().publish()
            
            self.stdout.write(f'Finished: {new_page.title}')
            
        f.close()
        self.stdout.write(self.style.SUCCESS('All Done! Success!'))

    def get_and_save_image(self, url):
        if len(url) > 500:
            img_name = f'old_img_{str(uuid.uuid4().hex.upper()[0:6])}.jpg'
        else:
            img_name = url.split("/")[-1]
        self.stdout.write(f'Getting img: {img_name}...')

        try:
            tmpfile, _ = urllib.request.urlretrieve(url)
        except ValueError:
            url = 'https://oldsite.com' + url
            tmpfile, _ = urllib.request.urlretrieve(url)
        except urllib.error.HTTPError:
            self.stdout.write(self.style.WARNING(f'Skipping, No img at {url}'))
            return None

        new_img = Image(
            title=img_name, 
            file=SimpleUploadedFile(img_name, open(tmpfile, "rb").read()), 
            collection=self.collection)
        new_img.save()
        if not new_img:
            self.stdout.write(self.style.WARNING(f'Something messed up with img at {url}'))
        urllib.request.urlcleanup()
        self.stdout.write('Success img')
        return new_img
    
    def get_classifier_term(self, classifier_term):
        term = ClassifierTerm.objects.filter(name=classifier_term)
        if not term:
            self.stdout.write(self.style.WARNING(f'No term for {term}'))
            return None
        self.stdout.write(f'Success Classifier: {term}')
        return term
    
    def make_slug(self, url, title):
        print('slugging: ', url, title)
        slug = url.replace('/article/', '') if url else None
        try:
            validate_slug(slug)
            if not Page.objects.filter(slug=slug).count() >= 1:
                return slug
        except exceptions.ValidationError:
            pass
        print('Old slug invalid. will make new on save')
        return None
    
    def replace_body_images(self, body):
        soup = BeautifulSoup(body, features="html5lib")
        for elem in soup.findAll('img'):
            new_img = self.get_and_save_image(elem['src'])
            if not new_img:
                elem.decompose()
                continue
            elem['src'] = new_img.file.url
            elem['class'] = elem.get('class', []) + ['imported-article-img']

        return str(soup)

import json
import urllib.request
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.validators import validate_slug
from django.core import exceptions
from django.utils.text import slugify
from django.utils.timezone import make_aware
from wagtail.core.models import Collection
from wagtail.images.models import Image
from wagtail.documents.models import Document
from website.models import (
    GatedMediaIndexPage,
    GatedMediaPage,
    PaperIndexPage,
    PaperPage,
    PodcastIndexPage,
    PodcastPage
)


class Command(BaseCommand):
    help = "Imports from old drupal 7 site via json format"
    """
    Need to have created desired index pages before running this.
    Sample Command: python manage.py import_pages export.json -t 'Podcast'
    Sample JSON to parse:
    pages: [
        0: {
            content: {
                title:	"Healthcare Article Title",
                category:	"Ideas", :classifier_terms:
                cover_image: {
                    src:	"https://site.com/sites/default/files/field/image/image.jpg",
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
                slug:	"/article/healthcare-article"
            }
        },
    ]
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img_collection = Collection.objects.get(name='prev img')
        self.paper_collection = None

    def add_arguments(self, parser):
        parser.add_argument('the_file', help='the file to import')
        parser.add_argument('-t', '--type', type=str, help='Page Type, Paper, Podcast, GatedMedia, etc.', )


    def handle(self, *args, **options):
        
        if not options['type']:
            raise CommandError('Plz specify page type, ex: -t Podcast')
        
        try:
            page_types = {
                'GatedMedia': [GatedMediaIndexPage.objects.first(), GatedMediaPage],
                'Paper': [PaperIndexPage.objects.get(title='Papers'), PaperPage],
                'Report': [PaperIndexPage.objects.get(title='Reports'), PaperPage],
                'Podcast': [PodcastIndexPage.objects.first(), PodcastPage],
            }
            # Should only be one type of each index page
            parent = page_types[options['type']][0]
            page_type = page_types[options['type']][1]
        except Exception:
            raise CommandError(
                f"Couldn't find Page Type with name {options['type']}, "
                f"(Note: must be string), options are: {list(page_types.keys())}"
            )
        
        print('Found Page Type', parent, page_type)

        if page_type is PaperPage:
            collection_name = 'Reports' if options['type'] == 'Report' else 'Papers'
            self.paper_collection = Collection.objects.get(name=collection_name)

        # import pages into new site
        with open(options['the_file'], 'r') as f:
            data = json.load(f)

        for page in data['pages']:
            content = page['content']
            
            print('Starting: ', content['title']) 
            
            slug = self.make_slug(options['type'], content['slug'], content['title'])
            
            with transaction.atomic():
                new_page = page_type(
                    title=content['title'],
                    slug=slug,
                    first_published_at=make_aware(datetime.strptime(content['date_display'], "%Y-%m-%d")),
                    date_display=content['date_display'],
                )

                if page_type is PaperPage:
                    pdf = self.get_and_save_paper(content['paper'])
                    new_page.paper = pdf
                    body_content = self.remove_old_download_btn(content['body'])   
                else:
                    body_content = content['body']

                new_body = [{'type': 'html', 'value': body_content}]

                if options['type'] == 'Report' and content['report_html']:
                    report_html = self.replace_body_images(content['report_html'])
                    new_body.append({'type': 'html', 'value': report_html})
                   
                if page_type is PodcastPage:
                    new_page.podcast_url = content['podcast_url']
                
                if page_type is GatedMediaPage:
                    new_page.caption = content['caption'] if content['caption'] else ''
                    body_content = self.replace_body_images(content['body'])
                    new_body = [{'type': 'html', 'value': body_content}]                   
                    new_body.append({
                        "type": "embed_video", 
                        "value": {
                            "settings": {"custom_template": "", "custom_css_class": "", "custom_id": ""},
                            "url": f"{content['youtube_link']}"
                        }
                    })

                new_page.body = json.dumps(new_body)
                    
                cover_image = self.get_and_save_image(content['cover_image']['src']) or ''
                new_page.cover_image = cover_image

                parent.add_child(instance=new_page)
                
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
        cover_image = Image(
            title=img_name, 
            file=SimpleUploadedFile(img_name, open(tmpfile, "rb").read()), 
            collection=self.img_collection)
        cover_image.save()
        if not cover_image:
            self.stdout.write(self.style.WARNING(f'Something messed up with img at {url}'))
        urllib.request.urlcleanup()
        self.stdout.write('Success img')
        return cover_image
    
    def get_and_save_paper(self, url):
        self.stdout.write(f'Getting PDF at: {url}')
        file_name = url.split("/")[-1]
        tmpfile, _ = urllib.request.urlretrieve(url)
        pdf = Document(
            title=file_name.replace('.pdf', ''), 
            file=SimpleUploadedFile(file_name, open(tmpfile, "rb").read()), 
            collection=self.paper_collection)
        pdf.save()
        if not pdf:
            self.stdout.write(self.style.WARNING(f'Something messed up with pdf at {url}'))
        urllib.request.urlcleanup()
        self.stdout.write('Success PDF')
        return pdf
    
    def make_slug(self, page_type, url, title):
        stripper = {
            'GatedMedia': '/media/',
            'Paper': '/paper/',
            'Report': '/paper/',
            'Podcast': '/content/',
        }
        try:
            slug = url.replace(stripper[page_type], '') or ''
            validate_slug(slug)
            return slug
        except exceptions.ValidationError:
            print('Old slug invalid. New: ', slugify(title))
            return slugify(title)
    
    def remove_old_download_btn(self, body):
        soup = BeautifulSoup(body, features="html5lib")
        for elem in soup.findAll('a'):
            if 'ownload' or 'DOWNLOAD' in elem.get_text():
                elem.decompose()
                break
        return str(soup)
    
    def replace_body_images(self, body):
        soup = BeautifulSoup(body, features="html5lib")
        for elem in soup.findAll('img'):
            new_img = self.get_and_save_image(elem['src'])
            elem['src'] = new_img.file.url
            elem['class'] = elem.get('class', []) + ['imported-sr-img']
        return str(soup)

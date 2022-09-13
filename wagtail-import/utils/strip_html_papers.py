import json
from bs4 import BeautifulSoup
from website.models import PaperPage

def strip_html():
    papers = PaperPage.objects.filter(paper__collection__name='Papers')
    for paper in papers:
        v = paper.body[0].value
        soup = BeautifulSoup(v, "html.parser")
        for data in soup(['style', 'script']):
            data.decompose()
        data = ' '.join(soup.stripped_strings)
        paper.body = json.dumps([{'type': 'text', 'value': data}])
        paper.save()

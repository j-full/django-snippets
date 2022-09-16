# django-snippets

Useful / Helpful things and solutions I came up with that other could find useful or that I wanted to keep track of.



### [Through Table Example](https://github.com/j-full/django-snippets/blob/main/through-table-example-models.py)
An example of using a custom through table in Django for Many to Many relationships. This example is for a simple event booking system

### [Djano Admin override mixin](https://github.com/j-full/django-snippets/blob/main/admin-override-mixins.py)
Override Django admin use of select for Foreign Keys and M2M - and uses autocomplete for mega performance improvement

### [Wagtail Content Import/Transfer](https://github.com/jerempy/django-snippets/tree/main/wagtail-import)
Django management command for importing large amounts of content to a wagtail site via command line. Contains specifics for the site this was used for but could easily be swapped out or modified for use cases. Works by reading a json file with the content, and for any images it goes to the url and saves it locally to the new site, creates new link and inserts into the new content

Included functionality was for importing article type pages, basic web pages, users, gated media requiring login for access to pdfs, youtube embedded videos and podcasts. Thousands of pieces of Content was exported from a legacy Drupal 7 website as json and imported here.

### [Account Token Generator](https://github.com/jerempy/django-snippets/blob/main/account-token-gen.py)
For making tokens to send in emails for things like account activation. Doesn't require saving token to a database as it decodes and looks up the user_id in this case. Works the same as a password reset token


class AutocompleteOverrideMixin:
    """ By default Django's Admin lists all relationship fields as a Select Field.
    This is useful in some cases, but in many could cause problems as it requires pulling all
    records from the database in order to populate the select choices dropdown. In some production sites
    this can lead to many seconds to load a single page in django admin.
    This Mixin sets all relationships in admin where it is used to use autocomplete instead of select for performance reasons
    It leverages the get_fields() method is called as part of instantiating the admin
    """

    def get_fields(self, request, obj=None):
        fields = self.model._meta.fields
        new_fields = []
        for field in fields:
            if isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                new_fields.append(field.name)
        self.autocomplete_fields = (*self.autocomplete_fields, *new_fields)
        return super().get_fields(request, obj)

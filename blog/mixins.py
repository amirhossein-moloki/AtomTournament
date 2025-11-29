class DynamicFieldsMixin:
    """
    A serializer mixin that takes an additional `fields` argument that controls
    which fields should be displayed.
    """
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class DynamicSerializerViewMixin:
    """
    A view mixin that takes an additional `fields` argument that controls
    which fields should be displayed.
    """
    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())

        if self.request.method == 'GET':
            fields_query = self.request.query_params.get('fields')
            if fields_query:
                fields = tuple(f.strip() for f in fields_query.split(','))
                kwargs['fields'] = fields

        return serializer_class(*args, **kwargs)

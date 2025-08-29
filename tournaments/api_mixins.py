class DynamicFieldsMixin:
    """
    A mixin that allows clients to control which fields should be returned
    by passing a 'fields' query parameter.
    """

    def get_serializer(self, *args, **kwargs):
        """
        Override to inject 'fields' from the query parameters into the serializer.
        """
        fields = self.request.query_params.get("fields")
        if fields:
            kwargs["fields"] = fields.split(",")
        return super().get_serializer(*args, **kwargs)

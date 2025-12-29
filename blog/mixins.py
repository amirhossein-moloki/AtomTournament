from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType

from .models import Reaction


from . import serializers

class ReactionMixin:
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def react(self, request, pk=None, slug=None):
        obj = self.get_object()
        serializer = serializers.ReactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reaction_value = serializer.validated_data['reaction']

        try:
            reaction = Reaction.objects.get(
                user=request.user,
                content_type=ContentType.objects.get_for_model(obj.__class__),
                object_id=obj.pk,
                reaction=reaction_value
            )
            reaction.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Reaction.DoesNotExist:
            Reaction.objects.create(
                user=request.user,
                content_type=ContentType.objects.get_for_model(obj.__class__),
                object_id=obj.pk,
                reaction=reaction_value
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='reactions')
    def reactions(self, request, pk=None, slug=None):
        obj = self.get_object()
        reactions = obj.reactions.all()
        serializer = serializers.ReactionSerializer(reactions, many=True)
        return Response(serializer.data)


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

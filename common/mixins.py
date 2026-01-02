class FileChangeDetectionMixin:
    """
    A mixin that detects changes to a specified file field on a model instance.

    To use, inherit this mixin in your model and set the
    `MONITORED_FILE_FIELD` attribute to the name of the file field
    you want to track.

    Note: This mixin's logic is bypassed by bulk operations like QuerySet.update().
    """
    MONITORED_FILE_FIELD = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.MONITORED_FILE_FIELD:
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            self._original_file_name = field_file.name if field_file else None

    def save(self, *args, **kwargs):
        image_changed = False
        update_fields = kwargs.get('update_fields')
        is_new = self._state.adding

        if self.MONITORED_FILE_FIELD:
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            current_file_name = field_file.name if field_file else None

            # If update_fields is specified, only check for changes if the monitored field is included
            if update_fields is None or self.MONITORED_FILE_FIELD in update_fields:
                if is_new and current_file_name:
                    image_changed = True
                elif not is_new and self._original_file_name != current_file_name:
                    image_changed = True

        self._image_changed = image_changed

        super().save(*args, **kwargs)

        if self.MONITORED_FILE_FIELD:
            # After saving, update the original file name to the current one
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            self._original_file_name = field_file.name if field_file else None

    @property
    def image_has_changed(self):
        return getattr(self, '_image_changed', False)

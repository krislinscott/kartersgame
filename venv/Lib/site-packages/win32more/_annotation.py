import sys

if sys.version_info < (3, 14):

    def get_annotations_string(obj):
        return obj.__annotations__
else:
    from annotationlib import Format, get_annotations

    def get_annotations_string(obj):
        return get_annotations(obj, Format.STRING)

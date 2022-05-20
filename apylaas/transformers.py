import werkzeug
import io

# _transformers = None


# def register(type, transformer, input_type):
#     transformers = get_transformers()
#     transformers[type] = [transformer, input_type]
try:
    from PIL import Image

    has_PIL = True
except ImportError:
    has_PIL = False


def default_type_to_html():
    transformers = [
        (str, "text"),
        (int, "text"),
        (float, "text"),
        (bool, "checkbox"),
    ]
    if has_PIL:
        transformers.append((Image, "file"))

    def list_transformer(type):
        if "List" in str(type):
            return "text"
        #     return '<input type="text" />'

    transformers.append(list_transformer)

    return transformers


def default_input_to_python():
    transformers = [
        (str, lambda s: str(s)),
        (int, lambda s: int(s)),
        (float, lambda s: float(s)),
        (bool, lambda s: s == "on"),
    ]

    if has_PIL:

        def imager(data: werkzeug.datastructures.FileStorage):
            return Image.open(io.BytesIO(data.read()))

        transformers.append((Image, imager))

    def list_transformer(type):
        if "List" in str(type):

            def fn(value):
                # print(value)
                return [int(x.strip()) for x in value.split(",")]
                # return [1, 2, 3]

            return fn

        return None

    transformers.append(list_transformer)

    return transformers


def get_default_transformers():
    transformers = {
        str: [lambda s: str(s), "text"],
        int: [lambda s: int(s), "text"],
        float: [lambda s: float(s), "text"],
        bool: [lambda s: s == "on", "checkbox"],
    }

    try:
        from PIL import Image

        has_PIL = True
    except ImportError:
        has_PIL = False

    if has_PIL:

        def imager(data: werkzeug.datastructures.FileStorage):
            return Image.open(io.BytesIO(data.read()))

        transformers[Image] = (imager, "file")

    return transformers


# def get_default_transformers():
#     global _transformers
#     if _transformers is None:
#         _transformers = _init()

#     return _transformers

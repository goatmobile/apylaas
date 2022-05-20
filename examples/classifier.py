"""
some text with a bunch of words of words of words of words of words of words of words of words of words of words of words of words of words of words of words of words
"""

from torchvision import transforms, models
import torch
import time
import json
from PIL import Image


_model = None


def _get_model():
    global _model
    if _model is None:
        _model = models.mobilenet_v3_small(pretrained=True)
        _model.eval()
    return _model


def predict(img: Image) -> str:
    model = _get_model()
    time.sleep(2)
    transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    img_t = transform(img)
    batch_t = torch.unsqueeze(img_t, 0)
    r = model(batch_t)
    _, index = torch.max(r, 1)

    with open("imagenet_class_index.json") as f:
        classes = json.load(f)

    _, name = classes[str(index.item())]
    return " ".join([x.title() for x in name.split("_")])

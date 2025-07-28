# Based on https://github.com/RE-N-Y/imscore/blob/main/src/imscore/preference/model.py

from importlib import resources
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as T
from transformers import AutoImageProcessor,AutoModel,AutoProcessor
import numpy as np
from PIL import Image

def get_size(size):
    if isinstance(size, int):
        return (size, size)
    elif "height" in size and "width" in size:
        return (size["height"], size["width"])
    elif "shortest_edge" in size:
        return size["shortest_edge"]
    else:
        raise ValueError(f"Invalid size: {size}")
    
def get_image_transform(processor:AutoImageProcessor):
    config = processor.to_dict()
    resize = T.Resize(get_size(config.get("size"))) if config.get("do_resize") else nn.Identity()
    crop = T.CenterCrop(get_size(config.get("crop_size"))) if config.get("do_center_crop") else nn.Identity()
    normalise = T.Normalize(mean=processor.image_mean, std=processor.image_std) if config.get("do_normalize") else nn.Identity()

    return T.Compose([resize, crop, normalise])

class ClipScorer(torch.nn.Module):
    def __init__(self, dtype):
        super().__init__()
        self.model = AutoModel.from_pretrained("openai/clip-vit-large-patch14")
        self.processor = AutoProcessor.from_pretrained("openai/clip-vit-large-patch14")
        self.tform = get_image_transform(self.processor.image_processor)
        self.eval()
    
    def _process(self, pixels):
        dtype = pixels.dtype
        pixels = self.tform(pixels)
        pixels = pixels.to(dtype=dtype)

        return pixels

    @torch.no_grad()
    def __call__(self, pixels, prompts):
        texts = self.processor(text=prompts, padding='max_length', truncation=True, return_tensors="pt").to(pixels.device)
        pixels = self._process(pixels)
        outputs = self.model(pixel_values=pixels, **texts)
        return outputs.logits_per_image.diagonal()/30



def main():
    scorer = ClipScorer(
        dtype=torch.float32
    )

    images=[
    "assets/test.jpg",
    "assets/test.jpg"
    ]
    pil_images = [Image.open(img) for img in images]
    prompts=[
        'an image of cat',
        'not an image of cat'
    ]
    images = [np.array(img) for img in pil_images]
    images = np.array(images)
    images = images.transpose(0, 3, 1, 2)  # NHWC -> NCHW
    images = torch.tensor(images, dtype=torch.uint8)/255.0
    print(scorer(images, prompts))

if __name__ == "__main__":
    main()
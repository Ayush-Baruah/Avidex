import torch
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from torch.utils.data import Dataset, DataLoader

class BirdImageDataset(Dataset):
    def __init__(self,samples,transform):
        self.samples = []
        self.transform = transform
        for path, label in samples:
            try: 
                Image.open(path).verify()
                self.samples.append((path,label))
            except Exception:
                print(f"Skipping corruptfile: {path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        transformed_image = self.transform(image)
        return transformed_image, label
import torch
import json
from PIL import Image
from pathlib import Path
import torchvision.transforms as transforms
import requests
from io import BytesIO
from .model import *

# Anchor to this file's own directory, so these paths work no matter
# where the process that imports this module was launched from.
MODEL_DIR = Path(__file__).resolve().parent

url = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fwww.papahanaumokuakea.gov%2Fimages%2Fnews_imgs%2Flaysan_duck_translocation_1.jpg&f=1&nofb=1&ipt=e8d19acf07fcfddd2b8c43973ad06ebedc0a648434854b006e62f477a3920f94&ipo=images"

# Load class mapping first to get num_classes
with open(MODEL_DIR / "idx_to_class.json", "r") as f:
    idx_to_class = json.load(f)

num_classes = len(idx_to_class)

# Load the best model
device = "mps" if torch.backends.mps.is_available() else "cpu"
model = BirdCNN(num_classes=num_classes)
model.load_state_dict(torch.load(MODEL_DIR / "best_bird_cnn.pt", map_location=device))
model = model.to(device)
model.eval()  # Set to evaluation mode

# Define the same transforms used for validation
val_trans = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def classify_image(img, top_k=10):
    """
    Runs one PIL Image through the model and returns the top_k predictions.
    This is the shared core — classify_image_from_url/_file/_upload all
    just get an Image object however they need to, then call this.
    """
    img_tensor = val_trans(img.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        top_probs, top_indices = torch.topk(probabilities, top_k, dim=1)

    results = [
        (idx_to_class[str(top_indices[0][i].item())], top_probs[0][i].item())
        for i in range(top_k)
    ]
    return results[0][0], results


def classify_image_from_url(url, top_k=10):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return classify_image(img, top_k)


def classify_image_from_file(file_path, top_k=10):
    img = Image.open(file_path)
    return classify_image(img, top_k)

if __name__ == "__main__":
    print(classify_image_from_url(url))

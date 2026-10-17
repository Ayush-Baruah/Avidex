import torch
import json
from PIL import Image
import torchvision.transforms as transforms
import requests
from io import BytesIO
from model import *

url = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fcdn.pixabay.com%2Fphoto%2F2021%2F02%2F28%2F14%2F59%2Fsnow-goose-6057474_1280.jpg&f=1&nofb=1&ipt=29f3181b495ee0aa389c90ecdc1b7df2a206cb6704e39ba2d713541016419ca0&ipo=images"

# Load class mapping first to get num_classes
with open("idx_to_class.json", "r") as f:
    idx_to_class = json.load(f)

num_classes = len(idx_to_class)

# Load the best model
device = "mps" if torch.backends.mps.is_available() else "cpu"
model = BirdCNN(num_classes=num_classes)
model.load_state_dict(torch.load("best_bird_cnn.pt", map_location=device))
model = model.to(device)
model.eval()  # Set to evaluation mode

# Define the same transforms used for validation
val_trans = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def classify_image_from_url(url, top_k=10):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert('RGB')
    img_tensor = val_trans(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        
        # Get top 10 predictions
        top_probs, top_indices = torch.topk(probabilities, top_k, dim=1)
    
    print(f"Top {top_k} predictions:")
    print("-" * 40)
    for i in range(top_k):
        idx = top_indices[0][i].item()
        confidence = top_probs[0][i].item()
        class_name = idx_to_class[str(idx)]
        print(f"{i+1}. {class_name}: {confidence:.4f} ({confidence*100:.2f}%)")
    
    # Return the top prediction and all results
    top_class = idx_to_class[str(top_indices[0][0].item())]
    return top_class, [(idx_to_class[str(top_indices[0][i].item())], top_probs[0][i].item()) for i in range(top_k)]

def classify_image_from_file(file_path, top_k=10):
    img = Image.open(file_path).convert('RGB')
    img_tensor = val_trans(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        
        # Get top 10 predictions
        top_probs, top_indices = torch.topk(probabilities, top_k, dim=1)
    
    print(f"Top {top_k} predictions:")
    print("-" * 40)
    for i in range(top_k):
        idx = top_indices[0][i].item()
        confidence = top_probs[0][i].item()
        class_name = idx_to_class[str(idx)]
        print(f"{i+1}. {class_name}: {confidence:.4f} ({confidence*100:.2f}%)")
    
    # Return the top prediction and all results
    top_class = idx_to_class[str(top_indices[0][0].item())]
    return top_class, [(idx_to_class[str(top_indices[0][i].item())], top_probs[0][i].item()) for i in range(top_k)]

# Use it:
# top_class, all_predictions = classify_image_from_file('path/to/image.jpg')


# Use it:
top_class, all_predictions = classify_image_from_url(url)


print(top_class)

import torchvision.transforms as transforms
import json
from model import *
from selection import *
from datasetClass import *
from pathlib import Path
from PIL import Image, ImageFile

val_samples, train_samples = split_dataset(IMAGE_DIR, class_to_idx(IMAGE_DIR))

mean, std =[0.485, 0.456, 0.406],[0.229, 0.224, 0.225]

train_trans = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
    transforms.RandomResizedCrop(128, scale=(0.4,1.0)),
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])

val_trans = transforms.Compose([
    transforms.Resize((128,128)),
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])

train_ds = BirdImageDataset(train_samples, train_trans)
val_ds = BirdImageDataset(val_samples, val_trans)

train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=16, shuffle=False)



device = "mps" if torch.backends.mps.is_available() else "cpu"
model = BirdCNN(num_classes=len(class_to_idx(IMAGE_DIR)))
model = model.to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr = 0.001)



num_epochs = 60
best_accuracy = 0.0   # before the epoch loop

# Training loop
for epoch in range(num_epochs):
    print("----------")
    # One full pass over the training data
    model.train() # tells layers like BatchNorm to behave in "training mode"
    running_loss = 0.0
    running_val_loss = 0.0
    correct = 0

    # batch loop
    for images, labels in train_loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() *images.size(0)

    epoch_loss = running_loss / len(train_ds)
    print("Epoch",epoch+1,":")
    print(f"Training:\nLoss: {epoch_loss:.4f}")

    with torch.no_grad():
        model.eval()

        # batch loop
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)
            _, predicted = torch.max(outputs, dim = 1)

            running_val_loss += loss.item() * images.size(0)
            correct += (predicted == labels).sum().item()

            
        epoch_val_loss = running_val_loss / len(val_ds)
        accuracy = correct / len(val_ds)
        print("Validation")
        print("Loss value:",epoch_val_loss)
        print("Accuracy:",accuracy)

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            torch.save(model.state_dict(), "best_bird_cnn.pt")
            print(f"New best model saved (accuracy: {accuracy:.4f})")


# class_to_idx(IMAGE_DIR) returns {birdFolderName: index}. Inference needs
# the reverse — given a predicted index, what bird is it? Saving this
# once, right after training, means inference always uses the exact
# mapping the model was trained with, instead of recomputing it later
# and risking a mismatch if folders ever change.
idx_to_class = {index: name for name, index in class_to_idx(IMAGE_DIR).items()}

with open("idx_to_class.json", "w") as f:
    json.dump(idx_to_class, f)
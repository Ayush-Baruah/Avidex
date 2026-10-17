import torch
import torch.nn as nn

# A reusable "conv block": the repeating unit of the network.
# in_ch = channels coming in (3 for RGB on the first block)
# out_ch = how many filters this block learns
def conv_block(in_ch, out_ch):
    return nn.Sequential(
        # 3x3 filters; padding=1 keeps height/width unchanged
        nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
        # normalizes activations per channel -> faster, steadier training
        nn.BatchNorm2d(out_ch),
        # keeps positive values, zeroes negatives (adds non-linearity)
        nn.ReLU(),
        # halves height and width (128 -> 64, etc.)
        nn.MaxPool2d(2),
    )

# A class that inherits from nn.Module. The (nn.Module) in parentheses is
# what makes it a subclass and gives it PyTorch's machinery (parameter
# tracking, .to(device), .train()/.eval(), saving weights, etc.)
class BirdCNN(nn.Module):

    # __init__ runs once, when you create the model: Classifier(num_classes=10)
    # Its job: define the layers this model owns.
    def __init__(self, num_classes):
        # REQUIRED: runs nn.Module's own setup first. Without this line,
        # assigning layers below raises an error.
        super().__init__()

        # Assigning a layer to self.<name> registers it, so its weights
        # get tracked and later updated by the optimizer.
        self.featureExtractor = nn.Sequential(conv_block(3, 32),conv_block(32,64),conv_block(64,128), conv_block(128,256))
        self.classifierHead = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(256, num_classes))

    # forward runs every time data passes through the model.
    # Its job: use the layers from __init__, in order, on the input x
    # and return the result.
    def forward(self, x):
        x = self.featureExtractor(x)
        x = self.classifierHead(x)
        return x
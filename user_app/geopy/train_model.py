"""
train_model.py - Train the Scene Classifier on Disaster Images

This script fine-tunes MobileNetV2 on your disaster scene dataset
to improve classification accuracy for floods, fires, etc.

STEP 1: Organize your images in this structure:
    data/train/
        urban_road/
            img1.jpg
            img2.jpg
        bridge_flyover/
            img1.jpg
        water_flood/
            img1.jpg
            img2.jpg
        residential/
            ...
        rural/
            ...
        commercial/
            ...
        landmark/
            ...
        transit/
            ...

STEP 2: Run training:
    python train_model.py

STEP 3: Model saved to: models/scene_classifier.pth
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from datetime import datetime


# Configuration
CONFIG = {
    "data_dir": "data/train",           # Directory with training images
    "model_save_path": "models/scene_classifier.pth",
    "num_epochs": 10,
    "batch_size": 16,
    "learning_rate": 0.001,
    "image_size": 224,
    "device": "cuda" if torch.cuda.is_available() else "cpu"
}

# Scene categories (must match folder names)
CATEGORIES = [
    "urban_road",
    "bridge_flyover", 
    "residential",
    "water_flood",
    "rural",
    "commercial",
    "landmark",
    "transit",
    "industrial",
    "unknown"
]


def create_model(num_classes: int):
    """Create MobileNetV2 model for scene classification."""
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    
    # Freeze early layers (optional - keeps pretrained features)
    for param in model.features[:10].parameters():
        param.requires_grad = False
    
    # Replace classifier for our classes
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    
    return model


def get_transforms():
    """Get image transforms for training and validation."""
    train_transform = transforms.Compose([
        transforms.Resize((CONFIG["image_size"], CONFIG["image_size"])),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((CONFIG["image_size"], CONFIG["image_size"])),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    return train_transform, val_transform


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for inputs, labels in dataloader:
        inputs, labels = inputs.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
    
    accuracy = 100.0 * correct / total
    avg_loss = running_loss / len(dataloader)
    return avg_loss, accuracy


def validate(model, dataloader, criterion, device):
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
    
    accuracy = 100.0 * correct / total
    avg_loss = running_loss / len(dataloader)
    return avg_loss, accuracy


def main():
    print("=" * 60)
    print("SCENE CLASSIFIER TRAINING")
    print("=" * 60)
    print(f"\nDevice: {CONFIG['device']}")
    print(f"Data directory: {CONFIG['data_dir']}")
    print()
    
    # Check if data directory exists
    if not os.path.exists(CONFIG["data_dir"]):
        print("❌ ERROR: Training data not found!")
        print()
        print("Please organize your images like this:")
        print()
        print("  data/train/")
        print("      water_flood/")
        print("          flood1.jpg")
        print("          flood2.jpg")
        print("      bridge_flyover/")
        print("          bridge1.jpg")
        print("      urban_road/")
        print("          road1.jpg")
        print("      ...")
        print()
        print("Then run this script again.")
        return
    
    # Create transforms
    train_transform, val_transform = get_transforms()
    
    # Load dataset
    print("Loading dataset...")
    dataset = datasets.ImageFolder(CONFIG["data_dir"], transform=train_transform)
    
    # Split into train/val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    print(f"  Training images: {len(train_dataset)}")
    print(f"  Validation images: {len(val_dataset)}")
    print(f"  Classes: {dataset.classes}")
    print()
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=CONFIG["batch_size"], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=CONFIG["batch_size"], shuffle=False)
    
    # Create model
    print("Creating model...")
    num_classes = len(dataset.classes)
    model = create_model(num_classes)
    model = model.to(CONFIG["device"])
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=CONFIG["learning_rate"])
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)
    
    # Training loop
    print("\nStarting training...")
    print("-" * 60)
    
    best_acc = 0.0
    for epoch in range(CONFIG["num_epochs"]):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, CONFIG["device"])
        val_loss, val_acc = validate(model, val_loader, criterion, CONFIG["device"])
        scheduler.step()
        
        print(f"Epoch {epoch+1}/{CONFIG['num_epochs']}: "
              f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.1f}% | "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.1f}%")
        
        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            os.makedirs("models", exist_ok=True)
            torch.save(model.state_dict(), CONFIG["model_save_path"])
            print(f"  ✓ Saved best model (acc: {best_acc:.1f}%)")
    
    print("-" * 60)
    print(f"\n✅ Training complete!")
    print(f"   Best validation accuracy: {best_acc:.1f}%")
    print(f"   Model saved to: {CONFIG['model_save_path']}")
    print()
    print("To use the trained model:")
    print("  1. The model will be loaded automatically by scene_model.py")
    print("  2. Or load manually: torch.load('models/scene_classifier.pth')")


def create_sample_structure():
    """Create the expected folder structure for training data."""
    base_dir = "data/train"
    
    for category in CATEGORIES:
        path = os.path.join(base_dir, category)
        os.makedirs(path, exist_ok=True)
        
        # Create a README in each folder
        readme_path = os.path.join(path, "README.txt")
        with open(readme_path, "w") as f:
            f.write(f"Place {category} images here.\n")
            f.write(f"Suggested: 50-200 images per category.\n")
    
    print(f"✓ Created folder structure in {base_dir}/")
    print("\nNow add images to each category folder:")
    for cat in CATEGORIES:
        print(f"  - {base_dir}/{cat}/")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        create_sample_structure()
    else:
        main()

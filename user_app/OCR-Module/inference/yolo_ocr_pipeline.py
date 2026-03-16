import cv2
import pytesseract
from ultralytics import YOLO
import os

# ---------------- CONFIG ----------------
YOLO_MODEL_PATH = "../runs/detect/train2/weights/best.pt"
IMAGE_PATH = "../data/raw_images/img2.png"
OUTPUT_DIR = "cropped_text_regions"

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- LOAD MODELS ----------------
model = YOLO(YOLO_MODEL_PATH)

# ---------------- READ IMAGE ----------------
image = cv2.imread(IMAGE_PATH)
if image is None:
    raise ValueError("Image not found!")

# ---------------- YOLO TEXT DETECTION ----------------
results = model(image, conf=0.02, imgsz=960)

print("\n[INFO] Running YOLO text detection...\n")

for idx, box in enumerate(results[0].boxes):
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    conf = float(box.conf[0])

    # Crop detected text region
    crop = image[y1:y2, x1:x2]

    if crop.size == 0:
        continue

    crop_path = f"{OUTPUT_DIR}/crop_{idx}.jpg"
    cv2.imwrite(crop_path, crop)

    # ---------------- OCR PREPROCESSING ----------------
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    _, thresh = cv2.threshold(
    enhanced, 0, 255,
    cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # ---------------- OCR ----------------
    text = pytesseract.image_to_string(
        thresh,
        config="--oem 3 --psm 6"
    ).strip()

    print(f"[DETECTED REGION {idx}]")
    print(f"Confidence : {conf:.2f}")
    print(f"OCR Text   : {text if text else 'No text found'}")
    print("-" * 40)

print(f"[DEBUG] Total boxes detected: {len(results[0].boxes)}")

annotated = results[0].plot()
cv2.imshow("YOLO Detections", annotated)
cv2.waitKey(0)
cv2.destroyAllWindows()
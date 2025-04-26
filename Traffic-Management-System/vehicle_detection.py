# vehicle_detection.py
import torch
import cv2

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Define the vehicle classes YOLO detects
vehicle_labels = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']

def detect_vehicles(frame):
    results = model(frame)
    detections = results.pandas().xyxy[0]

    counts = {'car': 0, 'truck': 0, 'bus': 0, 'bike': 0, 'rickshaw': 0}
    for _, row in detections.iterrows():
        label = row['name']
        if label == 'car':
            counts['car'] += 1
        elif label == 'truck':
            counts['truck'] += 1
        elif label == 'bus':
            counts['bus'] += 1
        elif label in ['motorcycle', 'bicycle']:
            counts['bike'] += 1

    return counts

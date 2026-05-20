# YOLO Training Guide

This folder contains scripts for training and evaluating a license plate detector with Ultralytics YOLO.

## Dataset Format

Use standard YOLO detection format:

```text
dataset/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

Each label file should contain one license plate box per line:

```text
class_id x_center y_center width height
```

Values are normalized from 0 to 1. The default class is:

```yaml
0: license_plate
```

## Configure Data

Edit `data.yaml`:

```yaml
path: ../datasets/license-plates
train: images/train
val: images/val
test: images/test
names:
  0: license_plate
```

## Train

From the `training` folder:

```bash
python train_yolo.py --data data.yaml --epochs 50 --imgsz 640 --batch 16 --model yolov8n.pt
```

The best model is copied to:

```text
../backend/models/plate_detector.pt
```

## Evaluate

```bash
python evaluate_yolo.py --model ../backend/models/plate_detector.pt --data data.yaml
```

The evaluation script prints precision, recall, mAP@50, mAP@50-95, and inference timing.

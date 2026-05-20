import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained YOLO plate detector.")
    parser.add_argument(
        "--model",
        default="../backend/models/plate_detector.pt",
        help="Path to trained model.",
    )
    parser.add_argument("--data", default="data.yaml", help="Path to YOLO data.yaml.")
    parser.add_argument("--imgsz", type=int, default=640, help="Evaluation image size.")
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Ultralytics is not installed. Run: pip install -r ../backend/requirements.txt"
        ) from exc

    script_dir = Path(__file__).resolve().parent
    model_path = Path(args.model)
    data_path = Path(args.data)
    if not model_path.is_absolute():
        model_path = script_dir / model_path
    if not data_path.is_absolute():
        data_path = script_dir / data_path

    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")

    model = YOLO(str(model_path))
    metrics = model.val(data=str(data_path), imgsz=args.imgsz, split=args.split)

    box = metrics.box
    speed = getattr(metrics, "speed", {})

    print("Evaluation metrics")
    print(f"Precision:   {float(box.mp):.4f}")
    print(f"Recall:      {float(box.mr):.4f}")
    print(f"mAP@50:      {float(box.map50):.4f}")
    print(f"mAP@50-95:   {float(box.map):.4f}")
    print(f"Preprocess:  {speed.get('preprocess', 0):.2f} ms/image")
    print(f"Inference:   {speed.get('inference', 0):.2f} ms/image")
    print(f"Postprocess: {speed.get('postprocess', 0):.2f} ms/image")


if __name__ == "__main__":
    main()

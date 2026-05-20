import argparse
import shutil
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO for license plate detection.")
    parser.add_argument("--data", default="data.yaml", help="Path to YOLO data.yaml.")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs.")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size.")
    parser.add_argument("--batch", type=int, default=16, help="Batch size.")
    parser.add_argument("--model", default="yolov8n.pt", help="Base Ultralytics model.")
    parser.add_argument("--project", default="runs", help="Training output directory.")
    parser.add_argument("--name", default="plate_detector", help="Training run name.")
    parser.add_argument(
        "--output",
        default="../backend/models/plate_detector.pt",
        help="Destination for the best trained model.",
    )
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
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = script_dir / data_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = script_dir / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.model)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
    )

    save_dir = Path(getattr(results, "save_dir", Path(args.project) / args.name))
    best_model = save_dir / "weights" / "best.pt"
    if not best_model.exists():
        raise SystemExit(f"Training finished, but best model was not found at {best_model}")

    shutil.copy2(best_model, output_path)
    print(f"Best model saved to {output_path}")


if __name__ == "__main__":
    main()

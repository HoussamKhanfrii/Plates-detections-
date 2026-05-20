def _require_cv2_numpy():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV and NumPy are required for preprocessing. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc
    return cv2, np


def preprocess_basic(image):
    cv2, _np = _require_cv2_numpy()
    resized = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    return denoised


def preprocess_threshold(image):
    cv2, _np = _require_cv2_numpy()
    gray = preprocess_basic(image)
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        8,
    )


def preprocess_contrast(image):
    cv2, _np = _require_cv2_numpy()
    gray = preprocess_basic(image)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return enhanced


def preprocess_sharpen(image):
    cv2, np = _require_cv2_numpy()
    contrasted = preprocess_contrast(image)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(contrasted, -1, kernel)
    return sharpened


def preprocess_for_ocr(image):
    """Return multiple OCR-ready variants so OCR can pick the best result."""
    cv2, _np = _require_cv2_numpy()
    candidates = [
        {"name": "original", "image": image},
        {"name": "basic", "image": preprocess_basic(image)},
        {"name": "contrast", "image": preprocess_contrast(image)},
        {"name": "threshold", "image": preprocess_threshold(image)},
        {"name": "sharpen", "image": preprocess_sharpen(image)},
    ]

    normalized_candidates = []
    for candidate in candidates:
        candidate_image = candidate["image"]
        if len(candidate_image.shape) == 2:
            candidate_image = cv2.cvtColor(candidate_image, cv2.COLOR_GRAY2BGR)
        normalized_candidates.append(
            {"name": candidate["name"], "image": candidate_image}
        )
    return normalized_candidates

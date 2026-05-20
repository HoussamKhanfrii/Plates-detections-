from config import Config
from services.preprocessing_service import preprocess_for_ocr
from services.validation_service import clean_plate_text, score_plate_candidate


class OCRService:
    def __init__(self):
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
            except ImportError as exc:
                raise RuntimeError(
                    "EasyOCR is not installed. Install dependencies with: "
                    "pip install -r requirements.txt"
                ) from exc

            self._reader = easyocr.Reader(
                Config.OCR_LANGUAGES,
                gpu=Config.OCR_USE_GPU,
                verbose=False,
            )
        return self._reader

    def read_text(self, image):
        reader = self._get_reader()
        results = reader.readtext(image, detail=1, paragraph=False)

        if not results:
            return {
                "raw_text": "",
                "ocr_confidence": 0.0,
            }

        text_parts = []
        confidences = []
        for _bbox, text, confidence in results:
            if text and str(text).strip():
                text_parts.append(str(text).strip())
                confidences.append(float(confidence))

        raw_text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "raw_text": raw_text,
            "ocr_confidence": round(avg_confidence, 4),
        }

    def extract_best_text(self, plate_image, country_profile="generic"):
        best = {
            "raw_text": "",
            "cleaned_text": "",
            "ocr_confidence": 0.0,
            "is_valid": False,
            "preprocessing": "none",
            "score": 0.0,
        }

        for candidate in preprocess_for_ocr(plate_image):
            ocr_result = self.read_text(candidate["image"])
            validation = clean_plate_text(
                ocr_result["raw_text"],
                country_profile=country_profile,
                apply_fixes=True,
            )
            score = score_plate_candidate(
                validation["cleaned_plate"],
                ocr_result["ocr_confidence"],
                validation["is_valid"],
            )

            if score > best["score"]:
                best = {
                    "raw_text": ocr_result["raw_text"],
                    "cleaned_text": validation["cleaned_plate"],
                    "ocr_confidence": ocr_result["ocr_confidence"],
                    "is_valid": validation["is_valid"],
                    "preprocessing": candidate["name"],
                    "score": round(score, 4),
                }

        return best


ocr_service = OCRService()

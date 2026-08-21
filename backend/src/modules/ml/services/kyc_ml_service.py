"""``KycMlService`` -- Phase 9. OCR, liveness, face match for KYC auto-screening.

Integration point: Phase 2's ``KycService`` calls these methods during
``SUBMITTED → AUTO_SCREENING`` transition. Each method logs to ``MlPrediction``
before returning.

Current implementation uses open-source alternatives (Tesseract OCR, OpenCV
face detection) for demo purposes. Production deployment should replace with
AWS Rekognition or similar managed service for better accuracy + compliance.
"""

from __future__ import annotations

import io
from typing import Any

import cv2
import numpy as np
import pytesseract
from austial.common import Injectable
from austial.orm import InjectRepository, Repository

from src.modules.ml.entities.ml_prediction import MlPrediction


@Injectable()
class KycMlService:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
    ):
        self.ml_prediction_repo = ml_prediction_repo

    async def extract_kyc_fields(self, document_bytes: bytes, document_type: str) -> dict[str, Any]:
        """OCR extraction from identity document.

        Args:
            document_bytes: Raw image bytes (JPEG/PNG)
            document_type: "passport" | "drivers_license" | "national_id"

        Returns:
            Structured dict with extracted fields: name, date_of_birth, id_number, etc.
        """
        try:
            img_array = np.frombuffer(document_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            ocr_text = pytesseract.image_to_string(gray)

            extracted_fields = {
                "raw_text": ocr_text,
                "name": self._extract_name(ocr_text),
                "date_of_birth": self._extract_dob(ocr_text),
                "id_number": self._extract_id_number(ocr_text, document_type),
                "document_type": document_type,
            }

            confidence = self._calculate_extraction_confidence(extracted_fields)

            await self._log_prediction(
                model_name="kyc_ocr",
                model_version="tesseract_v5.3",
                input_features={"document_type": document_type, "image_size_bytes": len(document_bytes)},
                prediction_output=extracted_fields,
                confidence_score=confidence,
            )

            return extracted_fields

        except Exception as e:
            await self._log_prediction(
                model_name="kyc_ocr",
                model_version="tesseract_v5.3",
                input_features={"document_type": document_type, "image_size_bytes": len(document_bytes)},
                prediction_output={"error": str(e)},
                confidence_score=0.0,
            )
            raise

    async def verify_liveness(self, video_bytes: bytes) -> dict[str, Any]:
        """Liveness detection from selfie video.

        Args:
            video_bytes: Raw video bytes (MP4/MOV)

        Returns:
            Dict with liveness_passed (bool), confidence_score (float), analysis details
        """
        try:
            video_path = f"/tmp/liveness_{id(video_bytes)}.mp4"
            with open(video_path, "wb") as f:
                f.write(video_bytes)

            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            face_detected_count = 0

            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

                if len(faces) > 0:
                    face_detected_count += 1

            cap.release()

            liveness_passed = face_detected_count > frame_count * 0.5
            confidence = face_detected_count / frame_count if frame_count > 0 else 0.0

            result = {
                "liveness_passed": liveness_passed,
                "confidence_score": confidence,
                "frame_count": frame_count,
                "face_detected_count": face_detected_count,
            }

            await self._log_prediction(
                model_name="liveness_detection",
                model_version="opencv_haarcascade_v1",
                input_features={"video_size_bytes": len(video_bytes)},
                prediction_output=result,
                confidence_score=confidence,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="liveness_detection",
                model_version="opencv_haarcascade_v1",
                input_features={"video_size_bytes": len(video_bytes)},
                prediction_output={"error": str(e)},
                confidence_score=0.0,
            )
            raise

    async def match_face(self, selfie_bytes: bytes, id_photo_bytes: bytes) -> dict[str, Any]:
        """Face matching between selfie and ID photo.

        Args:
            selfie_bytes: Raw image bytes from live selfie
            id_photo_bytes: Raw image bytes from identity document

        Returns:
            Dict with match_passed (bool), similarity_score (float 0-1)
        """
        try:
            selfie_img = self._bytes_to_image(selfie_bytes)
            id_img = self._bytes_to_image(id_photo_bytes)

            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

            selfie_faces = face_cascade.detectMultiScale(selfie_img, scaleFactor=1.1, minNeighbors=5)
            id_faces = face_cascade.detectMultiScale(id_img, scaleFactor=1.1, minNeighbors=5)

            if len(selfie_faces) == 0 or len(id_faces) == 0:
                similarity_score = 0.0
                match_passed = False
            else:
                similarity_score = self._calculate_similarity(selfie_img, id_img, selfie_faces[0], id_faces[0])
                match_passed = similarity_score > 0.6

            result = {
                "match_passed": match_passed,
                "similarity_score": similarity_score,
                "selfie_faces_detected": len(selfie_faces),
                "id_faces_detected": len(id_faces),
            }

            await self._log_prediction(
                model_name="face_match",
                model_version="opencv_orb_v1",
                input_features={
                    "selfie_size_bytes": len(selfie_bytes),
                    "id_photo_size_bytes": len(id_photo_bytes),
                },
                prediction_output=result,
                confidence_score=similarity_score,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="face_match",
                model_version="opencv_orb_v1",
                input_features={
                    "selfie_size_bytes": len(selfie_bytes),
                    "id_photo_size_bytes": len(id_photo_bytes),
                },
                prediction_output={"error": str(e)},
                confidence_score=0.0,
            )
            raise

    async def _log_prediction(
        self,
        model_name: str,
        model_version: str,
        input_features: dict[str, Any],
        prediction_output: dict[str, Any],
        confidence_score: float | None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        """Internal helper: log every prediction to MlPrediction table."""
        prediction = MlPrediction()
        prediction.model_name = model_name
        prediction.model_version = model_version
        prediction.input_features = input_features
        prediction.prediction_output = prediction_output
        prediction.confidence_score = confidence_score
        prediction.entity_type = entity_type
        prediction.entity_id = entity_id

        await self.ml_prediction_repo.save(prediction)

    def _bytes_to_image(self, image_bytes: bytes) -> np.ndarray:
        """Convert bytes to OpenCV image."""
        img_array = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

    def _extract_name(self, ocr_text: str) -> str | None:
        """Simple heuristic: look for lines with capitalized words."""
        lines = ocr_text.split("\n")
        for line in lines:
            if line.isupper() and len(line.split()) >= 2:
                return line.strip()
        return None

    def _extract_dob(self, ocr_text: str) -> str | None:
        """Look for date patterns in OCR text."""
        import re

        date_pattern = r"\b\d{2}[-/]\d{2}[-/]\d{4}\b"
        match = re.search(date_pattern, ocr_text)
        return match.group(0) if match else None

    def _extract_id_number(self, ocr_text: str, document_type: str) -> str | None:
        """Look for ID number patterns."""
        import re

        if document_type == "passport":
            pattern = r"\b[A-Z]\d{8}\b"
        else:
            pattern = r"\b\d{8,12}\b"

        match = re.search(pattern, ocr_text)
        return match.group(0) if match else None

    def _calculate_extraction_confidence(self, fields: dict[str, Any]) -> float:
        """Simple confidence: fraction of non-null extracted fields."""
        total_fields = 3
        extracted = sum(1 for k in ["name", "date_of_birth", "id_number"] if fields.get(k) is not None)
        return extracted / total_fields

    def _calculate_similarity(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        face1: tuple[int, int, int, int],
        face2: tuple[int, int, int, int],
    ) -> float:
        """Simple similarity using ORB feature matching."""
        x1, y1, w1, h1 = face1
        x2, y2, w2, h2 = face2

        face1_crop = img1[y1 : y1 + h1, x1 : x1 + w1]
        face2_crop = img2[y2 : y2 + h2, x2 : x2 + w2]

        orb = cv2.ORB_create()
        kp1, des1 = orb.detectAndCompute(face1_crop, None)
        kp2, des2 = orb.detectAndCompute(face2_crop, None)

        if des1 is None or des2 is None:
            return 0.0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        return min(len(matches) / 100, 1.0)

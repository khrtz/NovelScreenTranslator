import pytesseract
from PIL import ImageGrab

from services.ocr_service import OCRService


class PytesseractOCRService(OCRService):
    def preprocess_image(self, image):
        return image

    def extract_text_from_image(self, image):
        text = pytesseract.image_to_string(image, config=r'--oem 3 --psm 6 -l eng')
        return text

    def postprocess_text(self, text):
        processed_text = text.strip().replace("\n", " ")
        return processed_text
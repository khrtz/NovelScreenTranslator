from abc import ABC, abstractmethod
from typing import Tuple
from PIL import ImageGrab

class OCRService(ABC):
    @abstractmethod
    def preprocess_image(self, image):
        pass

    @abstractmethod
    def extract_text_from_image(self, image):
        pass

    @abstractmethod
    def postprocess_text(self, text):
        pass

    def get_text_from_region(self, region) -> Tuple[str, bool]:
        x1, y1, x2, y2 = region
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        preprocessed_image = self.preprocess_image(screenshot)
        text = self.extract_text_from_image(preprocessed_image)
        processed_text = self.postprocess_text(text)
        success = bool(processed_text)
        return processed_text, success
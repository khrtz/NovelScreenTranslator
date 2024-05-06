import json
import os
from models.settings import Settings

class SettingsController:
    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings_dict = json.load(f)
                return Settings.from_dict(settings_dict)
        else:
            return Settings()

    def save_settings(self, settings):
        with open(self.settings_file, "w") as f:
            settings_dict = settings.to_dict()
            json.dump(settings_dict, f)
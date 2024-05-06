import json

class Settings:
    def __init__(self, regions=None, auto_translate=None, interval=1):
        if regions is None:
            regions = [None, None, None]
        if auto_translate is None:
            auto_translate = [False, False, False]
        self.regions = regions
        self.auto_translate = auto_translate
        self.interval = interval

    @classmethod
    def from_dict(cls, settings_dict):
        regions = settings_dict.get("regions", [None, None, None])
        auto_translate = settings_dict.get("auto_translate", [False, False, False])
        interval = settings_dict.get("interval", 1)
        return cls(regions, auto_translate, interval)

    def to_dict(self):
        return {
            "regions": self.regions,
            "auto_translate": self.auto_translate,
            "interval": self.interval
        }
import re
from emoji import emojize
import requests

import config


def translate_text(text, target_lang="JA", context_before="", context_after=""):
    if not text.strip():
        return text

    text = re.sub(r'@|®|©|¥|™', emojize(":two_hearts:", language="alias", variant="emoji_type"), text)

    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": config.DEEPL_API_KEY,
        "text": context_before + text + context_after,
        "target_lang": target_lang,
        "split_sentences": "1",
        "formality": "prefer_more"
    }
    response = requests.post(url, data=params)
    if response.status_code == 200:
        translations = response.json()['translations']
        translated_sentences = [t['text'] for t in translations]
        translated_text = "".join(translated_sentences)

        # 翻訳後のテキストで記号を置換
        translated_text = re.sub(r'@|®|©|¥', emojize(":pink heart:", language="alias", variant="emoji_type"), translated_text)

        return translated_text
    else:
        print("Failed to translate:", response.text)
        return "Translation failed."

from pathlib import Path
import json


def load_localization(locales_path="/Users/denysmarkovych/Documents/Codes/SearchAnime_TelegramBot/locales"):
    localizations = {}
    path = Path(locales_path)
    try:
        for file in path.glob('*.json'):
            language_code = file.stem
            with file.open('r', encoding='utf-8') as f:
                localizations[language_code] = json.load(f)
    except Exception as e:
        print(f"Failed to load localizations: {e}")
    return localizations
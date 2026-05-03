import re
from functools import lru_cache

from ..config import OFFLINE_ONLY, TRANSLATION_MODELS


class Translator:
    def translate(self, text: str, source_lang: str, target_lang: str, context: list[str] | None = None) -> str:
        if source_lang == target_lang:
            return text
        context_prefix = build_context_prefix(context or [])
        try:
            return self._model_translate(context_prefix + text, source_lang, target_lang)
        except Exception:
            return dictionary_fallback(text, source_lang, target_lang)

    def _model_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        from transformers import MarianMTModel, MarianTokenizer

        model_name = TRANSLATION_MODELS.get((source_lang, target_lang))
        if not model_name:
            raise RuntimeError("No configured model for language pair")
        tokenizer, model = load_model(model_name)
        batch = tokenizer([text], return_tensors="pt", truncation=True, max_length=512)
        generated = model.generate(**batch, max_new_tokens=160)
        return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]


@lru_cache(maxsize=4)
def load_model(model_name: str):
    from transformers import MarianMTModel, MarianTokenizer

    kwargs = {"local_files_only": OFFLINE_ONLY}
    return MarianTokenizer.from_pretrained(model_name, **kwargs), MarianMTModel.from_pretrained(model_name, **kwargs)


def build_context_prefix(context: list[str]) -> str:
    if not context:
        return ""
    clipped = " ".join(context)[-700:]
    return f"Context: {clipped}\nText: "


def dictionary_fallback(text: str, source_lang: str, target_lang: str) -> str:
    if (source_lang, target_lang) == ("en", "ur"):
        return translate_by_phrasebook(text, EN_UR_PHRASES, EN_UR_WORDS)
    if (source_lang, target_lang) == ("ur", "en"):
        return translate_by_phrasebook(text, UR_EN_PHRASES, UR_EN_WORDS)
    return text


def translate_by_phrasebook(text: str, phrases: dict[str, str], words: dict[str, str]) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    lowered = normalized.lower()
    for source in sorted(phrases, key=len, reverse=True):
        if source in lowered:
            pattern = re.compile(re.escape(source), flags=re.IGNORECASE)
            normalized = pattern.sub(phrases[source], normalized)
            lowered = normalized.lower()

    tokens = re.findall(r"[\w\u0600-\u06ff']+|[^\w\u0600-\u06ff\s]", normalized, flags=re.UNICODE)
    translated = [words.get(token.lower(), token) for token in tokens]
    return rebuild_sentence(translated) or text


def rebuild_sentence(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = re.sub(r"\s+([?.!,;:])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    return text.strip()


EN_UR_PHRASES = {
    "hello": "\u0627\u0644\u0633\u0644\u0627\u0645 \u0639\u0644\u06cc\u06a9\u0645",
    "hi": "\u0627\u0644\u0633\u0644\u0627\u0645 \u0639\u0644\u06cc\u06a9\u0645",
    "how are you": "\u0622\u067e \u06a9\u06cc\u0633\u06d2 \u06c1\u06cc\u06ba",
    "i am fine": "\u0645\u06cc\u06ba \u0679\u06be\u06cc\u06a9 \u06c1\u0648\u06ba",
    "thank you": "\u0634\u06a9\u0631\u06cc\u06c1",
    "good morning": "\u0635\u0628\u062d \u0628\u062e\u06cc\u0631",
    "good night": "\u0634\u0628 \u0628\u062e\u06cc\u0631",
    "what is your name": "\u0622\u067e \u06a9\u0627 \u0646\u0627\u0645 \u06a9\u06cc\u0627 \u06c1\u06d2",
    "my name is": "\u0645\u06cc\u0631\u0627 \u0646\u0627\u0645",
    "i need help": "\u0645\u062c\u06be\u06d2 \u0645\u062f\u062f \u06a9\u06cc \u0636\u0631\u0648\u0631\u062a \u06c1\u06d2",
    "call a doctor": "\u0688\u0627\u06a9\u0679\u0631 \u06a9\u0648 \u0628\u0644\u0627\u0626\u06cc\u06ba",
    "call an ambulance": "\u0627\u06cc\u0645\u0628\u0648\u0644\u06cc\u0646\u0633 \u0628\u0644\u0627\u0626\u06cc\u06ba",
    "where is the hospital": "\u06c1\u0633\u067e\u062a\u0627\u0644 \u06a9\u06c1\u0627\u06ba \u06c1\u06d2",
    "i have pain": "\u0645\u062c\u06be\u06d2 \u062f\u0631\u062f \u06c1\u06d2",
    "i have fever": "\u0645\u062c\u06be\u06d2 \u0628\u062e\u0627\u0631 \u06c1\u06d2",
    "i have fever and pain": "\u0645\u062c\u06be\u06d2 \u0628\u062e\u0627\u0631 \u0627\u0648\u0631 \u062f\u0631\u062f \u06c1\u06d2",
    "i need medicine": "\u0645\u062c\u06be\u06d2 \u062f\u0648\u0627 \u06a9\u06cc \u0636\u0631\u0648\u0631\u062a \u06c1\u06d2",
    "i need medicine and water": "\u0645\u062c\u06be\u06d2 \u062f\u0648\u0627 \u0627\u0648\u0631 \u067e\u0627\u0646\u06cc \u0686\u0627\u06c1\u06cc\u06d2",
    "doctor i need medicine and water": "\u0688\u0627\u06a9\u0679\u0631\u060c \u0645\u062c\u06be\u06d2 \u062f\u0648\u0627 \u0627\u0648\u0631 \u067e\u0627\u0646\u06cc \u0686\u0627\u06c1\u06cc\u06d2",
    "i feel dizzy": "\u0645\u062c\u06be\u06d2 \u0686\u06a9\u0631 \u0622 \u0631\u06c1\u06d2 \u06c1\u06cc\u06ba",
    "i cannot breathe": "\u0645\u062c\u06be\u06d2 \u0633\u0627\u0646\u0633 \u0646\u06c1\u06cc\u06ba \u0622 \u0631\u06c1\u06cc",
    "please speak slowly": "\u0628\u0631\u0627\u06c1 \u06a9\u0631\u0645 \u0622\u06c1\u0633\u062a\u06c1 \u0628\u0648\u0644\u06cc\u06ba",
    "i do not understand": "\u0645\u06cc\u06ba \u0633\u0645\u062c\u06be\u0627 \u0646\u06c1\u06cc\u06ba",
}

EN_UR_WORDS = {
    "i": "\u0645\u06cc\u06ba",
    "you": "\u0622\u067e",
    "we": "\u06c1\u0645",
    "they": "\u0648\u06c1",
    "he": "\u0648\u06c1",
    "she": "\u0648\u06c1",
    "my": "\u0645\u06cc\u0631\u0627",
    "your": "\u0622\u067e \u06a9\u0627",
    "am": "\u06c1\u0648\u06ba",
    "is": "\u06c1\u06d2",
    "are": "\u06c1\u06cc\u06ba",
    "have": "\u06c1\u06d2",
    "need": "\u0636\u0631\u0648\u0631\u062a",
    "want": "\u0686\u0627\u06c1\u062a\u0627",
    "and": "\u0627\u0648\u0631",
    "or": "\u06cc\u0627",
    "with": "\u06a9\u06d2 \u0633\u0627\u062a\u06be",
    "to": "\u06a9\u0648",
    "in": "\u0645\u06cc\u06ba",
    "for": "\u06a9\u06d2 \u0644\u06cc\u06d2",
    "help": "\u0645\u062f\u062f",
    "doctor": "\u0688\u0627\u06a9\u0679\u0631",
    "hospital": "\u06c1\u0633\u067e\u062a\u0627\u0644",
    "emergency": "\u0627\u06cc\u0645\u0631\u062c\u0646\u0633\u06cc",
    "ambulance": "\u0627\u06cc\u0645\u0628\u0648\u0644\u06cc\u0646\u0633",
    "pain": "\u062f\u0631\u062f",
    "fever": "\u0628\u062e\u0627\u0631",
    "medicine": "\u062f\u0648\u0627",
    "water": "\u067e\u0627\u0646\u06cc",
    "food": "\u06a9\u06be\u0627\u0646\u0627",
    "home": "\u06af\u06be\u0631",
    "where": "\u06a9\u06c1\u0627\u06ba",
    "what": "\u06a9\u06cc\u0627",
    "when": "\u06a9\u0628",
    "why": "\u06a9\u06cc\u0648\u06ba",
    "please": "\u0628\u0631\u0627\u06c1 \u06a9\u0631\u0645",
    "yes": "\u062c\u06cc \u06c1\u0627\u06ba",
    "no": "\u0646\u06c1\u06cc\u06ba",
    "now": "\u0627\u0628",
    "today": "\u0622\u062c",
    "tomorrow": "\u06a9\u0644",
    "good": "\u0627\u0686\u06be\u0627",
    "bad": "\u0628\u0631\u0627",
    "urgent": "\u0641\u0648\u0631\u06cc",
    "family": "\u062e\u0627\u0646\u062f\u0627\u0646",
    "friend": "\u062f\u0648\u0633\u062a",
    "name": "\u0646\u0627\u0645",
    "speak": "\u0628\u0648\u0644\u06cc\u06ba",
    "slowly": "\u0622\u06c1\u0633\u062a\u06c1",
}

UR_EN_PHRASES = {value: key for key, value in EN_UR_PHRASES.items()}
UR_EN_WORDS = {value: key for key, value in EN_UR_WORDS.items()}

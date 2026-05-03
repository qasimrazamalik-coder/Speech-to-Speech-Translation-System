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
    en_ur = {
        "hello": "السلام علیکم",
        "how are you": "آپ کیسے ہیں",
        "thank you": "شکریہ",
        "doctor": "ڈاکٹر",
        "hospital": "ہسپتال",
        "emergency": "ایمرجنسی",
        "pain": "درد",
        "medicine": "دوا",
    }
    ur_en = {value: key for key, value in en_ur.items()}
    table = en_ur if (source_lang, target_lang) == ("en", "ur") else ur_en
    lowered = text.lower()
    for source, translated in table.items():
        lowered = lowered.replace(source, translated)
    return lowered if lowered != text.lower() else f"[offline translation unavailable] {text}"

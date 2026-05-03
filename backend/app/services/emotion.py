def detect_emotion(text: str) -> str:
    value = text.lower()
    if "!" in text or any(word in value for word in ["great", "amazing", "زبردست", "خوش"]):
        return "excited"
    if any(word in value for word in ["sad", "pain", "hurt", "افسوس", "درد", "غم"]):
        return "sad"
    if "?" in text:
        return "curious"
    if any(word in value for word in ["urgent", "emergency", "فوری", "ایمرجنسی"]):
        return "urgent"
    return "neutral"

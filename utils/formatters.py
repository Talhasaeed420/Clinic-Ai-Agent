import logging

logger = logging.getLogger("utils.formatters")

def correct_number(number: str) -> str:
    """
    Normalize phone number formats:
    - Remove suffix after ';'
    - Convert local/US-style numbers to international format
    """
    if not number:
        return number

    number = number.split(";")[0].strip()

    if number.startswith("+1"):  # VAPI sending US prefix by mistake
        corrected = "+" + number[2:]
        logger.debug("Corrected US number", extra={"original": number, "corrected": corrected})
        return corrected
    elif number.startswith("0"):  # Local number
        corrected = "+" + number[1:]
        logger.debug("Corrected local number", extra={"original": number, "corrected": corrected})
        return corrected

    return number

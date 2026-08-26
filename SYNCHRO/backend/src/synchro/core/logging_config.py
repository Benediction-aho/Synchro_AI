import logging
import re
import sys

_BEARER_PATTERN = re.compile(r"(Bearer\s+)[\w.\-]+")
_PAT_PATTERN = re.compile(r"(pat_)[\w.\-]+")
_REDACTED = r"\1[REDACTED]"


class SecretScrubbingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        message = _BEARER_PATTERN.sub(_REDACTED, message)
        message = _PAT_PATTERN.sub(_REDACTED, message)
        return message


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        SecretScrubbingFormatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

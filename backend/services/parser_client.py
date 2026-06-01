import io
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests


logger = logging.getLogger(__name__)


class ParserClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "parser_error",
        status_code: int = 502,
        details: Any = None,
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details


@dataclass
class ParserClientConfig:
    base_url: str
    parse_path: str = "/api/parse"
    connect_timeout: float = 5.0
    read_timeout: float = 45.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.8


class ParserClient:
    def __init__(self, config: ParserClientConfig):
        self.config = config
        self.parse_url = f"{self.config.base_url.rstrip('/')}{self.config.parse_path}"

    def _safe_json(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            text = (response.text or "").strip()
            if not text:
                return {}
            try:
                return json.loads(text)
            except ValueError:
                return {"_raw": text[:2000]}

    def check_availability(self) -> bool:
        timeout = (self.config.connect_timeout, min(self.config.read_timeout, 6.0))
        try:
            response = requests.head(self.parse_url, timeout=timeout)
            if response.status_code < 500:
                return True
        except requests.RequestException as exc:
            logger.warning("Parser availability HEAD check failed: %s", exc)

        try:
            response = requests.options(self.parse_url, timeout=timeout)
            return response.status_code < 500
        except requests.RequestException as exc:
            logger.warning("Parser availability OPTIONS check failed: %s", exc)
            return False

    def parse_resume(
        self,
        *,
        filename: str,
        content_bytes: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        if not content_bytes:
            raise ParserClientError(
                "Uploaded file is empty.",
                code="empty_file",
                status_code=400,
            )

        timeout = (self.config.connect_timeout, self.config.read_timeout)
        attempts = max(1, int(self.config.max_retries) + 1)
        last_exc: Exception | None = None

        parser_variants = [
            {"file_field": "resume_file", "send_query": False},
            {"file_field": "file", "send_query": False},
            {"file_field": "resume", "send_query": False},
            {"file_field": "resume_file", "send_query": True},
            {"file_field": "file", "send_query": True},
            {"file_field": "resume", "send_query": True},
        ]

        for attempt in range(1, attempts + 1):
            try:
                last_400_payload = None
                response = None
                payload = {}

                for variant in parser_variants:
                    data = {
                        "section": "structured",
                        "response_mode": "builder",
                        # harmless aliases for parsers that use a different key
                        "mode": "builder",
                    }
                    files = {
                        variant["file_field"]: (
                            filename or "resume",
                            io.BytesIO(content_bytes),
                            content_type or "application/octet-stream",
                        )
                    }
                    params = data if variant["send_query"] else None

                    response = requests.post(
                        self.parse_url,
                        params=params,
                        data=data,
                        files=files,
                        timeout=timeout,
                    )
                    payload = self._safe_json(response)

                    if response.status_code < 400:
                        break

                    if response.status_code == 400:
                        last_400_payload = payload
                        logger.warning(
                            "Parser 400 for variant file_field=%s send_query=%s payload=%s",
                            variant["file_field"],
                            variant["send_query"],
                            payload,
                        )
                        continue

                    # For non-400 errors, stop variant loop and handle below.
                    break

                if response.status_code >= 500:
                    logger.error(
                        "Parser server error (%s): %s",
                        response.status_code,
                        payload,
                    )
                    raise ParserClientError(
                        "Parser service failed while processing the resume.",
                        code="parser_server_error",
                        status_code=502,
                        details=payload,
                    )

                if response.status_code >= 400:
                    logger.warning(
                        "Parser returned client error (%s): %s",
                        response.status_code,
                        payload,
                    )
                    raise ParserClientError(
                        "Parser rejected the uploaded resume.",
                        code="parser_request_error",
                        status_code=400,
                        details=last_400_payload or payload,
                    )

                if not isinstance(payload, dict):
                    logger.error("Parser response is not a JSON object: %r", payload)
                    raise ParserClientError(
                        "Parser returned an invalid response format.",
                        code="invalid_parser_response",
                        status_code=502,
                        details=payload,
                    )

                return payload
            except requests.Timeout as exc:
                last_exc = exc
                logger.error("Parser request timed out (attempt %s/%s).", attempt, attempts)
            except requests.RequestException as exc:
                last_exc = exc
                logger.error("Parser request failed (attempt %s/%s): %s", attempt, attempts, exc)
            except ParserClientError:
                raise

            if attempt < attempts:
                sleep_for = self.config.retry_backoff_seconds * attempt
                time.sleep(sleep_for)

        raise ParserClientError(
            "Parser service is unreachable or timed out.",
            code="parser_unavailable",
            status_code=503,
            details=str(last_exc) if last_exc else None,
        )

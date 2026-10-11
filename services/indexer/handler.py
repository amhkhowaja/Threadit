from __future__ import annotations

import os

from threadit_core.logging import configure_logging, get_logger
from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.services.stream_indexer import StreamIndexer

configure_logging(os.environ.get("THREADIT_LOG_LEVEL", "INFO"))
_log = get_logger("indexer")

_sign = os.environ.get("THREADIT_OPENSEARCH_SIGN", "false").lower() == "true"
_region = os.environ.get("THREADIT_AWS_REGION", "us-east-1")
_index = OpenSearchIndex(
    os.environ["THREADIT_OPENSEARCH_ENDPOINT"], sign=_sign, region=_region
)
_indexer = StreamIndexer(_index)


def handler(event: dict, _context=None) -> dict:
    records = event.get("Records", [])
    processed = _indexer.handle_records(records)
    _log.info("indexed_stream_batch", received=len(records), processed=processed)
    return {"processed": processed}

from dataclasses import replace
import json

import pytest

from rl.common.contracts import task_from_row
from rl.contract_algos.probe import request_body, validate_response


def test_probe_request_ignores_private_label_reference_and_metadata(core_row):
    task = task_from_row(core_row)
    args = {"model": "dedicated", "max_tokens": 99, "temperature": 1.0}
    before = request_body(task, **args)
    changed = replace(
        task, label="SECRET_LABEL",
        reference=replace(task.reference, target_image_bytes=b"SECRET_REFERENCE"),
        sampler=replace(task.sampler, opaque_id="SECRET_ID", level="SECRET_LEVEL"),
    )
    assert request_body(changed, **args) == before
    assert "SECRET" not in json.dumps(before)
    assert before["messages"][0]["content"][0]["type"] == "image_url"


def test_reject_model_remap_and_keep_truncation_visible():
    response = {"model": "actual", "choices": [
        {"message": {"content": "partial code"}, "finish_reason": "length"}
    ]}
    with pytest.raises(ValueError, match="unexpected model"):
        validate_response(response, "different")
    assert validate_response(response, "actual") == ("partial code", "length")


def test_exhausted_reasoning_budget_is_retained_as_empty_truncated_attempt():
    response = {"model": "actual", "choices": [
        {"message": {"content": None, "reasoning": "unfinished"}, "finish_reason": "length"}
    ]}
    assert validate_response(response, "actual") == ("", "length")

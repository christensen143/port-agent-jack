import json
import os
from copy import deepcopy
from signal import SIGINT
from typing import Any, Callable, Generator, Optional

import port_client
import pytest
import requests
from _pytest.monkeypatch import MonkeyPatch
from confluent_kafka import Consumer as _Consumer
from core.config import Mapping
from pydantic import parse_obj_as

from app.utils import sign_sha_256


@pytest.fixture
def mock_requests(monkeypatch: MonkeyPatch, request: Any) -> None:
    class MockResponse:
        status_code = request.param.get("status_code")
        text = "Invoker failed with status code: %d" % status_code

        def json(self) -> dict:
            return request.param.get("json")

        @property
        def ok(self) -> bool:
            return 200 <= self.status_code <= 299

        def raise_for_status(self) -> None:
            if 400 <= self.status_code <= 599:
                raise Exception(self.text)

    def mock_request(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse()

    monkeypatch.setattr(port_client, "get_port_api_headers", lambda *args: {})
    monkeypatch.setattr(requests, "request", mock_request)
    monkeypatch.setattr(requests, "get", mock_request)
    monkeypatch.setattr(requests, "post", mock_request)
    monkeypatch.setattr(requests, "delete", mock_request)
    monkeypatch.setattr(requests, "put", mock_request)


def terminate_consumer() -> None:
    os.kill(os.getpid(), SIGINT)


class Consumer(_Consumer):
    def __init__(self) -> None:
        pass

    def subscribe(
        self, topics: Any, on_assign: Any = None, *args: Any, **kwargs: Any
    ) -> None:
        pass

    def poll(self, timeout: Any = None) -> None:
        pass

    def commit(self, message: Any = None, *args: Any, **kwargs: Any) -> None:
        pass

    def close(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.fixture
def mock_kafka(monkeypatch: MonkeyPatch, request: Any) -> None:
    class MockKafkaMessage:
        def error(self) -> None:
            return None

        def topic(self, *args: Any, **kwargs: Any) -> str:
            return request.param[2]

        def partition(self, *args: Any, **kwargs: Any) -> int:
            return 0

        def offset(self, *args: Any, **kwargs: Any) -> int:
            return 0

        def value(self) -> bytes:
            return request.getfixturevalue(request.param[0])(request.param[1])

    def mock_subscribe(
        self: Any, topics: Any, on_assign: Any = None, *args: Any, **kwargs: Any
    ) -> None:
        pass

    def generate_kafka_messages() -> Generator[Optional[MockKafkaMessage], None, None]:
        yield MockKafkaMessage()
        while True:
            yield None

    kafka_messages_generator = generate_kafka_messages()

    def mock_poll(self: Any, timeout: Any = None) -> Optional[MockKafkaMessage]:
        return next(kafka_messages_generator)

    def mock_commit(self: Any, message: Any = None, *args: Any, **kwargs: Any) -> None:
        return None

    def mock_close(self: Any, *args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr(Consumer, "subscribe", mock_subscribe)
    monkeypatch.setattr(Consumer, "poll", mock_poll)
    monkeypatch.setattr(Consumer, "commit", mock_commit)
    monkeypatch.setattr(Consumer, "close", mock_close)
    result_fixture = request.getfixturevalue(request.param[0])
    return json.loads(result_fixture(request.param[1]).decode("utf-8"))


@pytest.fixture(scope="module")
def mock_webhook_change_log_message() -> Callable[[dict], bytes]:
    change_log_message = {
        "action": "Create",
        "resourceType": "run",
        "status": "TRIGGERED",
        "trigger": {
            "by": {"orgId": "test_org", "userId": "test_user"},
            "origin": "UI",
            "at": "2022-11-16T16:31:32.447Z",
        },
        "context": {
            "entity": None,
            "blueprint": "Service",
            "runId": "r_jE5FhDURh4Uen2Qr",
        },
        "diff": {
            "before": None,
            "after": {
                "id": "r_jE5FhDURh4Uen2Qr",
                "status": "IN_PROGRESS",
                "blueprint": {"identifier": "Service", "title": "Service"},
                "action": "Create",
                "endedAt": None,
                "source": "UI",
                "relatedEntityExists": False,
                "relatedBlueprintExists": True,
                "properties": {},
                "createdAt": "2022-11-16T16:31:32.447Z",
                "updatedAt": "2022-11-16T16:31:32.447Z",
                "createdBy": "test_user",
                "updatedBy": "test_user",
            },
        },
        "changelogDestination": {
            "type": "WEBHOOK",
            "agent": True,
            "url": "http://localhost:80/api/test",
        },
    }

    def get_change_log_message(invocation_method: Optional[dict]) -> bytes:
        # Deep copy to avoid mutating the original fixture data
        message_copy = deepcopy(change_log_message)
        if invocation_method is not None:
            # Merge the provided invocation_method with the existing one
            # to preserve default fields like "agent": True
            message_copy["changelogDestination"].update(invocation_method)
        return json.dumps(
            message_copy, separators=(",", ":"), ensure_ascii=False
        ).encode()

    return get_change_log_message


@pytest.fixture(scope="module")
def webhook_run_payload() -> dict:
    return {
        "action": "Create",
        "resourceType": "run",
        "status": "TRIGGERED",
        "trigger": {
            "by": {"orgId": "test_org", "userId": "test_user"},
            "origin": "UI",
            "at": "2022-11-16T16:31:32.447Z",
        },
        "context": {
            "entity": None,
            "blueprint": "Service",
            "runId": "r_jE5FhDURh4Uen2Qr",
        },
        "payload": {
            "entity": None,
            "action": {
                "id": "action_34aweFQtayw7SCVb",
                "identifier": "Create",
                "title": "Create",
                "icon": "DefaultBlueprint",
                "userInputs": {
                    "properties": {
                        "foo": {"type": "string", "description": "Description"},
                        "bar": {"type": "number", "description": "Description"},
                    },
                    "required": [],
                },
                "invocationMethod": {
                    "type": "WEBHOOK",
                    "agent": True,
                    "url": "http://localhost:80/api/test",
                },
                "trigger": "CREATE",
                "description": "",
                "blueprint": "Service",
                "createdAt": "2022-11-15T09:58:52.863Z",
                "createdBy": "test_user",
                "updatedAt": "2022-11-15T09:58:52.863Z",
                "updatedBy": "test_user",
            },
            "properties": {},
        },
        "headers": {
            "X-Port-Signature": "v1,uuBMfcio3oscejO5bOtL97K1AmiZjxDvou7sChjMNeE=",
            # the real signature of this payload using the secret
            # key test and the hardcoded timestamp mock
            "X-Port-Timestamp": 1713277889,
        },
    }


@pytest.fixture(scope="module")
def mock_webhook_run_message(webhook_run_payload: dict) -> Callable[[dict], bytes]:
    def get_run_message(invocation_method: Optional[dict]) -> bytes:
        # Deep copy to avoid mutating the original fixture data
        payload_copy = deepcopy(webhook_run_payload)
        if invocation_method is not None:
            # Merge the provided invocation_method with the existing one
            # to preserve default fields like "agent": True
            payload_copy["payload"]["action"]["invocationMethod"].update(
                invocation_method
            )
            # When mutating the payload, we need to ensure that the
            # headers are also updated
            timestamp = payload_copy["headers"]["X-Port-Timestamp"]
            payload_copy["headers"] = {}
            payload_copy["headers"]["X-Port-Signature"] = sign_sha_256(
                json.dumps(payload_copy, separators=(",", ":"), ensure_ascii=False),
                "test",
                str(timestamp),
            )
            payload_copy["headers"]["X-Port-Timestamp"] = timestamp
        return json.dumps(
            payload_copy, separators=(",", ":"), ensure_ascii=False
        ).encode()

    return get_run_message


@pytest.fixture()
def mock_control_the_payload_config(monkeypatch: MonkeyPatch) -> list[dict[str, Any]]:
    mapping = [
        {
            "enabled": ".payload.non-existing-field",
            "body": ".",
            "headers": {
                "MY-HEADER": ".resourceType",
            },
            "query": {},
        },
        {
            "enabled": True,
            "body": ".",
            "headers": {
                "MY-HEADER": ".resourceType",
            },
            "query": {},
            "report": {"link": '"http://test.com"'},
        },
    ]
    control_the_payload_config = parse_obj_as(list[Mapping], mapping)

    monkeypatch.setattr(
        "invokers.webhook_invoker.control_the_payload_config",
        control_the_payload_config,
    )

    return control_the_payload_config


@pytest.fixture
def mock_timestamp(monkeypatch: MonkeyPatch, request: Any) -> None:
    def mock_timestamp() -> int:
        return 1713277889

    monkeypatch.setattr("time.time", mock_timestamp)

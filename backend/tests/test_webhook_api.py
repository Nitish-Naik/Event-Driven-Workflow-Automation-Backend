def test_receive_sentry_event(api_client):
    payload = {
        "event_id": "sentry-event-1",
        "event_type": "issue.created",
        "issue_id": "123",
        "message": "Database connection failed",
    }

    response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    assert response.status_code == 202

    body = response.json()

    assert body["status"] == "accepted"
    assert body["event_id"]


def test_duplicate_sentry_event_is_accepted(
    api_client,
):
    payload = {
        "event_id": "duplicate-event",
        "event_type": "issue.created",
        "issue_id": "123",
    }

    first_response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    second_response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202

    assert second_response.json()["status"] == "duplicate"
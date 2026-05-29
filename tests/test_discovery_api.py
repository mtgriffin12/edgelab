from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_api_lists_discovery_ideas() -> None:
    response = client.get("/discovery/ideas")

    assert response.status_code == 200
    ideas = response.json()
    assert len(ideas) == 9
    assert any(idea["discovery_id"] == "relative-strength-pullback" for idea in ideas)


def test_api_reads_one_discovery_idea() -> None:
    response = client.get("/discovery/ideas/broad-fear-company-calm-pullback")

    assert response.status_code == 200
    idea = response.json()
    assert idea["title"] == "Broad Fear / Company Calm Pullback"
    assert idea["baseline_to_beat"]["baseline_id"] == "relative-strength-pullback"


def test_api_missing_discovery_idea_returns_404() -> None:
    response = client.get("/discovery/ideas/not-real")

    assert response.status_code == 404


def test_api_reads_discovery_card_as_markdown() -> None:
    response = client.get("/discovery/ideas/social-euphoria-without-price-confirmation/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## What This Idea Is" in response.text


def test_api_reads_discovery_lane_counts() -> None:
    response = client.get("/discovery/lanes")

    assert response.status_code == 200
    assert response.json() == {
        "known_strategy_library": 4,
        "edge_innovation_lab": 5,
    }


def test_api_reads_discovery_genealogy() -> None:
    response = client.get("/discovery/genealogy/broad-fear-company-calm-pullback")

    assert response.status_code == 200
    genealogy = response.json()
    assert genealogy["found"] is True
    assert [node["discovery_id"] for node in genealogy["lineage"]] == [
        "relative-strength-pullback",
        "broad-fear-company-calm-pullback",
    ]


def test_api_missing_genealogy_returns_404() -> None:
    response = client.get("/discovery/genealogy/not-real")

    assert response.status_code == 404


def test_api_reads_discovery_ledger() -> None:
    response = client.get("/discovery/ledger")

    assert response.status_code == 200
    entries = response.json()
    assert entries
    assert all(entry["outcome"] == "not_run" for entry in entries)

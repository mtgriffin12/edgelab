"""In-memory genealogy helpers for discovery ideas."""

from edgelab.discovery.schema import StrategyDiscoveryRecord, StrategyGenealogyNode


class StrategyGenealogy:
    """Read-only parent/child helper for discovery records."""

    def __init__(self, records: list[StrategyDiscoveryRecord]) -> None:
        self._records = {record.discovery_id: record for record in records}

    def root_ideas(self) -> list[StrategyDiscoveryRecord]:
        """Return records without parents."""

        return [record for record in self._records.values() if record.parent_discovery_id is None]

    def child_ideas(self, discovery_id: str) -> list[StrategyDiscoveryRecord]:
        """Return direct child records for a discovery ID."""

        return [
            record
            for record in self._records.values()
            if record.parent_discovery_id == discovery_id
        ]

    def trace_lineage(self, discovery_id: str) -> list[StrategyGenealogyNode]:
        """Trace root-to-record lineage."""

        lineage: list[StrategyGenealogyNode] = []
        current = self._records.get(discovery_id)
        while current is not None:
            lineage.append(self._to_node(current))
            parent_id = current.parent_discovery_id
            current = self._records.get(parent_id) if parent_id is not None else None
        return list(reversed(lineage))

    def describe_difference_from_parent(self, discovery_id: str) -> str:
        """Explain how a record differs from its parent."""

        record = self._records.get(discovery_id)
        if record is None:
            return "Discovery idea not found."
        if record.parent_discovery_id is None:
            return "This is a root idea."
        return record.adaptation_notes or "This child idea changes the parent in a documented way."

    def genealogy_for(self, discovery_id: str) -> dict[str, object]:
        """Return JSON-friendly genealogy details."""

        record = self._records.get(discovery_id)
        if record is None:
            return {"discovery_id": discovery_id, "found": False, "lineage": [], "children": []}
        return {
            "discovery_id": discovery_id,
            "found": True,
            "provenance": record.provenance.value,
            "plain_english_difference": self.describe_difference_from_parent(discovery_id),
            "lineage": [node.model_dump(mode="json") for node in self.trace_lineage(discovery_id)],
            "children": [
                self._to_node(child).model_dump(mode="json")
                for child in self.child_ideas(discovery_id)
            ],
        }

    def _to_node(self, record: StrategyDiscoveryRecord) -> StrategyGenealogyNode:
        return StrategyGenealogyNode(
            discovery_id=record.discovery_id,
            title=record.title,
            provenance=record.provenance,
            parent_discovery_id=record.parent_discovery_id,
            plain_english_difference=self.describe_difference_from_parent(record.discovery_id),
        )

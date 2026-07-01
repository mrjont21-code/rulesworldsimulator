import json
import hashlib
import logging
from config import settings

logger = logging.getLogger(__name__)


class JsonBuilder:

    def __init__(self):
        self.min_quality = settings.MIN_QUALITY_SCORE
        self.max_rules = settings.MAX_FINAL_RULES

    def build(self, extracted_rules):
        valid_rules = [
            r for r in extracted_rules
            if r and r.get("quality_score", 0) >= self.min_quality
        ]

        logger.info(
            f"Filtering: {len(extracted_rules)} total -> "
            f"{len(valid_rules)} passed quality threshold"
        )

        deduplicated = self._deduplicate(valid_rules)

        categorized = self._categorize(deduplicated)

        final = {
            "metadata": {
                "total_rules": len(deduplicated),
                "min_quality_score": self.min_quality,
                "sources_used": list(set(
                    r.get("source", "unknown") for r in deduplicated
                )),
            },
            "rules": categorized,
        }

        return final

    def _deduplicate(self, rules):
        seen_hashes = set()
        unique = []

        for rule in rules:
            rule_type = rule.get("rule_type", "unknown")
            params = rule.get("parameters", {})
            body = params.get("body_composition", "")
            breathes = str(params.get("breathes", []))

            hash_input = f"{rule_type}_{body}_{breathes}"
            rule_hash = hashlib.md5(hash_input.encode()).hexdigest()

            if rule_hash not in seen_hashes:
                seen_hashes.add(rule_hash)
                rule["rule_id"] = f"rule_{rule_hash[:8]}"
                unique.append(rule)

        unique.sort(key=lambda r: r.get("quality_score", 0), reverse=True)

        return unique[:self.max_rules]

    def _categorize(self, rules):
        categories = {
            "body_composition_rules": [],
            "respiration_rules": [],
            "habitat_rules": [],
            "energy_rules": [],
            "weakness_rules": [],
        }

        for rule in rules:
            params = rule.get("parameters", {})

            if params.get("body_composition"):
                categories["body_composition_rules"].append(rule)

            if params.get("breathes"):
                categories["respiration_rules"].append(rule)

            if params.get("habitat") or params.get("temperature_range"):
                categories["habitat_rules"].append(rule)

            if params.get("energy_source"):
                categories["energy_rules"].append(rule)

            if params.get("weaknesses"):
                categories["weakness_rules"].append(rule)

        return categories

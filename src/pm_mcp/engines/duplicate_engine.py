from __future__ import annotations

import re
from typing import Any


class DuplicateEngine:
    @staticmethod
    def normalize(value: str | None) -> str:
        if not value:
            return ""
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return " ".join(value.split())

    @staticmethod
    def detect(project_id: int, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        project_tasks = [task for task in tasks if task.get("project_id") == project_id]
        matches = []
        for i, left in enumerate(project_tasks):
            for right in project_tasks[i + 1:]:
                left_text = f"{left.get('title', '')} {left.get('description', '')}"
                right_text = f"{right.get('title', '')} {right.get('description', '')}"
                left_norm = DuplicateEngine.normalize(left_text)
                right_norm = DuplicateEngine.normalize(right_text)
                if not left_norm or not right_norm:
                    continue
                overlap = len(set(left_norm.split()) & set(right_norm.split()))
                total = max(len(set(left_norm.split())), len(set(right_norm.split())))
                similarity = round((overlap / total) * 100, 2) if total else 0.0
                if similarity >= 50:
                    matches.append({
                        "task_a": left["id"],
                        "task_b": right["id"],
                        "similarity": similarity,
                        "explanation": "The tasks share a meaningful set of key terms and likely describe the same work.",
                        "recommendation": "Review whether these tasks should be merged or clarified to reduce duplication.",
                    })
        return matches

from __future__ import annotations

from collections import defaultdict
from typing import Any


class DependencyEngine:
    @staticmethod
    def analyze(project_id: int, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        project_tasks = [task for task in tasks if task.get("project_id") == project_id]
        task_by_id = {task["id"]: task for task in project_tasks}
        blocked = []
        chains = []
        for task in project_tasks:
            deps = task.get("dependencies") or []
            if deps:
                missing = [dep for dep in deps if dep not in task_by_id]
                if missing:
                    blocked.append({"task_id": task["id"], "title": task.get("title"), "missing_dependencies": missing})
                else:
                    if any(task_by_id[dep].get("status") != "DONE" for dep in deps):
                        blocked.append({"task_id": task["id"], "title": task.get("title"), "blocking_dependencies": deps})
            if task.get("status") == "BLOCKED":
                blocked.append({"task_id": task["id"], "title": task.get("title"), "reason": "Marked blocked"})

        for task in project_tasks:
            dep_chain = []
            visited = set()
            current = task["id"]
            while True:
                dep_chain.append(current)
                visited.add(current)
                direct_deps = [dep for dep in (task_by_id.get(current, {}).get("dependencies") or []) if dep in task_by_id]
                if not direct_deps:
                    break
                current = direct_deps[0]
                if current in visited:
                    break
            chains.append({"task_id": task["id"], "title": task.get("title"), "chain": dep_chain})

        circular = []
        for task in project_tasks:
            deps = task.get("dependencies") or []
            if task["id"] in deps:
                circular.append({"task_id": task["id"], "reason": "Self dependency"})

        return {
            "blocked_tasks": blocked,
            "dependency_chains": chains,
            "circular_dependencies": circular,
            "tasks_that_cannot_start_yet": [
                {"task_id": task["id"], "title": task.get("title"), "depends_on": task.get("dependencies")}
                for task in project_tasks
                if (task.get("dependencies") or [])
            ],
            "critical_path_candidates": [
                task["id"] for task in project_tasks if task.get("priority") in {"HIGH", "CRITICAL"}
            ],
        }

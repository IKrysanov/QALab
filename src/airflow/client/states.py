"""Терминальные состояния DAGRun / TaskInstance для polling-хелперов.

Состояния храним строками — Airflow возвращает state как строку (иногда null),
и реальный набор может отличаться от перечислений в ``models.common``.
"""

# DAGRun достиг финального состояния — дальше не изменится.
TERMINAL_DAG_RUN_STATES = frozenset({"success", "failed"})

# TaskInstance в финальном состоянии. up_for_retry / up_for_reschedule /
# deferred / scheduled / queued / running — НЕ финальные (ещё поедут дальше).
TERMINAL_TASK_INSTANCE_STATES = frozenset(
    {"success", "failed", "skipped", "upstream_failed", "removed"}
)

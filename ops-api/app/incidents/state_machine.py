from app.common.exceptions import ConflictError

# action -> (allowed_from_statuses, target_status or None for non-status actions)
ACTION_RULES: dict[str, tuple[frozenset[str], str | None]] = {
    "acknowledge": (frozenset({"open"}), "acknowledged"),
    "start_investigation": (frozenset({"open", "acknowledged"}), "investigating"),
    "mitigate": (frozenset({"investigating"}), "mitigated"),
    "resolve": (frozenset({"investigating", "mitigated"}), "resolved"),
    "close": (frozenset({"resolved"}), "closed"),
    "reopen_investigation": (frozenset({"resolved"}), "investigating"),
    "assign": (frozenset({"open", "acknowledged", "investigating", "mitigated", "resolved"}), None),
    "update_severity": (
        frozenset({"open", "acknowledged", "investigating", "mitigated", "resolved"}),
        None,
    ),
    "add_note": (
        frozenset(
            {
                "open",
                "acknowledged",
                "investigating",
                "mitigated",
                "resolved",
                "closed",
            }
        ),
        None,
    ),
}


def validate_action(current_status: str, action: str) -> str | None:
    if action not in ACTION_RULES:
        raise ConflictError(
            message=f"未知动作: {action}",
            data={"current_status": current_status, "requested_action": action},
        )

    allowed_from, target_status = ACTION_RULES[action]
    if current_status not in allowed_from:
        target_hint = target_status or "不变"
        raise ConflictError(
            message=f"不允许从 {current_status} 执行 {action}（目标: {target_hint}）",
            data={"current_status": current_status, "requested_action": action},
        )
    return target_status

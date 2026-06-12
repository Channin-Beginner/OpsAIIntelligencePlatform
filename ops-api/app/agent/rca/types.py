from typing import Any, Literal

EvidenceType = Literal["metric", "log", "trace", "kb"]


def evidence_item(
    *,
    type: EvidenceType,
    source: str,
    summary: str,
    query: str | None = None,
    detail: Any = None,
) -> dict[str, Any]:
    """RCA 证据链统一结构（阶段三 3.C 编排消费）。"""
    payload: dict[str, Any] = {
        "type": type,
        "source": source,
        "summary": summary,
    }
    if query:
        payload["query"] = query
    if detail is not None:
        payload["detail"] = detail
    return payload

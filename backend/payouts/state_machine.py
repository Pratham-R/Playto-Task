from payouts.models import PayoutRequest

_ALLOWED: dict[str, set[str]] = {
    PayoutRequest.Status.PENDING: {PayoutRequest.Status.PROCESSING},
    PayoutRequest.Status.PROCESSING: {
        PayoutRequest.Status.COMPLETED,
        PayoutRequest.Status.FAILED,
    },
    PayoutRequest.Status.COMPLETED: set(),
    PayoutRequest.Status.FAILED: set(),
}


class InvalidTransition(Exception):
    pass


def transition(payout: PayoutRequest, to_status: str) -> None:
    """
    Mutate payout.status if the transition is legal. Does NOT save —
    caller must call payout.save(). Raises InvalidTransition for illegal
    moves (e.g. COMPLETED→PENDING, FAILED→COMPLETED, anything backward).
    """
    allowed = _ALLOWED.get(payout.status, set())
    if to_status not in allowed:
        raise InvalidTransition(
            f"Transition {payout.status!r} → {to_status!r} is not allowed"
        )
    payout.status = to_status

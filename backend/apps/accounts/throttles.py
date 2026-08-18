"""Throttles for the authentication endpoints."""

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5/min per IP on `POST /auth/token/`, so credential stuffing is not free.

    Scoped to the anonymous (IP) bucket deliberately: rate-limiting per *username* would
    let an attacker lock a known account out by burning its quota.
    """

    scope = "login"

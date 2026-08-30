"""Custom DRF exception handler + role helpers.

Maps the domain's `RuleViolation` (business-rule breaks: FIFO-44 overflow, bad exit
seq, unknown sensor) to a clean HTTP 400 JSON response instead of a 500 HTML page.
All other exceptions fall back to DRF's default handler.
"""
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from mes.models import Operator
from mes.services import RuleViolation

# Operator role groups (mirrors the `role` column seeded from staging).
ROLE_MANAGER = 'manager'
ROLE_SUPERVISOR = 'supervisor'
ROLE_OPERATOR = 'operator'
ROLE_ADMIN = 'admin'

# Any role at or above this level may read dashboards / journey.
MANAGER_ROLES = {ROLE_MANAGER, ROLE_ADMIN}


class IsManager(BasePermission):
    """Allow only Manager / Admin — used for dashboard + journey reads (SRS F7).

    The authenticated Django user links 1:1 to an `Operator` row (seeded from staging
    with its `role`); we resolve the role through that link.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        operator = Operator.objects.filter(operator_code=request.user.username).first()
        role = (operator.role or '') if operator else ''
        return role in MANAGER_ROLES


def exception_handler(exc, context):
    if isinstance(exc, RuleViolation):
        return Response({'detail': str(exc)}, status=400)
    return drf_exception_handler(exc, context)

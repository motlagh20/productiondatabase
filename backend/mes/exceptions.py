"""Custom DRF exception handler.

Maps the domain's `RuleViolation` (business-rule breaks: FIFO-44 overflow, bad exit
seq, unknown sensor) to a clean HTTP 400 JSON response instead of a 500 HTML page.
All other exceptions fall back to DRF's default handler.
"""
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from mes.services import RuleViolation


def exception_handler(exc, context):
    if isinstance(exc, RuleViolation):
        return Response({'detail': str(exc)}, status=400)
    return drf_exception_handler(exc, context)

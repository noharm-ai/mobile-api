from enum import Enum


class Permission(Enum):
    ADMIN_DRUGS = "admin drug attributes"
    ADMIN_DRUGS__OVERWRITE_ATTRIBUTES = "permits overwriting attributes on copy"

    ADMIN_EXAMS = "admin exams"
    ADMIN_EXAMS__COPY = "copy exams from other segments"
    ADMIN_EXAMS__MOST_FREQUENT = "get most frequent exams"

    ADMIN_FREQUENCIES = "admin frequency configs"
    ADMIN_ROUTES = "admin routes configs"
    ADMIN_SUBSTANCE_RELATIONS = "admin substance relations"
    ADMIN_SUBSTANCES = "admin substances"
    ADMIN_SEGMENTS = "admin segments"
    ADMIN_UNIT_CONVERSION = "admin unit conversions"

    ADMIN_USERS = "admin users"

    ADMIN_INTEGRATION_REMOTE = "grants integration remote access"

    ADMIN_INTERVENTION_REASON = "admin intervention reason recordss"

    CHECK_PRESCRIPTION = "check prescriptions"

    SCORE_SEGMENT = "grant permission to generate score to the entire segment"

    INTEGRATION_UTILS = "grants permission to actions to help integration process"
    INTEGRATION_STATUS = "grants access to view current integration status"

    VIEW_REPORTS = "grants permission to view reports"
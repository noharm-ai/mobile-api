from sqlalchemy import asc, desc
from datetime import timedelta

from models.main import db
from models.prescription import Patient
from models.regulation import RegSolicitation, RegSolicitationType
from models.requests.regulation_prioritization_request import (
    RegulationPrioritizationRequest,
)


def get_prioritization(request_data: RegulationPrioritizationRequest):
    query = (
        db.session.query(RegSolicitation, RegSolicitationType, Patient)
        .outerjoin(
            RegSolicitationType,
            RegSolicitation.id_reg_solicitation_type == RegSolicitationType.id,
        )
        .outerjoin(Patient, RegSolicitation.admission_number == Patient.admissionNumber)
    )

    if request_data.startDate:
        query = query.filter(RegSolicitation.date >= request_data.startDate.date())

    if request_data.endDate:
        query = query.filter(
            RegSolicitation.date
            <= (request_data.endDate + timedelta(hours=23, minutes=59))
        )

    if request_data.typeList:
        query = query.filter(
            RegSolicitation.id_reg_solicitation_type.in_(request_data.typeList)
        )

    if request_data.stageList:
        query = query.filter(RegSolicitation.stage.in_(request_data.stageList))

    for order in request_data.order:
        direction = desc if order.direction == "desc" else asc
        if order.field in ["date", "risk"]:
            query = query.order_by(direction(getattr(RegSolicitation, order.field)))

    query = query.limit(request_data.limit).offset(request_data.offset)

    return query.all()

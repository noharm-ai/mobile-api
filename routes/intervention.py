from flask_api import status
from models.main import *
from models.appendix import *
from models.prescription import *
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from .utils import tryCommit
from services.admin import intervention_reason_service
from services import intervention_service
from exception.validation_error import ValidationError

app_itrv = Blueprint("app_itrv", __name__)


@app_itrv.route(
    "/prescriptions/drug/<int:idPrescriptionDrug>/<int:drugStatus>", methods=["PUT"]
)
@jwt_required()
def setDrugStatus(idPrescriptionDrug, drugStatus):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    pd = PrescriptionDrug.query.get(idPrescriptionDrug)
    if pd is not None:
        pd.status = drugStatus
        pd.update = datetime.today()
        pd.user = user.id

    return tryCommit(db, str(idPrescriptionDrug), user.permission())


@app_itrv.route("/intervention/<int:idPrescriptionDrug>", methods=["PUT"])
@app_itrv.route("/intervention", methods=["PUT"])
@jwt_required()
def createIntervention(idPrescriptionDrug=None):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    data = request.get_json()

    if idPrescriptionDrug:
        return {
            "status": "error",
            "message": "Você está usando uma versão desatualizada da NoHarm. Pressione ctrl+f5 para atualizar.",
            "code": "erros.oldVersion",
        }, status.HTTP_400_BAD_REQUEST

    try:
        intervention = intervention_service.save_intervention(
            id_intervention=data.get("idIntervention", None),
            id_prescription=data.get("idPrescription", "0"),
            id_prescription_drug=data.get("idPrescriptionDrug", "0"),
            new_status=data.get("status", "s"),
            user=user,
            admission_number=data.get("admissionNumber", None),
            id_intervention_reason=data.get("idInterventionReason", None),
            error=data.get("error", None),
            cost=data.get("cost", None),
            observation=data.get("observation", None),
            interactions=data.get("interactions", None),
            transcription=data.get("transcription", None),
            economy_days=data.get("economyDays", None),
            expended_dose=data.get("expendedDose", None),
        )
    except ValidationError as e:
        return {"status": "error", "message": str(e), "code": e.code}, e.httpStatus

    return tryCommit(db, intervention, user.permission())


def sortReasons(e):
    return e["description"]


@app_itrv.route("/intervention/reasons", methods=["GET"])
@jwt_required()
def getInterventionReasons():
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    list = intervention_reason_service.get_reasons(active_only=True)

    return {
        "status": "success",
        "data": intervention_reason_service.list_to_dto(list),
    }, status.HTTP_200_OK


@app_itrv.route("/intervention/search", methods=["POST"])
@jwt_required()
def search_interventions():
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    data = request.get_json()

    results = intervention_service.get_interventions(
        admissionNumber=data.get("admissionNumber", None),
        startDate=data.get("startDate", None),
        endDate=data.get("endDate", None),
        idSegment=data.get("idSegment", None),
        idPrescription=data.get("idPrescription", None),
        idPrescriptionDrug=data.get("idPrescriptionDrug", None),
    )

    return {"status": "success", "data": results}, status.HTTP_200_OK

import os
from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.main import *
from services import summary_service
from exception.validation_error import ValidationError

app_summary = Blueprint("app_summary", __name__)


@app_summary.route("/summary/<int:admission_number>", methods=["GET"])
@jwt_required()
def get_structured_info(admission_number):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    os.environ["TZ"] = "America/Sao_Paulo"

    try:
        result = summary_service.get_structured_info(
            admission_number=admission_number, user=user
        )
    except ValidationError as e:
        return {"status": "error", "message": str(e), "code": e.code}, e.httpStatus

    return {"status": "success", "data": result}, status.HTTP_200_OK

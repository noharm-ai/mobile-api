import os
from flask import Blueprint, request
from flask_jwt_extended import (jwt_required, get_jwt_identity)

from flask_api import status
from models.main import *
from models.appendix import *
from models.segment import *
from models.prescription import *
from services.admin import frequency_service
from exception.validation_error import ValidationError

app_admin_freq = Blueprint('app_admin_freq',__name__)

@app_admin_freq.route('/admin/frequency', methods=['GET'])
@jwt_required()
def get_frequencies():
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    list = frequency_service.get_frequencies()

    return {
        'status': 'success',
        'data': frequency_service.list_to_dto(list)
    }, status.HTTP_200_OK
    

@app_admin_freq.route('/admin/frequency', methods=['PUT'])
@jwt_required()
def update_frequency():
    data = request.get_json()
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    os.environ['TZ'] = 'America/Sao_Paulo'

    try:
        freq =  frequency_service.update_daily_frequency(\
            data.get('id', None), data.get('dailyFrequency', None), user\
        )
    except ValidationError as e:
        return {
            'status': 'error',
            'message': str(e),
            'code': e.code
        }, e.httpStatus

    return tryCommit(db, frequency_service.list_to_dto([freq]))
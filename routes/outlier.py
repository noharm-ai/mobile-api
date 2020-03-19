from flask_api import status
from models import db, User, Patient, Prescription, PrescriptionDrug, InterventionReason, Intervention, Segment, setSchema, Department, Outlier, Drug
from sqlalchemy import desc, asc
from flask import Blueprint, request
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)

app_out = Blueprint('app_out',__name__)

@app_out.route('/outliers/<int:idSegment>/<int:idDrug>', methods=['GET'])
@jwt_required
def getOutliers(idSegment=1, idDrug=1):
    user = User.find(get_jwt_identity())
    setSchema(user.schema)
    outliers = Outlier.query\
        .filter(Outlier.idSegment == idSegment, Outlier.idDrug == idDrug)\
        .order_by(Outlier.countNum.desc())\
        .all()
    d = Drug.query.get(idDrug)

    db.engine.dispose()

    results = []
    for o in outliers:
        results.append({
            'idOutlier': o.id,
            'idDrug': o.idDrug,
            'countNum': o.countNum,
            'dose': o.dose,
            'frequency': o.frequency,
            'score': o.score,
            'manualScore': o.manualScore,
            'antimicro': d.antimicro,
            'mav': d.mav,
            'controlled': d.controlled
        })

    return {
        'status': 'success',
        'data': results
    }, status.HTTP_200_OK


@app_out.route('/outliers/<int:idOutlier>', methods=['PUT'])
@jwt_required
def setManualOutlier(idOutlier):
    data = request.get_json()

    user = User.find(get_jwt_identity())
    setSchema(user.schema)
    o = Outlier.query.get(idOutlier)
    o.idUser = user.id
    o.manualScore = data.get('manualScore', None)

    try:
        db.session.commit()

        return {
            'status': 'success',
            'data': o.id
        }, status.HTTP_200_OK
    except AssertionError as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_400_BAD_REQUEST
    except Exception as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_500_INTERNAL_SERVER_ERROR


@app_out.route('/drugs/<int:idDrug>', methods=['PUT'])
@jwt_required
def setDrugClass(idDrug):
    data = request.get_json()

    user = User.find(get_jwt_identity())
    setSchema(user.schema)
    d = Drug.query.get(idDrug)
    d.antimicro = bool(data.get('antimicro', 0))
    d.mav = bool(data.get('mav', 0))
    d.controlled = bool(data.get('controlled', 0))

    try:
        db.session.commit()

        return {
            'status': 'success',
            'data': d.id
        }, status.HTTP_200_OK
    except AssertionError as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_400_BAD_REQUEST
    except Exception as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_500_INTERNAL_SERVER_ERROR

@app_out.route('/drugs', methods=['GET'])
@app_out.route('/drugs/<int:idSegment>', methods=['GET'])
@jwt_required
def getDrugs(idSegment=1):
    user = User.find(get_jwt_identity())
    setSchema(user.schema)

    drugs = Drug.query\
            .join(Outlier, Outlier.idDrug == Drug.id)\
            .filter(Outlier.idSegment == idSegment)\
            .order_by(asc(Drug.name))\
            .all()

    db.engine.dispose()

    results = []
    for d in drugs:
        results.append({
            'idDrug': d.id,
            'name': d.name,
        })

    return {
        'status': 'success',
        'data': results
    }, status.HTTP_200_OK
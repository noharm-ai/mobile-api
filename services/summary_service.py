import json
from flask_api import status
from sqlalchemy import asc, desc, func, between

from models.main import db
from models.appendix import *
from models.prescription import *
from models.notes import *
from models.enums import RoleEnum, MemoryEnum
from services import memory_service, prescription_agg_service
from exception.validation_error import ValidationError


def get_structured_info(admission_number, user, mock=False):
    roles = user.config["roles"] if user.config and "roles" in user.config else []
    if (
        RoleEnum.SUPPORT.value not in roles
        and RoleEnum.ADMIN.value not in roles
        and RoleEnum.DOCTOR.value not in roles
    ):
        raise ValidationError(
            "Usuário não autorizado",
            "errors.unauthorizedUser",
            status.HTTP_401_UNAUTHORIZED,
        )

    patient = (
        db.session.query(Patient)
        .filter(Patient.admissionNumber == admission_number)
        .first()
    )

    if patient is None:
        raise ValidationError(
            "Registro inválido",
            "errors.invalidRecord",
            status.HTTP_400_BAD_REQUEST,
        )

    return {
        "patient": _get_patient_data(patient),
        "exams": _get_exams(patient.idPatient, user.schema),
        "allergies": None,
        "drugsUsed": _get_all_drugs_used(
            admission_number=admission_number, schema=user.schema
        ),
        "drugsSuspended": _get_all_drugs_suspended(
            admission_number=admission_number, schema=user.schema
        ),
        "receipt": _get_receipt(admission_number=admission_number, schema=user.schema),
        "summaryConfig": _get_summary_config(admission_number, mock),
    }


def _get_patient_data(patient: Patient):
    return {
        "idPatient": patient.idPatient,
        "admissionNumber": patient.admissionNumber,
        "admissionDate": patient.admissionDate.isoformat()
        if patient.admissionDate
        else None,
        "dischargeDate": patient.dischargeDate.isoformat()
        if patient.dischargeDate
        else None,
        "birthdate": patient.birthdate.isoformat() if patient.birthdate else None,
        "gender": patient.gender,
        "weight": patient.weight,
        "height": patient.height,
        "imc": round((patient.weight / pow(patient.height / 100, 2)), 2)
        if patient.weight is not None and patient.height is not None
        else None,
        "color": patient.skinColor,
    }


def _get_summary_config(admission_number, mock):
    summary_config = memory_service.get_memory(MemoryEnum.SUMMARY_CONFIG.value)
    annotations = _get_all_annotations(admission_number)

    config = [
        {"key": "reason"},
        {"key": "previousDrugs"},
        {"key": "diagnosis"},
        {"key": "dischargeCondition"},
        {"key": "dischargePlan"},
        {"key": "procedures"},
        {"key": "exams"},
    ]
    prompts = {}
    result = {
        "url": summary_config.value["url"],
        "apikey": summary_config.value["apikey"],
    }

    for c in config:
        key = c["key"]
        if mock:
            text = memory_service.get_memory(f"summary_text_{key}")
            prompts[key] = json.dumps(summary_config.value[key]).replace(
                ":replace_text", text.value["text"]
            )
        else:
            prompts[key] = json.dumps(summary_config.value[key]).replace(
                ":replace_text", annotations[key]["value"]
            )

        result[key] = {
            "prompt": json.loads(prompts[key]),
            "audit": annotations[key]["list"],
        }

    return result


def _get_all_annotations(admission_number):
    first = (
        db.session.query(ClinicalNotes)
        .filter(ClinicalNotes.admissionNumber == admission_number)
        .order_by(asc(ClinicalNotes.date))
        .first()
    )
    last = (
        db.session.query(ClinicalNotes)
        .filter(ClinicalNotes.admissionNumber == admission_number)
        .order_by(desc(ClinicalNotes.date))
        .first()
    )

    reason = _get_annotation(
        admission_number=admission_number,
        field="motivo",
        add=True,
        interval="4 DAYS",
        compare_date=first.date,
    )

    previous_drugs = _get_annotation(
        admission_number=admission_number,
        field="medprevio",
        add=True,
        interval="1 DAY",
        compare_date=first.date,
    )

    diagnosis = _get_annotation(
        admission_number=admission_number,
        field="diagnostico",
        add=True,
        interval=None,
        compare_date=None,
    )

    clinical_summary = _get_annotation(
        admission_number=admission_number,
        field="resumo",
        add=False,
        interval="1 DAY",
        compare_date=last.date,
    )

    discharge_plan = _get_annotation(
        admission_number=admission_number,
        field="planoalta",
        add=False,
        interval="1 DAY",
        compare_date=last.date,
    )

    procedures = _get_annotation(
        admission_number=admission_number,
        field="procedimentos",
        add=True,
        interval=None,
        compare_date=None,
    )

    exams = _get_annotation(
        admission_number=admission_number,
        field="exames",
        add=True,
        interval=None,
        compare_date=None,
    )

    discharge_condition = _get_annotation(
        admission_number=admission_number,
        field="condicaoalta",
        add=False,
        interval="1 DAY",
        compare_date=last.date,
    )

    return {
        "reason": reason,
        "previousDrugs": previous_drugs,
        "diagnosis": diagnosis,
        "clinicalSummary": clinical_summary,
        "dischargePlan": discharge_plan,
        "procedures": procedures,
        "exams": exams,
        "dischargeCondition": discharge_condition,
    }


def _get_annotation(admission_number, field, add, interval, compare_date):
    query = (
        db.session.query(func.jsonb_array_elements_text(ClinicalNotes.summary[field]))
        .select_from(ClinicalNotes)
        .filter(ClinicalNotes.admissionNumber == admission_number)
    )

    if compare_date:
        if add:
            query = query.filter(
                between(
                    func.date(ClinicalNotes.date),
                    func.date(compare_date),
                    func.date(compare_date) + func.cast(interval, INTERVAL),
                )
            )
        else:
            query = query.filter(
                between(
                    func.date(ClinicalNotes.date),
                    func.date(compare_date) - func.cast(interval, INTERVAL),
                    func.date(compare_date),
                )
            )

    results = query.order_by(ClinicalNotes.date).all()

    uniqueList = set()
    for i in results:
        uniqueList.add(i[0])

    return {"value": ". ".join(uniqueList)[:1500], "list": list(uniqueList)}


def _get_exams(id_patient, schema):
    query = f"""
    select
        distinct on (e.fkpessoa,s.abrev)
        e.fkpessoa,
        s.abrev,
        resultado,
        dtexame,
        s.referencia,
        e.unidade,
        s.min,
        s.max
    from
        {schema}.pessoa pe
    inner join {schema}.exame e on
        pe.fkpessoa = e.fkpessoa
    inner join {schema}.segmentoexame s on
        s.tpexame = lower(e.tpexame)
    where 
        e.fkpessoa = :id_patient
        and (resultado < s.min or resultado > s.max)
    order by
        fkpessoa,
        abrev,
        dtexame desc
    """

    exams = db.session.execute(query, {"id_patient": id_patient})

    exams_list = []
    for e in exams:
        exams_list.append(
            {
                "name": e[1],
                "date": e[3].isoformat() if e[3] else None,
                "result": e[2],
                "measureUnit": e[5],
            }
        )

    return exams_list


def _get_all_drugs_used(admission_number, schema):
    query = f"""
    select 
        distinct(coalesce(s.nome, m.nome)) as nome
    from
        {schema}.presmed pm
        inner join {schema}.prescricao p on (pm.fkprescricao = p.fkprescricao)
        inner join {schema}.medicamento m on (pm.fkmedicamento = m.fkmedicamento)
        left join public.substancia s on (m.sctid = s.sctid)
    where 
        p.nratendimento = :admission_number
        and origem <> 'Dietas'
    order by
        nome
    """

    result = db.session.execute(query, {"admission_number": admission_number})

    list = []
    for i in result:
        list.append(
            {
                "name": i[0],
            }
        )

    return list


def _get_all_drugs_suspended(admission_number, schema):
    query = f"""
    select 
        distinct(coalesce(s.nome, m.nome)) as nome
    from
        {schema}.presmed pm
        inner join {schema}.prescricao p on (pm.fkprescricao = p.fkprescricao)
        inner join {schema}.medicamento m on (pm.fkmedicamento = m.fkmedicamento)
        left join public.substancia s on (m.sctid = s.sctid)
    where 
        p.nratendimento = :admission_number
        and pm.origem <> 'Dietas'
        and pm.dtsuspensao is not null 
        and (
            select count(*)
            from {schema}.presmed pm2
                inner join {schema}.prescricao p2 on (pm2.fkprescricao = p2.fkprescricao)
            where 
                p2.nratendimento = p.nratendimento 
                and pm2.fkprescricao > pm.fkprescricao
                and pm2.fkmedicamento = pm.fkmedicamento
                and pm2.dtsuspensao is null 
        ) = 0
    order by
        nome
    """

    result = db.session.execute(query, {"admission_number": admission_number})

    list = []
    for i in result:
        list.append(
            {
                "name": i[0],
            }
        )

    return list


def _get_receipt(admission_number, schema):
    last_agg = prescription_agg_service.get_last_agg_prescription(admission_number)

    if last_agg == None:
        return []

    query = f"""
    select distinct on (nome_med, frequencia, dose, fkunidademedida, via) * from (
        select 
            m.nome as nome_med, p.dtprescricao, f.nome as frequencia , pm.dose, pm.fkunidademedida, pm.via
        from
            {schema}.presmed pm
            inner join {schema}.prescricao p on (pm.fkprescricao = p.fkprescricao)
            inner join {schema}.medicamento m on (pm.fkmedicamento = m.fkmedicamento)
            left join {schema}.frequencia f on (pm.fkfrequencia = f.fkfrequencia)
        where 
            p.nratendimento = :admission_number
            and pm.origem <> 'Dietas'
            and date(:date) between p.dtprescricao::date and p.dtvigencia 
            and pm.dtsuspensao is null
        order by
            nome_med, p.dtprescricao desc
    ) receita
    """

    result = db.session.execute(
        query, {"admission_number": admission_number, "date": last_agg.date}
    )

    list = []
    for i in result:
        list.append(
            {
                "name": i[0],
                "frequency": i[2],
                "dose": i[3],
                "measureUnit": i[4],
                "route": i[5],
            }
        )

    return list

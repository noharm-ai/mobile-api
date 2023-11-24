from sqlalchemy import func
from datetime import date

from models.main import *
from models.appendix import *
from models.segment import *
from models.enums import ReportEnum
from services import memory_service
from services.reports import cache_service


def get_prescription_report(user):
    cache_data = (
        db.session.query(Memory)
        .filter(Memory.kind == ReportEnum.RPT_GENERAL.value)
        .filter(func.date(Memory.update) == date.today())
        .first()
    )

    if cache_data != None:
        return cache_service.generate_link(
            cache_data.key, ReportEnum.RPT_GENERAL.value, user.schema
        )

    list = _get_prescription_list(user)

    cache = memory_service.save_unique_memory(ReportEnum.RPT_GENERAL.value, {}, user)

    cache_service.save_cache(
        cache_id=cache.key,
        report=ReportEnum.RPT_GENERAL.value,
        schema=user.schema,
        data=list,
    )

    return cache_service.generate_link(
        cache.key, ReportEnum.RPT_GENERAL.value, user.schema
    )


def _get_prescription_list(user):
    sql = f"""
        select 
            distinct on (p.fkprescricao)
            p.fksetor,
            p.fkprescricao,
            p.convenio,
            p.nratendimento,
            s.nome as setorNome,
            p.dtprescricao::date as data,
            case 
                when p.status = 's' then 1
                when pa.fkprescricao is not null then 1
                else 0
            end as checada,
            case 
                when pa.fkprescricao is null then coalesce(array_length(p.aggmedicamento,1), 1)
                else pa.total_itens
            end total_itens,
            case 
                when p.status <> 's' and pa.fkprescricao is null then 0
                when pa.fkprescricao is not null then pa.total_itens 
                else coalesce(array_length(p.aggmedicamento,1), 1)
            end total_itens_checados,
            case
                when p.status <> 's' and pa.fkprescricao is null then 'Não Checado'
                when pa.fkprescricao is not null then user_pa.nome
                else user_p.nome
            end as userNome
        from 
            {user.schema}.prescricao p 
            inner join {user.schema}.setor s on s.fksetor = p.fksetor
            left join (
                select * from {user.schema}.prescricao_audit pa where pa.tp_audit = 1
            ) pa on pa.fkprescricao = p.fkprescricao
            left join public.usuario user_p on (p.update_by = user_p.idusuario)
            left join public.usuario user_pa on pa.created_by = user_pa.idusuario
        where 
            p.agregada = true 
            and p.concilia IS null 
            and s.fksetor in (select s2.fksetor from {user.schema}.segmentosetor s2 where s2.idsegmento is not null)
            and p.dtprescricao > now() - interval '2 months'
        order by p.fkprescricao, pa.created_at desc
    """

    db_session = db.create_scoped_session(
        options={"bind": db.get_engine(db.get_app(), ReportEnum.RPT_BIND.value)}
    )

    results = db_session.execute(sql).fetchall()
    itens = []
    for i in results:
        itens.append(
            {
                "idDepartment": i[0],
                "idPrescription": i[1],
                "insurance": i[2],
                "admissionNumber": i[3],
                "department": i[4],
                "date": i[5].isoformat(),
                "checked": i[6],
                "itens": i[7],
                "checkedItens": i[8],
                "responsible": i[9],
            }
        )

    return itens

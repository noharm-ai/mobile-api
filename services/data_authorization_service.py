from models.main import db, UserAuthorization, User
from models.enums import FeatureEnum
from services import memory_service, permission_service


def has_segment_authorization(id_segment: int, user: User):
    if id_segment == None:
        # some cases dont have a segment defined
        return True

    if permission_service.has_maintainer_permission(user):
        return True

    if memory_service.has_feature(FeatureEnum.AUTHORIZATION_SEGMENT.value):
        auth = (
            db.session.query(UserAuthorization)
            .filter(UserAuthorization.idUser == user.id)
            .filter(UserAuthorization.idSegment == id_segment)
            .first()
        )

        if auth != None:
            return True

        return False

    return True

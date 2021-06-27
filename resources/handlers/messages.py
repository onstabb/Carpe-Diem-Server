from ..core.types import ServerMessage


class ProfileEdited(ServerMessage):
    id: int
    name: str
    age: int
    gender: str
    preferred_gender: str
    description: str
    city: str
    photo: str


class LikeNotification(ServerMessage):
    pass


class MutualSympathy(ServerMessage):
    mobile_phone: int

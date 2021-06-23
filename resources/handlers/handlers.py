# coding=utf-8
import config
from ..utils import *
from ..core import dp
from ..core.types import STATUSES
from ..core.db import Profile, GENDERS, Relationship, RELATIONSHIP_STATES
from ..core.utils import FileManager
from . import requests
from . import responses
from . import messages
from . import errors


@dp.register_handler(request_type=requests.TestRequest, validate_token=False)
async def test_handler(data: requests.TestRequest):
    return responses.ServerResponse(status=STATUSES.OK, comment=data.text)


@dp.register_handler(request_type=requests.Login, validate_token=False)
async def login(data: requests.Login):

    if not data.password:
        await SmsService.send_sms_code(data.mobile)
        return responses.ServerResponse(status=STATUSES.OK, comment="SMS-confirmation sent")

    user = Profile.get_one(password=security.create_hash(data.password))
    if not user:
        raise errors.IncorrectPassword("Invalid user or password")

    session = await dp.user_start_session(profile=user, request=data.request)
    return responses.ServerResponse(status=STATUSES.OK, save_session=session)


@dp.register_handler(request_type=requests.SmsCodeConfirmation, validate_token=False)
async def sms_code_confirmation(data: requests.SmsCodeConfirmation):
    mobile: int = await SmsService.storage_pop(data.code)

    if not mobile:
        raise errors.InvalidSmsCode("SMS-confirmation code is not valid")

    new_pass = security.build_password(length=config.UTILS_GEN_PASSWORD_LENGTH)
    hashed_password = security.create_hash(new_pass)
    user = Profile.get_one(mobile=mobile)

    if not user:
        user = Profile(mobile=mobile, password=hashed_password)

    user.password = hashed_password
    user.save()

    session = await dp.user_start_session(profile=user, request=data.request)
    return responses.NewUserRegistered(status=STATUSES.OK, new_password=new_pass, save_session=session)


@dp.register_handler(request_type=requests.EditProfile, validate_token=True)
async def edit_profile(data: requests.EditProfile):

    if not data.name.isalpha() or len(data.name) > config.DB_PROF_NAME_MAX_LEN:
        raise errors.InvalidRequestData(f"Name must be alphabetical and contain <{config.DB_PROF_NAME_MAX_LEN} symbols")

    if config.DB_PROF_MIN_USER_AGE > data.age:
        raise errors.InvalidRequestData("Only 18 age can use service")

    if data.gender not in GENDERS.all:
        raise errors.InvalidRequestData("Gender must be inscribed correctly")

    if data.preferred_gender not in GENDERS.preferences:
        raise errors.InvalidRequestData("Preferred gender must be inscribed correctly")

    try:
        data.description.encode('utf-8')
        assert len(data.description) < config.DB_PROF_DESCRIPTION_MAX_LEN
    except (UnicodeDecodeError, AssertionError):
        raise errors.InvalidRequestData(
            f"Description must be utf-8 encoded and contain <{config.DB_PROF_DESCRIPTION_MAX_LEN} symbols"
        )

    locality = await GeoAPI.get_geo_data(locality=data.locality, lang=config.GEO_API_RESP_DATA_LANG)

    user = data.user

    if data.photo:
        FileManager.image_compression(data.photo)
        user.photo = data.photo

    user.name = data.name
    user.age = data.age
    user.gender = data.gender
    user.preferred_gender = data.preferred_gender
    user.description = data.description
    user.coordinates = locality.coordinates
    user.city = locality.city
    user.state = locality.state
    user.country = locality.country
    user.save()

    for relation in user.get_all_relationships():
        relation: Relationship
        if relation.status == RELATIONSHIP_STATES.established:
            other_user: Profile = relation.get_neighbour(data.user)
            message: messages.ProfileEdited = messages.ProfileEdited(
                id=other_user.id_,
                name=other_user.name,
                age=other_user.age,
                gender=other_user.gender,
                preferred_gender=other_user.preferred_gender,
                description=other_user.description,
                city=other_user.city,
                photo=other_user.photo,
            )
            await dp.send_ws_message(sender=data.user, data=message, profile=other_user)
        else:
            relation.delete()

    return responses.ServerResponse(status=STATUSES.OK)


@dp.register_handler(request_type=requests.SelectProfile, check_profile_filled=True)
async def select_profile(data: requests.SelectProfile):
    candidates = data.user.select_candidates(config.DB_SELECTING_AGE_DIFF)
    if len(candidates) > 1:
        distances: list = [
            (GeoAPI.calculate_distance(data.user.coordinates, profile.coordinates), profile) for profile in candidates
        ]
        distance, selected_profile = min(distances, key=lambda kv: kv[0])
    else:
        selected_profile = candidates.pop()
    selected_profile: Profile
    if not selected_profile.get_relationship_if_exists(profile=data.user):
        new_relationship: Relationship = Relationship(
            profile_1=data.user,
            profile_2=selected_profile,
        )
        new_relationship.save()

    return responses.SelectedProfile(
        status=STATUSES.OK,
        id=selected_profile.id_,
        name=selected_profile.name,
        age=selected_profile.age,
        gender=selected_profile.gender,
        preferred_gender=selected_profile.preferred_gender,
        description=selected_profile.description,
        city=selected_profile.city,
        photo=selected_profile.photo,
    )


@dp.register_handler(request_type=requests.EvaluateProfile, check_profile_filled=True)
async def evaluate_profile(data: requests.EvaluateProfile):
    relationship: Relationship = data.user.get_relationship_if_exists(data.id)
    if not relationship:
        raise errors.InvalidProfile("Profile is invalid")

    if data.evaluation not in (RELATIONSHIP_STATES.like, RELATIONSHIP_STATES.skip):
        raise errors.InvalidRequestData("You can like or pass profile")

    if relationship.status != RELATIONSHIP_STATES.wait:
        raise errors.RelationshipsAreDefined("Relationships between profiles are defined")

    state1: str = relationship.get_profile_state(data.user)
    if state1 != RELATIONSHIP_STATES.wait:
        raise errors.ChoiceAreMade("The choice has already been made")

    other_user: Profile = relationship.get_neighbour(data.user)
    state2: str = relationship.get_profile_state(other_user)

    relation_status: str = RELATIONSHIP_STATES.table[data.evaluation][state2]
    if relation_status == RELATIONSHIP_STATES.wait and data.evaluation == RELATIONSHIP_STATES.like:
        await dp.send_ws_message(other_user, messages.LikeNotification(), sender=data.user)
    elif relation_status == RELATIONSHIP_STATES.established:
        await dp.send_ws_message(other_user, messages.MutualSympathy(mobile_phone=other_user.mobile), sender=data.user)
        await dp.send_ws_message(data.user, messages.MutualSympathy(mobile_phone=data.user.mobile), sender=other_user)

    relationship.set_profile_state(data.user, state=data.evaluation)
    relationship.status = relation_status
    relationship.save()

    return responses.ServerResponse(status=STATUSES.OK)

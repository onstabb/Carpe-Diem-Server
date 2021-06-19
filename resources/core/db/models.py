from datetime import datetime
from typing import Union, List, Set

from mongoengine import *
from mongoengine.queryset.visitor import Q as MQ  # multiple query

from .types import GENDERS, RELATIONSHIP_STATES
import config


class Profile(Document):
    id_ = SequenceField(primary_key=True)
    registered = DateTimeField(default=datetime.utcnow(), required=True)
    name = StringField(max_length=config.DB_PROF_NAME_MAX_LEN)
    age = IntField(min_value=config.DB_PROF_MIN_USER_AGE)
    gender = StringField(choices=GENDERS.all)
    preferred_gender = StringField(choices=GENDERS.preferences)
    description = StringField(max_length=config.DB_PROF_DESCRIPTION_MAX_LEN)
    coordinates = GeoPointField()
    city = StringField()
    state = StringField()
    country = StringField()
    photo = StringField()
    mobile = IntField(unique=True, required=True)
    password = StringField(required=True)

    @classmethod
    def get_one(cls, filled: int = 0, **kwargs) -> Union['Profile', None]:
        """
        Get user from database
        :param filled: 0 - no matter, 1 - not filled, 2 - filled 
        :return: actual profile of the user
        """
        try:
            if filled == 1:
                user = cls.objects.get(MQ(**kwargs) & MQ(photo__exists=False))
            elif filled == 2:
                user = cls.objects.get(MQ(**kwargs) & MQ(photo__exists=True) & MQ(name__exists=True))
            else:
                user = cls.objects.get(**kwargs)
        except DoesNotExist:
            user = None

        return user

    @property
    def is_filled(self) -> bool:
        if self.photo and self.name:
            return True
        return False

    def get_all_relationships(self) -> List['Relationship']:
        return Relationship.objects(MQ(profile_1=self) | MQ(profile_2=self))

    def check_relationship_exists(self, with_profile: 'Profile') -> bool:
        if Relationship.objects.get(
                (MQ(profile_1=self) & MQ(profile_2=with_profile)) | (MQ(profile_2=self) & MQ(profile_1=with_profile))
        ):
            return True
        else:
            return False

    def select_candidates(self, age_difference: int = config.DB_SELECTING_AGE_DIFF) -> Set['Profile']:
        user_relations = self.get_all_relationships()
        suitable_candidates = set()
        excluded_candidates_ids = set()
        if user_relations:
            for relationship in user_relations:
                relationship: Relationship

                profile_status: str = relationship.get_profile_status(self)
                other_user = relationship.get_neighbour(self)

                if (relationship.status in RELATIONSHIP_STATES.not_for_selecting) or \
                        (profile_status == RELATIONSHIP_STATES.skip):
                    excluded_candidates_ids.add(other_user.id_)
                else:
                    suitable_candidates.add(other_user)
                    return suitable_candidates

        if self.preferred_gender == GENDERS.any:
            do_not_search: str = GENDERS.male if self.gender == GENDERS.female else GENDERS.female
            candidates = self.objects(
                MQ(age__lte=age_difference+self.age) & MQ(age__gte=age_difference-self.age) &        # age
                MQ(preferred_gender__ne=do_not_search) &                                            # gender
                MQ(id___nin=excluded_candidates_ids)                                            # excluded candidates
            )
        else:
            candidates = self.objects(
                MQ(age__lte=age_difference+self.age) & MQ(age__gte=age_difference-self.age) &
                MQ(gender=self.preferred_gender) & MQ(preferred_gender__ne=self.preferred_gender) &
                MQ(id___nin=excluded_candidates_ids)
            )

        suitable_candidates = set(candidates)
        if not suitable_candidates:
            suitable_candidates = self.select_candidates(age_difference=age_difference+config.DB_SELECTING_AGE_DIFF)

        return suitable_candidates


"""                             Relationship Profile Selection State Table
         |||  Start |||  Scenario 1 ||| Scenario 2  |||     Scenario 3     |||     Scenario 4     ||| Scenario 5  |||
         |||    0   |||__1___|__2___|||__1___|___2__|||__1___|__2___|___3__|||__1___|__2___|__3___|||__1___|___2__|||
profile1:|||  wait  ||| like | like ||| like | like ||| wait | like | like ||| wait | like | like ||| wait | pass |||
profile2:|||  wait  ||| wait | like ||| wait | pass ||| pass | wait | like ||| pass | wait | pass ||| pass | pass |||
      
  status:|||  WAIT  ||| WAIT |  OK  ||| WAIT | FAIL ||| WAIT | WAIT |  OK  ||| WAIT | WAIT | FAIL ||| WAIT | FAIL |||

OK - established
FAIL - refused
"""


class Relationship(Document):
    profile_1 = ReferenceField(document_type=Profile, required=True)
    profile_2 = ReferenceField(document_type=Profile)
    profile1_state = StringField(
        choices=RELATIONSHIP_STATES.for_profiles, default=RELATIONSHIP_STATES.wait, required=True
    )
    profile2_state = StringField(
        choices=RELATIONSHIP_STATES.for_profiles, default=RELATIONSHIP_STATES.wait, required=True
    )

    status = StringField(choices=RELATIONSHIP_STATES.general, default=RELATIONSHIP_STATES.wait, required=True)

    def get_neighbour(self, profile: Profile) -> Profile:
        if profile == self.profile_1:
            return self.profile_2
        elif profile == self.profile_2:
            return self.profile_1
        else:
            raise ValueError("Given profile must be in this relationship!")

    def get_profile_status(self, profile: Profile) -> str:
        if profile == self.profile_1:
            return self.profile1_state
        elif profile == self.profile_2:
            return self.profile2_state
        else:
            raise ValueError("Given profile must be in this relationship!")


__all__ = [Profile, Relationship]

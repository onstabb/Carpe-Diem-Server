from typing import Dict

from pydantic import BaseModel


class _Genders(BaseModel):
    male = "male"
    female = "female"
    any = "any"

    @property
    def preferences(self) -> tuple:
        return self.male, self.female, self.any

    @property
    def all(self) -> tuple:
        return self.male, self.female


class _RelationShipStates(BaseModel):
    like: str = "like"
    skip: str = "pass"
    wait: str = "wait"

    refused: str = "refused"
    established: str = "established"

    table: Dict[str, Dict[str, str]] = {
        wait: {wait: wait, like: wait, skip: wait},
        like: {wait: wait, like: established, skip: refused},
        skip: {wait: wait, like: refused, skip: refused},
    }

    @property
    def for_profiles(self) -> tuple:
        return self.like, self.skip, self.wait

    @property
    def general(self) -> tuple:
        return self.wait, self.refused, self.established

    @property
    def not_for_selecting(self) -> tuple:
        return self.refused, self.established


GENDERS = _Genders()
RELATIONSHIP_STATES = _RelationShipStates()

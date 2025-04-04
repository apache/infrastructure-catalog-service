# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import typing

import pydantic
import pydantic.utils
import asfquart

# Namespace scheme for catalog object definitions:
# All data objects have at least two definitions:
# - a BaseFoo class for the minimal representation of an object
# - a Foo class which has all the publicly available (useful) information on a data object
# If a Foo object can contain sensitive information that should only be accessible within
# the organization, we add an additional ExtendedFoo class that contains the private
# information, and define all Foo objects as ExtendedFoo. As ExtendedFoo will be a sub-class
# of Foo, we can freely downgrade the information from sensitive to public-only by using a
# result set that only accepts the Foo class. When that result set is fed an ExtendedFoo
# object, it will automatically downgrade it, removing sensitive information.

class CatalogObject(pydantic.BaseModel):
    """A standard Pydantic BaseModel with an added self-reference URL for each object."""
    ref_url: str = None
    @pydantic.field_serializer('ref_url')
    def make_ref(self, _ref_url, _info):
        my_id = getattr(self, "id")
        my_class = self.__class__.__name__.lower().removeprefix("extended")
        return f"https://{asfquart.APP.config.hostname}/lookup/{my_class}/{my_id}"


# Legal person definitions
class BasePerson(CatalogObject):
    """The shortest public representation of a person. Contains a person's user ID and public name only."""
    id: str
    name: str

class Person(BasePerson):
    """Extended public details of a person"""
    primary_email: str = pydantic.Field(description="The primary email address of this person")
    projects: list["BaseProject"] = []  # We use BaseProject because it does not recurse.

class ExtendedPerson(Person):
    """Extended public and private details of a person"""
    account_created_ts: int = 0
    alternate_emails: list[str] = None
    # More elements to be added later

# Mailing list definitions
class BaseMailingList(CatalogObject):
    """A mailing list at the foundation"""
    id: str


class MailingList(BaseMailingList):
    project: "BaseProject"
    address: str = pydantic.Field(description="The mailing list address", default_factory=lambda kv: kv["id"])
    # auto-set list-id field with a factory
    list_id: str = pydantic.Field(description="The List-ID header for this mailing list", default_factory=lambda kv: "<" + kv["address"].replace("@", ".") + ">")

class ExtendedMailingList(MailingList):
    moderators: list[str] = None
    subscribers: list[str] = None

# Repository definitions
class GitRepository(CatalogObject):
    """A git repository"""
    id: str
    sourceURL: str
    mirrorURL: str = None
    project: str


class SubversionRepository(CatalogObject):
    """A subversion repository"""
    id: str
    sourceURL: str
    project: str


# Project definitions
class BaseProject(CatalogObject):
    """A short representation of a project with basic data"""
    id: str
    name: str
    website: str

class Project(BaseProject):
    """A comprehensive representation of a project"""
    mailinglists: typing.Optional[list[BaseMailingList]] = []
    chair: BasePerson | None
    committers: list[BasePerson] = []
    pmc_members: list[BasePerson] = []
    repositories: list[GitRepository|SubversionRepository] = []


ANY_CLASS = ExtendedPerson|Person|BasePerson|ExtendedMailingList|MailingList|GitRepository|SubversionRepository|Project|BaseProject
ANY_PUBLIC_CLASS = Person|BasePerson|MailingList|GitRepository|SubversionRepository|Project|BaseProject


class Collection:

    @staticmethod
    def shorthand(object_type: str|CatalogObject):
        """Converts a string or CatalogObject subclass into a shorthand definition slug,
        removing the Extended classifier from the name if present."""

        if issubclass(type(object_type), type(CatalogObject)):
            object_type = object_type.__name__
        return object_type.lower().removeprefix("extended")

    def __init__(self):
        """Initializes a collections cache. This can hold any number of lists of data objects defined in here."""
        self._cache = {}

    def replace(self, object_type: str, obj_list: list[ANY_CLASS] = None):
        """Replace the entire list of `object_type` objects in the cache with the new list, atomically"""
        oid = self.shorthand(object_type)
        self._cache[oid] = {
            obj.id: obj for obj in obj_list
        }

    def add(self, object: ANY_CLASS):
        """Adds an object to the cache lists. The bundle the object belongs to is automatically
        determined when adding."""
        oid = self.shorthand(object.__class__)
        if oid not in self._cache:
            self._cache[oid] = {}
        self._cache[oid][object.id] = object

    def list(self, object_type: str|CatalogObject):
        """Returns a complete list (tuple!) of all items of this type"""
        return tuple(self._cache.get(object_type, {}).values())

    def get(self, object_type: str|CatalogObject, **kwargs):
        """Fetches a single item of a type if all the kwargs items match the entry, otherwise returns None"""
        oid = self.shorthand(object_type)
        uid = kwargs.get("id")
        if kwargs == {"id": uid}:
            return self._cache[oid].get(uid)
        for entry in self._cache.get(oid, {}).values():
            if all (getattr(entry, k) == v for k,v in kwargs.items()):
                return entry

    def get_all(self, object_type: str|CatalogObject, **kwargs):
        """Returns all items of a certain type that matches the kwargs"""
        oid = self.shorthand(object_type)
        for entry in self._cache.get(oid, {}).values():
            if all (getattr(entry, k) == v for k,v in kwargs.items()):
                yield entry

# This is the standard (unfiltered) result set for auth'ed access.
class ResultSet(pydantic.BaseModel):
    results: list[ANY_CLASS]
    no_results: int = 0

# This is the public access result set, which downgrades from ANY_CLASS to ANY_PUBLIC_CLASS
class PublicResultSet(pydantic.BaseModel):
    results: list[ANY_PUBLIC_CLASS]
    no_results: int = 0

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
import logging
import typing

import asfquart

import app.concepts
import asyncio
import asfpy.clitools
import re
import time

LDAP_PEOPLE_BASE = "ou=people,dc=apache,dc=org"
LDAP_MEMBER_BASE = "cn=member,ou=groups,dc=apache,dc=org"
LDAP_CHAIRS_BASE = "cn=pmc-chairs,ou=groups,ou=services,dc=apache,dc=org"
LDAP_PMCS_BASE = "ou=project,ou=groups,dc=apache,dc=org"
LDAP_DN = "uid=%s,ou=people,dc=apache,dc=org"
LDAP_OWNER_FILTER = "(|(ownerUid=%s)(owner=uid=%s,ou=people,dc=apache,dc=org))"
LDAP_MEMBER_FILTER = "(|(memberUid=%s)(member=uid=%s,ou=people,dc=apache,dc=org))"
LDAP_ROOT_BASE = "cn=infrastructure-root,ou=groups,ou=services,dc=apache,dc=org"
LDAP_TOOLING_BASE = "cn=tooling,ou=groups,ou=services,dc=apache,dc=org"

LDAP_UID_RE = re.compile(r"^(?:uid=)?([^,]+).*$")

def short_uid(uid: str):
    xuid = LDAP_UID_RE.match(uid)
    if xuid:
        return xuid.group(1)
    return uid


async def find_people():
    results = await asfpy.clitools.ldapsearch_cli_async(ldap_base=LDAP_PEOPLE_BASE, ldap_scope="sub")
    people = []
    for result in results:
        if "uid" in result:  # If this is a committer, add them
            person = app.concepts.ExtendedPerson(
                id = result["uid"][0],
                name = result["cn"][0],
                primary_email = result["asf-committer-email"][0],
                account_created_ts=int(time.time()),
            )
            people.append(person)
    app.collectors.collection.replace("person", people)



async def find_projects():
    results = await asfpy.clitools.ldapsearch_cli_async(ldap_base=LDAP_PMCS_BASE, ldap_scope="sub")
    projects = []


    # Run through all projects alphabetically
    for result in sorted(results, key=lambda x: x.get("cn", ["??"])[0]):
        if "cn" in result:
            cn = result["cn"][0]
            prname = cn.capitalize()
            first_person = None
            project = app.concepts.Project(
                id = cn,
                name = f"Apache {prname}",  # this is just a test - we'll use committee-info.txt soon enough
                website = f"https://{cn}.apache.org",
                chair = None,
            )
            # committers
            for uid in result.get("member", []):
                asfid = short_uid(uid)
                if asfid:
                    person = app.collectors.collection.get("person", id=asfid)
                    project.committers.append(person)
                    if project not in person.projects:
                        person.projects.append(project)

            # PMC
            for uid in result.get("owner", []):
                asfid = short_uid(uid)
                if asfid:
                    person = app.collectors.collection.get("person", id=asfid)
                    if not first_person:
                        first_person = person
                    project.pmc_members.append(person)
                    if project not in person.projects:
                        person.projects.append(project)

            projects.append(project)

            # Assign a fake chair for now
            project.chair = first_person
            app.collectors.collection.replace("project", projects)
            await asyncio.sleep(0.1)


    app.collectors.collection.replace("project", projects)

async def scan():
    while True:
        await find_people()
        await find_projects()
        await asyncio.sleep(3600)


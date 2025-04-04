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

"""ASF Infrastructure Catalog Service"""
import itertools
import logging

import asfquart
import asfquart.generics
from asfquart.base import QuartApp

# Avoid OIDC for now by overriding default URLs
asfquart.generics.OAUTH_URL_INIT = "https://oauth.apache.org/auth?state=%s&redirect_uri=%s"
asfquart.generics.OAUTH_URL_CALLBACK = "https://oauth.apache.org/token?code=%s"


def create_app(app_dir: str | None = None, cfg_path: str | None = None):
    kwargs = {}
    if app_dir is not None:
        kwargs["app_dir"] = app_dir
    if cfg_path is not None:
        kwargs["cfg_path"] = cfg_path

    APP = asfquart.construct("catalog_service", **kwargs)
    APP.config.hostname = "catalog-test.apache.org"

    import app.collectors
    import app.renderers.lookup
    import app.renderers.static

    logging.basicConfig(
        level=logging.ERROR,
        format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    )


    # setup data bundle
    #APP.data = tasks.DataBundle(APP.cfg.base.data_dir)

    # setup url converters
    #APP.url_map.converters["date"] = converters.DateConverter
    #APP.url_map.converters["agenda_element"] = converters.AgendaElementConverter

    @APP.before_serving
    async def startup():
        """Setup app"""

        # load the initial data
#        await APP.data.load_data()

        # add background tasks
        APP.add_runner(app.collectors.ldap.scan, name=f"LDAP Scan:{APP.app_id}")

    @APP.after_serving
    async def shutdown():
        """Shutdown any running background tasks"""
        # APP.background_tasks.clear()
        pass

    return APP


def main() -> QuartApp:
    return create_app()


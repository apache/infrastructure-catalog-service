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

import asfquart
import asfquart.auth
import quart

# Static files (or index.html if requesting a dir listing)
@asfquart.APP.route("/<path:path>")
@asfquart.APP.route("/")
async def static_files(path="index.html"):
    if path.endswith("/"):
        path += "index.html"
    return await quart.send_from_directory("./htdocs/", path)

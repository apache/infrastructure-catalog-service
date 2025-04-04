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
import app.concepts.collections

collection = asfquart.APP.data

@asfquart.APP.route("/lookup")
@asfquart.APP.route("/lookup/<string:type>")
@asfquart.APP.route("/lookup/<string:type>/<string:uid>")
# Require membership for now, while we test
@asfquart.auth.require(asfquart.auth.Requirements.member)
async def lookup_public(type: str = "project", uid: str = None):
    query = await asfquart.utils.formdata()
    if uid:
        query["id"] = uid

    datatype = type.lower()

    # Quick hack to emulate anonymous access for now
    anonymous_data_only = query.pop("anonymous", "??") != "??"

    target = collection.list(datatype)

    if target and isinstance(target, tuple):
            # If anonymous access, we "downgrade" the data objects to their public versions
            # through pydantic "disinheritance", using a public result set that only accepts
            # the public parent versions of our extended data objects.
            # Thus, if anon, ExtendedPerson results get downgraded to Person
            if anonymous_data_only:
                result_set = app.concepts.collections.PublicResultSet(results=[])
            else:
                result_set = app.concepts.collections.ResultSet(results=[])
            for entry in target:
                entry_as_dict = entry.dict(include=query.keys())
                if all(entry_as_dict.get(k) == v for k,v in query.items()):
                    result_set.results.append(entry)
            result_set.no_results = len(result_set.results)
            if "schema" in query:
                return result_set.model_json_schema()
            else:
                as_json = True
                if "text/html" in quart.request.accept_mimetypes:
                    return f"""
<!doctype html>
<html>
  <head>
    <script src="/json.js"></script>
  </head>
  <body>
  <div id="main"></div>
  </body>
  <script type="text/ecmascript">
  function linkify() {{
    const result = document.getElementById("json").shadowRoot.querySelectorAll("span.value-data");
    for (const node of result) {{
        if (node.innerText.match(/^"https:\/\/.+"$/)) {{
            const link = document.createElement("a");
            link.href = node.innerText.substring(1, node.innerText.length-1);
            link.innerText = node.innerText;
            link.style.color = "var(--base0D)";
            node.innerText = "";
            node.appendChild(link);
        }}        
    }}
  }}
  const jsonViewer = document.createElement("andypf-json-viewer")
    jsonViewer.id = "json"
    jsonViewer.expanded = 4
    jsonViewer.indent = 2
    jsonViewer.showDataTypes = true
    jsonViewer.theme = "monokai"
    jsonViewer.showToolbar = true
    jsonViewer.showSize = true
    jsonViewer.showCopy = true
    jsonViewer.expandIconType = "square"
    jsonViewer.data = {result_set.model_dump_json(indent=2)}
    document.getElementById("main").appendChild(jsonViewer);
    addEventListener("DOMContentLoaded", linkify);
  
  </script>
</html>
                    """
                else:
                    return quart.Response(response=result_set.model_dump_json(indent=2), content_type="application/json")
    else:
        return quart.Response(response=f"No such object type, {datatype}", content_type="text/plain", status=400)

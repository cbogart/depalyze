import os
import json
import datetime
import pytz
import dateutil.parser
import versionhistory

def extract_author(row):
    try:
        if "maintainers" in row["doc"] and "email" in row["doc"]["maintainers"][0]:
            return row["doc"]["maintainers"][0]["email"]
        elif "author" in row["doc"]:
            return row["doc"]["author"]["name"]
        else:
            return ""
    except:
        return ""

    
def scan_npm_json(fname):
    with open(fname, "r") as f:
        npms = json.load(f)
    da = dict()
    dc = dict()
    dv = dict()
    for row in npms["rows"]:
        p = row["key"]
        if "time" not in row["doc"] or \
             ("unpublished" in row["doc"]["time"] and \
              "versions" not in row["doc"]["time"]):
            continue
        try:
            da[p] = extract_author(row)
            dc[p] = { v : dateutil.parser.parse(row["doc"]["time"][v]) for v in row["doc"]["versions"] }
            dv[p] = { v : dict() for v in row["doc"]["versions"] }
            for t in row["doc"]["versions"]:
                for deptype in ["dependencies"]:
                    for dep in row["doc"]["versions"][t].get(deptype, []):
                        if dep not in dv[p][t]:
                            dv[p][t][dep] = []
                        dv[p][t][dep].append((deptype, row["doc"]["versions"][t][deptype][dep]))
        except Exception, e:
            print "Skipping ",p,"because",e
            #import pdb
            #pdb.set_trace()

    vh = versionhistory.VersionHistories()
    vh.preload(da, dc, dv, datetime.datetime.now().replace(tzinfo=pytz.UTC))
    return vh



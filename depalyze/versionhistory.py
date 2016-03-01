from __future__ import print_function
import pdb
import pytz
import sys
import json
import dateutil.parser
from dateutil.relativedelta import relativedelta
import re
from collections import defaultdict
import datetime
from timeline.timeline import Timeline
import dateutil
from pointspans import PointSpans
from matplotlib import dates
from matplotlib import pyplot
import matplotlib
from pylab import *


class NotApplicable(Exception): 
    pass
class NoVersionsException(Exception):
    pass
standardRPackages = ["base","compiler","datasets",
     "grDevices","graphics","grid","methods","parallel",
     "splines","stats","stats4", "tcltk","utils"]
addOnRPackages = ["KernSmooth","MASS","Matrix","boot","class",
     "cluster","codetools","foreign","lattice","mgcv","nlme",
     "nnet","rpart", "spatial","survival"]
defaultLoaded = ["base","datasets","utils","grDevices",
     "graphics","stats","methods","R"]

def hashColor(key, selected = False):
    """Return a color unique for this key, brigher if selected.

    Of course the color can't really be unique because there are more keys
    in the world than colors; but the algorithm tries to make similar strings
    come out different colors so they can be distinguished in a chart or graph"""

    def tw(t): return t ^ (t << (t%5)) ^ (t << (6+(t%7))) ^ (t << (13+(t%11)))
    theHash = tw(hash(key) % 5003)
    ifsel = 0x00 if selected else 0x80
    (r,g,b) = (ifsel |  (theHash & 0x7f),
               ifsel | ((theHash>>8) & 0x7F),
               ifsel | ((theHash>>16) & 0x7F))
    return "#{0:02x}{1:02x}{2:02x}".format(r,g,b)

class VersionHistories():
    """Represent the version and dependency history of an entire software ecosystem

     self.da = name -> author   (or some other indicator of "togetherness" of a group of packages)
     self.dc = name -> version -> date,
     self.dv = name -> version -> import name-> [(type, versionrefstring)]

     self.end_of_time: the last date we have version history data about; e.g. today, if
             dataset is current
    """

    def __init__(self):
        self.da = {}
        self.dc = {}
        self.dv = {}
        self.auxdata = {}
        self.depscache = {}
        self.rdepscache = {}
        self.logwith = lambda *k: print(*k)
        self.end_of_time = datetime.datetime.now().replace(tzinfo=pytz.UTC)

    def serialize(self):
        return {"da": self.da, 
                "dc": self.dc, 
                "dv": self.dv, 
                "aux": self.auxdata, 
                "eot": self.end_of_time, 
                "deps": self.depscache, 
                "rdeps": self.rdepscache}

    def deserialize(self, dct):
        self.preload(dct["da"], dct["dc"], dct["dv"], dct["eot"]) 
        self.depscache = dct["deps"]
        self.rdepscache = dct["rdeps"]
        self.auxdata = dct["aux"] if "aux" in dct else {}
        self.logwith("Loaded ", len(list(self.packages())), "packages")

    def get_aux(self, key):
        return self.auxdata[key]

    def set_aux(self, key, data):
        self.auxdata[key] = data

    def set_end_of_time(self, end_of_time):
        self.end_of_time = end_of_time
        if self.end_of_time.tzinfo is None:
            self.end_of_time = self.end_of_time.replace(tzinfo=pytz.UTC)

    def force_timezone_awareness(self):
        if self.end_of_time.tzinfo is None:
            self.end_of_time = self.end_of_time.replace(tzinfo=pytz.UTC)
        for p in self.dc:
            for v in self.dc[p]:
                if self.dc[p][v].tzinfo is None:
                    self.dc[p][v] = self.dc[p][v].replace(tzinfo=pytz.UTC)

    def validate(self):
        for p in self.dc:
            assert p in self.dv, "Not all packages in dv: " + p
        for p in self.dv:
            assert p in self.dc, "Not all packages in dc: " + p
        for p in self.dv:
            assert isinstance(p, basestring), "weird package " + str(p)
            for v in self.dv[p]:
                assert isinstance(v, basestring), "weird version " + p + " v" + str(v)
                for d in self.dv[p][v]:
                    assert isinstance(d, basestring), "weird dependency " + p + " v" + v + " d" + str(d)
                    for (tag,constraint) in self.dv[p][v][d]:
                        assert isinstance(tag, basestring) and isinstance(constraint, basestring), \
                             "Bad contents of dv at " + str((p,v,d)) + ":" + str(self.dv[p][v][d])

    def preload(self, da, dc, dv, end_of_time):
        self.da = da
        self.dc = dc
        self.dv = dv
        self.depscache = {}
        self.rdepscache = {}
        self.end_of_time = end_of_time
        self.force_timezone_awareness()

    def logging(self, logfn):
        self.logwith = logfn

    def dep_version_spans(self, package, dep):
        """list of dependency version ref strings, and the timespan over which they were valid"""
        ps = PointSpans()
        for v in self.versions(package):
            if dep in self.dv[package][v] and len(self.dv[package][v][dep]) > 0:
                ps.addchange(self.dv[package][v][dep][0][1], self.dc[package][v])
            else:
                ps.addchange(None, self.dc[package][v])
        return list(ps.foreach(self.end_of_time))

    def buildReverseDependencies(self):
        """Find and cache reverse dependency information

        This is slow, so don't run it if not necessary

        """
        self.rdepscache = defaultdict(set)
        self.rdeptimes = defaultdict(defaultdict)
        self.logwith(str(len(self.dc.keys())) + " packages to process")
        pcount = 0
        for p in self.dc.keys():
            pcount = pcount + 1
            if (pcount % 1000 == 0):
                self.logwith("   package #"+ str(pcount)+ ":" + str(p))
            for d in self.dependencies(p):
                self.rdepscache[d].add(p)
                self.rdeptimes[d][p] = self.dep_version_spans(p, d)
        self.logwith("   ...Done with reverse dependencies")

    def versions(self, package):
        """List all known versions of this package, in chrono order"""
        return sorted(self.dc[package].keys(), key=lambda v: self.dc[package][v])

    def date_of_version(self, package, version): return self.dc[package][version]

    def reverse_dependencies(self, package):
        if len(self.rdepscache) == 0:
            self.buildReverseDependencies()
        return self.rdepscache[package]

    def present_transitive_dependencies(self, package, skip=set()):
        deps = set(self.present_dependencies(package)) - skip
        deps1 = set()
        for d in deps:
            deps1 = deps1 + self.present_transitive_dependencies(d, deps + skip)
        return deps + deps1 - skip

    def present_dependencies(self, package):
        return [d for d in self.dv[package][self.latest_version(package)] if d in self.dc]

    def dependencies(self, package):
        """List all packages that have ever been dependencies of a package"""
        if package not in self.depscache:
            depset = set()
            for v in self.dv[package]:
                for dep in self.dv[package][v]:
                    depset.add(dep)
            self.depscache[package] = depset 
        return self.depscache[package]

    def showTimeline(self, package, abortIfBoring = False, colwidth = 20, file=None):
        """Textual timeline visualization of versions and dependencies of a package

        Shows version changes to a package, version changes to its dependencies
        and reverse dependencies, and changes to the version numbers specified in
        the dependency links.

        package: the "focal" package to build the visualization around
        returns: yields a list of strings that can be printed out
        """
        self.logwith("Building timeline for"  + str(package))
        if len(self.rdepscache) == 0:
            self.buildReverseDependencies()
        history = []  # (time, column#, text), column = "revdep", "focal", or "dep"
    
        deps = self.dependencies(package)
        revdeps = self.rdeptimes[package].keys()
        self.logwith("Package: " + package)
        for v in self.versions(package):
            history.append((self.dc[package][v], "focal", package + " v" + v))
    
        self.logwith("Dependencies: " + ",".join(deps))
        self.logwith("Reverse Dependencies:" + ",".join(revdeps))
    
        if (abortIfBoring and (len(deps) == 0 or len(revdeps) == 0)):
            raise Exception("uninteresting package: ", package)
    
        for d in deps:
            self.logwith("   Dep: "+ str(d))
            try:
                for depver in self.dc[d]:
                     history.append((self.dc[d][depver], "dep", d + " v" + depver))
            except Exception ,e:
                self.logwith("     No dep info available for " + str(d) + " Error: " + str(e))
            try:
                for (k,st,en) in self.rdeptimes[d][package]:
                     history.append((st, "dep", "ref: " + package + " -> " + d + " v" + k))
                     #history.append((en, "dep", "ref: " + package + " -> " + d + " v" + k + " (end)"))
            except Exception ,e:
                self.logwith("     No2 dep info available for " + str(d) + " Error: " + str(e))
        for r in revdeps:
            self.logwith("   RevDep: "+str(r))
            try:
                for rdepver in self.dc[r]:
                     history.append((self.dc[r][rdepver], "revdep", r + " v" + rdepver))
            except Exception ,e:
                self.logwith("     No reverse dep info available for " + str(d) + "  Error:" + str(e))
            try:
                for (k,st,en) in self.rdeptimes[package][r]:
                     history.append((st, "revdep", "ref: " + r + " -> " + package + " v" + k))
                     #history.append((en, "revdep", "ref: " + r + " -> " + package + " v" + k + " (end)"))
            except Exception ,e:
                self.logwith("     No2 reverse dep info available for " + str(d) + "  Error:" + str(e))
        history = sorted(history, key=lambda (k,c,t): k)
        lasttime = ""
       
        format = "%25s   %{}s   %{}s   %{}s".format(colwidth, colwidth, colwidth)
        op = [format % ("Time", "Dependency changes", package, "Downstream dependencies")]
        for (tstamp,colname,text) in history:
            (tempus, tleft, tmid, tright) = ("", "","","")
            try:
                tempus = tstamp.strftime("%Y-%m-%d")
            except Exception, e:
                self.logwith("Invalid date", str(tstamp), e)
                tempus = "(bad date)"
            if (tempus == lasttime):
                tempus = ""
            else:
                lasttime = tempus
            if colname == "revdep": tright = text
            if colname == "focal": tmid = text
            if colname == "dep": tleft = text
            op.append(format % (tempus,tleft,tmid,tright))
        if file == None:
            return op
        else:
            with open(file, "w") as f:
                f.write("\n".join(op).encode('ascii','ignore'))

    def packages_by_author(self, author_match):
        """Return [(packagename, author)] list of pairs, where author_match is a substring of author"""
        for p in self.da:
            if author_match in self.da[p]:
                yield (p, self.da[p])

    def packages(self):
        for p in self.dc:
            yield p

    def interesting_packages(self):
        for p in self.packages():
            try:
                i = self.interesting(p)
                if i is not None:
                    yield i
            except Exception, e:
                self.logwith("Error checking interestingness of ", p, ":", e)

    def recently_active(self, p, recent_date = None, activity_level = 2):
        if recent_date is None:
            recent_date = self.end_of_time.replace(year = self.end_of_time.year - 1)
        recent_changes = [v for v in self.versions(p) if self.dc[p][v] > recent_date]
        return len(recent_changes) >= activity_level
            
    def latest_version(self, p): 
        try:
            return self.versions(p)[-1]
        except:
            raise NoVersionsException(p)

    def downstreamer(self, p, explain=False):
        """Criteria for determining that a package might pose interesting challenges
        for its author(s) in keeping up with dependencies"""

        if explain:
            self.logwith("Interestingness test for ", p)

        auth = self.author(p)
        # Less than three downstreams
        # at least three *changes* in version to some upstream package
        # poor string similarity with upstream package's author

        #rd = self.reverse_dependencies(p)
        #rds = [r for r in rd if self.author(r) != auth]
        #small_downstream = len(rds) < 4
        #if (small_downstream and explain):
        #    self.logwith("\tSmall downstream:", auth, "!=", ",".join([self.author(d) for d in rds]))

        # http://stackoverflow.com/questions/18715688/find-common-substring-between-two-strings
        def longestSubstringFinder(string1, string2):
            answer = ""
            len1, len2 = len(string1), len(string2)
            for i in range(len1):
                match = ""
                for j in range(len2):
                    if (i + j < len1 and string1[i + j] == string2[j]):
                        match += string2[j]
                    else:
                        if (len(match) > len(answer)): answer = match
                        match = ""
            return answer


        pd = self.present_dependencies(p)
        best = ""
        for upstr in pd:
            vch = self.dep_versions(p, upstr)
            if len(vch) > 8:
                 if explain:
                     self.logwith("\t" + str(len(vch)) + " changes to upstream " + upstr)
                 common = longestSubstringFinder(self.author(p), self.author(upstr))
                 if explain:
                     self.logwith("\tLongest common author substring is " + common)
                 if len(common) < 8:
                     best = upstr
                     break
            elif explain:
                 self.logwith("\t",p,"'s upstream",upstr,"doesn't have many version changes:",vch)

        if best == "" and explain:
            self.logwith("\t", p, "has no upstreams with lots of version changes")
        return best != ""

    def interesting(self, p, explain=False):
        """Criteria for determining that a package might pose interesting challenges
        for its author(s) in keeping up with dependencies"""

        if explain:
            self.logwith("Interestingness test for ", p)
            #import pdb
            #pdb.set_trace()

        auth = self.author(p)

        pd = self.present_dependencies(p)
        pds = [d for d in pd if self.author(d) != auth]
        diverse_upstream = len(pds) > 2
        if (diverse_upstream and explain):
            self.logwith("\tDiverse upstream:", auth, "!=", ",".join([self.author(d) for d in pds]))

        busy_upstreams = len([d for d in pds if self.recently_active(d)]) > 1
        if (busy_upstreams and explain):
            self.logwith("\tBusy upstream:", ','.join([d for d in pds if self.recently_active(d)]))

        rd = self.reverse_dependencies(p)
        rds = [r for r in rd if self.author(r) != auth]
        diverse_downstream = len(rds) > 2
        if (diverse_downstream and explain):
            self.logwith("\tDiverse downstream:", auth, "!=", ",".join([self.author(d) for d in rds]))

        recently_updated = (self.end_of_time - self.dc[p][self.latest_version(p)]).total_seconds() < 365*24*24*60;
        if (recently_updated and explain):
            self.logwith("\tRecently updated:", self.latest_version(p), " update on ", self.dc[p][self.latest_version(p)])

        if (diverse_upstream and diverse_downstream and recently_updated and busy_upstreams):
            return (p, pd, rd)
        else:
            return None

    def dep_version_changes(self, p):
        """List of circumstances (version) when package changed what version of dep it pointed to"""
        lastversion = ""
        result = {}
        for v in self.versions(p):
            thisversion = json.dumps(self.dv[p][v], indent=4)
            if thisversion != lastversion:
                result[v] = thisversion
            lastversion = thisversion
        return result

    def dep_versions(self, p, dep):
        """List of circumstances (version) when package changed what version of dep it pointed to"""
        lastversion = ""
        result = {}
        for v in self.versions(p):
            if dep in self.dv[p][v] and len(self.dv[p][v][dep]) > 0:
                thisversion = self.dv[p][v][dep][0][1]
                if thisversion != lastversion:
                    result[v] = thisversion
                lastversion = thisversion
            else:
                thisversion = ""
                if thisversion != lastversion:
                    result[v] = thisversion
                lastversion = thisversion
        return result

    def todo(self):
        """Functions still to be ported from previous implementation

    def allHistories(self):
        (rd, rdt) = buildReverseDependencies()
        for pk in npmKeys(npms):
            try:
                timel = list(showTimeline(pk, rd, rdt))
                pkn = pk.replace("/", "_")
                with open ("timelines/" + pkn + ".timeline.txt", "w") as f:
                    f.write("\n".join(timel))
            except Exception, e:
                print e
        """

    def author(self, p): return self.da.get(p,"")

    def graph_package_deps(self, p, pngname):
    
        tl = Timeline()
        
        def epoch(t): return t.toordinal() #float(t.strftime("%s"))
       
        def authColor(p): return hashColor(self.author(p))

        #depbar = "LightSkyBlue"
        #focalbar = "Yellow"
        reflbar = "PaleGoldenrod"
        

        vers_names = self.versions(p)

        # extend each version until the end of hte subsequent version
        for v,w in zip(vers_names[:-1], vers_names[1:]):     # Lost author for author color
            tl.span(p, epoch(self.dc[p][v]), epoch(self.dc[p][w]), p + ":" + v, v, authColor(p), None)
        vlast = vers_names[-1]
        tl.span(p, epoch(self.dc[p][vlast]), epoch(self.end_of_time), p + ":" + vlast, vlast, authColor(p), None)
    
        for dep in self.dependencies(p):
            for (ref,st,en) in self.dep_version_spans(p, dep):
                tl.span(dep, epoch(st), epoch(en), dep + "::" + ref, ref, reflbar, "bottom")
    
            depvers = self.dep_versions(p, dep)
            try:
                vn2 = self.versions(dep)
                for vv,ww in zip(vn2[:-1], vn2[1:]):
                    self.logwith( "deploop", vv,ww, self.dc[dep].keys())
                    tl.span(dep, epoch(self.dc[dep][vv]), epoch(self.dc[dep][ww]),
                            dep + ":" + vv, vv, authColor(dep), "top") 
                vvlast = vn2[-1]
                tl.span(dep, epoch(self.dc[dep][vvlast]), epoch(self.end_of_time),
                       dep + ":" + vvlast, vvlast, authColor(dep), "top") 
            except Exception, e:
                self.logwith("Exception processing dependency", dep, e)
            for vn in vers_names:
                if vn in depvers:
                    dep_ver = self.extractVersionLimiter(depvers[vn])
                    self.logwith( dep_ver)
                    destrec = tl.findByKey(dep + ":" + dep_ver)
                    srcrec = tl.findByKey(p + ":" + vn)
                    if len(destrec) > 0 and len(srcrec) > 0:
                        tl.connect(destrec[0], srcrec[0])
                        self.logwith( "version", vn, "of", p, "did link to dependency", dep, "version", dep_ver)
                    else:
                        self.logwith( "version", vn, "of", p, "***can't*** find dependency", \
                               dep, "version", dep_ver, "lendestrec=", len(destrec), "lensrcrec=", len(srcrec))
                else:
                    self.logwith(vn,"is not in",list(depvers))
                    self.logwith( "version", vn, "of", p, "did not update dependency on", dep)
    
        try:
            fig, ax = plt.subplots(figsize=(100,max(7, 3*len(tl.categories()))))
            tl.draw_time_axis(ax, limit_view_category=p)
            tl.draw_bars(ax)
            tl.draw_connections(ax)
            t = plt.title("Upstream dependencies: packages that " + p + " depends on\n ", fontsize=90)
            savefig(pngname, bbox_extra_artists=[t], bbox_inches="tight")
        except Exception, e:
            import traceback
            traceback.print_exc()
            print("Error drawing figure for ", p, ":", e)
        plt.close("all")

    def average_update_frequency(self):
        return self.average_update_frequency_criterion( lambda p: True)

    def average_update_frequency_of_upstreams(self):
        return self.average_update_frequency_criterion(
            lambda p: len(list(self.reverse_dependencies(p))) > 0)


    def average_update_frequency_criterion(self, criterion):
        countable = 0
        auf = 0.0
        for p in self.packages():
            try:
                if criterion(p):
                    uf = self.update_frequency(p)
                    auf = auf + uf
                    countable += 1
            except NotApplicable:
                pass
        print("Of", countable)
        return auf/countable

    def average_dependency_update_frequency(self):
        countable = 0
        auf = 0.0
        for p in self.packages():
            try:
                uf = self.dependency_update_frequency(p)
                auf = auf + uf
                if (uf > 1.5):
                    pass
                    #print("Package",p,"Has short dependency update frequency of",uf, (1.0/uf))
                    #pdb.set_trace()
                countable += 1
            except:
                pass
        print("Of", countable)
        return auf/countable

    def update_frequency(self, p):
        """How many times per day was package updated (usually a fraction less than one)"""
        num_updates = len(self.versions(p))
        dates = [self.dc[p][ver] for ver in self.dc[p]]
        span = max(dates)-min(dates)
        if len(dates) < 2:
            print(p,"has only one revision")
            import pdb
            if p == "relimp": pdb.set_trace()
            raise NotApplicable(p)
        elif span.days == 0:
            return 0
        else:
            return (num_updates-1)*1.0/span.days    

    def dependency_update_frequency(self, p):
        num_updates = len(self.dep_version_changes(p))
        dates = [self.dc[p][ver] for ver in self.dc[p]]
        span = max(dates)-min(dates)
        if (len(list(self.reverse_dependencies(p))) == 0):
            raise Exception("Package without deps")
        return (num_updates-1)*1.0/span.days    



    def graph_package_downstreams(self, p, pngname):
    
        tl = Timeline()
        
        def epoch(t): return t.toordinal() #float(t.strftime("%s"))
       
        def authColor(p): return hashColor(self.author(p))

        reflbar = "PaleGoldenrod"
        
        vers_names = self.versions(p)

        # Just show the first 20; the image gets too big otherwise
        for dep in list(self.reverse_dependencies(p))[:20]:
            for (ref,st,en) in self.dep_version_spans(dep, p):
                try:
                    vname = str(ref).strip()
                    if vname == "": vname = "*"
                except:
                    self.logwith("Could not correct version name ", ref)
                    vname = ref
                tl.span(dep, epoch(st), epoch(en), dep + "::" + ref, "-->" + vname, reflbar, "bottom", invisibleBar=True)
    
            depvers = self.dep_versions(dep, p)
            try:
                vn2 = self.versions(dep)
                for vv,ww in zip(vn2[:-1], vn2[1:]):
                    self.logwith( "deploop", vv,ww, self.dc[dep].keys())
                    tl.span(dep, epoch(self.dc[dep][vv]), epoch(self.dc[dep][ww]),
                            dep + ":" + vv, vv, authColor(dep), "top") 
                vvlast = vn2[-1]
                tl.span(dep, epoch(self.dc[dep][vvlast]), epoch(self.end_of_time),
                       dep + ":" + vvlast, vvlast, authColor(dep), "top") 
            except Exception, e:
                self.logwith("Exception processing dependency", dep, e)
            for vn in vers_names:
                if vn in depvers:
                    dep_ver = self.extractVersionLimiter(depvers[vn])
                    self.logwith( dep_ver)
                    destrec = tl.findByKey(dep + ":" + dep_ver)
                    srcrec = tl.findByKey(p + ":" + vn)
                    if len(destrec) > 0 and len(srcrec) > 0:
                        tl.connect(destrec[0], srcrec[0])
                        self.logwith( "version", vn, "of", p, "did link to dependency", dep, "version", dep_ver)
                    else:
                        self.logwith( "version", vn, "of", p, "***can't*** find dependency", \
                               dep, "version", dep_ver, "lendestrec=", len(destrec), "lensrcrec=", len(srcrec))
                else:
                    self.logwith(vn,"is not in",list(depvers))
                    self.logwith( "version", vn, "of", p, "did not update dependency on", dep)

        # extend each version until the end of hte subsequent version
        for v,w in zip(vers_names[:-1], vers_names[1:]):     # Lost author for author color
            tl.span(p, epoch(self.dc[p][v]), epoch(self.dc[p][w]), p + ":" + v, v, authColor(p), None)

        vlast = vers_names[-1]
        tl.span(p, epoch(self.dc[p][vlast]), epoch(self.end_of_time), p + ":" + vlast, vlast, authColor(p), None)
    
    
        try:
            fig, ax = plt.subplots(figsize=(100,max(7, 3*len(tl.categories()))))
            tl.draw_time_axis(ax, limit_view_category=p)
            tl.draw_bars(ax)
            tl.draw_connections(ax)
            t = plt.title("Downstream dependencies: packages that depend on " + p + "\n ", fontsize=90)
            savefig(pngname, bbox_extra_artists=[t], bbox_inches="tight")
        except Exception, e:
            import traceback
            traceback.print_exc()
            print("Error drawing figure for ", p, ":", e)
        plt.close("all")

    vlimit = re.compile("\d[\.[a-z_A-Z0-9-]]+")
    def extractVersionLimiter(self, limit):
        ans = VersionHistories.vlimit.search(limit)
        if ans is None:
            return ""
        else:
            return "/" + str(ans.group(0))

    def investigate(self, plots, colwidth=20):
        for (p, pd, rd) in self.interesting_packages():
            self.dumpVis(plots, p, colwidth=colwidth)

    def dumpVis(self, plots, p, colwidth=20):
        self.showTimeline(p, colwidth=colwidth, file=plots + "/" + p + ".timeline.txt")
        self.graph_package_deps(p, plots + "/" + p + ".svg")
        self.graph_package_downstreams(p, plots + "/" + p + ".down.svg")

    def versionAsOf(self, p, asOfDate):
        "What version of package p was newest as of some date?"
        maxver = None
        maxverdate = datetime.datetime(1971,1,1,0,0,tzinfo=pytz.UTC)
        for (ver, verdate) in self.dc[p].iteritems():
            if verdate > maxverdate and verdate < asOfDate:
                maxver = ver
                maxverdate = verdate
        return maxver

    def depCountAsOf(self, p, asOfDate):
        "How many dependencies did package p have as of some date?"
        v = self.versionAsOf(p, asOfDate)
        return len(set(self.dv[p][v].keys()) - set(defaultLoaded))

    def depCountsAll2versions(self, asOfDate):
        for p in self.dv:
          if self.numDistinctVersionDates(p) > 1:
            try:
                yield self.depCountAsOf(p,asOfDate)
            except KeyError:
                pass

    def depCountsAll(self, asOfDate):
        for p in self.dv:
            try:
                yield self.depCountAsOf(p,asOfDate)
            except KeyError:
                pass

    def numDistinctVersionDates(self, p):
        return len(set(self.dc[p].values()))

    def graphDepCountDistribution(self, asOfDate, pngfile, yaxisVisible=True, distinctVersionsOnly = True):

        import numpy as np
        import matplotlib.mlab as mlab
        import matplotlib.pyplot as plt

        import pdb; pdb.set_trace()
        if distinctVersionsOnly:
            x = list(self.depCountsAll2versions(asOfDate))
        else:
            x = list(self.depCountsAll(asOfDate))
        print(len(x), "packages considered", sum(x)*1.0/len(x), "average #deps", len([x1 for x1 in x if x1>20]), "more than 20")
        # the histogram of the data
        plt.rc('xtick', labelsize=20)
        plt.rc('ytick', labelsize=20)
        n, bins, patches = plt.hist(x, max(x)+1, normed=1, facecolor='green', alpha=0.75)
        
        # add a 'best fit' line
        
        #plt.xlabel('Dependency count')
        #plt.ylabel('Probability')
        #plt.title(r'Histogram of Dependencies')
        plt.axis([0, 20, 0, 0.4])
        #if (not yaxisVisible):
        #    plt.axes().get_yaxis().set_visible(False)
        plt.grid(False)
        
        plt.savefig(pngfile, bbox_inches="tight")
        #plt.show()

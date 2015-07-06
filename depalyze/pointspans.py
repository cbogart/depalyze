import dateutil.parser
import datetime

class PointSpans:
    """Manage named timespans, defined by point state changes, merging those that are adjacent and have
    the same name"""
    def __init__(self):
        self.points = []

    def addchange(self, name, changetime):
        assert type(changetime) is datetime.datetime, \
              "called addchange with type" + str(type(changetime)) + " " + str(changetime)
        self.points.append((name, changetime))

    def foreach(self, endtime):
        assert type(endtime) is datetime.datetime, \
              "called foreach with type" + str(type(endtime)) + " " + str(endtime)
        self.merge()
        spans = sorted(self.points, key=lambda (n,t): t)
        for (s,e) in zip(spans, spans[1:] + [("", endtime)]):
            if (e[1]>s[1] and s[0] != None):
                yield (s[0], s[1], e[1])

    def merge(self):
        from inspect import getouterframes, currentframe
        def mergerec(items):
            if (len(items) < 2):
                return items
            rest = mergerec(items[1:])
            if len(rest) and items[0][0] == rest[0][0]:
                return [items[0]] + rest[1:]
            else:
                return [items[0]] + rest
        self.points = mergerec(self.points)

    def test(self):
        a = PointSpans()
        d3 = dateutil.parser.parse("2001-3-1")
        d5 = dateutil.parser.parse("2001-5-1")
        d7 = dateutil.parser.parse("2001-7-1")
        d9 = dateutil.parser.parse("2001-9-1")
        d11 = dateutil.parser.parse("2001-11-1")
        a.addchange("a", d3)
        a.addchange("a", d5)
        a.addchange("b", d7)
        a.addchange("a", d9)

        assert list(a.foreach(d11)) == [("a",d3,d7),("b",d7,d9),("a",d9,d11)], str(a.foreach(d11))

PointSpans().test()

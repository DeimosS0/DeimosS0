"""GitHub contribution data for the generated panels: the last 12 months' calendar and the all-time total."""
import json
import math
import os
import urllib.request

USER = "DeimosS0"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
QUARTILES = ["FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

CALENDAR = """{user(login:"%s"){contributionsCollection{contributionYears
  contributionCalendar{weeks{contributionDays{date weekday contributionCount contributionLevel}}}}}}"""
YEAR = """y%d:contributionsCollection(from:"%d-01-01T00:00:00Z",to:"%d-12-31T23:59:59Z"){
  contributionCalendar{totalContributions}}"""


def gql(query):
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": query}).encode(),
                                 {"Authorization": f"bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def fetch():
    """Calendar weeks of the last 12 months and the all-time contribution count."""
    cc = gql(CALENDAR % USER)["contributionsCollection"]
    years = gql('{user(login:"%s"){%s}}' % (USER, " ".join(YEAR % (y, y, y) for y in cc["contributionYears"])))
    return cc["contributionCalendar"]["weeks"], sum(v["contributionCalendar"]["totalContributions"] for v in years.values())


def level(xp):
    """Level n starts at 5·(n-1)² XP, one XP per contribution."""
    return math.isqrt(xp // 5) + 1


def streaks(counts):
    """Current and best run of days with contributions; today may still be empty without breaking the run."""
    best = run = 0
    for n in counts:
        run = run + 1 if n else 0
        best = max(best, run)
    i, cur = len(counts) - 1, 0
    if counts and not counts[i]:
        i -= 1
    while i >= 0 and counts[i]:
        cur, i = cur + 1, i - 1
    return cur, best

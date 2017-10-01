import os
from operator import itemgetter, attrgetter


from flask import session, redirect, url_for, escape, request


import xml.etree.ElementTree as ET

from settings import *


def parse_xml(filename):
    tree = ET.parse(filename)
    return tree.getroot()


def get_contest_config():
    if "contest" in session:
        return parse_xml(os.path.join(IJE_PATH, session["contest"] + ".xml"))
    else:
        return None

def is_login_valid(login, password):
    contest_config = get_contest_config()
    if contest_config is None:
        return False
    for party_xml in contest_config.iter("party"):
        if party_xml.attrib["id"] == login:
            if party_xml.attrib["password"] == password:
                return True
            return False
    return False


def is_contest_valid(contest_id):
    if "login" in session:
        return False
    contests = contests_list()
    for contest in contests:
        if contest["id"] == contest_id:
            return True
    return False


def can_submit():
    return "login" in session and "contest" in session


def can_view_messages():
    return "login" in session and "contest" in session


to_short_verdict = {
    "accepted": "AC",
    "wrong-answer": "WA",
    "presentation-error": "PE",
    "time-limit-exceeded": "TL",
    "idleness-limit-exceeded": "IL",
    "memory-limit-exceeded": "ML",
    "compilation-error": "CE",
    "runtime-error": "RE",
    "not-tested": "NT",
    "fail": "FL",
}


def get_messages():
    contest_xml = get_contest_config()
    submits_xml = parse_xml(os.path.join(CONFIG_PATHS["results_dir"], contest_xml.attrib["submits"]))
    show_comment = contest_xml.get("showcomment") == "true"
    show_test = contest_xml.get("showtest") == "true"
    submits = []
    for submit_xml in submits_xml.iter("submit"):
        if submit_xml.attrib["party"] == session["login"]:
            comment = submit_xml.attrib["comment"]
            test = submit_xml.get("test")
            if not show_comment and submit_xml.get("outcome") != "compilation-error":
                comment = ""
            if not show_test or test == "0":
                test = ""
            submits.append({"problem": submit_xml.attrib["problem"], "id": int(submit_xml.attrib["id"]),
                            "time": int(submit_xml.attrib["time"]), "verdict": to_short_verdict[submit_xml.attrib["outcome"]],
                            "comment": comment, "language": submit_xml.attrib["language-id"],
                            "test": test})
    submits = sorted(submits, key=itemgetter("time"), reverse=True)
    return submits
    #return [{"problem": "01.A", "id": "5", "time": 55, "verdict": "WA", "comment": "2nd nummbers differ"},
            #{"problem": "01.B", "id": "5", "time": 65, "verdict": "AC", "comment": ""}]


def get_contest_time():
    contest_xml = get_contest_config()
    results_xml = parse_xml(os.path.join(CONFIG_PATHS["results_dir"], contest_xml.attrib["monitor"]))
    time = results_xml.attrib["time"]
    return time


def can_view_monitor():
    return "contest" in session


def get_results():
    contest_xml = get_contest_config()
    results_xml = parse_xml(os.path.join(CONFIG_PATHS["results_dir"], contest_xml.attrib["monitor"]))
    results = []
    for team_xml in results_xml.iter("party"):
        team = {"id": team_xml.attrib["id"],
                "name": team_xml.attrib["name"],
                "solved": int(team_xml.attrib["solved"]),
                "penalty": int(team_xml.attrib["time"]),
                "results": []
                }
        for problem_xml in team_xml.findall("problem"):
            solved = int(problem_xml.attrib["solved"]) > 0
            tries = abs((int(problem_xml.attrib["solved"])))
            time = -1
            if tries != 0:
                time = problem_xml.findall("submit")[tries - 1].attrib["time"]
            if time == -1:
                team["results"].append({"verdict": "", "time": "", "style": "NO"})
                continue
            time = int(time)
            if solved:
                if tries == 1:
                    team["results"].append({"verdict": "+", "time": time, "style": "AC"})
                else:
                    team["results"].append({"verdict": "+" + str(tries - 1), "time": time, "style": "AC"})
            else:
                team["results"].append({"verdict": "-" + str(tries), "time": time, "style": "RJ"})
        results.append(team)
    results = sorted(results, key=itemgetter("penalty"))
    results = sorted(results, key=itemgetter("solved"), reverse=True)
    if len(results) == 0:
        return results
    results[0]["place"] = 1
    for i in range(1, len(results)):
        if (results[i]["solved"], results[i]["penalty"]) == (results[i - 1]["solved"], results[i - 1]["penalty"]):
            results[i]["place"] = results[i - 1]["place"]
        else:
            results[i]["place"] = i + 1
    for team in results:
        team["solved_parity"] = ["group_even", "group_odd"][team["solved"] % 2]
    return results
    #return [{"id": "NN1", "name": "Суперкоманда 1", "results": [
                #{"verdict": "+", "time": "01:23"},
                #{"verdict": "-4", "time": "02:23"}
            #], "score": 1, "penalty": "83", "place": 1},
            #{"id": "NN2", "name": "Суперкоманда 2", "results": [
                #{"verdict": "+3", "time": "01:20"},
                #{"verdict": ".", "time": ""}
            #], "score": 1, "penalty": "140", "place": 2}]


def contests_list():
    contests_xml = parse_xml(CONFIG_PATHS["contests"])
    contests = []
    for contest_xml in contests_xml.iter("acm-contest"):
        config_path = contest_xml.attrib["settings"]
        config_xml = parse_xml(os.path.join(IJE_PATH, config_path))
        contests.append({"id": config_path[:-4], "name": config_xml.attrib["title"], "config_path": os.path.join(IJE_PATH, config_path)})
    return contests


def get_contest_name(id):
    contests = contests_list()
    for contest in contests:
        if contest["id"] == id:
            return contest["name"]
    return None


def get_contest_status_time():
    contest_xml = get_contest_config()
    results_xml = parse_xml(os.path.join(CONFIG_PATHS["results_dir"], contest_xml.attrib["monitor"]))
    time = results_xml.attrib["time"]
    status = results_xml.attrib["status"]
    length = results_xml.attrib["length"]
    return status + ", " + time + " из " + length


def problems_list():
    config_xml = get_contest_config()
    problems = []
    for problem_xml in config_xml.iter("problem"):
        problems.append({"id": problem_xml.attrib["id"], "name": problem_xml.attrib["name"]})
    return problems
    #return [{"id": "01.A", "name": "problem A"}, {"id": "01.B", "name": "problem 2"}]


def languages_list():
    ije_xml = parse_xml(CONFIG_PATHS["ije"])
    languages = []
    for language_xml in ije_xml.iter("language"):
        languages.append({"id": language_xml.attrib["id"], "name": language_xml.attrib["name"]})
    return languages
    #return [{"id": "cpp", "name": "C++"}, {"id": "pas", "name": "Pascal"}]


def replace_pattern(pattern, c, fill):
    need_len = pattern.count(c)
    if len(fill) < need_len:
        fill = "0" * (need_len - len(fill)) + fill
    if len(fill) > need_len:
        fill = fill[(len(fill) - need_len):]
    return pattern.replace(c * need_len, fill)


def get_filename(problem, language):
    ije_xml = parse_xml(CONFIG_PATHS["ije"])
    pattern = ije_xml.get("solutions-format")
    pattern = replace_pattern(pattern, "@", session["login"])
    pattern = replace_pattern(pattern, "#", problem.split(".")[0])
    pattern = replace_pattern(pattern, "$", problem.split(".")[1])
    return os.path.join(CONFIG_PATHS["solutions_dir"], pattern + "." + language)


def get_submission_source(problem, submission_id, time, language):
    filename = "{}_{}_{}_{}.{}".format(session["login"], problem.replace(".", ""), time, submission_id, language)
    path = os.path.join(CONFIG_PATHS["archive_dir"], problem, filename)
    if not os.path.isfile(path):
        return u"Невозможно получить исходный код."
    with open(path, "r") as file:
        source = file.read()
    return source

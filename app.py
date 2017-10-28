import os

from flask import Flask
app = Flask(__name__)

from flask import session, redirect, url_for, escape, request, send_file
from flask import render_template


import ije


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "contest" not in session:
            return redirect(url_for("choose_contest", error=u"Сначала необходимо выбрать контест"))
        return render_template("login.html")
    else:
        login = request.form["login"]
        password = request.form["password"]
        if ije.is_login_valid(login, password):
            session["login"] = login
            return redirect(url_for("index"))
        else:
            return redirect(url_for("login", error=u"Неправильный логин или пароль"))


@app.route("/logout")
def logout():
    session.pop("login", None)
    return redirect(url_for('index'))


@app.route("/choose_contest", methods=["GET", "POST"])
def choose_contest():
    if request.method == "GET":
        if "login" in session:
            return redirect(url_for("index", error=u"Сначала необходимо выйти из системы"))
        contests = ije.contests_list()
        return render_template("choose_contest.html", contests=contests)
    else:
        contest_id = request.form["contest_id"]
        if contest_id == "None":
            session.pop("contest", None)
            session.pop("contest_name", None)
            return redirect(url_for("index"))
        if ije.is_contest_valid(contest_id):
            session["contest"] = contest_id
            session["contest_name"] = ije.get_contest_name(contest_id)
            return redirect(url_for("index"))
        else:
            return redirect(url_for("choose_contest", error=u"Вы не можете войти в этот контест"))


def get_uploaded_file(input_name):
    if input_name not in request.files:
        return None
    f = request.files[input_name]
    if not f or f.filename == "":
        return None
    return f


@app.route("/submit", methods=["GET", "POST"])
def submit():
    if not ije.can_submit():
        return redirect(url_for("index", error=u"Вы не можете отправлять решения."))
    if request.method == "GET":
        return render_template("submit.html", problems=ije.problems_list(), languages=ije.languages_list())
    else:
        problem = request.form["problem"]
        language = request.form["language"]
        source_textarea = request.form["source_textarea"]
        source_file = get_uploaded_file("source_file")
        if source_file and source_textarea:
            return redirect(url_for("submit", error=u"Вы не можете одновременно вставить исходный код и выбрать файл."))
        elif not source_file and not source_textarea:
            return redirect(url_for("submit", error=u"Выберите файл или скопируйте исходный код в форму."))
        filename = ije.get_filename(problem, language)
        if source_file:
            source_file.save(filename)
        else:
            with open(filename, "w") as f:
                f.write(source_textarea)
        return redirect(url_for("messages", message=u"Решение успешно отправлено! Удачи!"))


@app.route("/messages")
def messages():
    if not ije.can_view_messages():
        return redirect(url_for("index", error=u"Вы не можете просматривать сообщения."))
    messages = ije.get_messages()
    return render_template("messages.html", messages=messages)


@app.route("/showmessage")
def showmessage():
    if not ije.can_view_messages():
        return redirect(url_for("index", error=u"Вы не можете просматривать сообщения."))
    messages = ije.get_messages()
    message = None
    message_id = request.args["id"]
    for m in messages:
        if str(m["id"]) == message_id:
            message = m
    if message is None:
        return redirect(url_for("messages", error=u"Данное сообщение не найдено."))
    source = ije.get_submission_source(message["problem"], message["id"], message["time"], message["language"])
    return render_template("showmessage.html", message=message, source=source)


@app.route("/monitor")
def monitor():
    if not ije.can_view_monitor():
        return redirect(url_for("index", error=u"Вы не можете просматривать результаты."))
    problems = ije.problems_list()
    results = ije.get_results()
    return render_template("monitor.html", problems=problems, results=results)


@app.route("/statements")
def statements():
    if not ije.can_view_statements():
        return redirect(url_for("index", error=u"Условия недоступны."))
    return send_file(ije.get_statements_filename())


def get_contest_time(smth):
    return ije.get_contest_status_time()


def format_time(mins):
    if mins == "":
        return ""
    else:
        return "%d:%02d" % (mins // 60, mins % 60)


def htmlsafe(source):
    source = source.replace("&", "&amp;")
    source = source.replace("\"", "&quot;")
    source = source.replace("<", "&lt;")
    source = source.replace(">", "&gt;")
    source = source.replace("\n", "</br>")
    source = source.replace("\t", "&nbsp;" * 4)
    source = source.replace(" ", "&nbsp;")
    return source


def shrink_comment(comment):
    if len(comment) < 100:
        return comment
    pos = 100
    if comment[pos:].find(";") < 5:
        pos = pos + comment[pos:].find(";") + 1
    return comment[:pos] + "..."


app.jinja_env.filters['format_time'] = format_time
app.jinja_env.filters['htmlsafe'] = htmlsafe
app.jinja_env.filters['shrink_comment'] = shrink_comment
app.jinja_env.filters['get_contest_time'] = get_contest_time


# testing only. should be changed before using
app.secret_key = b'\x800S\x9eM\x1c\xa6\xe4\x1b\x9a\xaf$\xa1/b\x1f9_A\xac*\xff\xa6\xcf'
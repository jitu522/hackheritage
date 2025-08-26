from flask import render_template, session

def init_exit_routes(app):
    @app.route("/exit")
    def exit_page():
        session.clear()
        return render_template("exit.html")
from flask import render_template, request, redirect, url_for, session
import re
from db import get_db_connection

def init_select_routes(app):
    @app.route("/", methods=["GET", "POST"])
    def select_details():
        if request.method == "POST":
            branch = request.form["branch"].strip()
            semester = request.form["semester"].strip()
            year = request.form["year"].strip()

            session["branch"] = branch
            session["semester"] = semester
            session["year"] = year

            courses_table = re.sub(r'\W+', '_', f"{branch}_{semester}_{year}_courses".lower())
            session["courses_table"] = courses_table

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {courses_table} (
                    id SERIAL PRIMARY KEY,
                    teacher_name VARCHAR(100) NOT NULL,
                    course_name VARCHAR(100) NOT NULL,
                    course_code VARCHAR(50) NOT NULL,
                    tutorial_time VARCHAR(20) NULL,
                    lab_time VARCHAR(20) NULL,
                    tutorials_per_week INTEGER DEFAULT 0,
                    labs_per_week INTEGER DEFAULT 0
                )
            """)

            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for("add_course"))

        return render_template("user_select.html")
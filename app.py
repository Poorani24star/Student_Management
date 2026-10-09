
import os

import boto3
from flask import Flask, render_template, request, redirect, url_for, flash
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-this")

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
TABLE_NAME = "StudentRecords"

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)
table = dynamodb.Table(TABLE_NAME)


@app.route("/")
def index():
    try:
        response = table.scan()
        students = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            response = table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            students.extend(response.get("Items", []))

        students.sort(key=lambda s: s.get("studentID", ""))
        return render_template("index.html", students=students)

    except ClientError:
        app.logger.exception("Unable to read student records")
        flash("Could not load student records. Check database access.")
        return render_template("index.html", students=[]), 500


@app.route("/add", methods=["POST"])
def add_student():
    student_id = request.form.get("studentID", "").strip()
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    email = request.form.get("email", "").strip()
    year = request.form.get("year", "").strip()

    if not all([student_id, name, department, email, year]):
        flash("Please fill in every field.")
        return redirect(url_for("index"))

    try:
        table.put_item(
            Item={
                "studentID": student_id,
                "name": name,
                "department": department,
                "email": email,
                "year": year
            },
            ConditionExpression="attribute_not_exists(studentID)"
        )
        flash("Student added successfully.")

    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            flash("That student ID already exists.")
        else:
            app.logger.exception("Unable to add student")
            flash("Could not add student. Check database access.")

    return redirect(url_for("index"))


@app.route("/update/<student_id>", methods=["POST"])
def update_student(student_id):
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    email = request.form.get("email", "").strip()
    year = request.form.get("year", "").strip()

    if not all([name, department, email, year]):
        flash("Please fill in every field.")
        return redirect(url_for("index"))

    try:
        table.update_item(
            Key={"studentID": student_id},
            UpdateExpression=(
                "SET #n = :n, department = :d, "
                "email = :e, #y = :y"
            ),
            ConditionExpression="attribute_exists(studentID)",
            ExpressionAttributeNames={
                "#n": "name",
                "#y": "year"
            },
            ExpressionAttributeValues={
                ":n": name,
                ":d": department,
                ":e": email,
                ":y": year
            }
        )
        flash("Student updated successfully.")

    except ClientError:
        app.logger.exception("Unable to update student")
        flash("Could not update student. Check the student ID and database access.")

    return redirect(url_for("index"))


@app.route("/delete/<student_id>", methods=["POST"])
def delete_student(student_id):
    try:
        table.delete_item(
            Key={"studentID": student_id},
            ConditionExpression="attribute_exists(studentID)"
        )
        flash("Student deleted successfully.")

    except ClientError:
        app.logger.exception("Unable to delete student")
        flash("Could not delete student. Check the student ID and database access.")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
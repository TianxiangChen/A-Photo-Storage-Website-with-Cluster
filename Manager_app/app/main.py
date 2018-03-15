from flask import render_template, redirect, url_for, request, g
from app import webapp


# Display an HTML page with links
def main():
    return render_template("main.html",title="Photo Storage System -- Manager Control")

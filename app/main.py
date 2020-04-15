
from flask import render_template
from app import webapp


#landing page
@webapp.route('/')
def main():

	return render_template("home.html")


#About page, gives info about application and development team
@webapp.route('/about')
def about():
	
	return render_template("about.html")


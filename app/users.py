
from flask import session, request, render_template, redirect, url_for
from flask import flash
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from app import webapp
import os
from passlib.hash import sha256_crypt
from werkzeug.utils import secure_filename
from datetime import datetime
from app.images import is_logged_in

import boto3
from boto3.dynamodb.conditions import Key
import base64

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DDB_USER_TBL_NAME ='Users'
DDB_FUL_TBL_NAME ='FaceUnlock_Users'
BUCKET_NAME ='ece1779-a3'
PATH_TO_IMAGES_DIR = './app/images'

#Helper function to add data to table
def putItem_User(username,password,email,name):

    
    table = dynamodb.Table(DDB_USER_TBL_NAME)

    response = table.put_item(
       Item={
            'username': username,
            'password': password,
            'email':email,
            'name' : name,
        }
    )

    print("Item addition succeeded")

    return

#Helper function to add data to table
def putItem_FUL(username):

    
    table = dynamodb.Table(DDB_FUL_TBL_NAME)

    response = table.put_item(
       Item={
            'username': username,
        }
    )

    print("Item addition succeeded")

    return



#User login
@webapp.route('/login', methods = ['GET', 'POST'])
def login():

	if request.method == 'POST':
		#Get Form Fields
		username = request.form['username']
		password_check = request.form['password']
		table = dynamodb.Table(DDB_USER_TBL_NAME)

		response = table.get_item(Key = {'username' : username})

		if 'Item' in response:
            
			password = response['Item']['password']

			if sha256_crypt.verify(password_check, password):

				session['logged_in'] = True
				session['username'] = username
				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))

			else:
				error = 'Invalid login'
				return render_template('login.html', error = error)

		else:
			error = 'Username not found'
			return render_template('login.html', error = error)
			 
	return render_template('login.html')



#User login using face recognition
@webapp.route('/face_unlock', methods = ['GET', 'POST'])
def face_unlock():
	
	if request.method == 'POST':
	#Get Form Fields
		username = request.form['username']
		key1 = 'static/faces/' + username +'_master.jpeg'
		key2 = 'static/faces/image.jpeg'
		response = face_match(key1, key2)

		if(response):
			session['logged_in'] = True
			session['username'] = username
			flash('Faces matched', 'success')
			return redirect(url_for('dashboard'))
		else:
			flash('Faces did not match, identity theft is not a joke', 'danger')
			return render_template('face_unlock.html')
	return render_template('face_unlock.html')

#Check if there is a face match
def face_match(key1, key2):
    
	client = boto3.client('rekognition')

	response = client.compare_faces(SimilarityThreshold=80,
		SourceImage={'S3Object': {'Bucket': 'ece1779-a3', 'Name': key1}},
		TargetImage={'S3Object': {'Bucket': 'ece1779-a3', 'Name': key2}})

	if response['FaceMatches']:
		return True
	else:
		return False

#Get image from webcam
@webapp.route('/image', methods=['POST'])
def image():

	if request.method == 'POST':
		i = request.files['image']  # get the image
		f = 'image.jpeg' 
		filename = 'static/faces/'+f

		s3 = boto3.client('s3')
		s3.put_object(Body = i, Bucket = BUCKET_NAME, Key=filename,ContentType='image/jpeg', ACL='public-read')

	return render_template('login.html')

#Get image from webcam when registering new user
@webapp.route('/image_register', methods=['POST'])
def image_register():

	if request.method == 'POST':
		i = request.files['image']  # get the image
		f = 'image.jpeg' 
		filename = 'static/tmp/'+f

		s3 = boto3.client('s3')
		s3.put_object(Body = i, Bucket = BUCKET_NAME, Key=filename,ContentType='image/jpeg', ACL='public-read')

	return render_template('login.html')


#User register for face unlock
@webapp.route('/face_register', methods = ['GET', 'POST'])
def face_register():
	
	if request.method == 'POST':

	#Get Form Fields
		username = request.form['username']
		putItem_FUL(username = username)
		destination_face = 'static/faces/' + username  + '_master.jpeg'
		key = 'static/tmp/image.jpeg'

		s3 = boto3.resource('s3')

		copy_source = {'Bucket': BUCKET_NAME,'Key': key}
		otherkey = 'static/faces/' + username + '_master.jpeg'
		s3.meta.client.copy(copy_source, BUCKET_NAME, otherkey, ExtraArgs = {'ACL' : 'public-read'})

		obj = s3.Object(BUCKET_NAME, key)
		obj.delete()

		flash('Thank you for registering. You can now log in.', 'success')
		return redirect(url_for('face_unlock'))

	return render_template('face_register.html')

#class for Register form, used to register new users also does validation of form
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min = 1, max = 50)])
	username = StringField('Username', [validators.Length(min = 4, max = 25)])
	email = StringField('Email', [validators.Length(min = 6, max = 50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message = 'Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')

#Register user for normal unlock using username and password
@webapp.route('/register', methods = ['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name  = form.name.data 
		email = form.email.data 
		username = form.username.data 
		password = sha256_crypt.encrypt(str(form.password.data))
		putItem_User(username = username, password = password, email = email, name = name)
		flash('Thank you for registering. You can now log in.', 'success')
		return redirect(url_for('login'))
		
	return render_template("register.html", form = form)

#User logout
@webapp.route('/logout',methods=['GET','POST'])
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))




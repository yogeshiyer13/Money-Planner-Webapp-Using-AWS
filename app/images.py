
from flask import session, request, render_template, redirect, url_for, flash
from flask import logging, send_from_directory, jsonify
from app import webapp
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from wand.image import Image
import time

import boto3
from boto3.dynamodb.conditions import Key

DDB_IMG_TBL_NAME ='Images'
DDB_COST_TBL_NAME ='Costs'
BUCKET_NAME = 'ece1779-a3'
ALLOWED_IMAGE_EXT = ["PNG", "JPG", "JPEG"]

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

#Do not allow log out when not logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please log in', 'danger')
            return redirect(url_for('login'))
    return wrap

#Update Image table, add image for user
def updateItem_Image(username,img_name):

    db = boto3.client("dynamodb")
    response = db.update_item(TableName=DDB_IMG_TBL_NAME,
                   Key={'username':{'S':username}},
                   UpdateExpression="ADD img_name :element",
                   ExpressionAttributeValues={":element":{"SS":[img_name]}})

#Update Image table and place image name in relevant category
def updateItem_Image_Cat(username,img_name, category):

    db = boto3.client("dynamodb")
    string = "ADD {} :element".format(category)
    response = db.update_item(TableName=DDB_IMG_TBL_NAME,
                   Key={'username':{'S':username}},
                   UpdateExpression=string,
                   ExpressionAttributeValues={":element":{"SS":[img_name]}})

    
#Get images for particular user
def getItem_Image(username):

    table = dynamodb.Table(DDB_IMG_TBL_NAME)
    response = table.get_item(Key = {'username' : username})

    if 'Item' in response:
            
        img_names = response['Item']['img_name']

        return img_names

#Get images for particular user for a specific category
def getItem_Image_Cat(username, category):

    table = dynamodb.Table(DDB_IMG_TBL_NAME)
    response = table.get_item(Key = {'username' : username})

    if 'Item' in response:
            
        img_names = response['Item'][category]

        return img_names

#Save image file to S3, also make thumbnail and upload that as well
def save_file(username, file, filename):

    s3 = boto3.client('s3')
    destination_origin = 'static/' + username +'/origin/' + filename
    s3.put_object(Body = file, Bucket = BUCKET_NAME, Key=destination_origin,ContentType='image/jpeg', ACL='public-read')
    response = s3.get_object(Bucket=BUCKET_NAME, Key=destination_origin)
    image_binary = response['Body']

    with Image(blob=image_binary) as img:
         with img.clone() as thumb:
            size = thumb.width if thumb.width < thumb.height else thumb.height
            thumb.crop(width=size, height=size, gravity='center')
            thumb.resize(256,256)
            jpeg_ = thumb.make_blob('jpeg')
            s3 = boto3.client('s3')
            destination_thumb = 'static/' + username +'/thumbnails/' + filename
            s3.put_object(Body = jpeg_, Bucket = BUCKET_NAME, Key=destination_thumb,ContentType='image/jpeg', ACL='public-read')
    

    return 'Successfully Uploaded'

#Check if image is allowed
def allowed_img(filename):

    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in ALLOWED_IMAGE_EXT:
        return True
    else:
        return False

#User add photo
#Saves file, updates table, updates table category
@webapp.route('/add_photo', methods = ['GET', 'POST'])
@is_logged_in
def add_photo():

    if request.method == 'POST':

        if request.files:

            image = request.files["image"]

            if image.filename == "":

                flash('Image must have a filename', 'danger')
                return redirect(url_for('add_photo'))

            if not allowed_img(image.filename):

                flash('Image is not a valid extension', 'danger')
                return redirect(url_for('add_photo'))

            else:

                now = datetime.now()
                now_str = now.strftime("%d_%m_%Y__%H_%M_%S")
                filename = secure_filename(image.filename)

                username = session['username']
                filename = str(username+"_"+now_str+"_"+filename)
                
                save_file(username = username, file = image, filename = filename)
                updateItem_Image(username = username, img_name = filename)

                time.sleep(4)
                category = read_receipt(username = username)
                updateItem_Image_Cat(username = username, img_name = filename, category = category)
 
            flash('Photo uploaded successfully', 'success')
            return redirect(url_for('add_photo'))

        
    return render_template("add_photo.html")

#View photo
@webapp.route('/view/<string:image_name>', methods = ['GET', 'POST'])
@is_logged_in
def view_photo(image_name):

    username = session['username']
    return render_template("view.html", username=username, image_name=image_name)

#Read from second S3 Bucket the category that the uploaded receipt falls under
def read_receipt(username):
    TXT_BUCKET_NAME = 'imageadded-text1'
    KEY = 'data_detected.txt'
    s3 = boto3.resource('s3')
    obj = s3.Object(TXT_BUCKET_NAME, KEY)
    body = obj.get()['Body'].read().decode("utf-8")

    splitted = body.split()

    category = splitted[0]
    amount = splitted[1]

    table = dynamodb.Table(DDB_COST_TBL_NAME)
    response = table.get_item(Key = {'username' : username})

    if 'Item' in response:
        
        clothing = response['Item']['clothing']
        retail = response['Item']['retail']
        rest = response['Item']['restaurants']
        misc = response['Item']['misc']

        if category == 'clothing':
            clothing = str(float(clothing) + float(amount))
        elif category == 'retail':
            retail = str(float(retail) + float(amount))
        elif category == 'restaurant':
            rest = str(float(rest) + float(amount))
        else:
            misc = str(float(misc) + float(amount))
    else:
        if category == 'clothing':
            clothing = amount
            retail = '0'
            rest = '0'
            misc = '0'
        elif category == 'retail':
            retail = amount
            clothing ='0'
            rest = '0'
            misc = '0'
        elif category == 'restaurant':
            rest = amount
            clothing = '0'
            retail = '0'
            misc = '0'
        else:
            misc = amount
            clothing = '0'
            retail = '0'
            rest = '0'

    putItem_Cost(username = username,clothing = clothing,retail = retail,restaurant =  rest ,misc = misc)
    return category

#Put the amount from receipt in Cost Table
def putItem_Cost(username,clothing,retail,restaurant,misc):

    
    table = dynamodb.Table(DDB_COST_TBL_NAME)

    response = table.put_item(
       Item={
            'username': username,
            'clothing': clothing,
            'retail':retail,
            'restaurants' : restaurant,
            'misc': misc
        }
    )

    print("Item addition succeeded")

    return

#Search feature
@webapp.route('/search', methods = ['GET', 'POST'])
def search():

    if request.method == 'POST':
        search = request.form['search']
        username = session['username']
        
        if search.lower() == 'clothing':
            image_names = getItem_Image_Cat(username = username, category = 'clothing')
            return render_template('clothing.html', username = username, image_names=image_names)

        elif search.lower() == 'retail':
            image_names = getItem_Image_Cat(username = username, category = 'retail')
            return render_template('retail.html', username = username, image_names=image_names)

        elif search.lower() == 'restaurant':
            image_names = getItem_Image_Cat(username = username, category = 'restaurant')
            return render_template('restaurant.html', username = username, image_names=image_names)

        elif search.lower() == 'misc':
            image_names = getItem_Image_Cat(username = username, category = 'misc')
            return render_template('misc.html', username = username, image_names=image_names)  

        else:
            flash('Incorrect search. Please search "clothing", "retail", "restaurant" or "misc".', 'danger')
            return redirect(url_for('dashboard'))

    return redirect(url_for('dashboard'))

#User dashboard
@webapp.route('/dashboard', methods = ['GET', 'POST'])
@is_logged_in
def dashboard():

    username = session['username']
    image_names = getItem_Image(username = username)
    recv_data = data(username = username)

    return render_template('dashboard.html', image_names=image_names, username=username, data = recv_data)

#Receive the data from the Cost table for each category
def data(username):


    table = dynamodb.Table(DDB_COST_TBL_NAME)
    response = table.get_item(Key = {'username' : username})

    if 'Item' in response:
        
        clothing = response['Item']['clothing']
        retail = response['Item']['retail']
        rest = response['Item']['restaurants']
        misc = response['Item']['misc']

        data = {'Categories' : 'Amount($)', 'Clothing' : float(clothing), 'Retail' : float(retail), 'Restaurants' : float(rest), 'Miscellaneous' : float(misc)}

        return data

    data = {'Categories' : 'Amount($)', 'Clothing' : 0, 'Retail' : 0, 'Restaurants' : 0, 'Miscellaneous' : 0}
    return data




# Money-Planner-Webapp-Using-AWS
Receipt classifier webapp in a serverless framework (Zappa) using Amazon Web Services 
using Flask library of Python, DynamoDB, Rekognition, Textract, Lambda   

The app has been deployed using zappa from AWS. To run the static app you can simply do the following:

Instructions:

1. Set the config file
In the config.py file, you need to set up your own database first!

2. Run the flask:
virtual env to run the flask by using python3:

For Mac OS:
 - python3 -m venv venv
 - source ./venv/bin/activate
 
For Windows OS:
 - python3 -m venv venv
 - ./venv/bin/activate

setup the env for flask:

For Mac OS:
EXPORT FLASK_APP=main.py
EXPORT FLASK_ENV=development flask run 

For Windows user:
set FLASK_APP=main.py
set FLASK_ENV=development
flask run Hope this works.

The app does the following tasks: 

1. Allow user to upload an image of a receipt taken by a camera or scanned
2. It then extracts the text information from it
3. This data is then cleaned to extract and store only the information that is of use for calculating expenses.
4. The user can now see how much he/she has spent in each category separately.
5. The cost limit reached can be seen under each category for the user.
6. The user can also search for details of specific category of receipts.

Each user can choose to sign up for face login to provide an extra layer of security, 
and prevent unauthorized access to their financial information.



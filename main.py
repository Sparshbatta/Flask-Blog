from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import datetime
from werkzeug.utils import secure_filename 
import json
import os
import math

is_local_server = True
with open("config.json", 'r') as f:
    params = json.load(f)["params"]

app = Flask(__name__)
app.secret_key='secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail_user'],
    MAIL_PASSWORD=params['gmail_password']
)
mail = Mail(app)
if is_local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["prod_uri"]
db = SQLAlchemy(app)


class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(75), nullable=False)
    tagline = db.Column(db.String(120), nullable=True)
    slug = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    image_url = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():

    #Pagination logic
    posts = Posts.query.filter_by().all()
    last = math.floor(len(posts)/int(params['num_posts']))
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page=1
    else:
        page=int(page)
    posts = posts[(page-1)*int(params['num_posts']):(page-1)*int(params['num_posts'])+int(params['num_posts'])]
    if(page==1):
        prev="#"
        next="/?page="+str(page+1)
    elif(page==last):
        prev="/?page="+str(page-1)
        next="#"
    else:
        prev="/?page="+str(page-1)
        next="/?page="+str(page+1)
    
    return render_template("index.html", params=params, posts=posts, prev=prev, next=next)


@app.route("/about")
def about():
    return render_template("about.html", params=params)


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/login')


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        entry = Contacts(
            name=name, phone=phone, message=message, date=datetime.now(), email=email
        )
        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            'New Message from '+name,
            sender=email,
            recipients=[params['gmail_user']],
            body='Email-ID:'+email+'\n'+'Phone Number:'+phone+'\n'+message)
    return render_template("contact.html", params=params)


@app.route('/post/<string:post_slug>', methods=['GET'])
def fetch_post(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.filter_by().all()
        return redirect(url_for('dashboard'))
    if(request.method=="POST"):
        username = request.form.get('uname')
        userpassword = request.form.get('password')
        if(username == params['admin_user'] and userpassword == params['admin_password']):
            session['user']=username
            posts = Posts.query.filter_by().all()
            return render_template('dashboard.html',params=params, posts=posts)
        else:
            return render_template('login.html',params=params)
    else:
        return render_template('login.html',params=params)


@app.route('/dashboard',methods=['GET','POST'])
def dashboard():
    posts = Posts.query.filter_by().all()
    return render_template('dashboard.html', params=params, posts=posts)


@app.route('/edit/<string:sno>', methods=['GET', 'POST'])
def edit(sno):
    if('user' in session and params['admin_user'] == session['user']):
        if(request.method=='POST'):
            title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            description = request.form.get('description')
            image_url = request.form.get('post_image')
            date=datetime.now()
            if(sno=='0'):
                post = Posts(title=title, tagline=tagline, slug=slug, description=description, image_url=image_url, date=date)
                db.session.add(post)
                db.session.commit()
                return redirect('/')
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.tagline = tagline
                post.slug = slug
                post.description = description
                post.image_url = image_url
                post.date = date
                db.session.commit()
            return redirect('/post/'+slug)
    post = Posts.query.filter_by(sno=sno).first()
    return render_template('edit.html', params=params, post=post)


@app.route('/delete/<string:sno>', methods=['GET','POST'])
def delete(sno):
    if('user' in session and session['user']==params['']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route('/uploader', methods=['GET','POST'])
def uploader():
    if(request.method=='POST'):
        f = request.files['file1']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        return "Uploaded successfully"

app.run(debug=True)
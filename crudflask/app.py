from flask import Flask, render_template,flash,request, redirect,url_for,session,logging
#from data import Articles
from flaskext.mysql import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
app= Flask(__name__)
import html.parser
#config MYSQL
app.config['MYSQL_DATABASE_HOST']= 'localhost'
app.config['MYSQL_DATABASE_USER']= 'root'
app.config['MYSQL_DATABASE_PASSWORD']= '12345'
app.config['MYSQL_DATABASE_DB']= 'flaskapp'
app.config['MYSQL_CURSORCLASS']= 'DictCursor'

#INIT MYSQL
mysql=MySQL(app)
mysql.init_app(app)
con=mysql.connect()
#Articles= Articles()

@app.route('/')
def index():
    return render_template('home.html')
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    cur = con.cursor()
    result = cur.execute("SELECT * FROM articles")
    articles=[dict(id=row[0],title=row[1]) for row in cur.fetchall()]
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    cur.close()

@app.route('/article/<string:id>/')
def article(id):
    cur = con.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article=cur.fetchone()
    html_parser = html.parser.HTMLParser()
    
    data={'title':article[1],'author':article[2],'body':html_parser.unescape(article[3]),'create_date':article[4]}
    return render_template('article.html', data=data)

class RegisterForm(Form):
    name= StringField('Name',[validators.Length(min=1,max=50)])
    username = StringField('Username', [validators.Length(min=4,max=25)])
    email = StringField('Email', [validators.Length(min=6,max=25)])
    password=PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = con.cursor()
    result = cur.execute("SELECT * FROM articles where author=%s",session['username'])
    articles=[dict(id=row[0],title=row[1],author=row[2],create_date=row[4]) for row in cur.fetchall()]
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()


@app.route('/delete_article/<string:id>/')
@is_logged_in
def delete_article(id):
    cur = con.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    con.commit()
    cur.close()
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_article/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    cur=con.cursor()
    cur.execute('SELECT * FROM articles WHERE id=%s',id)
    article=cur.fetchone()
    data={'id':article[0],'title':article[1],'body':article[3]}
    con.close()
    form= ArticleForm(request.form)
    form.title.data=data['title']
    form.body.data=data['body']

    if request.method=='POST' and form.validate():
        title=request.form['title']
        body=request.form['body']
        cur = con.cursor()
        cur.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        con.commit()
        cur.close()
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        #get form fields
        username=request.form['username']
        password_temp=request.form['password']
        #db cursor
        cur=con.cursor()
        result= cur.execute("SELECT * from users where username= %s",[username])
        if result > 0 :
            data= cur.fetchone()
            password=data[3]
            if sha256_crypt.verify(password_temp,password):
                session['logged_in']=True
                session['username']=username
                flash('You are now logged in !','success')
                return redirect(url_for('dashboard'))
            else:
                error="Invalid login"
                return render_template('login.html',error=error)
            cur.close()   
        else:
            error="User was not found."
            return render_template('login.html',error=error)        
    return render_template('login.html')



@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('Hope to see you soon !','info')
    return redirect(url_for('login'))


@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(str(form.password.data))
        #Create Cursor

        cur=con.cursor()
        cur.execute("INSERT into users(name,email,username,password) values(%s,%s,%s,%s)",(name,email,username,password))
        con.commit()
        cur.close()
        flash('You are now registered !','success')
        redirect(url_for('login'))
    return render_template('register.html',form=form)

 

@app.route('/practice')
def practice():
    return render_template('practice.html')
@app.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur=con.cursor()
        cur.execute("INSERT into articles(title,body,author) VALUES(%s,%s,%s)", (title, body,session['username']))
        con.commit()
        cur.close()
        flash('Article Created','success')
        redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)
if __name__== '__main__':
    app.secret_key="secret123"
    app.run(debug=True)
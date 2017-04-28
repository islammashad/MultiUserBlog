import os
import re
import hmac
import webapp2
import jinja2
from user import User
from post import Post
from comment import Comment

# Use db 
from google.appengine.ext import db

#for working on Templates 
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'r8YNrsoLRmWk74ACtvv0cffqcREqkTNv'

# Jinja2 template base methods
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

# Blog base method
def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class BlogFront(BlogHandler):
    def get(self):
        posts = greetings = Post.all().filter('parent_id =', None).order('-created')
        self.render('front.html', posts = posts)

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        uid = self.read_secure_cookie('user_id')

        if post.likes and uid in post.likes:
            likeStatus = 'Unlike'
        else:
            likeStatus = 'Like'

        comments = Comment.all().filter('parent_id =', post_id).order('-created')

        if not post:
            self.render("404.html")

        self.render("post.html", post = post, uid = uid,
            likeStatus = likeStatus, comments = comments)

    def post(self, post_id):
        if not self.user:
            self.render("login-form.html",
                        alert = "Please login to comment")

        content = self.request.get('content')
        uid = self.read_secure_cookie('user_id')
        user_name = self.user.name

        if content:
            post = Comment(parent = blog_key(),
                   content = content, user_id = uid, parent_id = post_id,
                   user_name = user_name)
            post.put()
            self.redirect('/blog/%s' % post_id)
        else:
            error = "Subject and content can't be blank"
            self.render("post.html", content = content,
                error = error)

class NewPost(BlogHandler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.render("login-form.html",
                        alert = "Please login to create a new post")

        subject = self.request.get('subject')
        content = self.request.get('content')

        uid = self.read_secure_cookie('user_id')
        user_name = self.user.name

        if subject and content:
            p = Post(parent = blog_key(), subject = subject, content = content,
                     user_id = uid, user_name = user_name)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "subject and content can't be blank"
            self.render("newpost.html", subject=subject, content=content,
                error=error)

# regex functions for User validation
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        # make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/')

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')


        
class LikePage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        uid = self.read_secure_cookie('user_id')

        if not post:
            self.render("404.html")

        if not self.user:
            self.render("login-form.html",
                        alert = "Please login to like the post")

        elif post.user_id != uid:
            if post.likes and uid in post.likes:
                post.likes.remove(uid)
            else:
                post.likes.append(uid)
            post.put()
            self.redirect('/blog/%s' % str(post.key().id()))

        else:
            error = "You can't like your own post"
            self.render("error.html", error = error)

class DeletePage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.render("404.html")

        uid = self.read_secure_cookie('user_id')

        if post.user_id != uid:
            error = "You don't have permission to delete this post"
        else:
            error = ''
            db.delete(key)

        self.render("delete.html", error = error)

class DeleteComment(BlogHandler):
    def get(self, comment_id):
        key = db.Key.from_path('Comment', int(comment_id), parent=blog_key())
        comment = db.get(key)

        if not comment:
            self.render("404.html")

        uid = self.read_secure_cookie('user_id')

        if comment.user_id != uid:
            error = "You don't have permission to delete this comment"
        else:
            error = ''
            db.delete(key)

        self.render("delete.html", error = error, parent_id = comment.parent_id)

class EditPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.render("404.html")

        uid = self.read_secure_cookie('user_id')

        if post.user_id != uid:
            error = "You don't have permission to edit this post"
        else:
            error = ""

        self.render("edit.html", post = post, uid = uid, error = error)

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        uid = self.read_secure_cookie('user_id')

        subject = self.request.get('subject')
        content = self.request.get('content')

        if post.user_id == uid and subject and content:
            post.subject = subject
            post.content = content
            post.put()
            self.redirect('/blog/%s' % str(post.key().id()))
        else:
            error = "Subject and content can't be blank"
            self.render("edit.html", post = post, error = error)

class EditComment(BlogHandler):
    def get(self, comment_id):
        key = db.Key.from_path('Comment', int(comment_id), parent=blog_key())
        comment = db.get(key)

        if not comment:
            self.render("404.html")

        uid = self.read_secure_cookie('user_id')

        if comment.user_id != uid:
            error = "You don't have permission to edit this comment"
        else:
            error = ""

        self.render("edit.html", comment = comment, uid = uid, error = error)

    def post(self, comment_id):
        key = db.Key.from_path('Comment', int(comment_id), parent=blog_key())
        comment = db.get(key)

        uid = self.read_secure_cookie('user_id')

        content = self.request.get('content')

        if comment.user_id == uid and content:
            comment.content = content
            comment.put()
            self.redirect('/blog/%s' % str(comment.parent_id))
        else:
            error = "Content can't be blank"
            self.render("edit.html", comment = comment, error = error)

app = webapp2.WSGIApplication([('/', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/newpost', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/like/([0-9]+)', LikePage),
                               ('/delete/([0-9]+)', DeletePage),
                               ('/delete-comment/([0-9]+)', DeleteComment),
                               ('/edit/([0-9]+)', EditPage),
                               ('/edit-comment/([0-9]+)', EditComment)
                               ],
                              debug=True)

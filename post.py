from google.appengine.ext import db

class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    likes = db.StringListProperty()
    user_id = db.StringProperty()
    user_name = db.StringProperty()
    parent_id = db.StringProperty()

    def render_text(self):
        return self.content.replace('\n', '<br>')

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

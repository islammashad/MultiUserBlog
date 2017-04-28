from google.appengine.ext import db

class Comment(db.Model):
    user_id = db.StringProperty(required=True)
    user_name = db.StringProperty(required=True)
    parent_id = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    likes = db.StringListProperty()

    def render_text(self):
        return self.content.replace('\n', '<br>')

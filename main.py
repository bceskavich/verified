from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, g
from flask_oauthlib.client import OAuth
from tweepy.api import API
from tweepy import Cursor, OAuthHandler
import requests
import os
import json

CSRF_ENABLED = True

# Your Twitter credentials here
consumer_key = 'GgXkbQnIzPDU57RPhVSorGJxW'
consumer_secret = 'e1zpB6aDOJTp96cIbart7VCLvFcjPIEt33dOrIXpe5NZDxdtGU'

app = Flask(__name__)
app.debug = True
app.config.from_object(__name__)
app.secret_key = os.urandom(24)

oauth = OAuth(app)
twitter = oauth.remote_app(
    'twitter',
    consumer_key = consumer_key,
    consumer_secret = consumer_secret,
    base_url = 'https://api.twitter.com/1.1/',
    request_token_url = 'https://api.twitter.com/oauth/request_token',
    access_token_url = 'https://api.twitter.com/oauth/access_token',
    authorize_url = 'https://api.twitter.com/oauth/authorize'
)

oauth.init_app(app)

@app.before_request
def before_reqeust():
    g.screen_name = None
    if 'user_info' in session:
        g.screen_name = session['user_info']['screen_name']

def get_verified_count():
    access_token = session['user_info']['access_token']
    access_secret = session['user_info']['access_secret']
    user_id = session['user_info']['user_id']

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    twitter_api = API(auth_handler=auth)

    follower_count = 0
    verified_count = 0
    regular_count = 0

    verified_users = []

    for item in Cursor(twitter_api.followers, user_id=user_id, count=200).items(200):
        data = item._json
        if data['verified'] == True:
            verified_count += 1
            user = {
                'handle': data['screen_name'],
                'avatar': data['profile_image_url_https']
            }
            verified_users.append(user)
        else:
            regular_count += 1
        follower_count += 1

    return verified_count, regular_count, follower_count, verified_users

def write_to_file(user, follower_count, verified_count, regular_count):
    filename = 'data/' + user + '_counts.csv'
    with open(filename, 'w') as outfile:
        outfile.write('value,count')
        outfile.write('\n')
        outfile.write('follower_count,' + str(follower_count))
        outfile.write('\n')
        outfile.write('verified_count,' + str(verified_count))
        outfile.write('\n')
        outfile.write('regular_count,' + str(regular_count))


@app.route('/')
@app.route('/index')
def index():
    screen_name = None
    verified_count = None,
    verified_users = None
    regular_count = None
    follower_count = None
    if g.screen_name is not None:
        screen_name = g.screen_name
        verified_count, regular_count, follower_count, verified_users = get_verified_count()
        write_to_file(screen_name, follower_count, verified_count, regular_count)
    return render_template('index.html',
        screen_name=screen_name,
        verified_count=verified_count,
        verified_users=verified_users,
        regular_count=regular_count,
        follower_count=follower_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    return twitter.authorize(callback=url_for('auth',
        next=request.args.get('next') or request.referrer or None))

@app.route('/auth', methods = ['GET', 'POST'])
@twitter.authorized_handler
def auth(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'Hmmmm, something went wrong.')
        return redirect(next_url)
    print json.dumps(resp, indent=1)
    user_info = {
        'user_id': resp['user_id'],
        'screen_name': resp['screen_name'],
        'access_token': resp['oauth_token'],
        'access_secret': resp['oauth_token_secret']
    }
    session['user_info'] = user_info
    return redirect(next_url)

@app.route('/logout')
def logout():
    session.pop('user_info', None)
    flash("You've been logged out!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()

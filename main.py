from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, g
from flask_oauthlib.client import OAuth
from tweepy.api import API
from tweepy import Cursor, OAuthHandler
import requests
import os
import json

CSRF_ENABLED = True

# Your Twitter credentials here
consumer_key = ''
consumer_secret = ''

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# app.debug = True
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
    g.logged_in = False
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

    verified_users = []

    exception = False
    try:
        for item in Cursor(twitter_api.followers, user_id=user_id, count=200).items():
            data = item._json
            if data['verified'] == True:
                verified_count += 1
                user = {
                    'handle': data['screen_name'],
                    'avatar': data['profile_image_url_https']
                }
                verified_users.append(user)
            else:
                pass
            follower_count += 1
    except:
        exception = True

    return verified_count, follower_count, verified_users, exception

def write_to_file(user, follower_count, verified_count):
    filename = 'data/' + user + '_counts.csv'
    with open('static/' + filename, 'w') as outfile:
        outfile.write('value,count')
        outfile.write('\n')
        outfile.write('follower_count,' + str(follower_count))
        outfile.write('\n')
        outfile.write('verified_count,' + str(verified_count))

    return filename


@app.route('/')
@app.route('/index')
def index():
    screen_name = 'ceskavich'
    verified_count = None
    verified_users = None
    follower_count = None
    datafile = None
    percentage = None
    percent = None
    if g.logged_in:
        verified_count = session['count_info']['verified_count']
        follower_count = session['count_info']['follower_count']
        verified_users = session['count_info']['verified_users']
        filename = session['count_info']['filename']
        datafile = session['count_info']['datafile']
        percent = session['count_info']['percent']
        percentage = session['percentage']
    elif g.screen_name is not None:
        g.logged_in = True
        verified_count, follower_count, verified_users, exception = get_verified_count()
        if exception:
            flash('Ah man, Twitter rate limited us. Try again in about 15 minutes.')
            return redirect(url_for('logout'))
        else:
            filename = write_to_file(screen_name, follower_count, verified_count)
            datafile = url_for('static', filename=filename)
            percentage = (float(verified_count) / float(follower_count)) * 100
            percent = "{0:.2f}".format(percentage)
            session['count_info'] = {
                'verified_count': verified_count,
                'follower_count': follower_count,
                'verified_users': verified_users,
                'filename': filename,
                'datafile': datafile,
                'percent': percent,
                'percentage': percentage
            }
    return render_template('index.html',
        screen_name=g.screen_name,
        verified_count=verified_count,
        verified_users=verified_users,
        follower_count=follower_count,
        percentage=percentage,
        percent=percent,
        datafile=datafile)

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
    g.logged_in = False
    g.screen_name = None
    return redirect(url_for('index'))

@app.route('/error')
def error():
    return 'ERROR'

if __name__ == '__main__':
    app.run()

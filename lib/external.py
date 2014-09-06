""" This file contains functions like signing on and registering
    that do not require any previous authentication. """

import os
from flask import request, session
from passlib.hash import sha256_crypt
from postmark import PMMail

import db
from models.users import User
from utils import CONFIG, resp


def login(args):
    """ Confirm that a username and password match a User record in the db. """
    username = args.get('username')
    password = args.get('password')

    if username and password:
        encrypted_pass = sha256_crypt.encrypt(password)
        user_match = db.session.query(User)\
                               .filter(User.username == username)\
                               .filter(User.password == encrypted_pass).first()
        if user_match:
            if user_match.active:
                session.update({
                    'username': user_match.username,
                    'userId': user_match.id,
                    'loggedIn': True
                })
                return resp()
            else:
                return resp(False, 'Please confirm your registration before logging in')
        else:
            return resp(False, 'Login credentials invalid')
    else:
        return resp(False, 'You must provide a username and password')


def register(args):
    """ Checks for existing accounts under the given username and email.
        If there are no matching usernames or emails,
        create a new User entry and send a verification email."""

    existing_matches = db.session.query(User)\
                              .filter(db.or_(User.username == args['username'],
                                             User.email == args['email']))\
                              .all()

    names_to_check = [u.username for u in existing_matches]
    if args['username'] in names_to_check:
        return resp(False, 'Chosen Username already exists')

    emails_to_check = [u.email for u in existing_matches]
    if args['email'] in emails_to_check:
        return resp(False, 'Given email already has an account. ' +
                           'Please sign in or recover your account information')

    new_user = User(username=args['username'],
                    email=args['email'],
                    password=sha256_crypt.encrypt(args['password']),
                    active=False)

    new_user.insert()

    verify_link = '{0}external/verify?id={1}'.format(request.url_root, new_user.id)

    subject = "Welocome to {0}!".format(CONFIG.get('app', 'name'))

    msg = '\n'.join([
        'Welcome! Your account has been created!',
        'Please click the link below to verify your email address.',
        verify_link, '', '',
        'Thank you for joining. We hope you enjoy your account.'
    ])

    email = PMMail(api_key=os.environ.get('POSTMARK_API_KEY'),
                   subject=subject,
                   sender=CONFIG.get('email', 'sender'),
                   to=new_user.email,
                   text_body=msg)

    email.send()

    return resp()


def verify(args):
    """ Activates a user after they click the email link. """
    user_id = args.get('id')

    if not user_id:
        raise UserWarning("User ID missing")

    user = db.session.query(User).filter(User.id == user_id).first()

    if not user:
        raise UserWarning("No user found matching ID")

    user.active = True

    return 'dashboard.html'

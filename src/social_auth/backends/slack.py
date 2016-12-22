"""
Obtain
SLACK_CLIENT_ID & SLACK_CLIENT_SECRET
and put into sentry.conf.py
"""
from __future__ import absolute_import

import requests

from social_auth.backends import BaseOAuth2, OAuthBackend

SLACK_TOKEN_EXCHANGE_URL = 'https://slack.com/api/oauth.access'
SLACK_AUTHORIZATION_URL = 'https://slack.com/oauth/authorize'
SLACK_USER_DETAILS_URL = 'https://slack.com/api/users.identity'


class SlackBackend(OAuthBackend):
    """Slack OAuth authentication backend"""
    name = 'slack'
    EXTRA_DATA = [
        ('email', 'email'),
        ('name', 'full_name'),
        ('id', 'id'),
        ('refresh_token', 'refresh_token')
    ]

    def get_user_details(self, response):
        """Return user details from Slack account"""

        return {
            'email': response.get('email'),
            'id': response.get('id'),
            'full_name': response.get('name')
        }


class SlackAuth(BaseOAuth2):
    """Slack OAuth authentication mechanism"""
    AUTHORIZATION_URL = SLACK_AUTHORIZATION_URL
    ACCESS_TOKEN_URL = SLACK_TOKEN_EXCHANGE_URL
    AUTH_BACKEND = SlackBackend
    SETTINGS_KEY_NAME = 'SLACK_CLIENT_ID'
    SETTINGS_SECRET_NAME = 'SLACK_CLIENT_SECRET'
    REDIRECT_STATE = False
    DEFAULT_SCOPE = ['identity.basic']

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        try:
            resp = requests.get(SLACK_USER_DETAILS_URL,
                                params={'token': access_token})
            resp.raise_for_status()
            return resp.json()['user']
        except ValueError:
            return None

    @classmethod
    def refresh_token(cls, token):
        params = cls.refresh_token_params(token)
        response = requests.post(cls.ACCESS_TOKEN_URL, data=params,
                                 headers=cls.auth_headers())
        response.raise_for_status()
        return response.json()

# Backend definition
BACKENDS = {
    'slack': SlackAuth,
}

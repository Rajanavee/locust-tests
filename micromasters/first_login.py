"""
locust file for micromasters
This tests the veri first login to micromasters
"""
import random
from urlparse import urljoin, urlparse

from locust import HttpLocust, TaskSet, task

import settings


class UserLoginAndProfile(TaskSet):

    username = None
    mm_csrftoken = None

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        self.username = random.choice(settings.USERNAMES_IN_EDX)

    def login(self):
        """
        Function to login an user on MicroMasters assuming she has an account on edX
        """
        # load the login form to get the token
        login_form = self.client.get(
            urljoin(settings.EDXORG_BASE_URL, '/login'),
            name='/login[edx login page]',
        )
        cookies = login_form.cookies.get_dict()
        # login edx
        self.client.post(
            urljoin(settings.EDXORG_BASE_URL, '/user_api/v1/account/login_session/'),
            data={
                "email": "{}@example.com".format(self.username),
                "password": "test",
                'remember': 'false'
            },
            headers={'X-CSRFToken': cookies.get('csrftoken')},
            name='/user_api/v1/account/login_session/[edx login form]'
        )
        # login micromasters
        self.client.get(
            '/login/edxorg/',
            name='/login/edxorg/[micromasters]'
        )
        # get the csrftoken
        parsed_url = urlparse(settings.MICROMASTERS_BASE_URL)
        domain = parsed_url.netloc
        if ':' in domain:
            domain = domain.split(':')[0]
        self.mm_csrftoken = self.client.cookies.get('csrftoken', domain=domain)

    def logout(self):
        """
        Logout from edx and micromasters
        """
        # logout edX
        self.client.get(
            urljoin(settings.EDXORG_BASE_URL, '/logout'),
            name='/logout[edx]'
        )
        # logout micromasters
        self.client.get(
            '/logout',
            name='/logout[micromasters]'
        )

    def index_no_login(self):
        """Load index page without being logged in"""
        self.client.get("/")

    def profile_tabs(self):
        """
        Profile tabs
        """
        # loading part
        self.client.get('/profile/')
        resp_profile = self.client.get(
            '/api/v0/profiles/{}/'.format(self.username),
            name="'/api/v0/profiles/[username]/"
        )
        profile = resp_profile.json()
        self.client.get('/api/v0/dashboard/')
        self.client.get('/api/v0/course_prices/')
        self.client.get('/api/v0/enrolledprograms/')

        # reset the profile as much as possible for the next run
        profile['education'] = []
        profile['work_history'] = []
        if profile['agreed_to_terms_of_service'] is True:
            del profile['agreed_to_terms_of_service']
        else:
            profile['agreed_to_terms_of_service'] = True
        filled_out = profile['filled_out']
        del profile['filled_out']
        del profile['email_optin']
        del profile['image']

        # submission part
        profile.update({
            'birth_country': 'IT',
            'city': 'Los Angeles',
            'country': 'US',
            'date_of_birth': '2000-01-12',
            'first_name': '{}'.format(self.username),
            'gender': 'f',
            'last_name': 'Example',
            'nationality': 'IT',
            'preferred_language': 'en',
            'preferred_name': '{} Preferred'.format(self.username),
            'state_or_territory': 'US-CA',
        })

        self.client.patch(
            '/api/v0/profiles/{}/'.format(self.username),
            json=profile,
            headers={'X-CSRFToken': self.mm_csrftoken},
            name="'/api/v0/profiles/[username]/",
        )
        self.client.post(
            '/api/v0/enrolledprograms/',
            json={'program_id': settings.MICROMASTERS_PROGRAM_ID},
            headers={'X-CSRFToken': self.mm_csrftoken},
        )
        self.client.get('/api/v0/dashboard/')
        self.client.get('/api/v0/course_prices/')

        # education
        # add the high school
        profile['education'].append(
            {
                "degree_name": "hs",
                "graduation_date": "1998-02-01",
                "field_of_study": None,
                "online_degree": False,
                "school_name": "School User",
                "school_city": "Lexington",
                "school_state_or_territory": "US-MA",
                "school_country": "US"
            }
        )
        self.client.patch(
            '/api/v0/profiles/{}/'.format(self.username),
            json=profile,
            headers={'X-CSRFToken': self.mm_csrftoken},
            name="'/api/v0/profiles/[username]/",
        )
        # add college
        profile['education'].append(
            {
                "degree_name": "m",
                "graduation_date": "2008-12-01",
                "field_of_study": "14.0903",
                "online_degree": False,
                "school_name": "University of Here",
                "school_city": "Bologna",
                "school_state_or_territory": "IT-BO",
                "school_country": "IT",
                "graduation_date_edit": {"year": "2008", "month": "12"}
            }
        )
        self.client.patch(
            '/api/v0/profiles/{}/'.format(self.username),
            json=profile,
            headers={'X-CSRFToken': self.mm_csrftoken},
            name="'/api/v0/profiles/[username]/",
        )

        # professional
        profile['work_history'].append(
            {
                "position": "Senior Software Engineer",
                "industry": "Computer Software",
                "company_name": "MIT",
                "start_date": "2000-01-01",
                "end_date": None,
                "city": "Cambridge",
                "country": "US",
                "state_or_territory": "US-MA",
                "start_date_edit": {"year": "2000", "month": "1"}
            }
        )
        self.client.patch(
            '/api/v0/profiles/{}/'.format(self.username),
            json=profile,
            headers={'X-CSRFToken': self.mm_csrftoken},
            name="'/api/v0/profiles/[username]/",
        )

        # I am done!
        if not filled_out:
            profile.update({
                'filled_out': True,
            })
            self.client.patch(
                '/api/v0/profiles/{}/'.format(self.username),
                json=profile,
                headers={'X-CSRFToken': self.mm_csrftoken},
                name="'/api/v0/profiles/[username]/",
            )

    @task
    def login_and_profile(self):
        """
        The actual task with the different operations in the right sequence to be run by locust
        """
        self.index_no_login()

        self.login()

        self.profile_tabs()

        self.logout()


class WebsiteUser(HttpLocust):
    host = settings.MICROMASTERS_BASE_URL
    task_set = UserLoginAndProfile
    min_wait = 1000
    max_wait = 3000
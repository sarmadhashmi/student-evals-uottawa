 from bs4 import BeautifulSoup
from robobrowser import RoboBrowser
from time import sleep
# MAYBE? CSV OUTPUT
# rating by prof
# prof, faculty, session + year, course code,
# search for prof
# get sessions, years, indexes(prof), evaltypes, faculties here

class Infoweb(object):
    def __init__(self, username, password):
        self.br = RoboBrowser()
        self.username = username
        self.password = password
        self.loggedIn = False

    def login(self):
        self.br.open("https://uozone2.uottawa.ca/user/login")
        login_form = self.br.get_form(id="user-login-form")
        login_form["name"] = self.username
        login_form['pass'] = self.password
        self.br.submit_form(login_form)
        user = self.br.find('span', {'class':'username'}).text
        if user == 'Anonymous':
            raise ValueError("Incorrect credentials provided.")
        else:
            self.loggedIn = True
            print("Logged in as " + user)

    def goToEvaluations(self):
        assert self.loggedIn
        self.br.open("https://uozone2.uottawa.ca/apps/s-report")
        html = self.br
        if "Evaluation of Teaching and Courses" not in html.parsed:
            raise LookupError("Site is down.")
        sessions = html.findAll('input', {'name': 'sess-'})
        years = [x.text for x in html.find('select', {'name': 'ctury'}).find_all('option')]
        indices = html.findAll('input', {'name': 'itype'})
        evalTypes = html.findAll('input', {'name': 'eval-'})
        faculties = [{'name': x.name, 'value': x['value']} for x in html.find('select', {'name': 'ctury'}).find_all('option')]
        print years
        print faculties
        print indices

    # Search by prof and/or course
    def getEvaluations(self, prof, course):
        assert self.loggedIn
        if prof and course:
            print('Searching by prof ' + prof + ' and course ' + course)
        elif prof:
            print('Searching by prof ' + prof)
        elif course:
            print('Searching by prof ' + course)
        else:
            print('No prof or course provided.')

    def fillEvaluationsForm(self, session, year, index, evalType, faculty):
        assert self.br.geturl() == "https://web.uottawa.ca/uopr/WSN003;Lang=EN"
        self.br.select_form(nr=0)
        print('placeholder')            # something here

    def logout(self):
        try:
            assert self.loggedIn
            self.br.open("http://uozone.uottawa.ca/en/logout")
            self.loggedIn = False
            print("Logged out...")
        except:
            print("Not logged in.")

    def close(self):
        self.logout()

if __name__ == '__main__':
    try:
        w = Infoweb('username', 'password')
        w.login()
        w.goToEvaluations()
    except Exception as e:
        print e
    finally:
        w.close()


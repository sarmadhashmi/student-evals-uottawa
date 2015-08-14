from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
import urllib, urllib2
import cookielib
import requests

# MAYBE? CSV OUTPUT
# rating by prof
# prof, faculty, session + year, course code,
# search for prof
# get sessions, years, indexes(prof), evaltypes, faculties here
DEFAULT_TIMEOUT = 60
cookie_file = 'my.cookies'
class Infoweb(object):
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.loggedIn = False


    def openSiteWithRetry(self, site, wait=None, retries=4, timeout=DEFAULT_TIMEOUT):
        for i in range(retries):
            try:
                print "Trying to open page: " + site
                if wait:
                    self.br.open(site, wait=False)
                    result, resources = self.br.wait_for_selector(wait, timeout=timeout)
                    if not result:
                        raise LookupError(wait + " not found.")
                else:
                    self.br.open(site, timeout=timeout)
                break
            except TimeoutError:
                if i == retries - 1:
                    print "Tried to open page " + str(retries) + " times. uOttawa site must be REALLY slow. Try again in a minute or two."
                    raise
                else:
                    sleep(3)
                    continue
            except LookupError:
                raise

    def login(self):
        # Build query to login
        headers = {'User-Agent': 'Mozilla/5.0'}
        login_data = dict()
        login_data['name'] = self.username
        login_data['pass'] = self.password
        login_data['form_build_id'] = 'form-o9zTDwe0qqz4hLM0HHakazlRDb8VRKcFKveViBvKrC8'
        login_data['form_id'] = 'user_login_block'
        login_data['op'] = 'Login'
        p = self.session.post("https://uozone2.uottawa.ca/user/login", login_data, headers=headers)

        # Confirm logged in
        html = BeautifulSoup(p.content, "html.parser")
        user = html.find('span', {'class': 'username'}).text
        if user == 'Anonymous':
            raise ValueError("Incorrect credentials provided.")
        else:
            self.loggedIn = True
            print("Logged in as " + user)

    def fieldToMap(self, html, name, select=False):
        ret = []
        if select:
            sel = html.find('select', attrs={'name': name})
            if sel:
                for opt in sel.find_all('option'):
                    txt = opt.text.encode("utf-8").strip()
                    if "value" in dict(opt.attrs):
                        ret.append({"name": txt, "value": opt["value"].encode("utf-8").strip()})
                    else:
                        ret.append({"name": txt, "value": txt})
        else:
            inputs = html.find_all('input', attrs={'name': name})
            print inputs.contents
            for i in inputs:
                txt = i.contents[0]
                ret.append({"name": txt.encode("utf-8").strip(), "value": i["value"].encode("utf-8").strip()})
        return ret

    def url(self):
        return self.br.main_frame.url().toString()

    def goToEvaluations(self):
        assert self.loggedIn
        r = self.session.get("https://uozone2.uottawa.ca/apps/s-report")
        print r.url
        return
        assert self.url() == 'https://web.uottawa.ca/uopr/WSN003;Lang=EN'
        html = BeautifulSoup(r.content, "html.parser")
        if "Teacher Course Evaluation" != html.find('title').text:
            raise LookupError("Site is down.")
        sessions = self.fieldToMap(html, 'sess-')
        years = self.fieldToMap(html, 'ctury', True)
        indices = self.fieldToMap(html, 'itype')
        evalTypes = self.fieldToMap(html, 'eval-')
        faculties = self.fieldToMap(html, 'facul', True)
        print sessions
        print years
        print indices
        print evalTypes
        print faculties
        self.fillEvaluationsForm('1', '2014', 'C', 'A', 'GENIE')


    # Search by prof or course
    def getEvaluations(self, prof, course):
        assert self.loggedIn and self.url().startswith("https://web.uottawa.ca/uopr/WSN003/ans001;Lang=EN;Student=" + self.username)
        if prof:
            print('Searching by prof ' + prof)

        elif course:
            print('Searching by prof ' + course)
        else:
            print('No prof or course provided.')

    def fillEvaluationsForm(self, session, year, iType, evalType, faculty):
        assert self.loggedIn and self.url() == 'https://web.uottawa.ca/uopr/WSN003;Lang=EN'
        # Fill and submit evaluations form
        self.session.fill("form", {
            "sess-": session,           # Session (1, 5, 9)
            "ctury": year,              # Year
            "itype": iType,             # Course Code (C) or Professor Name (T)
            "eval-": evalType,          # Regular (A), Medicine Block (B), Clinical Supervision (D)
            "facul": faculty            # Faculty (ex: engineering = GENIE)
        })
        self.br.call("form", "submit")
        result, resources = self.br.wait_for_selector('form')
        if not result:
            raise LookupError("No professors/courses found.")

        # Get list of courses/professors
        options, resources = self.br.evaluate("document.getElementsByName('indcr')[0].options")
        for opt in options:
            print opt
        self.br.capture_to('results.png')

    def logout(self):
        try:
            assert self.loggedIn
            self.session.get("https://uozone2.uottawa.ca/user/logout")
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
    finally:
        w.close()


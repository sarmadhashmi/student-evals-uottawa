from bs4 import BeautifulSoup
from ghost import Ghost
from robobrowser import RoboBrowser
import sys
from time import sleep
# MAYBE? CSV OUTPUT
# rating by prof
# prof, faculty, session + year, course code,
# search for prof
# get sessions, years, indexes(prof), evaltypes, faculties here

class Infoweb(object):
    def __init__(self, username, password):
        #self.br = RoboBrowser(parser="html.parser", history=True, tries=3, timeout=30)
        self.ghost = Ghost()
        self.br = self.ghost.start(download_images=False, wait_timeout=30)
        self.username = username
        self.password = password
        self.loggedIn = False

    def login(self):
        self.br.open("https://uozone2.uottawa.ca/user/login", timeout=30)
        self.br.fill("form[id=user-login-form]", {
            "name": self.username,
            "pass": self.password
        })
        self.br.call("form[id=user-login-form]", "submit", expect_loading=True)
        #login_form = self.br.get_form(id="user-login-form")
        #login_form["name"] = self.username
        #login_form['pass'] = self.password
        #self.br.submit_form(login_form)
        #user = self.br.find('span', {'class':'username'}).text
        html = BeautifulSoup(self.br.content, "html.parser")
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
                    txt = opt.txt.encode("utf-8").strip()
                    val = opt["value"]
                    if val is not None:
                        ret.append({"name": txt, "value": val.encode("utf-8").strip()})
                    else:
                        ret.append({"name": txt, "value": txt})
        else:
            inputs = html.find_all('input', attrs={'name': name})
            if name == 'sess-':
                ret = [{"name": i.text.strip().split()[0].encode("utf-8"), "value": i["value"].encode("utf-8").strip()} for i in inputs]
            else:
                ret = [{"name": i.text.encode("utf-8").strip(), "value": i["value"].encode("utf-8").strip()} for i in inputs]
        return ret

    def goToEvaluations(self):
        assert self.loggedIn
        self.br.open("https://uozone2.uottawa.ca/apps/s-report", timeout=30)
        html = BeautifulSoup(self.br.content, "html.parser")
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


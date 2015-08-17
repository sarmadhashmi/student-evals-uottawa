from bs4 import BeautifulSoup
from collections import OrderedDict
import re, requests, getpass

DEFAULT_TIMEOUT = 60
class Infoweb(object):
    def __init__(self, username, password):
        self.session = requests.Session()
        self.url = None
        self.postURL = None
        self.formOptions = dict()
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36"
        }
        self.username = username
        self.password = password
        self.loggedIn = False

    def login(self):
        # Build query to login
        login_data = dict()
        login_data['name'] = self.username
        login_data['pass'] = self.password
        login_data['form_build_id'] = 'form-o9zTDwe0qqz4hLM0HHakazlRDb8VRKcFKveViBvKrC8'
        login_data['form_id'] = 'user_login_block'
        login_data['op'] = 'Login'
        p = self.session.post("https://uozone2.uottawa.ca/user/login", login_data, headers=self.headers)
        self.url = p.url

        # Confirm logged in
        html = BeautifulSoup(p.content, "html.parser")
        user = html.find('span', {'class': 'username'}).text
        if user == 'Anonymous':
            raise ValueError("Incorrect credentials provided.")
        else:
            self.loggedIn = True
            print("Logged in as " + user)

    def fieldToMap(self, html, name, select=False):
        ret = OrderedDict()
        if select:
            sel = html.find('select', attrs={'name': name})
            if sel:
                for opt in sel.find_all('option'):
                    txt = opt.contents[0].encode("utf-8").strip()
                    if "value" in dict(opt.attrs):
                        ret[opt["value"].encode("utf-8").strip()] = txt
                    else:
                        ret[txt] = txt
        else:
            inputs = html.find_all('input', attrs={'name': name})
            for i in inputs:
                txt = i.contents[0]
                ret[i["value"].encode("utf-8").strip()] = txt.encode("utf-8").strip()
        return ret

    def getGlobalEvaluationValues(self):
        assert self.loggedIn
        r = self.session.get("https://uozone2.uottawa.ca/apps/s-report")
        assert r.url == 'https://web.uottawa.ca/uopr/WSN003;Lang=EN'
        self.url = r.url
        html = BeautifulSoup(r.content, "html.parser")
        if "Teacher Course Evaluation" != html.find('title').text:
            raise LookupError("Site is down.")
        self.formOptions["sessions"] = self.fieldToMap(html, 'sess-')
        self.formOptions["years"] = self.fieldToMap(html, 'ctury', True)
        self.formOptions["indices"] = self.fieldToMap(html, 'itype')
        self.formOptions["evalTypes"] = self.fieldToMap(html, 'eval-')
        self.formOptions["faculties"] = self.fieldToMap(html, 'facul', True)
        return html

    def searchByProf(self, html, faculty, prof_name):
        assert isinstance(html, BeautifulSoup)
        results = self._getAllEvaluationsForProfessor(html, faculty, prof_name)
        if len(results) == 0:
            return
        f = open('test.txt', 'w+')
        results_by = 'all_data'
        if results_by == 'all_display':
            for evaluations in results:
                for course in evaluations["evaluation_results"]:
                    f.write('Course: ' + course.encode('utf-8').strip() + ', Year: ' + evaluations["year"] + ', Session: ' + evaluations["session"] + '\n')
                    for e in evaluations["evaluation_results"][course]:
                        f.write('Question: ' + str(e["Question"]) + '\n')
                        f.write('Total Responses: ' + str(e["Total Responses"]) + '\n')
                        f.write('Average Rating: ' + str(e["Average Rating"]) + '\n')
                        for opt in e["Options"]:
                            f.write('\t' + opt + '\n')
                            for k in e["Options"][opt]:
                                f.write('\t\t' + k + ': ' + str(e["Options"][opt][k]) + '\n')
                    f.write('\n\n\n')
        elif results_by == 'all_data':
            data = dict()
            for evaluations in results:
                for course in evaluations["evaluation_results"]:
                    for e in evaluations["evaluation_results"][course]:
                        if e["Question"] not in data:
                            data[e["Question"]] = OrderedDict()
                            data[e["Question"]]["num_times_asked"] = 0.0
                            data[e["Question"]]["Options"] = OrderedDict()
                            data[e["Question"]]["Total Responses"] = 0.0
                            data[e["Question"]]["Average Rating"] = 0.0

                        data[e["Question"]]["num_times_asked"] += 1.0
                        data[e["Question"]]["Total Responses"] += e["Total Responses"]
                        data[e["Question"]]["Average Rating"] += e["Average Rating"]
                        for opt in e["Options"]:
                            if opt not in data[e["Question"]]["Options"]:
                                data[e["Question"]]["Options"][opt] = {
                                    "numerator": 0.0,
                                    "denominator": 0.0
                                }
                            num = e["Options"][opt]["Responses"]
                            percent = e["Options"][opt]["Percentage of Total"] / 100.0
                            data[e["Question"]]["Options"][opt]["numerator"] += percent*num
                            data[e["Question"]]["Options"][opt]["denominator"] += num

            for d in data:
                question = data[d]
                n = question["num_times_asked"]
                avg_rating = question["Average Rating"] / n
                f.write('Question: ' + d + '\n')
                f.write('Number of times professor asked this question: ' + str(n) + '\n')
                f.write('Number of students that have answered to this day: ' + str(question["Total Responses"]) + '\n')
                f.write('Average rating overall: ' + str(avg_rating) + '\n')
                for opt in question["Options"]:
                    numerator = question["Options"][opt]["numerator"]
                    denominator = question["Options"][opt]["denominator"]
                    if denominator:
                        f.write('\t' + opt + ': ' + str((numerator/denominator)*100.0) + '\n')
                    else:
                        f.write('\t' + opt + ': ' + str((numerator/1.0)*100.0) + '\n')
                f.write('\n\n')
        elif results_by == 'course_data':
            print 'placeholder'
        f.close()

    def _getAllEvaluationsForProfessor(self, html, faculty, prof):
        profData = None
        years = [x for x in self.formOptions["years"]]
        sessions = [x for x in self.formOptions["sessions"]]
        # Find indcr for prof
        for y in years:
            for s in sessions:
                if not profData:
                    res = self._getEvaluationFormValues(html, s, y, 'T', 'A', faculty, prof)
                    if len(res) > 0:
                        profData = res[0]
                        break
            if profData:
                break

        results = []
        # Prof not found in any year
        if not profData:
            return results
        print 'Prof found: ' + profData["professor"]
        # Prof found, now find evaluations
        for y in years:
            profData["postData"]["ctury"] = y
            for s in sessions:
                profData["postData"]["sess-"] = s
                evaluation_results = self._getEvaluation(profData["postData"])
                if evaluation_results:
                    results.append({
                        "evaluation_results": evaluation_results,
                        "year": y,
                        "session": self.formOptions["sessions"][s]
                    })
            print 'Got results for: ' + y
        return results

    def _getEvaluation(self, postData):
        assert self.loggedIn and self.postURL.startswith("https://web.uottawa.ca/uopr/WSN003/ans002;Lang=EN;Student=" + self.username)
        p = self.session.post(self.postURL, postData, headers=self.headers)
        if 'No record found' in p.content:
            return None
        evalHTML = BeautifulSoup(p.content, "html.parser")
        tables = [table for table in evalHTML.find_all('table') if "width" in dict(table.attrs) and table["width"] == "700"][:-1]
        res = []
        prof_mode = postData['itype'] == 'T'
        course_res = OrderedDict()
        for table in tables:
            rows = table.find_all('tr')
            for x in range(0, len(rows), 4):
                questionnaire_data = OrderedDict()
                questionnaire_data["Question"] = rows[x].text[rows[x].text.find('\n/') + 2:].strip()
                # Get poll options
                optionsStrings = list(rows[x + 1].stripped_strings)
                options = [optionsStrings[index + 1].encode('utf-8') for index, opt in enumerate(optionsStrings) if len(opt) == 1]

                # Get poll percentages/numbers
                numbers = [float(x) for x in list(rows[x + 3].stripped_strings)]
                questionnaire_data["Total Responses"] = numbers[0]
                questionnaire_data["Average Rating"] = numbers[1]
                questionnaire_data["Options"] = OrderedDict()

                i = 2
                for opt in options:
                    questionnaire_data["Options"][opt] = OrderedDict()
                    questionnaire_data["Options"][opt]["Responses"] = numbers[i]
                    questionnaire_data["Options"][opt]["Percentage of Total"] = numbers[i + 1]
                    i += 2

                res.append(questionnaire_data)

            if prof_mode:
                course = table.find_previous('a', href='#bottom').findNext('b').next_sibling
                if course not in course_res:
                    course_res[course] = []
                course_res[course] += res
                res = []

        return res or course_res

    def _getEvaluationFormValues(self, html, session, year, iType, evalType, faculty, filter=None):
        assert self.loggedIn and self.url == 'https://web.uottawa.ca/uopr/WSN003;Lang=EN'
        results = []
        self.postURL = html.find('form')['action']
        # Fill and submit evaluations form
        data = {
            "sess-": session,           # Session (1, 5, 9)
            "ctury": year,              # Year
            "itype": iType,             # Course Code (C) or Professor Name (T)
            "eval-": evalType,          # Regular (A), Medicine Block (B), Clinical Supervision (D)
            "facul": faculty            # Faculty (ex: engineering = GENIE)
        }
        p = self.session.post(self.postURL, data, headers=self.headers)
        if 'No evaluation found' in p.content:
            return results

        html = BeautifulSoup(p.content, "html.parser")
        self.postURL = html.find('form')['action']
        del data["facul"]
        # Get list of courses/professors
        options = html.find('select', {'name': 'indcr'}).find_all('option')
        for opt in options:
            txt = re.sub("\s\s+", " ", opt.contents[0])
            obj = dict()
            profData = data.copy()
            profData["indcr"] = opt["value"]                           # Update POST data for eval results
            if iType == 'T':
                obj["professor"] = txt
            elif iType == 'C':
                arr = [str(s).strip() for s in txt.encode('utf-8').strip().split('-')]
                obj["code"] = arr[0]
                obj["course"] = arr[1].replace(" ", "")
                obj["campus"] = arr[2]
                obj["professor"] = arr[3]
                obj["faculty"] = faculty
            obj["postData"] = profData
            if not filter:
                results.append(obj)
            elif iType == 'C' and filter in obj["course"]:
                results.append(obj)
            elif iType == 'T' and filter in obj["professor"]:
                results.append(obj)
        return results

    def logout(self):
        try:
            assert self.loggedIn
            self.session.get("https://uozone2.uottawa.ca/user/logout")
            self.session.get("https://web3.uottawa.ca/infoweb/logoff/en.html")
            self.loggedIn = False
            print("Logged out...")
        except:
            print("Not logged in.")

    def close(self):
        self.logout()
from prompt_toolkit.validation import Validator, ValidationError

class CourseCodeValidator(Validator):
    def validate(self, document):
        pattern = re.compile()
        if not pattern.match(course_code):
            raise ValidationError(message='Not a valid course code.', index=len(document.text))  # Move cursor to end of input.

class ListValidator(Validator):
    def __init__(self, options):
        self.valid_options = options
        super(ListValidator, self)

    def validate(self, document):
        if document not in self.valid_options:
            raise ValidationError(message='Invalid option.', index=len(document.text))  # Move cursor to end of input.

def get_input_and_validate(prompt, regex=None, is_password=False, is_confirm=False):
    pattern = None
    if is_confirm:
        regex = ['y', 'Y', 'n', 'N']
    if regex and isinstance(regex, list):
        pattern = re.compile('^[' + '|'.join(regex) + ']$')
    elif regex:
        pattern = re.compile(regex)

    success = False
    while not success:
        if is_password:
            tmp = getpass.getpass(prompt)
        else:
            tmp = raw_input(prompt)
        if not regex or (pattern and pattern.match(tmp)):
            success = True
        else:
            print 'Invalid option entered.'
    return tmp

if __name__ == '__main__':
    # Login
    print 'PRESS CTRL+D or COMMAND+D at any time to exit.'
    username = get_input_and_validate('Enter your uoZone or InfoWeb username: ')
    password = get_input_and_validate('Enter your uoZone or InfoWeb password: ', is_password=True)
    w = Infoweb(username, password)
    w.login()

    # Get details if successful login
    confirmed = False
    while not confirmed:
        print '\n'
        mode = get_input_and_validate('Would you like to search by Course Code (C) or Professor Name (T): ', ['c', 'C', 't', 'T'])
        if mode == 'T':
            prof_name = get_input_and_validate('Enter the name of the professor that you would like the evaluations for: ')
        else:
            course_code = get_input_and_validate('Enter the course code of the course that you would like the evaluations for: ', "^[A-Z]{3}[0-9]{4}$")

        print '\nPlease confirm your search details: '
        if mode == 'T':
            print 'Search by: Professor'
            print 'Search term: ' + prof_name
        else:
            print 'Search by: Course Code'
            print 'Search term: ' + course_code
        confirmed = get_input_and_validate("\nWould you like to search with the above criteria? (Enter y or n): ", is_confirm=True) == 'y'

    # Confirmed everything, time to get the stats
    exit()
    w = Infoweb(username, password)
    w.login()
    print 'Searching...'
    #try:
     #   w = Infoweb('username', 'password')
      #  w.login()
       # w.getGlobalEvaluationValues()
    #finally:
     #   w.close()



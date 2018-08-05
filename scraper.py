__author__ = 'Cooper Small'
__title__ = 'Website Scraper'

import bs4 as bs
from urllib.request import Request, urlopen, HTTPError
from lxml import etree
import re
import aiohttp
import asyncio
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os


class Website(object):

    _name = None
    _button = None
    _number = None
    _url = None
    _links = None
    _extensions = {'Index': None}

    _keys = ['private', 'parties', 'page',
             'contact', 'event', 'birthday',
             'party', 'catering', 'banquet',
             'wedding', 'Catering', 'Private',
             'Wedding', 'Parties', 'Party',
             'Contact', 'Event', 'Banquet',
             'EVENT', 'WEDDING', 'PARTIES',
             'CATERING', 'CONTACT', 'PRIVATE']

    def __init__(self, name, number, button, url):

        # if re.search('.php/', url) is not None or re.search('.html/', url) is not None:
        #     pass

        # elif re.search('.php', url) is not None or re.search('.html', url) is not None:
        #     url += '/'

        # else:
        #     domain_extensions = ['.com/', '.net/' '.org/', '.co/', '.us/', '.com',
        #                          '.net', '.org', '.co', '.us']

        #     for domain in domain_extensions:
        #         split = len(url.split(domain, 1))
        #         if split > 1:
        #             url = url.split(domain, 1)[0]
        #             if re.search('/', domain) is None:
        #                 domain += '/'
        #             url += domain
        #             print(url)
        #             break

        # if url[:4] != 'http':
        #     url = 'http://' + url

        number_formats = ['-', '.', ' ']

        for formats in number_formats:
            junk = number.split(formats, 1)
            if len(junk) > 1:
                if len(junk[0]) == 3:
                    junk[0] += formats
                    number = "".join(str(x) for x in junk)
                    break
                elif len(junk[0]) == 5:
                    junk[0] = junk[0].strip('(')
                    junk[0] = junk[0].strip(')')
                    junk[0] += formats
                    number = "".join(str(x) for x in junk)
                    break

        if len(number) != 12:
            number = 'Invalid Number'

        if re.search('https://app.eventplicity.com/', button) is None and re.search('http://forms.eventplicity.com/', button) is None:
            button = 'Invalid Button'

        try:
            button = button.rsplit('=', 1)[1]
        except:
            pass

        self._name = name
        self._button = button
        self._number = number
        self._url = url

    async def addWebsite(self):

        check = self._addIndex()

        if check == 1:
            print(check)
            print(self._name)
            check = await asyncio.gather(self._checkExtensions())
            print(check)
            print('\n')
        else:
            pass

        return check

    def _addIndex(self):

        check = 0

        try:
            headers = {'User-Agent':
                       "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36"}

            request = Request(self._url, None, headers)
            response = urlopen(request)
            source = response.read()

            webpage = bs.BeautifulSoup(source, 'lxml')
            self._extensions['Index'] = webpage

            if self._extensions['Index'] is not None:
                check = 1

                domain_extensions = ['.com/', '.net/' '.org/', '.co/', '.us/', '.com',
                                     '.net', '.org', '.co', '.us']

                for domain in domain_extensions:
                    split = len(self._url.split(domain, 1))
                    if split > 1:
                        self._url = self._url.split(domain, 1)[0]
                        if re.search('/', domain) is None:
                            domain += '/'
                        self._url += domain
                        print(self._url)
                        break

                if self._url[:4] != 'http':
                    self._url = 'http://' + self._url

        except:
            pass

        return check

    async def _checkExtensions(self):

        _extensions = {}
        keys = []
        urls = []

        nav_bar = self._extensions['Index'].nav

        if nav_bar is not None:
            print('__________________TRUE_________________')
            for nav in self._extensions['Index'].find_all('nav'):
                for link in nav.find_all('a', href=True):
                    url = str(link['href'])
                    key = self._cleanKey(str(link.string))
                    if key == 'None':
                        key = self._cleanKey(str(link.text))
                    if (re.search('facebook', url) is None and re.search('mailto', url) is None and re.search('google', url) is None
                            and re.search('eventplicity', url) is None and re.search('opentable', url) is None):
                        title = self._addTitle(key)
                        keys.append(title)
                        urls.append(url)

        else:
            for link in self._extensions['Index'].find_all('a', href=True):
                url = str(link['href'])
                for key in self._keys:
                    if (re.search(key, url) is not None and re.search('facebook', url) is None and re.search('mailto', url) is None
                            and re.search('google', url) is None and re.search('eventplicity', url) is None and re.search('opentable', url) is None):
                        title = self._addTitle(key)
                        keys.append(title)
                        urls.append(url)

        headers = {'User-Agent':
                   "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36"}

        links = [self._cleanUrl(url) for url in urls]
        self._links = dict(zip(keys, links))
        print(self._links)
        print(len(urls))
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                    urls = await asyncio.gather(*[self._addExtension(url, session) for url in urls])

        finally:
            await session.close()

        _extensions = dict(zip(keys, urls))
        _extensions['Index'] = self._extensions['Index']

        check = self._cleanExtensions(_extensions)
        print(check)

        return check

    async def _addExtension(self, url, session):

        url = self._cleanUrl(url)

        try:
            async with session.get(url) as response:
                source = await response.read()
                webpage = bs.BeautifulSoup(source.decode('utf-8'), 'lxml')
                return webpage.body

        except:
            pass

    def _addSelenium(self):

        _extensions = {'Index': None}

        path = os.getcwd()
        path = f'{path}/driver/chromedriver.exe'
        driver = webdriver.Chrome(path)
        driver.get(self._url)
        body = driver.page_source

        _extensions['Index'] = body
        print(body)

        try:
            links = driver.find_elements_by_xpath("//a[@href]")
        except:
            check = 0

        # print(links)
        for link in links:
            link_string = str(link.get_attribute('href'))
            # print(link_string)
            i = 0
            for key in self._keys:
                if link and re.search(key, link_string) is not None and re.search('eventplicity', link_string) is None:
                    body = self._click(link_string, path)
                    if body != '!-------------404_NOT_FOUND-------------!':
                        title = self._addTitle(key)
                        _extensions[title] = body
                        del self._keys[i]
                    else:
                        continue
                else:
                    i += 1
                    continue

        driver.close()
        check = self._cleanExtensions(_extensions)
        return check

    def _click(self, link, path):

        try:
            driver = webdriver.Chrome(path)
            driver.get(link)
            body = driver.page_source
            driver.close()

        except:
            body = '!-------------404_NOT_FOUND-------------!'

        return body

    def _cleanExtensions(self, _extensions):

        check = 0

        self._extensions.clear()
        self._extensions = {key: value for key, value in _extensions.items() if value is not None}

        from collections import OrderedDict
        ordered = OrderedDict(sorted(self._extensions.items(), key=lambda t: t[0]))
        self._extensions = dict(ordered)

        _extensions.clear()

        _extensions = {key: value for key, value in self._extensions.items()
                       if value not in _extensions.values()}

        if _extensions['Index'] is None:
            _extensions['Index'] = self._extensions['Index']

        self._extensions.clear()

        for key, value in _extensions.items():
            if key != '' and key != ' Page' and key != 'Home Page' and key != 'Welcome Page':
                self._extensions[key] = value
                check += 1

        return check

    def _addTitle(self, key):

        title = ''

        if key == 'private' or key == 'Private' or key == 'PRIVATE':
            key += ' parties'
        elif key == 'contact' or key == 'Contact' or key == 'CONTACT':
            key += ' us'
        elif key == 'party' or key == 'parties' or key == 'Party' or key == 'Parties' or key == 'PARTY' or key == 'PARTIES':
            key = 'private ' + key

        key += ' page'
        key = key.lower()
        title = key.title()

        return title

    def _cleanKey(self, key):

        key = re.sub(r"[\n\t]*", "", key)
        key = re.sub(' +', ' ', key)
        if key[:1] == ' ':
            key = key[1:]
        if key[-1:] == ' ':
            key = key[:-1]

        return key

    def _cleanUrl(self, url):

        full_url = ''

        if url == self._button:
            return
        elif re.search('http://', url) is not None or re.search('https://', url) is not None:
            full_url = url
        else:
            if url[:1] == '/':
                _url = self._url[:-1]
                full_url = _url + url
            else:
                full_url = self._url + url

        return full_url

    def runCheck(self):

        checks = {self._name: {}}

        for key in self._extensions:
            checks[self._name][key] = None
            check = {'Phone_Number': None, 'Eventplicity_Link': None}

            if self._url == '!-------------404_NOT_FOUND-------------!':
                check['Phone_Number'] = 'Website Not Found'
                check['Eventplicity Link'] = 'Website Not Found'
            else:
                check['Phone_Number'], check['Eventplicity_Link'] = self._checkNumber(key), self._checkButton(key)

            if check['Phone_Number'] == 0 and check['Eventplicity_Link'] == 0 and key != 'Index':
                del checks[self._name][key]

            else:
                checks[self._name][key] = check

            # checks[self._name][key] = check

        counter = 0
        for k, v in checks.items():
            for k, v in v.items():
                print(k, v)
                counter += 1
        print(counter)
        print('\n')

        return checks

    def _checkNumber(self, key):

        check = 0
        first_check = 0
        second_check = 0

        webpage = self._extensions[key]
        try:
            [junk.extract() for junk in webpage(['style', 'script', '[document]', 'head', 'title'])]
            webpage = webpage.getText()
        except:
            pass

        number = []
        for character in str(self._number):
            number.append(character)

        webtext = []
        for character in str(webpage):
            webtext.append(character)

        try:
            for i in range(len(webtext)):
                if webtext[i] == number[0]:
                    if webtext[i + 1] == number[1]:
                        if webtext[i + 2] == number[2]:
                            if webtext[i + 4] == number[4]:
                                if webtext[i + 5] == number[5]:
                                    if webtext[i + 6] == number[6]:
                                        if webtext[i + 8] == number[8]:
                                            if webtext[i + 9] == number[9]:
                                                if webtext[i + 10] == number[10]:
                                                    if webtext[i + 11] == number[11]:
                                                        first_check += 1

            number.insert(0, '(')
            number.insert(4, ')')

            for i in range(len(webtext)):
                if webtext[i] == number[0]:
                    if webtext[i + 1] == number[1]:
                        if webtext[i + 2] == number[2]:
                            if webtext[i + 3] == number[3]:
                                if webtext[i + 4] == number[4]:
                                    if webtext[i + 6] == number[6]:
                                        if webtext[i + 7] == number[7]:
                                            if webtext[i + 8] == number[8]:
                                                if webtext[i + 10] == number[10]:
                                                    if webtext[i + 11] == number[11]:
                                                        if webtext[i + 12] == number[12]:
                                                            if webtext[i + 13] == number[13]:
                                                                second_check += 1

            if first_check > 0 and second_check > 0:
                check = first_check + second_check

            elif first_check > 0 and second_check == 0:
                check = first_check

            elif first_check == 0 and second_check > 0:
                check = second_check

            else:
                pass

        except IndexError:
            pass

        return check

    def _checkButton(self, key):

        check = 0

        try:
            webpage = self._extensions[key].find_all('a', href=True)
            for link in webpage:
                url = str(link)
                if re.search(self._button, url) is not None:
                    check += 1
        except:
            for i in re.finditer(self._button, self._extensions[key]):
                check += 1

        return check


# x = Website('bona-sera', '706-251-9137', 'https://app.eventplicity.com/inquiry/?template_id=7f7e3a61699b450c83e18efe4fe3f16e', 'http://stoneysseafoodhouse.com/kingfishers/')
# loop = asyncio.get_event_loop()
# loop.run_until_complete(x.addWebsite())
# for k, v in x._extensions.items():
#     print(k)
# print(x._links)
# loop.close()

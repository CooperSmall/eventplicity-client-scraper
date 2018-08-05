__author__ = 'Cooper Small'
__title__ = 'Sheet Processsor'

import asyncio
import datetime
import time
import os
import re
import smtplib
import pickle
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from scraper import Website


class Sheet(object):

    name = None
    _last_report = None
    _row = 0
    _sheet = None
    _clients = []
    _columns = []
    _settings = []
    _skip = []

    def __init__(self, name, columns, token, row, skip):

        scopes = ['https://spreadsheets.google.com/feeds',
                  'https://www.googleapis.com/auth/drive']

        self._connectSheet(scopes, token, name)

        path = os.getcwd()
        self._last_report = pd.read_pickle(f'{path}/last_report.pkl')
        pd.options.display.max_rows = 9999
        print(self._last_report)

        if self._sheet:
            self.name = name
            self._findColumns(columns)
            self._row = int(row)

            if len(skip) > 0:
                self._skip = skip
            else:
                self._skip = None
        else:
            self.name = 'CONNECTION_ERROR'

    def main(self):

        row = self._row
        error_clients = {}
        unreachable_clients = {'404s': [], 'Missing_Info': [], 'Selenium': []}
        keys = []
        frames = []

        loop = asyncio.get_event_loop()

        try:
            for row in self._clients:

                    name = str(row[self._columns[0]])
                    number = str(row[self._columns[1]])
                    button = str(row[self._columns[2]])
                    url = str(row[self._columns[3]])

                    if (name and number and button and url and
                        number[:3].isdigit() is True and re.search('eventplicity', button) is not None):

                        client = Website(name, number, button, url)
                        connected = loop.run_until_complete(client.addWebsite())

                        if connected != 0:
                            check = client.runCheck()

                            if check == {name: {'Index': {'Phone_Number': 0, 'Eventplicity_Link': 0}}}:
                                if len(client._extensions) > 1:
                                    compare = self._compare(check, name)
                                    if compare is not None:
                                        error_clients[name] = {'Website': client, 'Check': compare, 'Connect': [name, number, button, url]}
                                    for key, value in check.items():
                                        keys.append(key)
                                        frame = pd.DataFrame.from_dict(value, orient='index')
                                        frames.append(frame)
                                else:
                                    unreachable_clients['Selenium'].append(name)
                            else:
                                compare = self._compare(check, name)
                                if compare is not None:
                                    error_clients[name] = {'Website': client, 'Check': compare, 'Connect': [name, number, button, url]}
                                for key, value in check.items():
                                    keys.append(key)
                                    frame = pd.DataFrame.from_dict(value, orient='index')
                                    frames.append(frame)

                        else:
                            unreachable_clients['404s'].append(name)

                    else:
                        unreachable_clients['Missing_Info'].append(name)

            error_clients = self._secondPass(error_clients, loop)

        finally:
            loop.close()

        self._generateData(keys, frames, unreachable_clients)
        subject, message = self._composeEmail(error_clients, unreachable_clients)

        return subject, message

    def _secondPass(self, clients, loop):

        error_clients = {}

        for client, value in clients.items():

            print(client)
            client_dict = {client: None}
            name, number, button, url = clients[client]['Connect']
            website = Website(name, number, button, url)
            loop.run_until_complete(website.addWebsite())
            check = website.runCheck()

            first_check = clients[client]['Check']
            second_check = self._compare(check, name)

            if first_check == second_check:
                client_dict[client] = value
                error_clients.update(client_dict)

        return error_clients

    def _compare(self, check, name):

        client = None
        changes = {'Added': {'Phone_Number': [], 'Button': []}, 'Removed': {'Phone_Number': [], 'Button': []}}
        new_pages = []

        try:
            frame = self._last_report.loc[name]
            last = frame.to_dict(orient='index')
            for k, v in last.items():
                print(k, v)
            print('\n')

            for check_key, check_value in check[name].items():
                for last_key, last_value in last.items():
                    if check_key == last_key:
                        if check_value != last_value:
                            if check_value['Phone_Number'] > last_value['Phone_Number']:
                                changes['Added']['Phone_Number'].append(check_key)
                            else:
                                changes['Removed']['Phone_Number'].append(check_key)

                            if check_value['Eventplicity_Link'] > last_value['Eventplicity_Link']:
                                changes['Added']['Button'].append(check_key)
                            else:
                                changes['Removed']['Button'].append(check_key)

            if len(check[name]) < len(last):
                last_keys = [key for key, value in last.items()]
                check_keys = [key for key, value in check[name].items()]
                removed = [key for key in last_keys if key not in check_keys]

                for fail in removed:
                    changes['Removed']['Phone_Number'].append(fail)
                    changes['Removed']['Button'].append(fail)

            elif len(check[name]) > len(last):
                last_keys = [key for key, value in last.items()]
                check_keys = [key for key, value in check[name].items()]
                pages = [key for key in check_keys if key not in last_keys]

                for page in pages:
                    new_pages.append(page)

        except KeyError:
            client = {'New': name, 'Changes': None, 'New_Pages': None}
            return client

        if (changes != {'Added': {'Phone_Number': [], 'Button': []}, 'Removed': {'Phone_Number': [], 'Button': []}}
            and len(new_pages) != 0):
            client = {'New': None, 'Changes': changes, 'New_Pages': new_pages}
        elif (changes != {'Added': {'Phone_Number': [], 'Button': []}, 'Removed': {'Phone_Number': [], 'Button': []}}
              and len(new_pages) == 0):
            client = {'New': None, 'Changes': changes, 'New_Pages': None}
        elif (changes == {'Added': {'Phone_Number': [], 'Button': []}, 'Removed': {'Phone_Number': [], 'Button': []}}
              and len(new_pages) != 0):
            client = {'New': None, 'Changes': None, 'New_Pages': new_pages}

        if client:
            # client = {key: value for key, value in client.items() if value is not None}
            print(client)

        return client

    def _composeEmail(self, error_clients, unreachable_clients):

        added, removed = self._sortClients(error_clients)

        date = datetime.datetime.now()
        date = f'{date.month}/{date.day}/{date.year}'

        subject = f'Web Scraper Report {date}'
        message = f"The following analysis was conducted on {date} of our clients who's information is stored on our {self.name} Google Spreadsheet:\n\n"

        if added is None and removed is None:
            message += "No changes to our information were detected on any of our clients' websites.\n"

        else:
            if added:
                message += 'Our information was added to the following client(s) webpages:\n'
                for error in added:
                    for client in error.keys():
                        message += f'\n\t{client}:\n'
                        try:
                            if error[client]['Phone_Number']:
                                message += '\t\tPhone Number:\n'
                                for page, link in error[client]['Phone_Number'].items():
                                    message += f'\t\t\t{page} ({link})\n'
                        except:
                            continue

                        try:
                            if error[client]['Button']:
                                message += '\t\tButton:\n'
                                for page, link in error[client]['Button'].items():
                                    message += f'\t\t\t{page} ({link})\n'
                        except:
                            continue

            if removed:
                message += 'Our information was removed from the following client(s) webpages:\n'
                for error in removed:
                    for client in error.keys():
                        message += f'\n\t{client}:\n'
                        try:
                            if error[client]['Phone_Number']:
                                message += '\t\tPhone Number:\n'
                                for page, link in error[client]['Phone_Number'].items():
                                    message += f'\t\t\t{page} ({link})\n'
                        except:
                            continue

                        try:
                            if error[client]['Button']:
                                message += '\t\tButton:\n'
                                for page, link in error[client]['Button'].items():
                                    message += f'\t\t\t{page} ({link})\n'
                        except:
                            continue

        if unreachable_clients != {'404s': [], 'Missing_Info': [], 'Selenium': []}:
            if len(unreachable_clients['404s']) > 0:
                message += "\nThe following client(s) websites are either inactive or temporarily unavailable:\n\n"
                for error in unreachable_clients['404s']:
                    if self._skip:
                        for skip in self._skip:
                            if error == skip:
                                error = None
                                break
                    if error:
                        message += f'\t{error}\n'

            if len(unreachable_clients['Missing_Info']) > 0:
                message += "\nThe following client(s) are missing the appropriate information to check their website:\n\n"
                for error in unreachable_clients['Missing_Info']:
                    if self._skip:
                        for skip in self._skip:
                            if error == skip:
                                error = None
                                break
                    if error:
                        message += f'\t{error}\n'

        return subject, message

    def _sortClients(self, clients):

        added = []
        removed = []

        if clients != {}:
            for client in clients.keys():
                if self._skip:
                    for skip in self._skip:
                        if client == skip:
                            client = None
                            break

                if client:
                    changes = {client: {}}
                    if clients[client]['Check']['Changes']:
                        if clients[client]['Check']['Changes']['Added']['Phone_Number'] != []:
                            client_dict = {'Phone_Number': {}}
                            pages = {}
                            for page in clients[client]['Check']['Changes']['Added']['Phone_Number']:
                                for _page, link in clients[client]['Website']._links.items():
                                    if page == _page:
                                        pages[page] = link
                            client_dict['Phone_Number'] = pages
                            changes[client] = client_dict

                        if clients[client]['Check']['Changes']['Added']['Button'] != []:
                            client_dict = {'Button': {}}
                            pages = {}
                            for page in clients[client]['Check']['Changes']['Added']['Button']:
                                for _page, link in clients[client]['Website']._links.items():
                                    if page == _page:
                                        pages[page] = link
                            client_dict['Button'] = pages
                            if changes == {client: {}}:
                                changes[client] = client_dict
                            else:
                                changes[client].update(client_dict)
                            
                        if changes != {client: {}}:
                            added.append(changes)
                            changes.clear()
                            changes = {client: {}}

                        if clients[client]['Check']['Changes']['Removed']['Phone_Number'] != []:
                            client_dict = {'Phone_Number': {}}
                            pages = {}
                            for page in clients[client]['Check']['Changes']['Removed']['Phone_Number']:
                                for _page, link in clients[client]['Website']._links.items():
                                    if page == _page:
                                        pages[page] = link
                            client_dict['Phone_Number'] = pages
                            changes[client] = client_dict

                        if clients[client]['Check']['Changes']['Removed']['Button'] != []:
                            client_dict = {'Button': {}}
                            pages = {}
                            for page in clients[client]['Check']['Changes']['Removed']['Button']:
                                for _page, link in clients[client]['Website']._links.items():
                                    if page == _page:
                                        pages[page] = link
                            client_dict['Button'] = pages
                            if changes == {client: {}}:
                                changes[client] = client_dict
                            else:
                                changes[client].update(client_dict)

                        if changes != {client: {}}:
                            removed.append(changes)

        if added == []:
            added = None

        if removed == []:
            removed = None

        return added, removed

    def _connectSheet(self, scopes, token, name):

        try:
            path = os.path.abspath(f'creds/{token}')
            creds = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
            client = gspread.authorize(creds)
            sheet = client.open(name).sheet1
            self._sheet = sheet
            data = sheet.get_all_records(empty2zero=False, head=1)
            for row in data:
                self._clients.append(list(row.values()))

        except:
            class ConnectionException (Exception):
                def __init__(self, *args):
                    super(ConnectionException, self).__init__('Please Review your Credentials and Pathways')
            raise ConnectionException()

    def _findColumns(self, columns):

        cols = []
        try:
            for column in columns:
                cell = self._sheet.find(column)
                col = int(cell.col) - 1
                if col >= 0:
                    cols.append(col)

        except:
            class ColumnException (Exception):
                def __init__(self, *args):
                    super(ColumnException, self).__init__('Please Review the Spelling and Order of your Columns')
            raise ColumnException()

        if len(cols) == len(columns):
            self._columns = cols
        else:
            raise ColumnException()

    def _generateData(self, keys, frames, unreachable_clients):

        report = pd.concat(frames, keys=keys, sort=False)
        path = os.getcwd()
        report.to_pickle(f'{path}/last_report.pkl')

        with open(f'{path}/errors.pkl', 'wb') as f:
            pickle.dump(unreachable_clients, f)


# x = Sheet('BotTest', ['Shortname', 'EVP Phone', 'Event Builder', 'Venue Website Link', 'Status'], 'client_secret.json', 2, ['101-steak'])
# error_clients = {'101-steak': {'Check': {'Changes': {'Added': {'Phone_Number': ['Contact Us Page'], 'Button': []}, 'Removed': {'Phone_Number': [], 'Button': []}}}}}
# u = {'404s': ['101-steak', 'wowowow'], 'Missing_Info': ['101-steak'], 'Selenium': {}}
# subject, message = x._composeEmail(error_clients, u)
# print(subject, '\n', message)
# x.main()

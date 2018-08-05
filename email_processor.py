import datetime
import email
import time
import os
import re
import pickle
import imaplib
import smtplib
import pandas as pd
from sheet_processor import Sheet


def main():

    settings = parseSettings()
    time = datetime.datetime.now().time()

    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(settings['USER'], settings['PASSWORD'])
    mail.select('Inbox')

    status, messages = mail.uid('search', None, '(UNSEEN)')
    message = ''

    if status == 'OK':

        for uid in messages[0].split():
            status, data = mail.uid('fetch', uid, '(RFC822)')

            if status == 'OK':
                sent_email = email.message_from_bytes(data[0][1])
                subject = str(email.header.make_header(email.header.decode_header(sent_email['Subject']))).lower()

                sender = str(email.header.make_header(email.header.decode_header(sent_email['From'])))
                sender = re.search('<(.*)>', sender)
                sender = sender.group(1)
                # TODO
                # Add Eventplicity email varification check
                
                if re.search('setting', subject) is not None:
                    subject, message = updateSettings(subject, sent_email)
                    print(subject, message)

                elif re.search('help', subject) is not None:
                    subject, message = sendHelp()

                else:
                    subject, message = lookupClient(subject)

                print(subject, message)
                _sendEmail(settings['USER'], settings['PASSWORD'], sender, subject, message)

            # mail.store(uid, '+FLAGS', '(\\Deleted)')
            # mail.expunge()

    start_time = datetime.datetime.strptime(settings['TIME_RANGE'][0], '%H:%M').time()
    end_time = datetime.datetime.strptime(settings['TIME_RANGE'][1], '%H:%M').time()

    if start_time <= time <= end_time:
        if settings['REPORT'] == 'yes':
            venue_master_database = Sheet(settings['NAME'], settings['COLUMNS'], settings['TOKEN'], settings['ROW'], settings['SKIP'])
            subject, message = venue_master_database.main()
            _sendEmail(settings['USER'], settings['PASSWORD'], settings['TO_ADDRESS'], subject, message)

    return settings['REFRESH']


def parseSettings():

    parsed_settings = {}

    path = os.getcwd()
    settings = f'{path}/SETTINGS.txt'

    with open(settings, 'r') as settings:
        settings = settings.read()
        settings = settings.split('\n')

    for setting in settings:
        if re.search('TO_ADDRESS: ', setting) is not None:
            parsed_settings['TO_ADDRESS'] = _parse('TO_ADDRESS: ', setting)

        elif re.search('FROM_ADDRESS: ', setting) is not None:
            parsed_settings['USER'] = _parse('FROM_ADDRESS: ', setting)

        elif re.search('PASSWORD: ', setting) is not None:
            parsed_settings['PASSWORD'] = _parse('PASSWORD: ', setting)

        elif re.search('NAME: ', setting) is not None:
            parsed_settings['NAME'] = _parse('NAME: ', setting)

        elif re.search('COLUMNS: ', setting) is not None:
            parsed_settings['COLUMNS'] = _parse('COLUMNS: ', setting)

        elif re.search('TOKEN: ', setting) is not None:
            parsed_settings['TOKEN'] = _parse('TOKEN: ', setting)

        elif re.search('ROW: ', setting) is not None:
            parsed_settings['ROW'] = int(_parse('ROW: ', setting))

        elif re.search('TIME_RANGE: ', setting) is not None:
            parsed_settings['TIME_RANGE'] = _parse('TIME_RANGE: ', setting)

        elif re.search('REFRESH: ', setting) is not None:
            parsed_settings['REFRESH'] = int(_parse('REFRESH: ', setting))

        elif re.search('SKIP: ', setting) is not None:
            parsed_settings['SKIP'] = _parse('SKIP: ', setting)

        elif re.search('REPORT: ', setting) is not None:
            parsed_settings['REPORT'] = _parse('REPORT: ', setting)

    return parsed_settings


def _parse(line, setting):

    setting = setting.split(line, 1)[1]
    setting.strip()

    if re.search('COLUMNS: ', line) is not None:
        setting = list(setting.split(', '))

    elif re.search('SKIP: ', line) is not None:
        try:
            setting = list(setting.split(', '))
            if setting[-1] == '':
                del setting[-1]
        except:
            setting = []

    elif re.search('TIME_RANGE: ', line) is not None:
        setting = list(setting.split(', '))

        start = setting[0].split(':')
        hour = int(start[0])
        if 1 <= hour <= 6:
            start[0] = str(hour + 12)
        setting[0] = start[0] + ':' + start[1]

        end = setting[1].split(':')
        hour = int(end[0])
        if 1 <= hour <= 6:
            end[0] = str(hour + 12)
        setting[1] = end[0] + ':' + end[1]

    return setting


def updateSettings(subject, message):
    
    update = None

    try:
        for section in message.walk():
            if section.get_content_type() == 'text/plain':
                update = section.get_payload()
                update = os.linesep.join([_ for _ in update.splitlines() if _])
    except:
        pass

    if re.search('address', subject) is not None:
        update = _update('TO_ADDRESS', update)
        update = _updateMessage(update)
        return update

    elif re.search('name', subject) is not None:
        update = _update('NAME', update)
        update = _updateMessage(update)
        return update

    elif re.search('columns', subject) is not None:
        update = _update('COLUMNS', update)
        update = _updateMessage(update)
        return update

    elif re.search('token', subject) is not None:
        update = _update('TOKEN', update)
        update = _updateMessage(update)
        return update

    elif re.search('row', subject) is not None:
        update = _update('ROW', update)
        update = _updateMessage(update)
        return update

    elif re.search('refresh', subject) is not None:
        update = _update('REFRESH', update)
        update = _updateMessage(update)
        return update

    elif re.search('time', subject) is not None:
        update = _update('TIME_RANGE', update)
        update = _updateMessage(update)
        return update

    elif re.search('unskip', subject) is not None:
        update = _update('SKIP', update, 1)
        update = _updateMessage(update)
        return update

    elif re.search('skip', subject) is not None:
        update = _update('SKIP', update)
        update = _updateMessage(update)
        return update

    elif re.search('report', subject) is not None:
        update = _update('REPORT', update)
        update = _updateMessage(update)
        return update

    _updateMessage(update)


def _update(setting, update, delete=None):

    path = os.getcwd()
    settings = f'{path}/SETTINGS.txt'
    text = ''

    if update and update != ' ':
        update.strip()

        with open(settings, 'r+') as s:
            settings = s.read()
            settings = list(settings.split('\n'))

            for line in settings:
                if re.search(setting, line) is not None:
                    before = line

                    try:
                        if re.search('SKIP', setting) is not None:
                            if delete:
                                print(line)
                                if line[-2:] == ': ':
                                    raise Exception
                                else:
                                    updated_list = line.split(': ')[1]
                                    updated_list = updated_list.split(', ')
                                    print(updated_list)
                                    for i, item in enumerate(updated_list):
                                        if item == update:
                                            del updated_list[i]
                                    update = ', '.join(updated_list)
                                    line = line.split(': ')[0]
                                    line = line + ': ' + update
                                    line.strip()

                            else:
                                if update[0] == ' ':
                                    update = update[1:]
                                if update[-1:] == ' ':
                                    del update[-1:]
                                if line[-2:] == ': ':
                                    line = line + update
                                else:
                                    line = line + ', ' + update

                        elif re.search('TIME_RANGE', setting) is not None:
                            if re.search(' - ', update):
                                update = list(update.split(' - '))
                            elif re.search('-', update):
                                update.split('-')
                            line = setting.split(f'{setting}: ', 1)[0]
                            line = line + ': ' + update[0] + ', ' + update[1]
                            line.strip()

                        elif re.search('ROW', setting) is not None or re.search('REFRESH', setting) is not None:
                            update = int(update)
                            line = setting.split(f'{setting}: ', 1)[0]
                            line = line + ': ' + update
                            line.strip()

                        elif re.search('REPORT', setting) is not None:
                            update.lower()
                            if update == 'yes' or update == 'no':
                                line = setting.split(f'{setting}: ', 1)[0]
                                line = line + ': ' + update
                                line.strip()
                            else:
                                raise Exception

                        else:
                            line = setting.split(f'{setting}: ', 1)[0]
                            line = line + ': ' + update
                            line.strip()

                        after = line

                    except:
                        after = line
                
                text += f'{line}\n'
            
            s.seek(0)
            s.truncate()
            s.write(text)

    else:
        before = 'error'
        after = 'error'

    return before, after


def _updateMessage(update=None):

    subject = ''
    message = ''

    if update:
        before, after = update
    else:
        before = None
        after = None

    if before and after and before != after:
        subject = 'Settings Update Complete'
        message = f"The following line in was updated in this program's settings: \n\n\t{before} (before)\n\t{after} (after)"
    elif before and after and before == after:
        subject = 'Settings Update Failed'
        message = f'Unable to update the following setting: \n\n\t{before}'
    else:
        subject = 'Settings Update Failed'
        message = "Unable to update your requested setting. "
        message += "Try checking your spelling and formatting. "
        message += "For further help, send 'help' in the subject line to this email address."

    return subject, message


def sendHelp():
    
    subject = 'Eventplicity Client Scraper Tutorial'
    message = 'WELCOME TO THE EVENTPLICITY CLIENT SCRAPER TUTORIAL\n\n'
    message += '--------------------------\nCURRENT SETTINGS\n--------------------------\n'

    path = os.getcwd()
    settings = f'{path}/SETTINGS.txt'

    with open(settings, 'r') as settings:
        settings = settings.read()
        settings = settings.split('\n')

    for setting in settings:
        if re.search('PASSWORD: ', setting) is not None:
            setting = 'PASSWORD: ************'
            message += f'{setting}\n'
        elif setting == '' or setting == ' ':
            continue
        else:
            message += f'{setting}\n'
    message += '\n'

    read_me = f'{path}/README.txt'

    with open(read_me, 'r') as read_me:
        read_me = read_me.read()

    message += read_me

    return subject, message


def _sendEmail(from_address, pwd, to_address, subject, message):

        message = "\r\n".join([
            f"From: {from_address}",
            f"To: {to_address}",
            f"Subject: {subject}",
            "",
            f"{message}"
        ])

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(from_address, pwd)
        server.sendmail(from_address, to_address, message)


def lookupClient(lookup):

    client = None
    path = os.getcwd()

    try:
        report = pd.read_pickle(f'{path}/last_report.pkl')
        frame = report.loc[lookup]
        client = frame.to_dict(orient='index')

    except:
        client = None

    try:
        title = lookup.replace('-', ' ')
        title = title.title()
    except:
        title = lookup.title()

    subject = f"{title}'s Search Results"
    message = ''

    if client:
        if client != {'Index': {'Phone_Number': 0, 'Eventplicity_Link': 0}}:
            message += f"We found instances of our EVP Phone Number and our Eventbuilder Link on {title}'s following pages:\n\n"
            for page, value in client.items():
                if page == 'Index':
                    page = 'Home Page'
                message += f'\t{page}:\n\n'

                for item, count in value.items():
                    if item == 'Phone_Number':
                        message += f'\t\t- Phone Number: {count}\n'

                    elif item == 'Eventplicity_Link':
                        message += f'\t\t- Link: {count}\n'

                message += '\n'

        else:
            message += f"We found no instances of our EVP Phone Number or our Eventbuilder Link on {lookup}'s website."

    else:
        try:
            with open(f'{path}/errors.pkl', 'rb') as f:
                clients = pickle.load(f)
        except:
            clients = None

        if clients:
            if clients['404s'] != []:
                for client in clients['404s']:
                    if client == lookup:
                        message += f"We detected {title}'s website is currently offline. "
                        message += 'Try checking their site manually, as some websites that make heavy use of JavaScript throw this error.'
                        break

            if clients['Missing_Info'] != [] and message == '':
                for client in clients['Missing_Info']:
                    if client == lookup:
                        message += f"We are missing the appropriate information for {title} on the Venue Master Database to search their website. "
                        message += "Makes sure the columns associated with our EVP phone number and Event Builder Link are filled out."
                        break

            if clients['Selenium'] != [] and message == '':
                for client in clients['Selenium']:
                    if client == lookup:
                        message += f"{title}'s website makes heavy use of JavaScript which this program is unable to process. "
                        message += 'Try checking their website manually.'
                        break

    if message == '':
        message += f"We encountered an unexpected error looking up '{lookup}'. "
        message += f"Please review your shortname's spelling and resending a lookup request or check {title}'s website manually. "
        message += "For instructions on how to use this program, send 'help' in the subject line to the address."

    return subject, message


# main()

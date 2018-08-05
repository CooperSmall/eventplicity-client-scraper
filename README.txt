------------------
BACKGROUND
------------------
This is a Python based web scraping application which leverages HTML consistencies across our clients' websites to detect our business information in the most flexible way possible. The program gathers a client's short-name, EVP number, event builder link, and website link from the appropriate columns on our Venue Master Database Google Sheet and searches their website for the information collected. After the search is complete, the total number of instances of each client's phone number and event builder link are stored in a local database. Clients whose websites are offline or are missing information from the spreadsheet are also stored locally.

----------
USEAGE
----------
Once per day, this program will query every client on the Venue Master Database and compare its results to the previous day. If information is either added or removed from the website, or even if nothing has changed, an email is sent to the owner with a list including the detected changes, clients who are offline, and clients missing information on the spreadsheet. The owner can choose to not receive daily update emails and/or skip clients who repeatedly ping the system. 

Anyone with an Eventplicity email account can ask this program how many times our number and button occur on a client's website per pages. To do so, simply send a client's short-name to this program's email address in the subject line and wait for a response. For example, to query 101 Steak, you would send '101-steak' in the subject line.

-------------
SETTINGS
-------------
Below is an explanation of each setting this program uses to run:
TO_ADDRESS: The address this program will send its daily report emails to
FROM_ADDRESS: This program's email address
PASSWORD: This program's password
NAME: The name of Eventplicity's Google Sheet (Venue Master Database)
COLUMNS: The name of each column used to retrieve information 
TOKEN: The Google Sheet authentication token
ROW: The row in which clients begin to appear (default is 2, as column headings fill row 1)
TIME_RANGE: The start time and end time in which this program will run its daily diagnostic (HH:MM)
REFRESH: How often this program will check for email query requests (in seconds)
SKIP: Clients this program will ignore when finalizing the daily report (will still store their information)
REPORT: Whether or not the 'To Address' will receive reports each day (yes or no)

-------------------------
CHANGE SETTINGS
-------------------------
To change a setting, send this program an email with the subject line 'settings -  ', followed by the name of the setting you want to change. For example, to change the TO_ADDRESS setting, you would use the subject line 'settings - to address' (replace all _'s with spaces) and type the name of the new email address in the body. Note: the change the time range, follow the format 'settings - HH:MM - HH:MM'.

---------
ISSUES
---------
As stated earlier, this program leverages the HTML structure of each client's webpage to parse their content. This program begins its parsing by checking for every link between the <nav> tags. If no <nav> tags are detected, this program will move on to check every link which contains one of the predetermined set of words; these words include: 'private', 'parties', 'events', 'catering', 'contact us', 'birthday', 'wedding', and several other. If this method is used, it could potentially miss webpages containing our information.
Again, this program leverages HTML consistencies to parse websites. Client's websites who makes heavy use of java script cannot be captured by this scraping technique. If you query one of these clients, you will receive an email stating the client's information cannot be captured. 

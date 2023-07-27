import re
import os
import sys
import math
import time
import json
import logging
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

from scraper import LinkedInSession
from api import allocateNewProxy

# grep CRON /var/log/syslog

conn = psycopg2.connect(
    host="3.77.153.132",
    database="triggify_db",
    user="postgres",
    password="relu@123"
)
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_details (
    user_id integer PRIMARY KEY,
    initial_scrape TIMESTAMP,
    last_scraped TIMESTAMP,
    ip text,
    launch integer,
    note text);
    """)

conn.commit()

def setNote(user_id, note):
    cursor.execute(f"""
        UPDATE "session_details"
        SET note = '{note}' 
        WHERE user_id = {user_id};
    """)
    conn.commit()

    logger.info(f'{user_id} : NOTE SET : {note}')

def getNote(user_id):
    cursor.execute(f"""
        SELECT note, last_scraped from "session_details"
        WHERE user_id = {user_id};
        """)
    user_note = cursor.fetchone()
    return user_note

def genToken():
    url = "https://api.triggifyapp.com/api/account/login"

    payload = json.dumps({
    "email": "mohitfreekaamaal.com@gmail.com",
    "password": "123456"
    })
    headers = {
    'Content-Type': 'application/json',
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception as e:
        error_logger.error(f'Generating token error: {e}')

    return response.json()['token']

def sendMail(user_id, email=None):
    note = getNote(user_id)
    if note['note'] == 'Email Sent':
        logger.info(f'{user_id} : {email} : Daily Email API already sent')
        return
    
    url = f"https://api.triggifyapp.com/api/account/email-post?email={email}"

    token = genToken()
    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.request("GET", url, headers=headers)
    except Exception as e:
        error_logger.error(f'{user_id} : {email} : {response} : Daily Email API : {e}')

    if response.status_code == 200:
        setNote(user_id,'Email Sent')
        cursor.execute(f"""
            INSERT INTO "App_linkedinscrapedstatus" (user_id, status, created_at, updated_at)
            VALUES ({user_id}, true, '{datetime.utcnow().strftime(date_format)}',
            '{datetime.utcnow().strftime(date_format)}')
            ON CONFLICT(user_id) DO UPDATE SET status = true,
            updated_at = '{datetime.utcnow().strftime(date_format)}';
            """)
        
        logger.info(f'{user_id} : {email} : Daily Email API : Status Code: {response.status_code} : {response.text}')
    else:
        error_logger.info(f'{user_id} : {email} : Daily Email API : Status Code: {response.status_code} : {response.text}')

def tokenError(user_id, email):
    url = f"https://api.triggifyapp.com/api/account/email-disconnect?email={email}"

    token = genToken()
    headers = {
        'Authorization': f'Bearer {token}'
    }

    note = getNote(user_id)

    if note['note'] == 'Token Error 2':
        error_logger.info(f'{user_id} : {email} : Token Error API : Email already sent twice')
        return
    
    if note['note'] == 'Token Error':
        error_logger.info(f'{user_id} : {email} : Token Error API : Email already sent')
        if note['last_scraped'] > (datetime.now() - timedelta(hours=48)):
            return
        else:
            setNote(user_id, 'Token Error 2')
            error_logger.info(f'{user_id} : {email} : Token Error API : Sending Email again')
    
    try:
        response = requests.request("GET", url, headers=headers)
    except Exception as e:
        error_logger.error(f'{user_id} : {email} : {response} : Token Error API : {e}')

    setNote(user_id, 'Token Error')
    error_logger.error(f'{user_id} : {email} : Token Error API : Status Code: {response.status_code} : {response.text}')

def resetUser(user_id, email):
    sendMail(user_id, email)

    cursor.execute(f"""
        SELECT * FROM "session_details"
        WHERE user_id = {user_id};
        """)
    user_detail = None
    try:
        user_detail = dict(cursor.fetchone())
    except Exception as e:
        print(e)
    
    if user_detail['initial_scrape'] < (datetime.now() - timedelta(hours=24)):
        logger.info(f'{user_id} : All keywords have been scraped, Resetting User')
        cursor.execute(f"""
            UPDATE "session_details"
            SET launch = 0,
            initial_scrape = '{datetime.now().strftime(date_format)}'
            WHERE user_id = {user_id};
        """)

        cursor.execute(f"""
            UPDATE "App_userkeyword"
            SET is_scraped = false
            WHERE user_id = {user_id};
        """)
        
        cursor.execute(f"""
            UPDATE "App_userurl"
            SET is_scraped = false
            WHERE user_id = {user_id};
        """)
        
        conn.commit()
        setNote(user_id,'None')
    else:
        logger.info(f'{user_id} : All keywords have been scraped but, initail scrape was less then 24h ago.')

    return
  
def canBeScraped(user_id, email):
    print('Checking scrape status')
    cursor.execute(f"""
        SELECT * FROM "session_details"
        WHERE user_id = {user_id};
        """)
    user_detail = None
    try:
        user_detail = dict(cursor.fetchone())
    except Exception as e:
        print(e)

    if user_detail:
        if user_detail['last_scraped'] <= (datetime.now() - timedelta(hours=launch_interval)) and user_detail['launch'] < max_launch:
            return True
        elif user_detail['initial_scrape'] < (datetime.now() - timedelta(hours=24)):
            resetUser(user_id, email)
    else:
        print('New User')
        cursor.execute(f"""
            INSERT INTO "session_details" (user_id, initial_scrape, last_scraped, launch) VALUES (
            {user_id},
            '{datetime.now().strftime(date_format)}',
            '{datetime.now().strftime(date_format)}',
            0);
        """)
        conn.commit()
        return True
    
    return False

def updateStatus(user_id):
    print('Updating scrape status')
    cursor.execute(f"""
        UPDATE "session_details"
        SET launch = launch + 1,
        last_scraped = '{datetime.now().strftime(date_format)}'
        WHERE user_id = {user_id};
    """)
    conn.commit()
    setNote(user_id, 'None')
    logger.info(f'{user_id} : Status Updated')

    return

def getCountryCode(country):
    with open(f"{base_dir}/country_code.json", "r", encoding='utf-8') as jsonFile:
        data: dict = json.load(jsonFile)
    if data.get(country):
        return data[country]['code']
    
    return None

def updatePost(user_id, data: dict|str, keyword, error=False):
    if not error:
        for post_id, details in data.items():
            try:
                cursor.execute(f"""
                    INSERT INTO "App_linkedinpost"(post_id,created_at,updated_at,posted_at,user_id,title,post_connection,
                    image,keyword,post_link,primary_subtitle,secondary_subtitle,profile_picture,summary)
                    VALUES({post_id},'{datetime.utcnow().strftime(date_format)}','{datetime.utcnow().strftime(date_format)}',
                    '{details['created_at']}',{user_id},'{details['title']}','{details['connection']}',
                    '{details['image']}','{details['keyword']}','{details['post_link']}',
                    '{details['primarySubtitle']}','{details['secondarySubtitle']}',
                    '{details['profile_picture']}','{details['summary']}');
                """)
            except Exception as e:
                conn.rollback()
                logger.error(f'{user_id} : {e} : {post_id} : {details}')
    else:
        error_logger.error(f'{user_id} : Result data error : {keyword} : {data}')

    try:
        logger.info(f'{user_id} : Setting Keyword as True {keyword}')
        cursor.execute(f"""
            UPDATE "App_userkeyword"
            SET is_scraped = true
            WHERE user_id = {user_id} AND keyword = '{keyword}';
        """)
        print(f'{keyword} has been set as true', flush=True)
        conn.commit()
    except Exception as e:
        logger.error(f'{user_id} : {e}')

    conn.commit()

def updateActivity(user_id, data: dict|str, url_id, keyword, error=False):
    logger.info(f'{user_id} : {keyword} : Updating')
    if not error:
        for post_id, details in data.items():
            try:
                cursor.execute(f"""
                    INSERT INTO "App_linkedinpost"(post_id,created_at,updated_at,posted_at,user_id,title,post_connection,image,
                    keyword,post_link,primary_subtitle,secondary_subtitle,profile_picture,summary)
                    VALUES({post_id},'{datetime.utcnow().strftime(date_format)}','{datetime.utcnow().strftime(date_format)}',
                    '{details['secondarySubtitle']}', {user_id},'{details['title']}','{details['connection']}',
                    '{details['image']}','{details['keyword']}','{details['post_link']}',
                    '{details['primarySubtitle']}','{details['secondarySubtitle']}',
                    '{details['profile_picture']}','{details["summary"]}');
                """)
            except Exception as e:
                conn.rollback()
                logger.error(f'{user_id} : {e} : {post_id} : {details}')
            
            try:
                logger.info(f'{user_id} : Setting Keyword as True / Updating Profile details : {details["keyword"]}')
                cursor.execute(f"""
                    UPDATE "App_userurl"
                    SET is_scraped = true,
                    name = '{details['title']}',
                    photo = '{details['profile_picture']}'
                    WHERE id = {url_id};
                """)
            except Exception as e:
                logger.error(f'{user_id} : {e} : {url_id} : {details["title"]} : {details["profile_picture"]}')
    else:
        error_logger.error(f'{user_id} : Result data error : {keyword} : {data}')
        logger.info(f'{user_id} : Setting Keyword as True : {keyword}')
        try:
            cursor.execute(f"""
                UPDATE "App_userurl"
                SET is_scraped = true
                WHERE id = {url_id};
            """)
            conn.commit()
        except Exception as e:
            logger.error(f'{user_id} : {url_id} : {e}')
        
    conn.commit()

def getIP(user_id, country, city):
    print('Getting IP')
    logger.info(f'{user_id} : Getting Dedicated IP') 
    cursor.execute(f"""
        SELECT ip FROM "session_details"
        WHERE user_id = {user_id};
        """)
    ip = None
    try:
        ip = cursor.fetchone()[0]
    except Exception as e:
        print(e)
    if ip:
        return ip
    else:
        logger.info(f'{user_id} : Allocating new IP')
        ip = allocateNewProxy(country, city)
        if ip:
            cursor.execute(f"""
                UPDATE "session_details"
                SET ip = '{ip}'
                WHERE user_id = {user_id};
            """)
            conn.commit()
            return ip
        
    error_logger.error(f'{user_id} : Allocation Error')

    return

def updateProfile(url_id, pData):
    cursor.execute(f"""
        UPDATE "App_userurl" SET 
        name = '{pData[1]}',
        photo = '{pData[2]}'
        WHERE id = {url_id};
    """)
    conn.commit()

def postThread(keywords: list):
    user_id = str(keywords[0]["user_id"])
    email = str(keywords[0]["email"])
    logger.info(f'{user_id} : {email} : Keywords to scrape, {len(keywords)}')
    logger.info(f'{user_id} : Starting')
    logger.info(f'{user_id} : Session Details : Country - {keywords[0]["country"]} : City - {keywords[0]["city"]} : ZIP - {keywords[0]["postal_code"]}')
    if not keywords[0]["cookie"]:
        error_logger.error(f'{user_id} : Linkedin token not present')
        return f'{user_id} Linkedin token not present'
    
    # country = getCountryCode(keywords[0]["country"].lower().strip())
    country = keywords[0]["country"]
    try:
        city = keywords[0]["city"].lower().strip().replace(' ','')
    except:
        city = ''

    if not country:
        error_logger.error(f'{user_id} : Invalid Country : {keywords[0]["country"]} : {country}')
        return f'{user_id} User Invalid Country'

    if not canBeScraped(user_id, email):
        logger.info(f'{user_id} : Waiting...')
        return f'{user_id} Waiting...'

    ip = getIP(user_id,country,city)
    if not ip:
        logger.info(f'{user_id} : No assigned IP')
        return f'{user_id} No IP'

    bot = LinkedInSession(
        country,
        city,
        keywords[0]["postal_code"],
        keywords[0]["cookie"],
        ip,
        use_proxy=True
    )

    bot.proxyTest()
    session_error = bot.login()

    if session_error == 'Token Error':
        error_logger.error(f'{user_id} : {email} : Invalid Token/Expired : "{keywords[0]["cookie"]}"')
        # updateStatus(user_id)
        tokenError(user_id, email)
        return f'{user_id} Invalid Token'
    elif session_error == 'Connection Error':
        error_logger.error(f'{user_id} : {email} : Connection Error')
        return f'{user_id} Connection Error'
    
    cursor.execute(f"""
        SELECT launch FROM "session_details"
        WHERE user_id = {user_id};
        """)
    
    if cursor.fetchone()['launch'] == 0:
        logger.info(f'{user_id} : Setting is_last true')
        print('First Launch')
        try:
            cursor.execute(f"""
            UPDATE "App_linkedinpost" SET is_last = true 
            WHERE ID = (SELECT ID FROM "App_linkedinpost" WHERE user_id = {user_id} ORDER BY created_at DESC LIMIT 1)
            """)
        except Exception as e:
            logger.error(f'{user_id} : Setting is_last : {e}')
        
        logger.info(f'{user_id} : Setting scrapedstatus false')
        try:
            cursor.execute(f"""
                INSERT INTO "App_linkedinscrapedstatus" (user_id, status, created_at, updated_at)
                VALUES ({user_id}, false, '{datetime.utcnow().strftime(date_format)}',
                '{datetime.utcnow().strftime(date_format)}')
                ON CONFLICT(user_id) DO UPDATE SET status = false,
                updated_at = '{datetime.utcnow().strftime(date_format)}';
                """)
        except Exception as e:
            conn.rollback()
            logger.error(f'{user_id} : Setting scrapedstatus false : {e}')

        conn.commit()
    # if cursor.fetchone()['launch'] > 0:
    #     logger.info(f'{user_id} : Setting scrapedstatus false')
    #     try:
    #         cursor.execute(f"""
    #             INSERT INTO "App_linkedinscrapedstatus" (user_id, status, created_at, updated_at)
    #             VALUES ({user_id}, false, '{datetime.utcnow().strftime(date_format)}',
    #             '{datetime.utcnow().strftime(date_format)}')
    #             ON CONFLICT(user_id) DO UPDATE SET status = false,
    #             updated_at = '{datetime.utcnow().strftime(date_format)}';
    #             """)
    #     except Exception as e:
    #         conn.rollback()
    #         logger.error(f'{user_id} : Setting scrapedstatus false : {e}')
    #     conn.commit()

    keyword_count = 0
    activity_count = 0

    keyword: dict
    for keyword in keywords:
        if keyword.get('keyword_id') and keyword_count < keywords_per_launch:
            logger.info(f'{user_id} : Scraping Keyword : {keyword["keyword"]}')
            keyword_count += 1
            
            multi_result = bot.search(sarch_type='keyword', input=keyword["keyword"], pages=page_per_keyword, filter='all')
            result = multi_result[0]
            logger.info(f'{user_id} : Keyword SCRAPED : {keyword["keyword"]}')
            if type(result) is dict: updatePost(user_id, result, keyword["keyword"])
            else: updatePost(user_id, result, keyword["keyword"], error=True)
        elif keyword.get('url_id') and activity_count < url_per_launch:
            logger.info(f'{user_id} : Scraping Activity : {keyword["keyword"]}')
            activity_count += 1
            url_id = str(keyword["url_id"])
            multi_result = bot.search(sarch_type='activity', input=keyword["keyword"])
            result = multi_result[0]
            if multi_result[1]:
                updateProfile(url_id,multi_result[1])
            logger.info(f'{user_id} : Activity SCRAPED : {keyword["keyword"]}')
            if type(result) is dict: updateActivity(user_id, result, url_id, keyword["keyword"])
            else: updateActivity(user_id, result, url_id, keyword["keyword"], error=True)
        else:
            pass

    updateStatus(user_id)
    return f'{user_id} Scraped'

def setup_log(name, log_file, level=logging.DEBUG):
    """To setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', "%H:%M:%S")

    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)
    handler

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

if not os.path.isdir(f"logs"): 
    os.makedirs('logs')

if not os.path.isdir(f"errors"): 
    os.makedirs('errors')

base_dir = os.path.dirname(os.path.realpath(__file__))

date = datetime.today()

if not os.path.isdir(f'{base_dir}/logs/{date.strftime("%b-%Y")}'): 
    os.makedirs(f'{base_dir}/logs/{date.strftime("%b-%Y")}')

if not os.path.isdir(f'{base_dir}/errors/{date.strftime("%b-%Y")}'): 
    os.makedirs(f'{base_dir}/errors/{date.strftime("%b-%Y")}')

date = datetime.today()
logger = setup_log('linked_logger',f'{base_dir}/logs/{date.strftime("%b-%Y")}/{date.strftime("%d-%b-%Y")}.log')
error_logger = setup_log('linked_logger_error',f'{base_dir}/errors/{date.strftime("%b-%Y")}/{date.strftime("%d-%b-%Y")}.log')

date_format = '%d-%b-%y %H:%M:%S'
file = f'{base_dir}/local db'

launch_interval = 4 # hours
max_page = 100 # (100 * 10) = 1000 results
max_launch = 5

# 100 posts over 10 launches of 10 posts each
url_per_launch = 3

if __name__ == '__main__':

    logger.info(f'Initiating')

    keywords_by_user: dict[int, list] = {}
    
    cursor.execute("""
        SELECT A.user_id, E.email,
        B.id as keyword_id, B.keyword, B.is_scraped,
        C.cookie,
        D.country, D.city, D.postal_code
        FROM "Subscription_subscriptiondetail" A
        RIGHT JOIN "App_userkeyword" B ON A.user_id = B.user_id
        RIGHT JOIN "App_linkedincookie" C ON B.user_id = C.user_id
        RIGHT JOIN "App_billingdetail" D ON C.user_id = D.user_id
        RIGHT JOIN "App_user" E ON D.user_id = E.id
        WHERE A.status = 'trialing' OR A.status = 'active';
        """)

    prev_id = None
    for i in cursor.fetchall():
        current_id = i['user_id']
        if current_id != prev_id:
            prev_id = current_id
            if not keywords_by_user.get(current_id): keywords_by_user[current_id] = []
        keywords_by_user[current_id].append(dict(i))

    
    cursor.execute("""
        SELECT A.user_id, E.email,
        B.id as url_id, B.url as keyword, B.is_scraped,
        C.cookie,
        D.country, D.city, D.postal_code
        FROM "Subscription_subscriptiondetail" A
        RIGHT JOIN "App_userurl" B ON A.user_id = B.user_id
        RIGHT JOIN "App_linkedincookie" C ON B.user_id = C.user_id
        RIGHT JOIN "App_billingdetail" D ON C.user_id = D.user_id
        RIGHT JOIN "App_user" E ON D.user_id = E.id
        WHERE A.status = 'trialing' OR A.status = 'active';
        """)

    prev_id = None
    for i in cursor.fetchall():
        current_id = i['user_id']
        if current_id != prev_id:
            prev_id = current_id
            if not keywords_by_user.get(current_id): keywords_by_user[current_id] = []
        keywords_by_user[current_id].append(dict(i))

    if not keywords_by_user:
        logger.info(f'No keywords/activity available to scrape')
        print('No matching Entries')

    total_keywords = {}
    posts_threading = []
    for user_id, value in keywords_by_user.items():
        total_keywords[user_id] = len(value) 
        logger.info(f'{user_id} : Total Keywords, {total_keywords[user_id]}')
        
        if all([True if i['is_scraped'] is True else False for i in value]):
            resetUser(str(user_id), value[0]['email'])
            continue
        
        # if all([True if i['is_scraped'] is False else False for i in value]):
        #     cursor.execute(f"""
        #         INSERT INTO "App_linkedinscrapedstatus" (user_id, status, created_at, updated_at)
        #         VALUES ({user_id}, false, '{datetime.utcnow().strftime(date_format)}',
        #         '{datetime.utcnow().strftime(date_format)}')
        #         ON CONFLICT(user_id) DO UPDATE SET status = false,
        #         updated_at = '{datetime.utcnow().strftime(date_format)}';
        #         """)
        
        posts_threading.append(list(filter(lambda d: d['is_scraped'] == False, value)))

    conn.commit()

    if posts_threading:
        for user in posts_threading:
            page_per_launch = int(max_page/max_launch)
            keywords_per_launch = math.ceil(total_keywords[user[0]['user_id']]/max_launch)
            page_per_keyword = int(page_per_launch/keywords_per_launch)
            result = postThread(user)
            print(result)
        
        logger.info(f'Finished!')
        print('Finished!')

        # with ProcessPoolExecutor(max_workers = max_threads) as executor:
        #     results = executor.map(postThread, posts_threading)
        # for result in results:
        #     if not result:
        #         print('Error',result)
        #     else:
        #         print(result)

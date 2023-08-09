import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from bs4 import NavigableString
import re
import os
import sys
import time
import json
import pickle
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import urllib3
from urllib3 import exceptions
urllib3.disable_warnings(exceptions.InsecureRequestWarning)

# Notes

# LinkedIn Rate Limits
# Search result extractions : Max 100 pages/1000 results per day over 5 launches minimum (20 page/launch)
# Post or article extractions : 100 posts over 10 launches of 10 posts each


# Scraping Parameters

search_launches = 5 # 5 times search launches PREDEFINED
max_pages = 10 # 10 Max Page Predefined
page_per_keyword = 5 ##5 page per keyword Predefined

date_format = '%d-%b-%y %H:%M:%S'


from functools import reduce
def find(dictionary, keys:str, default=None):
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary) #

class LinkedInSession:
    def __init__(self, country, city, zipcode, login_token, ip, use_proxy = True) -> None:
        self.country = country
        self.use_proxy = use_proxy
        self.session = requests.Session()
        retry = Retry(connect = 5, backoff_factor = 0.1, total = 5)
        adapter = HTTPAdapter(max_retries = retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # self.proxy_url = f'http://brd-customer-hl_68f06206-zone-zone2-country-{country}-city-{city}:z1u1zg8rg8zx@zproxy.lum-superproxy.io:22225'
        self.proxy_url = f'http://brd-customer-hl_68f06206-zone-isp-country-{country}-ip-{ip}:pjwc0b258w8l@zproxy.lum-superproxy.io:22225'
        if use_proxy:
            self.session.verify = False
            # self.session.verify = 'CA-BrightData.crt'
            self.session.proxies.update({
                'http': self.proxy_url,
                'https': self.proxy_url,
            })
        self.session.cookies.set("li_at", login_token, domain=".www.linkedin.com")

    def resetURL(self):
        if self.use_proxy:
            print('Resetting URL to country')
            proxy_url = f'http://brd-customer-hl_68f06206-zone-zone2-country-{self.country}:z1u1zg8rg8zx@zproxy.lum-superproxy.io:22225'

            self.session.proxies.update({ # Reset of url 
                'http': proxy_url,
                'https': proxy_url,
            })

            self.proxyTest()
        else:
            print('Huh! What?')
        
    def login(self):
        print("Login")
        # cookie_file = 'cookies'
        # if os.path.isfile(f'{cookie_file}.pickle'):
        #     print('Loading cookies from file')
        #     with open(f'{cookie_file}.pickle', 'rb') as f:
        #         self.session.cookies.update(pickle.load(f))
        #     return

        url = "https://www.linkedin.com/login"
        payload={}
        headers = {
        'authority': 'www.linkedin.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }
        try:
            response = self.session.request("GET", url, headers=headers, data=payload) # Request to made for login in linkdin
        except Exception as e:
            print("Connection Error,",e)
            return 'Connection Error'

        with open("linkdin.html", "w",encoding='utf-8') as f:
            f.write(response.text) # Response is saved in linkdin.html file 

        if 'Sign in' in response.text:
            print('Invalid Token or Expired') # if Sign in response.text it will print
            return 'Token Error'
    
        # print('Creating new cookie file')
        # with open(f'{cookie_file}.pickle', 'wb') as f:
        #     pickle.dump(self.session.cookies, f)
        
        return 'LoggedIn'
            
    def searchPosts(self, keyword: str, start=0, search='all'):
        res = {'status': '', 'message': '', 'data': ''}

        # url = f"https://www.linkedin.com/voyager/api/graphql?variables=(start:{start},origin:GLOBAL_SEARCH_HEADER,query:(keywords:{keyword},flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:resultType,value:List(CONTENT))),includeFiltersInResponse:false))&&queryId=voyagerSearchDashClusters.181547298141ca2c72182b748713641b"
        url = f"https://www.linkedin.com/voyager/api/graphql?variables=(start:{start},origin:FACETED_SEARCH,query:(keywords:{keyword},flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:datePosted,value:List(past-24h)),(key:resultType,value:List(CONTENT)),(key:sortBy,value:List(relevance))),includeFiltersInResponse:false))&&queryId=voyagerSearchDashClusters.b0928897b71bd00a5a7291755dcd64f0"
        if search == '1st':
            url = f"https://www.linkedin.com/voyager/api/graphql?variables=(start:{start},origin:FACETED_SEARCH,query:(keywords:{keyword},flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:postedBy,value:List(first)),(key:resultType,value:List(CONTENT)),(key:sortBy,value:List(relevance))),includeFiltersInResponse:false))&&queryId=voyagerSearchDashClusters.181547298141ca2c72182b748713641b"
        payload={}

        headers = {
        'authority': 'www.linkedin.com',
        'accept': 'application/vnd.linkedin.normalized+json+2.1',
        'accept-language': 'en-US,en;q=0.9',
        'csrf-token': self.session.cookies.get('JSESSIONID').replace('"',''),
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'x-li-lang': 'en_US',
        'x-li-track': '{"clientVersion":"1.12.4142","mpVersion":"1.12.4142","osName":"web","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":0.800000011920929,"displayWidth":1092.800016283989,"displayHeight":614.4000091552734}'
        }
        try:
            response = self.session.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            res['status'] = "Error"
            res['message'] = "Connection Error: "+str(e)
            return res
        if response.status_code != 200:
            res['status'] = "Error"
            res['message'] = "LinkedIn API Error: "+str(response.status_code)
            return res

        try:
            data = response.json()
            # with open('apiresponse.json', 'w') as f:
            #     json.dump(data, f, indent=4)
        except Exception as e:
            print(response.text)
            res['status'] = "Error"
            res['message'] = "Json Response Error: "+str(e)
            return res

        posts = {}
        result_count = 0
        i: dict
        for i in data['included']:
            if not i.get("template"):
                continue
            print(result_count,end='\r')
            try:
                
                post_id: str = i['trackingUrn']

                if post_id.find('activity:') == -1:
                    print("No id found")
                    continue

                result_count += 1
                raw_data = {}

                raw_data['keyword'] = keyword
                raw_data['post_link'] = 'https://www.linkedin.com/feed/update/'+post_id
                post_id = post_id[post_id.find('activity:')+len('activity:'):]

                pp = 'NA'
                base: dict = i['image']['attributes'][0]['detailData']
                if base:
                    try:
                        if profile_image := base['nonEntityProfilePicture']:
                            pp = profile_image['vectorImage']['artifacts'][0]['fileIdentifyingUrlPathSegment']
                        elif profile_image := base['nonEntityCompanyLogo']:
                            pp = profile_image['vectorImage']['artifacts'][0]['fileIdentifyingUrlPathSegment']
                    except Exception as e:
                        print("P-ID:",post_id)
                        print(e)
                        pass
                
                raw_data['profile_picture'] = pp
                
                raw_data['title'] = str(i['title']['text']).replace("'","''")
                try:
                    raw_data['connection'] = str(i['badgeText']['text']).replace('\u2022','').strip()
                except:
                    raw_data['connection'] = ""
                raw_data['primarySubtitle'] = str(i['primarySubtitle']['text']).replace('\u2022','').strip().replace("'","''")
                raw_data['secondarySubtitle'] = str(i['secondarySubtitle']['text']).replace('\u2022','').strip().replace("'","''") #Cleaning of data
                raw_data['summary'] = str(i['summary']['text']).replace('\u2022','').strip().replace("'","''")

                if raw_data['summary'].lower().find(keyword.lower()) == -1:
                    continue
                
                variables = re.findall(r"(\S*\d+)(\w+)\S*", raw_data['secondarySubtitle'])
                current_time = datetime.utcnow()
                if variables == []:
                    post_time = current_time
                else:
                    num, var = variables[0]
                    if var == 'm':
                        post_time = (current_time - timedelta(minutes=int(num)))
                    elif var == 'h':
                        post_time = (current_time - timedelta(hours=int(num)))
                    elif var == 'd':
                        post_time = (current_time - timedelta(days=int(num)))
                    else:
                        post_time = current_time

                raw_data['created_at'] = post_time.strftime(date_format)
                raw_data['updated_at'] = post_time.strftime(date_format)

                img = 'NA'
                base: dict = i['entityEmbeddedObject']['image']
                if base:
                    if post_images:= base['attributes'][0]['detailData']['vectorImage']:
                        img = post_images['rootUrl'] + post_images['artifacts'][0]['fileIdentifyingUrlPathSegment']
                        # for detail in post_images['artifacts']:
                        #     temp = {}
                        #     temp['width'] = detail['width']
                        #     temp['height'] = detail['height']
                        #     temp['expiresAt'] = detail['expiresAt']
                        #     temp['link'] = post_images['rootUrl']+detail['fileIdentifyingUrlPathSegment']
                        #     img.append(temp)
                    elif post_images := base['attributes'][0]['detailData']['imageUrl']:
                        img = post_images['url']
                raw_data['image'] = img

                posts[post_id] = raw_data
            except Exception as e:
                print("P-ID:",post_id)
                print("Error in scraping Post Value")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
        print()
        if result_count == 0:
            res['status'] = "Error"
            res['message'] = "No result"
            return res
        res['status'] = "Successful"
        res['message'] = "No Error"
        res['data'] = posts
        return res

    def getIdbyURL(self, url: str):
        print("Getting Profile ID")
        
        if url.find('linkedin.com/in/') == -1: return 

        payload={}
        headers = {
        'authority': 'www.linkedin.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }

        try:
            response = self.session.request("GET", url, headers=headers, data=payload) # request to the api 
        except Exception as e:
            print("Connection Error")
            return

        if response.status_code == 200:
            try:
                pattern = 'urn:li:fsd_profileCard'
                soup = BeautifulSoup(response.text, 'html.parser') # html parse using beautifulsoup
                code: NavigableString = soup(text=re.compile(pattern))[0]
                if not code:
                    return
                user_id = code.text[code.text.find(pattern)+len(pattern)+2:] # getting of user id from url 
                user_id = user_id[:user_id.find(",")]

                return user_id
            except Exception as e:
                print(e)
                return
        else:
            print("api error:",str(response.status_code))
            return

    def userActivity(self, user_id=None, user_url=None, start=0, token=None):
        res = {'status': '', 'message': '', 'data': '', 'id': '', 'start':'', 'token': ''}
        if not user_id:
            scrape_id_all = self.profileDetails(user_url)
            time.sleep(5)
            if not scrape_id_all:
                res['status'] = "Error"
                res['message'] = "Invalid url, or couldn't find profile id"
                return res
        else:
            print('Next Page')
            scrape_id = user_id
        
        scrape_id = scrape_id_all[0]
        
        print("Scraping Activity")
        url = f"https://www.linkedin.com/voyager/api/identity/profileUpdatesV2?count=20&includeLongTermHistory=true&moduleKey=creator_profile_all_content_view%3Adesktop&numComments=0{'&paginationToken='+quote_plus(token) if token else ''}&profileUrn=urn%3Ali%3Afsd_profile%3A{scrape_id}&q=profileMemberShareFeed&start={start}"

        payload={}
        headers = {
        'authority': 'www.linkedin.com',
        'accept': 'application/vnd.linkedin.normalized+json+2.1',
        'accept-language': 'en-US,en;q=0.9',
        'csrf-token': self.session.cookies.get('JSESSIONID').replace('"',''),
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }
        try:
            response = self.session.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            res['status'] = "Error"
            res['message'] = "Connection Error"
            return res
        reposts = []
        activity = {}
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as e:
                res['status'] = "Error"
                res['message'] = "Error Extracting data from json,"+str(e)
                return res
            
            with open('activityapiresponse.json','w') as f:
                json.dump(data,f,indent=2)
            
            def findLink(data,profile_id):
                for i in data['included']:
                    if i["$type"] != "com.linkedin.voyager.identity.shared.MiniProfile":
                        continue
                    pp = 'NA'
                    if i["entityUrn"] != profile_id:
                        continue
                    
                    try:
                        if base:= i['picture']:
                            for detail in base['artifacts']:
                                if detail['width'] >= 800:
                                    pp = base['rootUrl']+detail['fileIdentifyingUrlPathSegment']
                                    break
                                # temp = {}
                                # temp['width'] = detail['width']
                                # temp['height'] = detail['height']
                                # temp['expiresAt'] = detail['expiresAt']
                                # temp['link'] = base['rootUrl']+detail['fileIdentifyingUrlPathSegment']
                                # pp.append(temp)
                    except Exception as e:
                        print(e)
                    return pp

            next_page = data['data']['metadata']['paginationToken']
            count = 0
            result_count = 0
            i: dict
            for i in data['included']:
                if i["$type"] != "com.linkedin.voyager.feed.render.UpdateV2":
                    continue
                count += 1

                post_id: str = i['*socialDetail']

                raw_data = {}
                if post_id.find('activity:') == -1 and post_id.find('ugcPost:') == -1:
                    print("No id found")
                    continue
                
                raw_data['keyword'] = user_url
                raw_data['post_link'] = 'https://www.linkedin.com/feed/update/'+post_id.replace('urn:li:fs_socialDetail:','')
                if post_id.find('activity:') != -1:
                    post_id = post_id[post_id.find('activity:')+len('activity:'):]
                
                if post_id.find('ugcPost:') != -1:
                    post_id = post_id[post_id.find('ugcPost:')+len('ugcPost:'):]

                if i.get('*resharedUpdate'):
                    repost_id: str = i['*resharedUpdate']
                    repost_id = repost_id[repost_id.find('activity:')+len('activity:'):]   #user activity work and work of data fetched.
                    repost_id = repost_id[:repost_id.find(',')]
                    reposts.append(repost_id)
                    print('Repost id',repost_id)

                try:
                    try:
                        id_path = i['actor']['image']['attributes'][0]['*miniProfile']
                    except:
                        id_path = i['actor']['image']['attributes'][0]['miniProfileWithRingStatus']['*miniProfile']

                    if id_path != f"urn:li:fs_miniProfile:{scrape_id}":
                        continue
                    post_time: str = i['actor']['subDescription']['text']
                    post_time = post_time.split('•')[0].strip()
                    if any(post_time.endswith(s) for s in  ['d','w','mo','y']):
                        continue
                    result_count += 1

                    post_time = re.findall(r"(\S*\d+)(\w+)\S*", post_time)
                    current_time = datetime.utcnow()
                    if post_time == []:
                        post_time = current_time
                    else:
                        num, var = post_time[0]
                        if var == 'm':
                            post_time = (current_time - timedelta(minutes=int(num)))
                        elif var == 'h':
                            post_time = (current_time - timedelta(hours=int(num)))
                        else:
                            post_time = current_time

                    raw_data['title'] = i['actor']['name']['text'].replace("'","''")
                    raw_data['primarySubtitle'] = i['actor']['description']['text'].replace("'","''")
                    raw_data['secondarySubtitle'] = post_time
                    raw_data['summary'] = i['commentary']['text']['text'].replace("'","''")

                    
                    raw_data['profile_picture'] = scrape_id_all[2]
                    # try:
                    #     raw_data['profile_picture'] = findLink(data,i['actor']['image']['attributes'][0]['*miniProfile'])
                    # except Exception as e:
                    #     print(e)
                    #     continue
                    img = 'NA'
                    post_images = None
                    try:
                        post_images = i['content']['images'][0]['attributes'][0]['vectorImage']
                    except:
                        try:
                            post_images = i['content']['largeImage']['attributes'][0]['vectorImage']
                        except:
                            pass
                    
                    if post_images:
                        img = post_images['rootUrl'] + post_images['artifacts'][0]['fileIdentifyingUrlPathSegment']
                    raw_data['image'] = img

                    try:
                        raw_data['connection'] = i['actor']['supplementaryActorInfo']['text'].replace("'","\'")
                    except:
                        raw_data['connection'] = ''
                    
                    activity[post_id] = raw_data
                except Exception as e:
                    print("P-ID:",post_id)
                    print("Error in scraping Post Value",raw_data['post_link'])
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

            print("All recent activity scraped")
            for i in reposts:
                print('removing',i)
                if i in activity: del activity[i]
            
            if result_count == 0:
                res['status'] = "No result"
                res['data'] = activity
            else:
                res['status'] = "Successful"
                res['data'] = activity

            return res, scrape_id_all 
            
            # res['status'] = 'Incomplete'
            # res['data'] = activity
            # res['id'] = scrape_id
            # res['start'] = start
            # res['token'] = next_page
            # return res
        else:
            res['status'] = "Error"
            res['message'] = "LinkedIn API Error: "+str(response.status_code)
            return res

    def proxyTest(self):
        print('testing proxy') #proxy testing function to get ip,geo,city
        url = "http://lumtest.com/myip.json"
        try:
            response = self.session.request("GET", url)
        except Exception as e:
            print("Connection Error",e) 
            return
        
        if response.status_code == 200:
            res = response.json()
            print("Proxy Test:",res['ip'],res['country'],res['geo']['city'])
        elif response.status_code == 502:
            print('Invalid City')
            self.resetURL()
        elif response.status_code == 407:
            print('Invalid Country',self.country)
        else:
            print("Error:",response)
        
        return

    def dataTest(self): # datatest testing only
        data = {
            "7049291289539870720": {
                "connection": "3rd+",
                "image": [
                    {
                        "expiresAt": 1686182400000,
                        "height": 1080,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_2048_1536/0/1680682010704?e=1686182400&v=beta&t=_e9NBbR5SZIXnYe6AaVbhb_AxPxmrg2rpoUFqEjSw5o",
                        "width": 1080
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 20,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_20/0/1680682010713?e=1686182400&v=beta&t=YygxNUyIvm5CiRLtGdZMvxU_GItsfGC79_RnSU9k0hs",
                        "width": 20
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 1080,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_1280/0/1680682010713?e=1686182400&v=beta&t=YygOUfPBi2kmnCXasWHX_AruyPkwEDQlcaHHBcEJq60",
                        "width": 1080
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 480,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_480/0/1680682010713?e=1686182400&v=beta&t=437hkfx0eezNF7FpuyNWdE5cBMXWomPKNUr3DsV2Zww",
                        "width": 480
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 160,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_160/0/1680682010713?e=1686182400&v=beta&t=lvLiBf5P_a8FLnZdD6m-g5pkJeiNuDf1Sf4Zz3YMKwo",
                        "width": 160
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 800,
                        "link": "https://media.licdn.com/dms/image/D5622AQGpRW5hRWi6DA/feedshare-shrink_800/0/1680682010713?e=1686182400&v=beta&t=9BPcoNCWFWbXuL48CLGuOhVJg78d9JVgimNhijBCV3U",
                        "width": 800
                    }
                ],
                "keyword": "hiring",
                "post_link": "https://www.linkedin.com/feed/update/urn:li:activity:7049291289539870720",
                "primarySubtitle": "HR Executive at Techerudite",
                "profile_picture": "https://media.licdn.com/dms/image/D4D03AQHvDM29NTvaVA/profile-displayphoto-shrink_100_100/0/1683024467272?e=1688601600&v=beta&t=vjfCd1ky9Pf2B-4RGdEXVxnNODM187C187dKwiPPzB4",
                "secondarySubtitle": "1mo",
                "summary": "Hurrrrrrryyyyyyy Uppppp...\n\nWhy???\n\nBecause Techerudite is hiring for below profiles.\n\n#Graphicdesigner (Exp: 1 Year)\n#BDM (Exp: 1.5-4 Year)\n#Teamleader (Exp: 2+Year)\n#Projectmanager (Exp: 2+ Year with Developer Background)\n\nDrop CV to hr@techerudite.com or whatsapp on 7383590522.\n\n#like #share #comment",
                "title": "Disha Vaghela"
            },
            "7051412485983088640": {
                "connection": "3rd+",
                "image": [
                    {
                        "expiresAt": 1686182400000,
                        "height": 641,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_2048_1536/0/1681187744053?e=1686182400&v=beta&t=i9vR7GG_TMNZXxWytnrvemA6P_y2lchEWyjIaw1QSWw",
                        "width": 1232
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 10,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_20/0/1681187744052?e=1686182400&v=beta&t=Xfq6WMEJ96N37PKEEoq7Z8-wUcMAIiP441ut-nwwZVs",
                        "width": 20
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 641,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_1280/0/1681187744052?e=1686182400&v=beta&t=IA2PdiMBynT-PgcTrmIUViJDEuiWAlGbokIj6r3znCQ",
                        "width": 1232
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 249,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_480/0/1681187744053?e=1686182400&v=beta&t=fz7JIdPo5sgX5QpvhiotQQD9NeuMajtRd1RuV8CGrv0",
                        "width": 480
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 83,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_160/0/1681187744053?e=1686182400&v=beta&t=LbDO2sanXKnbugE5EtG6GbjzQ2R1pXf3OIUViqjhL_Q",
                        "width": 160
                    },
                    {
                        "expiresAt": 1686182400000,
                        "height": 416,
                        "link": "https://media.licdn.com/dms/image/D4D22AQH9nxXHyDk9ZA/feedshare-shrink_800/0/1681187744053?e=1686182400&v=beta&t=aEMZeOiIsQCN4TAMPWjdOeApX1jSeRReJKLuMp3xqIc",
                        "width": 800
                    }
                ],
                "keyword": "hiring",
                "post_link": "https://www.linkedin.com/feed/update/urn:li:activity:7051412485983088640",
                "primarySubtitle": "Senior Executive - Talent Acquisition",
                "profile_picture": "https://media.licdn.com/dms/image/D4D03AQGW7Opm5DW4pg/profile-displayphoto-shrink_100_100/0/1670346796756?e=1688601600&v=beta&t=Wyu_GmK9Pr5yiFu6aca8MKqR-VMcndB_oWjB5Okc_9U",
                "secondarySubtitle": "3w",
                "summary": "Dear Connections,\n\nWe at Deloitte, are actively hiring for our Financial Services team !! \n\nRole: PMO-Advisory\nLocation: Mumbai, Pune, Gurgaon and Bangalore \nExperience: 3-6 years\nNotice Period: Immediate to 60 days\n\n\nSpecific Minimum expertise/ experience:\n\n1.\tWork on strategic initiatives\n2.\tMonitor/Track projects under Operations from start to end\n3.\tKPI tracking\n4.\tCost Benefit Analysis for external vendor platform/services.\n5.\tSystem Implementation and RFPs for new platforms. \n\n\n\nFor More details and to apply kindly visit on the below mentioned link:\nhttps://lnkd.in/d7zbimJH\n\n#advisory #operationstransformation #PMO #financialservices #deloitte #big4 #digitaltransfomation #digitaltransformationstrategy #strategyconsulting #costreduction #operatingmodel #capitalmarket #financialservices #consulting #strategy",
                "title": "Prerna Anchalia"
            },
            "7060150458610282496": {
                "connection": " • You",
                "image": "No Image",
                "keyword": "https://www.linkedin.com/in/arsh-khan-09b466272",
                "post_link": "https://www.linkedin.com/feed/update/urn:li:activity:7060150458610282496",
                "primarySubtitle": "Freelance",
                "profile_picture": "",
                "secondarySubtitle": "1m",
                "summary": "#firstpost hello",
                "title": "Arsh Khan"
            },
            "7062333032136908801": {
                "connection": " • Following",
                "image": "No Image",
                "keyword": "https://www.linkedin.com/in/jiyad-mateen-2061431b6",
                "post_link": "https://www.linkedin.com/feed/update/urn:li:activity:7062333032136908801",
                "primarySubtitle": "Talent Acquisition Specialist at Genpact",
                "profile_picture": [
                    {
                        "expiresAt": 1689206400000,
                        "height": 100,
                        "link": "https://media.licdn.com/dms/image/C4D03AQFuvICNxtrp8A/profile-displayphoto-shrink_100_100/0/1623132137107?e=1689206400&v=beta&t=75afIrEu6WLpIG_aiJIceuOK3NFeFoFohOtN_FVRmbo",
                        "width": 100
                    },
                    {
                        "expiresAt": 1689206400000,
                        "height": 200,
                        "link": "https://media.licdn.com/dms/image/C4D03AQFuvICNxtrp8A/profile-displayphoto-shrink_200_200/0/1623132137107?e=1689206400&v=beta&t=Yu9QtbjXcGDv8JhUcijkHuKdGMY78s9NrJgKrlrvvUs",
                        "width": 200
                    },
                    {
                        "expiresAt": 1689206400000,
                        "height": 400,
                        "link": "https://media.licdn.com/dms/image/C4D03AQFuvICNxtrp8A/profile-displayphoto-shrink_400_400/0/1623132137107?e=1689206400&v=beta&t=cIFfq_VOx_GEaXIu3RWlEduqB58T6CYnlH7BOuoVLnU",
                        "width": 400
                    },
                    {
                        "expiresAt": 1689206400000,
                        "height": 800,
                        "link": "https://media.licdn.com/dms/image/C4D03AQFuvICNxtrp8A/profile-displayphoto-shrink_800_800/0/1623132137107?e=1689206400&v=beta&t=pLzVUtZ3wxHCPaOlyYeW8ETTnkuzRaHLYKh8BLG6h8g",
                        "width": 800
                    }
                ],
                "secondarySubtitle": "2h",
                "summary": "We are hiring for the position of Management Trainee- Deductions (OTC)\n\nLocation: Bangalore (work from office)\nShift: UK\nExperience: At least 3 years in OTC (Deductions)\nSap Mandate\n\nShare the resume and details as per format given below at jiyadmateen.ansari@genpact.com\"\n\nExperience in Order to cash:\nExperience in Deductions:\nCurrent Organization:\nCurrent CTC:\nExpected CTC:\nNotice Period:\nCurrent Location:\n\nOnly relevant candidates will be contacted.\n\n#deduction #deductions  #ordertocash   #order2cash #sap #p2p #ptp #OTC #bangalorejobs  #bangalorehiring #hiringalert #recruitment #southjobs #ncrjobs #bangalorejobs #delhincr #helpdesk #freshers #bcom #delhincr #gurgaonjobs #ncrjobs #jobseeksers  #rajasthan #jaipurjobs #accountingjobs #jaipurcity\n",
                "title": "Jiyad Mateen"
            }
        }
        return data

    def profileDetails(self, url: str):
        print("Getting Profile Deatils")
        
        if url.find('linkedin.com/in/') == -1: return 

        payload={}
        headers = {
        'authority': 'www.linkedin.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }

        try:
            response = self.session.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            print("Connection Error")
            return

        if response.status_code == 200:
            try:
                pattern = 'urn:li:fsd_profileCard'
                soup = BeautifulSoup(response.content, 'html.parser')
                code: NavigableString = soup(text=re.compile(pattern))[0]
                if not code:
                    return

                user_id = code.text[code.text.find(pattern)+len(pattern)+2:]
                user_id = user_id[:user_id.find(",")]
                
                details = json.loads(code.strip())
                with open('Delete.json','w') as f:
                    json.dump(details,f,indent=2)

                pp = 'NA'
                for meta in details['included']:
                    if not find(meta,'profilePicture'):
                        continue
                    
                    if meta.get('firstName'):
                            firstName = meta.get('firstName')

                    if meta.get('lastName'):
                        lastName = meta.get('lastName')

                    if base:=find(meta,'profilePicture.displayImageWithFrameReferenceUnion'):
                        base_url = find(base,'vectorImage.rootUrl')
                        prefix = base['vectorImage']['artifacts'][-1]['fileIdentifyingUrlPathSegment']
                        pp = base_url + prefix
                        
                    if base:=find(meta,'profilePicture.displayImageReference'):
                        base_url = find(base,'vectorImage.rootUrl')
                        prefix = base['vectorImage']['artifacts'][-1]['fileIdentifyingUrlPathSegment']
                        pp = base_url + prefix
                
                name = firstName + ' ' + lastName

                return user_id, name, pp
            except Exception as e:
                print(e)
                return
        else:
            print("api error:",str(response.status_code))
            return

    def search(self, sarch_type, input, pages=None, filter='all'):
        """
        type = keyword/activity

        input = 'any word'/url

        pages = number of pages to search

        filter = all/1st
        """

        return_data = {}
        pDetails = None
        if sarch_type == 'keyword':
            for page in range(pages):
                start = page*10
                print("Page:",page+1,"Start:",start)
                result: dict = self.searchPosts(input,start,search=filter) # search in page of given keyword
                if result['status'] == 'Successful':
                    return_data.update(result['data'])
                    # updateJSON('posts',result['data'])
                elif result['message'] == 'No result':
                    break
                elif result['status'] == "Error":
                    print(result['message'])
                    return result['message']
                    
                start += 10 # it will increment+=10 every iteration
                time.sleep(10)
        elif sarch_type == 'activity':
           
            result = {'status': None}

            while result['status'] != 'Successful':
                multi_result = self.userActivity(user_url=input)
                
                if type(multi_result) is dict:
                    result: dict  = multi_result
                else:
                    result: dict = multi_result[0]
                    pDetails = multi_result[1]

                if result['status'] == 'Successful':
                    return_data.update(result['data'])
                    break
                # elif result['status'] == 'Incomplete':
                #     return_data.update(result['data'])
                #     result: dict = self.userActivity(user_url=input,user_id=result['id'], start=result['start']+20, token=result['token'])
                else:
                    return_data = result['message']
                    break
        else:
            return 'Invalid type parameter use: keyword or activity'

        return return_data, pDetails


def updateJSON(file: str, newdata: dict):
    if os.path.exists(f"{file}.json"):
        if os.stat(f"{file}.json").st_size == 0: open(f"{file}.json", "w", encoding='utf-8').write('{}')
        with open(f"{file}.json", "r", encoding='utf-8') as jsonFile:
            data: dict = json.load(jsonFile)
        data.update(newdata)
    else:
        data = newdata
    with open(f"{file}.json", "w", encoding='utf-8') as jsonFile:
        json.dump(data, jsonFile, indent=4, sort_keys=True, ensure_ascii=False)


# import logging

# login_token = "AQEDAT9u9xkCffdPAAABiEzvr0kAAAGI4yM6qk0AqDDFH0Csy57_GGN5PKhrPS8xEAX_oZmWKW1A7OEW-COJZPV_tqa00o9aUh7QfX4_ZQCGznxuo3ivSqwAznx_4NaRGqsZZpFp2FBRtN8M3tJ2za30"

# # login_token = 'AQEDATMpnbUFBk_fAAABgiRSz4MAAAGILcluGE0ATCzQ8dLzrRnG1nDbP-m3Y5Y2E1DVomgA_6RyQtsugWuaX0zYqTwQ-wN903-Yi2qS0oZrmOvgkDtBAWVxm1XATD9EsUvZEKVSseP'
# bot = LinkedInSession(
#         'in',
#         'c',
#         'p',
#         login_token,
#         '193.9.56.67',
#         use_proxy = True
#     )

# bot.login()
# print(bot.search(sarch_type='activity', input="https://www.linkedin.com/in/vanshita-jain-2a29721b7/"))

# print(bot.profileDetails(url='https://www.linkedin.com/in/gayathri-r-b86a5321b/'))

# "https://www.linkedin.com/in/williamhgates"

# print(bot.search(sarch_type='activity', input="https://www.linkedin.com/in/vanshita-jain-2a29721b7/"))

# bot.login()
# res = bot.search(type='activity', input='https://www.linkedin.com/in/vanshita-jain-2a29721b7/')

# print(res)

# updateJSON('activity',res)
# search(login_token, type='keyword',input='hiring')

# search(login_token, type='keyword',input='hiring',filter='1st')

# https://www.linkedin.com/in/arsh-khan-09b466272
# search(login_token, type='activity',input='https://www.linkedin.com/in/jiyad-mateen-2061431b6')

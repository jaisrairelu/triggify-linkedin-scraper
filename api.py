import requests
import json

API_TOKEN = '2986335f-0819-4324-96e9-90a49139f89a'
headers = {'Authorization': f'Bearer {API_TOKEN}'}

def allocateNewProxy(country,city=''):
    data = {
        'customer': 'hl_68f06206',
        'zone': 'isp',
        'count': 1,
        'country': country,
        'country_city': country+'-'+city
    }
    try:
        response = requests.post('https://api.brightdata.com/zone/ips', data=data, headers=headers)
    except Exception as e:
        print("Connection Error: "+str(e))
        return None

    if response.status_code != 200:
        print(response,response.text,country,city)
        return None

    try:
        data = response.json()
    except Exception as e:
        print("LinkedIn API Error:",data)
        return None

    return data['new_ips'][0]

# ip = '178.171.26.83'
# data = {
#     'zone': 'isp',
#     'ips': [ip,ip]
# }

# r = requests.delete('https://api.brightdata.com/zone/ips', data=data, headers=headers)
# print(r.status_code,r.text)
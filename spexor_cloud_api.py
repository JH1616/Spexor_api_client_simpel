
import requests
import time
import atexit
import pickle
import os
import json


baseURL = "https://api.spexor-bosch.com"
auth_filename = os.path.join(os.path.dirname(__file__), "auth.pkl")


def print_pretty(yin):
    print (json.dumps(yin, indent=2, default=str))


class Spexor():
    def __init__(self) -> None:
        if os.path.isfile(auth_filename):
            with open(auth_filename, 'rb') as file:
                self.auth = pickle.load(file)
        else:
            self.auth = {
                        'device_code': None,
                        'device_code_expire':time.time(),
                        'access_token': None,
                        'access_token_expire':time.time(),
                        'refresh_token': None,
                        'refresh_token_expire':time.time(),
                        'webhooks':[]
                        }

        atexit.register(self.save_auth)

        self.all_spexors = []
        self.refresh_spexor_location()



    def save_auth(self):
        with open(auth_filename, 'wb') as file:
            pickle.dump(self.auth, file)


    def do_authentication(self):
        if self.auth['access_token_expire'] < time.time():
            if self.auth['refresh_token_expire'] < time.time():
                if self.auth['device_code_expire'] < time.time():
                    print("Request new device code")
                    self.request_device_code()

                print("Request new tokens")
                self.request_acess_token()

            else:
                print("Access token refreshed")
                self.refresh_acess_token()


    def request_device_code(self):
        #curl --location --request POST 'https://api.spexor-bosch.com/api/public/auth' --form 'client_id="spexor-3rdparty-service-auth"'
        response = requests.post(baseURL+'/api/public/auth', data={'client_id':'spexor-3rdparty-service-auth'}).json()
        self.auth['device_code'] = response['device_code']
        self.auth['device_code_expire'] = response['expires_in'] + time.time()
        print(f"Please go into Bosch Spexor App -> Account -> External Services and add a new service with the following code {response['user_code']}")
        input('Press Enter to continue.')


    def request_acess_token(self):
        #curl --location --request POST 'https://api.spexor-bosch.com/api/public/token' --form 'client_id="spexor-3rdparty-service-auth"' --form 'device_code="XXXX...XXXXXX"'
        response = requests.post(baseURL+'/api/public/token', data={'client_id':'spexor-3rdparty-service-auth', 'device_code':self.auth['device_code']}).json()
        self.auth['access_token'] = response['access_token']
        self.auth['access_token_expire'] = response['expires_in'] + time.time()
        self.auth['refresh_token'] = response['refresh_token']
        self.auth['refresh_token_expire'] = response['refresh_expires_in'] + time.time()

    def refresh_acess_token(self):
        #curl --location --request POST 'https://api.spexor-bosch.com/api/public/refresh' \
        # --header 'Content-Type: application/x-www-form-urlencoded' \
        # --header 'Authorization: Bearer xxx' \
        # --data-urlencode 'client_id=spexor-3rdparty-service-auth' \
        # --data-urlencode 'refresh_token=XXXXXXXXXX....XXXXXXXX'
        header = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Bearer xxx'}
        data = {'client_id':'spexor-3rdparty-service-auth', 'refresh_token':self.auth['refresh_token']}
        response = requests.post(baseURL+'/api/public/refresh', data=data, headers=header).json()
        self.auth['access_token'] = response['access_token']
        self.auth['access_token_expire'] = response['expires_in'] + time.time()
        self.auth['refresh_token'] = response['refresh_token']
        self.auth['refresh_token_expire'] = response['refresh_expires_in'] + time.time()


    def get_header(self):
        self.do_authentication()
        return {'Authorization': 'Bearer ' + self.auth['access_token']}


    def __update_all_spexors__(self, response, tree=[]):
        for s in response:
            found = False
            for spexor in self.all_spexors:
                if s['id'] == spexor['id']:
                    diver1 = spexor
                    diver2 = s
                    for i in tree:
                        diver1 = diver1[i]
                        diver2 = diver2[i]

                    diver1.update(diver2)
                    found = True
            if not found:
                self.all_spexors.append(s)


    def request_all_spexors_fast(self):
        #curl --location --request GET 'https://api.spexor-bosch.com/api/public/v1/spexors/' \
        # --header 'Authorization: Bearer XXXXXXX.....XXXXXX'
        return requests.get(baseURL+'/api/public/v1/spexors/', headers=self.get_header()).json()
    

    def refresh_spexor_location(self):
        #curl --location --request GET 'https://api.spexor-bosch.com/api/public/v1/spexors/location' \
        # --header 'Authorization: Bearer XXXXXXX.....XXXXXX'
        response = requests.get(baseURL+'/api/public/v1/spexors/location', headers=self.get_header()).json()
        self.__update_all_spexors__(response)
        return self.all_spexors
    
    def refresh_spexor_status(self, SpexorID=None):
        #curl --location --request GET 'https://api.spexor-bosch.com/api/public/v1/spexor/XXXXXXX' \
        # --header 'Authorization: Bearer XXXXXXX.....XXXXXX'
        response = []
        if SpexorID is not None:
            response.append(requests.get(baseURL+f'/api/public/v1/spexor/{SpexorID}', headers=self.get_header()).json())
        else:
            for spexor in self.all_spexors:
                response.append(requests.get(baseURL+f'/api/public/v1/spexor/{spexor["id"]}', headers=self.get_header()).json())
        self.__update_all_spexors__(response)
        return self.all_spexors
    
    def refresh_spexor_sensors(self, SpexorID=None):
        #curl --location --request GET 'https://api.spexor-bosch.com/api/public/v1/spexor/862430053823346/sensor?keys=AirQuality,AirQualityLevel,Temperature,Pressure,Acceleration,Light,Gas,Humidity,Microphone,PassiveInfrared,Fire' \
        # --header 'Authorization: Bearer XXXXXXX.....XXXXXX'
        urlattachment = 'sensor?keys=AirQuality,AirQualityLevel,Temperature,Pressure,Acceleration,Light,Gas,Humidity,Microphone,PassiveInfrared,Fire'

        response = []
        if SpexorID is not None:
            response.append({'id':SpexorID, 'sensors_status': requests.get(baseURL+f'/api/public/v1/spexor/{SpexorID}/{urlattachment}', headers=self.get_header()).json()})
        else:
            for spexor in self.all_spexors:
                response.append({'id':spexor["id"], 'sensors_status':requests.get(baseURL+f'/api/public/v1/spexor/{spexor["id"]}/{urlattachment}', headers=self.get_header()).json()})
        self.__update_all_spexors__(response)
        return self.all_spexors
    

    def refresh_all(self):
        self.refresh_spexor_location()
        self.refresh_spexor_status()
        self.refresh_spexor_sensors()
        return self.all_spexors
    

    def change_observation_state(self, observationType, targetState, SpexorID=None):
        #curl --location --request PATCH 'https://api.spexor-bosch.com/api/public/v1/spexor/862430053823346/status/observation' \
        # --header 'Authorization: Bearer XXXXXXX.....XXXXXX'
        #-H 'Content-Type: application/json' \
        #-d '[{"observationType":"Burglary","sensorMode":"Activated"}]'
        header = self.get_header()
        header.update({'Content-Type':'application/json'})
        data = [{"observationType":observationType,"sensorMode":targetState}]

        response = []
        if SpexorID is not None:
            response.append({'id':SpexorID, "status":{'observation':requests.patch(baseURL+f'/api/public/v1/spexor/{SpexorID}/status/observation', data=json.dumps(data), headers=header).json()}})
        else:
            for spexor in self.all_spexors:
                response.append({'id':spexor["id"], "status":{'observation':requests.patch(baseURL+f'/api/public/v1/spexor/{spexor["id"]}/status/observation', data=json.dumps(data), headers=header).json()}})
        self.__update_all_spexors__(response, ['status'])
        return self.all_spexors
    

    def get_webhook_event_hist(self, webhooksID):
        return requests.get(baseURL+f'/api/public/v1/webhooks/{str(webhooksID)}/log', headers=self.get_header()).json()
    
    def delete_webhook(self, webhooksID):
        response =  requests.delete(baseURL+f'/api/public/v1/webhooks/{str(webhooksID)}', headers=self.get_header())

        if response.status_code == 204:
            self.auth['webhooks'].pop(webhooksID)

        return self.get_all_webhooks()
    
    def register_webhook(self, SpexorID, url, events):
        header = self.get_header()
        header.update({'Content-Type':'application/json'})
        data = {
                "url": url,
                "events": events,
                "id": SpexorID,
                }

        response = requests.post(baseURL+f'/api/public/v1/webhooks', data=json.dumps(data), headers=header).json()
        webhookID = response.pop('id')
        self.auth['webhooks'].update({webhookID:response})
        return self.get_all_webhooks()
    

    def change_webhook(self, webhookID, SpexorID, url, events):
        header = self.get_header()
        header.update({'Content-Type':'application/json'})
        data = {
                "url": url,
                "events": events,
                "id": SpexorID,
                }

        response = requests.put(baseURL+f'/api/public/v1/webhooks/{str(webhookID)}', data=json.dumps(data), headers=header)
        if response.status_code == 204:
            self.auth['webhooks'][webhookID].update({'url': url, 'events': events})
        return self.get_all_webhooks()



    def get_all_webhooks(self):
        return self.auth['webhooks']





if __name__ == "__main__":
    s = Spexor()

    #less and different keys
    #print_pretty(s.request_all_spexors_fast())

    #print_pretty(s.refresh_spexor_location())
    #print_pretty(s.refresh_spexor_status())
    #print_pretty(s.refresh_spexor_sensors())

    print_pretty(s.refresh_all())
    #print_pretty(s.change_observation_state('Burglary', 'Deactivated'))
    #print_pretty(s.change_observation_state('Burglary', 'Activated'))

    #print_pretty(s.get_webhook_event_hist('ef66822b-ac15-4044-ab69-edb682971fbb'))
    #print_pretty(s.delete_webhook('aca3e80a-4d90-4d28-b8c3-a69e6b3de9f9'))
    #print_pretty(s.register_webhook('862430053823346', "https://www.google.com/", ['Test']))
    #print_pretty(s.change_webhook('13133f3b-7d24-4922-8915-d3e8c202820c', '862430053823346', "https://www.google.com/2", ['Test']))
    #print_pretty(s.get_all_webhooks())
    
import requests
import json
import sys

class Bot:

    def __init__(self, token):
        self._api_url = fr"https://api.telegram.org/bot{token}/"
    
    def _get_url(self, url, data):
        response = requests.get(url, params=data)
        #print("Response:", response)
        content = response.content.decode("utf8")
        return content

    def _get_json_from_url(self, url, data):
        content = self._get_url(url, data)
        js = json.loads(content)        
        return js

    def get_chat_list(self):   
        chat_list = []
        url = f"{self._api_url}getUpdates"
        data = dict()
        offset = None
        while True:     
            if offset:
                data['offset'] = offset
            updates = self._get_json_from_url(url, data)
            if(updates['ok'] == True and len(updates['result']) > 0):                                
                for i in updates['result']:
                    if i['message']['chat']['id'] not in chat_list:
                        chat_list.append(i['message']['chat']['id'])
                    offset = int(i['update_id']) + 1
            else:
                break                       
            
        return chat_list

    def _send_message_to_chat(self, message, chat_id):
        data = {'chat_id': chat_id, 'text': message}
        url = fr"{self._api_url}sendMessage"
        self._get_url(url, data)

    def _send_image_to_chat(self, image, chat_id):
        url = fr"{self._api_url}sendPhoto"
        files = {'photo': image}
        data = {'chat_id' : chat_id}
        requests.post(url, files=files, data=data)  

    def send_text_message(self, message, chats):        
        for id in chats:
            self._send_message_to_chat(message, id)

    def send_image(self, image, chats):
        for id in chats:
            self._send_image_to_chat(image, id)

def main(argv):
    usage = "usage: {} bot_token".format(argv[0])
    if len(argv) != 2:
        print(usage)
        sys.exit(1)
    bot = Bot(argv[1])
    print(bot.get_chat_list())                       
    
if __name__ == "__main__":
    main(sys.argv)            

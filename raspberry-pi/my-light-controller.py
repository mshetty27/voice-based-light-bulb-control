from sprw.io import Assistant, exceptions, IOT
from gpiozero import Button
from signal import pause

import dialogflow
from google.api_core.exceptions import InvalidArgument

import paho.mqtt.client as mqtt

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import json
import time

from datetime import datetime

B1 = Button(23)

#Setup sprw Assistant and call it say 'spark'
#@todo: Get access token from SP Robotics and set it here
spark = Assistant('PASTE YOUR SPRW ACCESS TOKEN HERE')
spark.microphone_device_index = 2
spark.speak('Press the button B1 and tell me what you want')

#Setup DialogFlow - the NLP based conversational interface
#@todo: This environment variable has to be set: GOOGLE_APPLICATION_CREDENTIALS='/home/pi/Desktop/ms/NewAgent-7fc2752f12de.json'
#@todo: Change project id
DIALOGFLOW_PROJECT_ID = 'newagent-kogffg'
DIALOGFLOW_LANGUAGE_CODE = 'en-US'
SESSION_ID = 'iot-raspberrypi'
session_client = dialogflow.SessionsClient()
session = session_client.session_path(DIALOGFLOW_PROJECT_ID, SESSION_ID)

#mqtt client
def on_acknowledgement(client, userdata, msg):
  ackStatus = str(msg.payload)
  print("Acknowledgement received. Bulb status: " + msg.topic + " " + ackStatus)
  #Update AWS IOT with the reported and desired status to the status of the bulb as acknowledged by NodeMCU
  #Note: desired status also has to be updated here. Otherwise Delta callback will be called
  updatePayload = '{"state":{"desired": {"status": "' + ackStatus + '"},"reported":{"status":"' + ackStatus + '"}}}'
  deviceShadowHandler.shadowUpdate(updatePayload, thing_update_callback, 5)

topic_to_publish = 'room/light' #Topic that your NodeMCU is listening to
topic_to_subscribe = 'room/light/status' #Topic that your NodeMCU is publishing to (acknowledgement)
mqttc=mqtt.Client()
mqttc.on_message = on_acknowledgement
mqttc.connect("localhost",1883,60)
mqttc.subscribe(topic_to_subscribe)
mqttc.loop_start()

# AWS IOT Stuff

# When any shadow state of our device in AWS IOT is updated, this callback will be called.
# Not doing anything here. Just logging the status of the update.
def thing_update_callback(payload, responseStatus, token):
  if responseStatus == "timeout":
    print("Update request " + token + " time out!")
  if responseStatus == "accepted":
    payloadDict = json.loads(payload)
    print("Update request with token: " + token + " accepted!")
    print(payloadDict)
  if responseStatus == "rejected":
    print("Update request " + token + " rejected!")

# When we update 'desired' state in the device shadow of AWS IOT, this callback will be called
# We can then take that request and switch the bulb ON/OFF
def thing_delta_callback(payload, responseStatus, token):
  print ('In Delta')
  print(responseStatus)
  payloadDict = json.loads(payload)
  print(payloadDict)
  desiredStatus = str(payloadDict["state"]["status"])
  spark.speak('Received a request to turn the light bulb ' + desiredStatus)
  mqttc.publish(topic_to_publish, desiredStatus)

# This will be called when we do a ShadowGet on the AWS IOT thing. 
# This is used to report the device status as recorded in AWS IOT
def thing_get_callback(payload, responseStatus, token):
   print ('In Get Callback')
   payloadDict = json.loads(payload)
   print(payloadDict)
   reportedStatus = str(payloadDict["state"]["reported"]["status"])
   reportedTimestamp =  payloadDict["metadata"]["reported"]["status"]['timestamp']
   dt = datetime.fromtimestamp(reportedTimestamp)
   time = spark.get_time_in_words(dt.hour,dt.minute)
   spark.speak("Status was reported to be")
   spark.speak(reportedStatus)
   spark.speak("at")
   spark.speak(time)

# Initialize AWSIoTMQTTShadowClient
# @todo: Change host, Download certificates for your thing. Change certificate names and thing name below
shadow_update_host = '<host-id>.iot.us-east-1.amazonaws.com'
shadow_update_rootCAPath = './certs/AmazonRootCA1.pem'
shadow_update_certificatePath = './certs/d9c6aa5121-certificate.pem.crt'
shadow_update_privateKeyPath = './certs/d9c6aa5121-private.pem.key'
shadow_update_port = 8883
shadow_update_thingName = 'edison'
shadow_update_clientId = 'raspberry_pi' #@todo: This session id can be randomized
myAWSIoTMQTTShadowClient = None
myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(shadow_update_clientId)
myAWSIoTMQTTShadowClient.configureEndpoint(shadow_update_host, shadow_update_port)
myAWSIoTMQTTShadowClient.configureCredentials(shadow_update_rootCAPath, shadow_update_privateKeyPath, shadow_update_certificatePath)
myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
myAWSIoTMQTTShadowClient.connect()
deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(shadow_update_thingName, True)
deviceShadowHandler.shadowRegisterDeltaCallback(thing_delta_callback)

while True:
    if B1.value==1:
        try:
            print('listening...')
            text_to_be_analyzed = spark.recognize_speech(language = 'en-IN')
            print(text_to_be_analyzed)

            text_input = dialogflow.types.TextInput(text=text_to_be_analyzed, language_code=DIALOGFLOW_LANGUAGE_CODE)
            query_input = dialogflow.types.QueryInput(text=text_input)

            try:
              response = session_client.detect_intent(session=session, query_input=query_input)
            except InvalidArgument:
              raise
            
            spark.speak(response.query_result.fulfillment_text)
            
            output_contexts = response.query_result.output_contexts
            command = ''
            if len(output_contexts) > 0:
              command = output_contexts[0].name
            
            if command.endswith('bulb-on'):
              #publish to mqtt broker
              mqttc.publish(topic_to_publish, 'ON')
            
            elif command.endswith('bulb-off'):
              #publish to mqtt broker
              mqttc.publish(topic_to_publish, 'OFF')
            
            elif command.endswith('bulb-status'):
              #get status of bulb
              #sending an empty update (this will be rejected and update callback will be called) 
              #will cause get callback to be called
              deviceShadowHandler.shadowUpdate('{}', thing_update_callback, 5)
              deviceShadowHandler.shadowGet(thing_get_callback, 5)
            
            else:
              spark.speak('Press button B1 to try again')
              
        except exceptions.SpeechRecognitionError as error:
            spark.speak('Sorry, I could not process the audio. Press button B1 to try again')
            print(error)

pause()

# IOT Project: Voice command based smart light bulb
This is a hobby project I did to learn IOT. The objective of this project is to
- Control a light bulb using voice commands on a Raspberry pi
- Control the light bulb from the cloud (AWS IOT Core) as well

## Components used
- A 5 watt light bulb and bulb holder
- Raspberry Pi 3 Model B (used one provided by SP Robotics, India. Comes with a board and with necessary ports & SD Card)
- Speaker Module for Raspberry Pi with Amplifier (used one provided by SP Robotics, India)
- Audio Splitter (used one provided by SP Robotics, India)
- Microphone (used one provided by SP Robotics, India)
- NodeMCU (ESP8266)
- 5V Relay Module ( I used a 2 channel relay. Could use a single channel as well)

## Setting things up
- To program the NodeMCU and upload code to it, you will need following. Refer [this](https://electronicsinnovation.com/nodemcu-arduinoide/ "Setting up NodeMCU to program with Arduino") to set them up
    - Arduino 1.8.12 IDE to program the NodeMCU
    - ESP8266 plugin
    - CP210X Drivers
- Connecting the bulb to the NodeMCU using a 5V Relay switch
    - To connect the NodeMCU to the 5V relay switch, I used the following configuration:
D4 (Node MCU)  <--> IN1 (Relay Module)
3V3(Node MCU)  <--> VCC (Relay Module)
GND(Node MCU)  <--> GND (Relay Module)
    - Take a bulb connected to a holder with wire. Cut off one of the wires and connect the ends to the output side of the relay to NO (Normally open) and the Common terminals. With this the relay switch will get connected in series with the bulb and will be in OFF position by default unless a signal is given to it from the NodeMCU
- Setting up Raspberry Pi
  - Connect speaker module to the raspberry pi giving it 5V supply
  - Connect Amplifier (part of the speaker mod) to audio splitter
  - Connect Microphone to audio spliter
  - Connect USB end of the splitter to USB port on the Raspberry Pi board
  - Connect monitor to the pi using HDMI cable. Connect USB keyboard and mouse too
  - Power the pi using 5V adapter
  - using NOOBS install Raspbian OS
- Installing pre-requisite modules in Raspberry Pi
    - Install python 3.5 (I used 3.5.3)
    - Set up MQTT broker/server using Mosquitto as described [here](https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/ "Installing Mosquitto broker on Raspberry pi")
    - Install the following modules for Python 3
        - sprw-iot (used to convert speech to text and vice-versa)
        - dialogflow (to understand user's intent using NLP)
        - google-api-core (required for dialogflow)
        - paho-mqtt (used to publish subscribe over MQTT)
        - AWSIoTPythonSDK (used to connect to AWS IOT)
- Creating the 'thing' in AWS IOT and generating & downloading certificates
  - Follow this [link](https://electronicsinnovation.com/what-is-aws-iot-how-to-creat-a-thing-in-aws-iot-core-its-certificates-policies/ "Setting up thing in AWS IOT") to understand how to set our thing in AWS IOT. 
  - After attaching policies with necessary permissions to interact with the thing, download certificates and also the Root CA certificate. These will be required by Raspberry Pi client to connect and update the thing via it's shadow
  - Create a shadow for the thing
 - Setting up an agent in Google Dialogflow and creating the intents
    - Set up an agent in dialogflow. An export of my agent is available as part of this project source
    - The following intents were defined
        - Default Welcome Intent
        - Default Fallback Intent (if none match)
        - Switch on the Bulb
        - Switch off the Bulb
        - Status of the Bulb
  
## Running the code
- Arduino code for the NodeMCU (node-mcu/mqtt-esp8266/mqtt-esp8266.ino)
    - Three things to be updated here as marked with @todo : your WIFI network SSID, your WIFI password and the mqtt server IP which is the IP address that the Raspberry Pi has got in your network
    - Firstly this code connects to WIFI and then tries to connect to the MQTT broker. It subscribes to the topic 'room/light'. The callback for this subscription is responsible for doing a digital write on the output pin (PIN 2 or D4) with a HIGH or LOW signal. It also publishes the 'ON'/'OFF' status immediately on the topic 'room/light/status'. 
    - Connect the NodeMCU to the computer using USB cable and flash the code onto it.
    - Plug the bulb on to the power supply. It will be off at first.
- Python code for Raspberry pi (raspberry-pi/my-light-controller.py)
    - Place the certs downloaded from AWS into the certs directory. I have placed dummy certs in the repo
    - Paste your SPRW access token.
    - Set up environment variable "GOOGLE_APPLICATION_CREDENTIALS" with a value as path of the agent configuration file (this can be obtained from the google project that gets automatically generated when you create a dialogflow agent)
    - Update your dialogflow project settings
    - Update your AWS IOT settings
    - This code does the following:
        - Listens for user's voice input after pressing button 'B1'. The voice from microphone is captured by SPRW-IOT library to convert to text
        - This text is sent to google dialogflow to get the user's intent.
        - Based on the user's intent, it either publishes 'ON'/'OFF' to topic 'room/light' or gets the status of the bulb from AWS IOT and speaks it out again using text to speech api of SPRW-IOT
        - Subscribes to topic 'room/light/status'. When the node-mcu acknowledges with status, this is updated on to the device shadow in AWS IOT.
        - When the desired status is updated in AWS IOT, it again either publishes 'ON'/'OFF' to topic 'room/light' based on the desired status. This way we can control the bulb not only with the voice commands on our assistant but also from the cloud
    - Run the code and test it out
  
## Testing it out
- Press the button B1 & speak 'Switch the bulb on' using the microphone. You should see the relay switching and Bulb turning ON
- Press the button B1 again & speak 'Switch the bulb off' using the microphone. You should see the relay switching and Bulb turning OFF
- Update the device shadow in AWS IOT by setting the the property called 'status' under the 'desired' state to 'ON'. You should see the relay switching and Bulb turning ON
- Press the button B1 again and speak 'What is the status of the bulb' or 'Is the bulb on' etc. The assistant should speak out the current status of the bulb by retrieving from AWS IOT.

## Conclusion
I had a fun time doing this project and learnt a great deal along the way. Hope these code and instructions could help someone out there!
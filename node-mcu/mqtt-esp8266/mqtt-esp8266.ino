/*
 * To be executed on a NodeMCU (ESP8266)
 * Connects to broker @ the specified IP address on a Raspberry Pi. 
 * Receives commands on specified topic to switch ON/OFF a light bulb connected to the NodeMCU via a relay switch
 * - publishes initial status to the topic "room/light/status"
 * - subscribes to the topic "room/light". If it receives 'ON' gives a signal to relay to switch on the light.  
 * - When it receives 'OFF', it sends a signal to relay to switch off the light
 * - Each time it takes action, it acknowledges by sending current status to the topic "room/light/status"
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// Update these with values suitable for your network.

const char* ssid = ""; //@todo: Your WIFI network SSID
const char* password = ""; //@todo: Your WIFI password
const char* mqtt_server = "192.168.X.X"; //@todo: Check the internal IP address of your Raspberry PI device and update

const byte LIGHT_PIN = 2;   // Pin to control the light with. Correponds to pin D4 on the NodeMCU
const char *TOPIC = "room/light";  // Topic to subcribe to
const char *ACK_TOPIC = "room/light/status";  // Topic to publish

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;

void setup_wifi() {

  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  randomSeed(micros());

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  String response;
  for (int i = 0; i < length; i++) {
    response += (char)payload[i];
  }
  
  Serial.println(response);

  if(response == "OFF"){
    digitalWrite(LIGHT_PIN, HIGH); //Turn the light OFF
    client.publish(ACK_TOPIC, "OFF"); //Acknowledge the status back
  }
  else if(response == "ON")  
  {
    digitalWrite(LIGHT_PIN, LOW); //Turn the light ON
    client.publish(ACK_TOPIC, "ON"); //Acknowledge the status back
  }

}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      // Once connected, publish an announcement...
      //client.publish("outTopic", "hello world");
      // ... and resubscribe
      client.subscribe(TOPIC);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup() {
  pinMode(LIGHT_PIN, OUTPUT); //Initialize the LIGHT_PIN pin as an output
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  //Initial condition - OFF. Also send the same to Raspberry Pi on the acknowledgement topic
  digitalWrite(LIGHT_PIN, HIGH);
  client.publish(ACK_TOPIC, "OFF");
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}

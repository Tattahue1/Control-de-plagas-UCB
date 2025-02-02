from machine import UART, Pin, I2C, ADC

from bmp281 import BMP281
import dht
import time
import uos

global temp
global hum

time.sleep(10)
# Initialize UART
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# check if rasp is working
led = machine.Pin(25, machine.Pin.OUT)
led.value(1)

humSensor = dht.DHT22(machine.Pin(2))

pres_working = False

try:
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
    pres_sensor = BMP281(i2c=i2c)
    pres_working = True
except Exception as e:
    print(e)

# initialize variables
temp = 0
hum = 0
pres = 0
humAlt = 0
tempAlt = 0
data_sent = 0
#url = 'http://raspico.free.beeceptor.com'
url = 'http://watchcloud.piensadiferente.net/weather/api/device/post/data'
led.value(0)

def send_command(command, delay=1):
    print(f"Sending command: {command}")
    uart.write(command + "\r")
    time.sleep(delay)
    response = ''
    while uart.any():
        response += uart.read().decode('utf-8')
    print(response)
    return response
        
def initialize_sim800():
    send_command('AT+SAPBR=3,1,"CONTYPE","GPRS"')
    time.sleep(2)
    send_command('AT+SAPBR=3,1,"APN","internet.tigo.bo"') #APN TIGO
    send_command('AT+SAPBR=1,1')
    time.sleep(2)
    send_command('AT+HTTPINIT')
    send_command('AT+HTTPPARA="CID",1')
    
def send_http_message(url, temp, hum, pres, uv):
    remainer = 0
    
    response = send_command("AT+CCLK?")
    #check time
    if '+CCLK' in response: 
        # Extract the time string from the response, which looks like: +CCLK: "yy/MM/dd,HH:mm:ss+zz"
        time_str = response.split('"')[1]
        minutes = time_str.split(',')[1].split(':')[1]
        print("Minutes:", minutes)
        seconds = time_str.split(',')[1].split(':')[2]
        seconds = seconds[0:2]
        print("Seconds:", seconds)
    
    remainer = int(minutes) % 5
    if remainer != 0:
        remainer = 5 - remainer
        substracter = remainer * 60 - int(seconds)
        time.sleep(remainer*60)

    #send to endpoint data
    initialize_sim800()
    send_command(f'AT+HTTPPARA="URL","{url}"')
    send_command('AT+HTTPPARA="CONTENT","application/json"')
    time.sleep(2)

    # Prepare data
    iddevice = "CCBA"
    temp = str(temp)
    hum = str(hum)
    pres = str(pres)
    uv = str(uv)
    altitude = "0"
    rain = "0"
    windf = "0"
    winds = "0"
    batt_level = "0"
    lat = "0"
    lon = "0"
    number = "0"

    data = f'''{{
      "iddevice": "{iddevice}",
      "temp": "{temp}",
      "hum": "{hum}",
      "pres": "{pres}",
      "uv": "{uv}",
      "altitude": "{altitude}",
      "rain": "{rain}",
      "windf": "{windf}",
      "winds": "{winds}",
      "batt_level": "{batt_level}",
      "lat": "{lat}",
      "lon": "{lon}",
      "number": "{number}"
    }}'''

    send_command(f'AT+HTTPDATA={len(data)},10000')
    time.sleep(2)
    uart.write(data + "\r")
    time.sleep(1)
    send_command('AT+HTTPACTION=1')
    time.sleep(10)
    send_command('AT+SAPBR=0,1')
    send_command('AT+HTTPTERM')
    return 1

def read_hum(humSensor):
    time.sleep(2)
    humSensor.measure()
    temp = humSensor.temperature()
    hum = humSensor.humidity()
    return(hum, temp)

def read_pres(pres_sensor):
    data_bmp = pres_sensor.read_all()
    if 'humidity' in data_bmp:
        return (data_bmp['pressure'], data_bmp['temperature'], data_bmp['humidity'])
    return (data_bmp['pressure'], data_bmp['temperature'], 0)

def read_UV(uv_sensor):
    time.sleep(2)
    raw_value = uv_sensor.read_u16()
    voltage = (raw_value / 65535.0) * 3.3
    #uv_index = (voltage - 0.99) * (15 / (2.9 - 0.99))
    
    if uv_index < 0:
        uv_index = 0
        
    return voltage

def restart():
    machine.reset()

wdt = machine.WDT(timeout=500000)
send_command('ATE0')
send_command('AT+CCLK="24/10/11,14:30:00+00"')

led.value(1)

repeater = 20 # iteraciones antes de enviar datos

try:
    while(True):
        if pres_working == False:
            try:
                i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
                pres_sensor = BMP281(i2c=i2c)
                pres_working = True
            except Exception as e:
                print(e)
        try:
            counter = 0
            while (counter < repeater): 
                if hum == 0:
                    try:
                        hum, temp = read_hum(humSensor)
                    except Exception as e:
                        print(f"Error: {e}")
                
                if pres == 0:
                    try:
                        pres, tempAlt, humAlt = read_pres(pres_sensor)
                    except Exception as e:
                        print(f"Error: {e}")
                
                if temp == 0:
                    temp = tempAlt
                if hum == 0:
                    hum = humAlt

                counter += 1
                time.sleep(1)
                
            led.value(0)
            data_sent = send_http_message(url, temp, hum, pres)
            
            temp = 0
            hum = 0
            pres = 0
            tempAlt = 0
            humAlt = 0
            uv = 0
            data_sent = 0
            led.value(1)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(50)
        
        wdt.feed()

except Exception as e:
    print(f"Error detectado: {e}, reiniciando...")
    restart()

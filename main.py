from machine import Pin, PWM, Timer, UART, ADC
import json


PIN_UART_TX = 0
PIN_UART_RX = 1
PIN_SERVO = 21
PIN_MOTOR_RIGHT_REV = 6
PIN_MOTOR_RIGHT_FWD = 7
PIN_MOTOR_LEFT_REV = 8
PIN_MOTOR_LEFT_FWD = 9
PIN_VOLTAGE = 28


uart_bot = UART(0, baudrate=38400, tx=Pin(PIN_UART_TX), rx=Pin(PIN_UART_RX), timeout=300)

led_pin = Pin("LED", Pin.OUT)

head_servo = PWM(Pin(PIN_SERVO, mode=Pin.OUT))
head_servo.freq(50)
head_servo.duty_u16(4914)
head_servo_pos = 4900
HEAD_POS_MIN = 3000
HEAD_POS_MAX = 6300
HEAD_SPEED = 120

adc_batt = ADC(PIN_VOLTAGE)

# PWM_LOOKUP_LEFT =  [0, 50, 60, 70, 90, 110, 140, 255]
# PWM_LOOKUP_RIGHT = [0, 40, 51, 60, 77,  93, 140, 255]
PWM_LOOKUP_LEFT =  [0, 12800, 15360, 17920, 23040, 28160, 35840, 65535]
PWM_LOOKUP_RIGHT = [0, 10240, 13056, 15360, 19712,  23808, 35840, 65535]
MAX_SPEED = 7
SPEED_INC = 0.5
cur_speed_left = 0.0
cur_speed_right = 0.0
set_speed_left = 0.0
set_speed_right = 0.0
motor_left_fwd = PWM(Pin(PIN_MOTOR_LEFT_FWD), freq=2000, duty_u16=0)
motor_left_rev = PWM(Pin(PIN_MOTOR_LEFT_REV), freq=2000, duty_u16=0)
motor_right_fwd = PWM(Pin(PIN_MOTOR_RIGHT_FWD), freq=2000, duty_u16=0)
motor_right_rev = PWM(Pin(PIN_MOTOR_RIGHT_REV), freq=2000, duty_u16=0)

# command from RPI
fwd = False
rev = False
left = False
right = False
cam_up = False
cam_down = False


def send_telemetry(timer):
    led_pin.value(1)
    json_tele = {
        "genericData" : { "status" : "OK" },
        "battery": {
            "min": 14.0,
            "max": 16.4,
            "uom": "V"
        }
    }
    voltage = adc_batt.read_u16()
    json_tele["battery"]["value"] =  round(voltage * 0.033076) / 100
    msg = json.dumps(json_tele, separators=(",", ":"))
    msg = msg + "\n"
    # print(f"send tele msg: {msg}")
    uart_bot.write(msg)
    led_pin.value(0)


def motorcontrol(timer):
    global cur_speed_left
    global cur_speed_right
    global set_speed_left
    global set_speed_right
    global fwd
    global rev
    global left
    global right
    global head_servo_pos

    set_speed_left = 0
    set_speed_right = 0

    if fwd:
        if left:
            set_speed_left = 4
            set_speed_right = 7
        elif right:
            set_speed_left = 7
            set_speed_right = 4
        else:
            set_speed_left = 7
            set_speed_right = 7
    elif rev:
        if left:
            set_speed_left = -7
            set_speed_right = -4
        elif right:
                set_speed_left = -4
                set_speed_right = -7
        else:
            set_speed_left = -7
            set_speed_right = -7
    else:
        if left:
            set_speed_left = -5
            set_speed_right = 5
        if right:
            set_speed_left = 5
            set_speed_right = -5

    if set_speed_left < cur_speed_left:
        cur_speed_left = cur_speed_left - SPEED_INC
    elif set_speed_left > cur_speed_left:
        cur_speed_left = cur_speed_left + SPEED_INC

    if cur_speed_left < -MAX_SPEED:
        cur_speed_left = -MAX_SPEED
    elif cur_speed_left > MAX_SPEED:
        cur_speed_left = MAX_SPEED

    if set_speed_right < cur_speed_right:
        cur_speed_right = cur_speed_right - SPEED_INC
    elif set_speed_right > cur_speed_right:
        cur_speed_right = cur_speed_right + SPEED_INC

    if cur_speed_right < -MAX_SPEED:
        cur_speed_right = -MAX_SPEED
    elif cur_speed_right > MAX_SPEED:
        cur_speed_right = MAX_SPEED

    if cur_speed_left >= 0:
        motor_left_rev.duty_u16(0)
        motor_left_fwd.duty_u16(int(cur_speed_left*9360))
    else:
        motor_left_fwd.duty_u16(0)
        motor_left_rev.duty_u16(int(-cur_speed_left*9360))

    if cur_speed_right >= 0:
        motor_right_rev.duty_u16(0)
        motor_right_fwd.duty_u16(int(cur_speed_right*9360))
    else:
        motor_right_fwd.duty_u16(0)
        motor_right_rev.duty_u16(int(-cur_speed_right*9360))

    if cam_up:
        head_servo_pos = head_servo_pos + HEAD_SPEED
    elif cam_down:
        head_servo_pos = head_servo_pos - HEAD_SPEED

    if head_servo_pos < HEAD_POS_MIN:
        head_servo_pos = HEAD_POS_MIN
    if head_servo_pos > HEAD_POS_MAX:
        head_servo_pos = HEAD_POS_MAX

    head_servo.duty_u16(head_servo_pos)
    print(f"servo: {head_servo_pos}")


if __name__ == '__main__':
    print("# Mechanical Booze Buddy system")

    telemetry_timer = Timer()
    telemetry_timer.init(period=1000, mode=Timer.PERIODIC, callback=send_telemetry)

    motor_timer = Timer()
    motor_timer.init(period=100, mode=Timer.PERIODIC, callback=motorcontrol)

    while True:
        line = uart_bot.readline()
        if line is not None and len(line) > 1:
            print(f"rec: {line}")
            try:
                json_msg = json.loads(line.decode('utf-8'))
                controls = json_msg["controls"]
                if controls is None:
                    continue
                fwd = controls["f"] != 0
                rev = controls["b"] != 0
                left = controls["l"] != 0
                right = controls["r"] != 0
                cam_up = controls["cam_up"] != 0
                cam_down = controls["cam_down"] != 0
                print(f"received cmd: f:{fwd}, r:{rev}, l:{left}, r:{right}")

            except Exception as err:
                print(f"error: {err}")
from machine import Pin
import time
import micropython
import _thread
import array

RECEIVER_PIN = 18

last_rising_time = 0
last_falling_time = 0

MAX_PULSES = 800
pulse_durations = array.array('I', [0] * MAX_PULSES)
pulse_index = 0

lock = _thread.allocate_lock()

micropython.alloc_emergency_exception_buf(100)

def handle_interrupt(pin):
    global last_rising_time, last_falling_time, pulse_index
    
    current_time = time.ticks_us()
    
    if pin.value() == 1:
        if last_falling_time != 0 or pulse_index == 0:  # Ensure the first recorded pulse is a low pulse
            high_duration = time.ticks_diff(current_time, last_falling_time) if last_falling_time != 0 else 0
            
            if pulse_index < MAX_PULSES:
                with lock:
                    pulse_durations[pulse_index] = high_duration
                    pulse_index += 1
        
        last_rising_time = current_time
    else:
        if last_rising_time != 0:
            low_duration = time.ticks_diff(current_time, last_rising_time)
            
            if pulse_index < MAX_PULSES:
                with lock:
                    pulse_durations[pulse_index] = low_duration
                    pulse_index += 1
        
        last_falling_time = current_time

try:
    # Wait for receiver to startup, improves reliability
    time.sleep(5)
    receiver = Pin(RECEIVER_PIN, Pin.IN)
    receiver.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=handle_interrupt)
    print(f'Starting reception on Pin {RECEIVER_PIN}.')

    while True:        
        time.sleep(2)
        
        if pulse_index > 50:
            with lock:
                pulse_copy = pulse_durations[:pulse_index]
                pulse_index = 0
            
            pulse_copy = list(pulse_copy)
            pulse_copy.pop(0) # First entry usually too long
            
            # Processing can be added here
            
            timestamp = time.localtime()
            message = '[{:02d}:{:02d}:{:02d}]: {} Pulses:\n{}'.format(timestamp[3],
                                                                  timestamp[4],
                                                                  timestamp[5],
                                                                    len(pulse_copy),
                                                                     pulse_copy)
            print(message)

except KeyboardInterrupt:
    print("Program terminated.")

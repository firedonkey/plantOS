import sys
import termios
import tty
import lgpio

GPIO17 = 17
GPIO27 = 27

chip = lgpio.gpiochip_open(0)

lgpio.gpio_claim_output(chip, GPIO17)
lgpio.gpio_claim_output(chip, GPIO27)

state = 0  # 0 = OFF, 1 = ON

print("Press SPACE or ENTER to toggle GPIO. Press 'q' to quit.")

def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

while True:
    key = get_key()

    if key == 'q':
        break

    if key == ' ' or key == '\r':  # space or enter
        state = 1 - state  # toggle

        lgpio.gpio_write(chip, GPIO17, state)
        lgpio.gpio_write(chip, GPIO27, state)

        if state:
            print("GPIO ON")
        else:
            print("GPIO OFF")

lgpio.gpiochip_close(chip)
print("Exited cleanly")

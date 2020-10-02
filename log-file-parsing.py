import json
import matplotlib.pyplot as plt

f = open("200918093122.log", "r")


# Storage class for common message data
class Message:
    def __init__(self):
        self.RunTime = 0
        self.Major = ''
        self.Minor = ''
        self.Param = {}


# Storage class for AutoMove Settings
class AutoMove:
    def __init__(self):
        self.Status = 0
        self.Pitch = 1000
        self.Pattern = 0
        self.Rotated = False
        self.RotatedTractor = False


# Data for printing diagnostics
clamp_time = []
clamp_pressure = []

inlet_time = []
inlet_pressure = []

valve_time = [[0.0] for y in range(16)]
valve_state = [[y] for y in range(16)]

total_valve_time = [{'A': 0, 'B': 0} for x in range(16)]

job_time = 0

valve_enable_time = 0
valve_on_time = 0

am_settings = AutoMove()

origin_x = 0.0
origin_y = 0.0

tube_row = []
tube_column = []

tube_x = []
tube_y = []

feed_in_time = []
feed_out_time = []

lances = 0x00

tube_time = [0]
tube_count = [0]


def clean_a_tube(row, column):
    tube_is_cleaned = False

    for index, tube in enumerate(tube_row):
        if tube == row and tube_column[index] == column:
            tube_is_cleaned = True
            break

    if not tube_is_cleaned:
        tube_row.append(row)
        tube_column.append(column)

        if am_settings.RotatedTractor:
            tmp = row
            row = column
            column = tmp

        if am_settings.Pattern == 0:
            if not am_settings.Rotated:
                tube_x.append(row * am_settings.Pitch + origin_x)
                tube_y.append(column * am_settings.Pitch + origin_y)
            else:
                tube_x.append(am_settings.Pitch * (1.414*row + 0.707 * column) + origin_x)
                tube_y.append(am_settings.Pitch * (0.707 * column) + origin_y)

        else:
            if not am_settings.Rotated:
                tube_x.append(am_settings.Pitch * (row + 0.5*column) + origin_x)
                tube_y.append(am_settings.Pitch * (0.866*column) + origin_y)
            else:
                tube_x.append(am_settings.Pitch * (1.732*row + 0.866*column) + origin_x)
                tube_y.append(am_settings.Pitch * (0.5*column) + origin_y)


# Parse every line in the file
for x in f:
    # Ensure first two characters are correct
    if x[0] == '_' and x[1] == '[':

        this_msg = Message()

        # Get the run time for the message and strip
        x = x[2:]
        this_msg.RunTime = float(x[:x.find(']')])/1000.0
        x = x[(x.find(']')+1):]

        # Get the major code and strip
        this_msg.Major = x[:x.find('.')]
        x = x[x.find('.')+1:]

        # Get the minor code and strip
        this_msg.Minor = x[:x.find('{')]
        x = x[x.find('{'):]

        # Remove ending new line character
        x = x.strip('\n')

        # Replace t/f w/ true/false
        x = x.replace(":t", ":true")
        x = x.replace(":f", ":false")

        # Try to decode into dictionary
        try:
            this_msg.Param = json.loads(x)
        except ValueError:
            print("Bad Line: " + x)
            break

        # Line was parsed, do processing here

        # Log the clamp pressure
        if this_msg.Major == 'PR' and this_msg.Minor == 'CL':
            clamp_time.append(this_msg.RunTime)
            clamp_pressure.append(this_msg.Param['p']/10)

        # Log the inlet pressure
        if this_msg.Major == 'PR' and this_msg.Minor == 'IN':
            inlet_time.append(this_msg.RunTime)
            inlet_pressure.append(this_msg.Param['p']/10)

        # Log the valve actuations (graphing and total)
        if this_msg.Major == 'VS' and this_msg.Minor == 'AC':
            valve_time[this_msg.Param['s']-1].append(this_msg.RunTime - (this_msg.Param['d']/1000.0))
            valve_time[this_msg.Param['s']-1].append(this_msg.RunTime)

            if this_msg.Param['v'] == 'A':
                valve_state[this_msg.Param['s']-1].append(0.5 + this_msg.Param['s']-1)
            else:
                valve_state[this_msg.Param['s']-1].append(-0.5 + this_msg.Param['s']-1)

            valve_state[this_msg.Param['s']-1].append(0 + this_msg.Param['s']-1)

            total_valve_time[this_msg.Param['s']-1][this_msg.Param['v']] += this_msg.Param['d']/1000.0

        # Log the bypass valve run time
        if this_msg.Major == 'VS' and this_msg.Minor == 'EN':
            if this_msg.Param['e']:
                valve_enable_time = this_msg.RunTime
            else:
                valve_on_time += this_msg.RunTime - valve_enable_time

        # Save the pattern configuration
        if this_msg.Major == 'SU' and this_msg.Minor == 'AM':
            am_settings.Status = this_msg.Param['s']
            am_settings.Pitch = this_msg.Param['p'] / 1000.0
            am_settings.Pattern = this_msg.Param['a']
            am_settings.Rotated = this_msg.Param['r']
            am_settings.RotatedTractor = this_msg.Param['t']

        # Save the AM Origin
        if this_msg.Major == 'AM' and this_msg.Minor == 'OG':
            origin_x = this_msg.Param['x'] / 1000.0
            origin_y = this_msg.Param['y'] / 1000.0

        # Save the lance selection
        if this_msg.Major == 'SU' and this_msg.Minor == 'LN':
            lances = this_msg.Param['l']

        # Save the tubes
        if this_msg.Major == 'AF' and this_msg.Minor == 'CL':
            feed_length = 0
            cleaned = 0

            if this_msg.Param['c'] & 0x01:
                clean_a_tube(this_msg.Param['r'] + 0, this_msg.Param['u'])
                feed_length += this_msg.Param['l']
                cleaned += 1

            if this_msg.Param['c'] & 0x02:
                clean_a_tube(this_msg.Param['r'] + 1, this_msg.Param['u'])
                feed_length += this_msg.Param['m']
                cleaned += 1

            if this_msg.Param['c'] & 0x04:
                if lances == 0x5:
                    clean_a_tube(this_msg.Param['r'] + 1, this_msg.Param['u'])
                else:
                    clean_a_tube(this_msg.Param['r'] + 2, this_msg.Param['u'])

                feed_length += this_msg.Param['n']
                cleaned += 1

            tube_time.append(this_msg.RunTime)
            tube_count.append(tube_count[-1] + cleaned)

            if cleaned > 0 and this_msg.Param['i'] > 0 and this_msg.Param['o'] > 0:
                feed_length /= cleaned
                feed_in_time.append(feed_length / this_msg.Param['i'])
                feed_out_time.append(feed_length / this_msg.Param['o'])

        # Update the total job run time
        job_time = this_msg.RunTime

print('Total Job Time: ' + str(job_time))

print('Total Valve Enable Time: ' + str(valve_on_time))

print('Tubes Cleaned: ' + str(len(tube_row)))

for idx, x in enumerate(total_valve_time):
    print('Valve ' + str(idx+1) + ' A: ' + str(x['A']) + ', B: ' + str(x['B']))

plt.step(tube_time, tube_count, where='post')
plt.title('Tube Count')
plt.xlabel('Time (s)')
plt.ylabel('Tubes (tubes)')
plt.show()

plt.scatter(tube_x, tube_y)
plt.title('Cleaned Tubes')
plt.xlabel('Horizontal (in)')
plt.ylabel('Vertical (in)')
plt.show()

plt.step(range(len(feed_in_time)), feed_in_time, where='post')
plt.step(range(len(feed_in_time)), feed_out_time, where='post')
plt.title('Feed In/Out Rates')
plt.xlabel('Clean (cycle)')
plt.ylabel('Rate (in/s)')
plt.show()

plt.step(inlet_time, inlet_pressure, where='post')
plt.title('Inlet')
plt.ylim(-2, 100)
plt.xlabel('Time (s)')
plt.ylabel('Pressure (PSI)')
plt.show()

plt.step(clamp_time, clamp_pressure, where='post')
plt.step(valve_time[4-1], [x-4+1 for x in valve_state[4-1]], where='post')
plt.title('Clamp')
plt.ylim(-2, 20)
plt.xlabel('Time (s)')
plt.ylabel('Pressure (PSI)')
plt.show()

for x in range(16):
    plt.step(valve_time[x], valve_state[x], where='post')
plt.title('Valves')
plt.xlabel('Time (s)')
plt.ylabel('Valve State')
plt.show()

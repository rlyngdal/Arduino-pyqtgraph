# Arduino-pyqtgraph
Display serial-data from an Arduino with python pyqtgraph 

The current code shows displacement data in a pyqtgraph-plot 
-measured with an arduino with an attached Ultrasonic Distance Sensor Module-

Basically I have struggled somewhat with getting measured data  from Arduino presented in a nice way.
Now I have a reasonably good way of doing it - and thought it would be worth to share to save time for others. But feel free to improve.

To get the code working there are a few steps / depencies
1. Install the Arduino-software
2. Get the Arduino NewPing library
3. Install Anaconda2 (Includes the pyqtgraph library and some other useful ones)
4. Get the Arduino Harware. I have an Arduino UNO conneted to a low cost Ultrasonic Distance Sensor Module
5. Now your ready to display the measured data.

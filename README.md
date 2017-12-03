# OrbBit - look a bit into the future

The OrbBit API is a means, not an end. It's a development accelerator for the robots that perform analysis and automatic trading.

It contains all the functions that:
 - May be used by several robots, so that they are implemented only once. 
 - Optimize operation of the robots, like data acquisition, which has to be done only once for all the robots.

Because it's developed in python, it takes advantage of a huge amount of resources readily available; then, each block presents a standard REST API through a socket. That allows for the robots to be implemented in any language that supports sockets. Development of the robots is this way focused on the algorithm only.


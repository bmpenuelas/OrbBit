#!/usr/bin/python3

import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class order_follow (threading.Thread):
    """Follow current trend and execute at the best spot.

    When selling it will wait for the peak, conversely on buys it will
    wait to reach the bottom. 

    Args:
        orderID (int): Order identifier (Do not repeat.)
        buysell (str): Order type. Valid options are "buy", "sell"
        m_a_samples (int): Moving average sample number. Icrease for
                           smoother curves at the cost of delayed signals.
        hysteresis (float): Avoid repeated orders within this band.
        wait_hyst_exit (bool): Do not execute order until hystereis band 
                               is exited in the opposite direction than it 
                               was entered. This avoids oders executed on 
                               small spikes.

    Attributes:
    """
        
    def __init__(self, orderID, buysell, volume, m_a_samples, hysteresis=0.0, wait_hyst_exit=False ):
        if (buysell!="buy" and buysell!="sell"):
            raise ValueError("ERR: Wrong order type.")
        if m_a_samples<=0:
            raise ValueError("ERR: Invalid Moving Average sample number.")

        threading.Thread.__init__(self)
        self.orderID = orderID
        self.buysell = buysell
        self.buy = 1 if buysell=="buy" else 0
        self.volume = volume
        self.direction = -1 if buysell=="buy" else 1
        self.m_a_samples = m_a_samples
        self.hysteresis = hysteresis


    def run(self):
        print ("Starting Order: " + self.name + self.buysell + "in FOLLOW mode.")

        slope_chg_val = self.det_slope_chg()
        # \todo when working: Execute order for volume units
        print("EXECUTED " + self.buysell + " with ID: " + self.orderID + " @ " + slope_chg_val) 

        print ("Exiting Order: " + self.name)


    def det_slope_chg(self):
        ##temporary
        data = pd.read_csv('../data/Data_HitBtc_XRPUSD_1t.csv', header=0)
        data['avg'] = (data['open'] + data['high'] + data['low'] + data['close']) / 4
        
        data = data.sort_values(by=['date'])
        data.index = range(len(data))
        
        plt.figure(1)
        plt.plot(data['date'], data['avg'])

        samples_vect = data['avg'][1]
        print( samples_vect )
        ##temporary

        #fetch ma samps + 1
        i = 0
        prev_val = np.mean( samples_vect[i:self.m_a_samples+i] )
        i += 1
        curr_val = np.mean( samples_vect[i:self.m_a_samples+i] )
        curr_slope = curr_val - prev_val

        while not( (curr_slope / self.direction) == 1 ):
            i += 1
            curr_val = np.mean( samples_vect[i:self.m_a_samples+i] )
            curr_slope = curr_val - prev_val
            prev_val = curr_val



#############################################################################
#                          MATH OPERATIONS                                  #
#############################################################################

class EMA():
    """ Calculate new EMA value from current value and a window of prev vals.
    """
    def __init__(self, value, window):
        self.window = window
        self.weights = np.exp(np.linspace(-1., 0., window))
        self.weights /= self.weights.sum()
        self.values = np.linspace(value, value, window)

    def updt(new_val):
        self.values = self.values[:-1].append(new_val)
        a =  np.convolve(self.values, self.weights, mode='full')[:len(self.values)]
        a[:window] = a[window]
        return a[-1]


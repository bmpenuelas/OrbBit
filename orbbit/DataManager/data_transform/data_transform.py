
import numpy as np


#############################################################################
#                                INDICATORS                                 #
#############################################################################

#%%--------------------------------------------------------------------------
# EMA
#----------------------------------------------------------------------------

def EMA_tick(window_size, values):
    """ EMA one value at a time.

    Args:
        window_size (int) EMA sample number
        values (list) len must be equal to window_size
    Returns:
        EMA (double) current EMA value
    """
    if len(values) != window_size:
        raise ValueError('Value len and window_size do not match.')

    weights = np.exp(np.linspace(-1., 0., window_size))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    return a[-1]


def EMA_history(window_size, values):
    """ EMA for complete history.
    
    Args:
        window_size (int) EMA sample number
        values (list) len must be greater than window_size
    Returns:
        EMA (array double) complete EMA history
    """
    weights = np.exp(np.linspace(-1., 0., window_size))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window_size] = a[window_size]
    return a



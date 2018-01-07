
import numpy as np


#############################################################################
#                                INDICATORS                                 #
#############################################################################

#%%--------------------------------------------------------------------------
# EMA
#----------------------------------------------------------------------------

def EMA_tick(window, values):
    """ EMA one value at a time.

    Args:
        window (int) EMA sample number
        values (list) len must be equal to window
    Returns:
        EMA (double) current EMA value
    """
    if len(values) != window:
        raise ValueError('Value len and window do not match.')

    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    return a[-1]


def EMA_history(window, values):
    """ EMA for complete history.
    
    Args:
        window (int) EMA sample number
        values (list) len must be greater than window
    Returns:
        EMA (array double) complete EMA history
    """
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a



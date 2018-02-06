
import numpy as np


#############################################################################
#                                INDICATORS                                 #
#############################################################################

#%%--------------------------------------------------------------------------
# EMA
#----------------------------------------------------------------------------

def EMA_tick(n_periods, current_value, previous_ema):
    """ EMA one value at a time.

    Args:
        n_periods (int) EMA sample number
        current_value

    Returns:
        EMA (double) current EMA value

    """

    most_recent_weight = 2 / (n_periods + 1)
    return (current_value - previous_ema) * most_recent_weight + previous_ema


def EMA_history(n_periods, values):
    """ EMA for complete history.
    
    Args:
        n_periods (int) EMA sample number
        values (list) len must be greater than n_periods

    Returns:
        EMA (array double) complete EMA history

    """

    ema = [values[0]]
    for i in range(1,len(values)):
      ema.append( EMA_tick(n_periods, values[i], ema[i-1]) )

    return ema



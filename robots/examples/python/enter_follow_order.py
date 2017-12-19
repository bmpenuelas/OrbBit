

import orbbit as orb



# Create order in a separate thread
oder1 = orb.order_follow(1, 'buy', 0.001, 10)
oder1.start()

# Wait for completion
oder1.join()
print ("Execution finalized.")

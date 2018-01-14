# #!/usr/bin/python3
# #!/usr/bin/python3

# import sys
# from   pkg_resources  import resource_filename
# import time
# import threading
# import queue
# import numpy as np
# import socket
# from   flask          import Flask, jsonify, abort, make_response, request
# from   flask_httpauth import HTTPBasicAuth
# import ccxt
# import pymongo
# import json

# # from   orbbit.OrderManager.data_transform.data_transform import *




# #%%##########################################################################
# #                              DATAMANAGER API                              #
# #############################################################################

# #----------------------------------------------------------------------------
# # Flask App error funcs redefinition
# #----------------------------------------------------------------------------

# app = Flask(__name__)

# @app.errorhandler(404)
# def not_found(error):
#     return make_response(jsonify({'error': 'Not found'}), 404)

# @app.errorhandler(400)
# def bad_request(error):
#     return make_response(jsonify({'error': 'Bad request'}), 400)



# #----------------------------------------------------------------------------
# # AUTHENTICATION
# #----------------------------------------------------------------------------

# auth = HTTPBasicAuth()
# """ Add @auth.login_required to a route/method definition to make it
#     password-protected.
# """

# @auth.get_password
# def get_password(username):
#     if username == 'rob':
#         return 'bot'
#     return None

# @auth.error_handler
# def unauthorized():
#     return make_response(jsonify({'error': 'Unauthorized access'}), 401)




# #----------------------------------------------------------------------------
# # ROUTES AND METHODS
# #----------------------------------------------------------------------------
# #----------------------------------------------------------------------------
# #   Route /datamanager
# #----------------------------------------------------------------------------

# @app.route('/ordermanager', methods=['GET'])
# def datamanager_status():
#     """ Get datamanager status.
#     Args:

#     Returns:
#         Status of the DataManager API and processes.
#     """

#     return jsonify({'a': 'aaaaa'})



# #%%--------------------------------------------------------------------------
# # PUBLIC METHODS
# #----------------------------------------------------------------------------

# class OrderManager_API (threading.Thread):
#     def __init__(self, threadID):
#         threading.Thread.__init__(self)
#         self.threadID = threadID

#     def run(self):
#         print('OrderManager_API STARTED with threadID ' + self.name)
#         app.run(debug=False)
#         print('OrderManager_API STOPPED with threadID ' + self.name)


# thread_OrderManager_API = OrderManager_API('thread_OrderManager_API')


# def start_API():
#     """ Start OrderManager API Server
#     Starts in a separate subprocess.

#     Args:

#     Returns:
#     """
#     print("Starting OrderManager API Server.")
#     thread_OrderManager_API.start()


# #----------------------------------------------------------------------------
# # Script mode
# #----------------------------------------------------------------------------
# if __name__ == '__main__':
#     print("OrderManager in script mode.")
#     start_API()

import sys
import subprocess

from   flask import Flask, jsonify, abort, make_response, request
from   flask_httpauth import HTTPBasicAuth

import ccxt


#----------------------------------------------------------------------------
# EXCHANGES SETUP
#----------------------------------------------------------------------------

hitbtc = ccxt.hitbtc({'verbose': False})
  
def print_markets():
  hitbtc_markets = hitbtc.load_markets()
  print(hitbtc.id, hitbtc_markets)


def fetch_ticker():
  hitbtc = ccxt.hitbtc({'verbose': False})
  return hitbtc.fetch_ticker('BTC/USD')








#----------------------------------------------------------------------------
# Flask App error funcs redefinition  
#----------------------------------------------------------------------------

app = Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)



#----------------------------------------------------------------------------
# AUTHENTICATION
#----------------------------------------------------------------------------

auth = HTTPBasicAuth()
""" Add @auth.login_required to a route/method definition to make it 
    password-protected.
"""

@auth.get_password
def get_password(username):
    if username == 'rob':
        return 'bot'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)



#----------------------------------------------------------------------------
# ROUTES AND METHODS
#----------------------------------------------------------------------------
#\todo Implement as real DB instead of memory

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]




#----------------------------------------------------------------------------
# ROUTES AND METHODS
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
#   Route /datamanager
#----------------------------------------------------------------------------

@app.route('/datamanager', methods=['GET'])
def get_data():
  """ Get all data.
  Return all data available in json format.

  Args:


  Returns:
    Json-formatted data.

  """
  return jsonify({'tasks': tasks})


@app.route('/datamanager/<int:task_id>', methods=['GET'])
def get_task(task_id):
  task = [task for task in tasks if task['id'] == task_id]
  if len(task) == 0:
      abort(404)
  return jsonify({'task': task[0]})


@app.route('/datamanager', methods=['POST'])
def create_task():
  if not request.json or not 'title' in request.json:
      print(request.json)
      abort(400)
  task = {
      'id': tasks[-1]['id'] + 1,
      'title': request.json['title'],
      'description': request.json.get('description', ""),
      'done': False
  }
  tasks.append(task)
  return jsonify({'task': task}), 201


@app.route('/datamanager/<int:task_id>', methods=['PUT'])
def update_task(task_id):
  task = [task for task in tasks if task['id'] == task_id]
  if len(task) == 0:
      abort(404)
  if not request.json:
      abort(400)
  if 'title' in request.json and type(request.json['title']) != unicode:
      abort(400)
  if 'description' in request.json and type(request.json['description']) is not unicode:
      abort(400)
  if 'done' in request.json and type(request.json['done']) is not bool:
      abort(400)
  task[0]['title'] = request.json.get('title', task[0]['title'])
  task[0]['description'] = request.json.get('description', task[0]['description'])
  task[0]['done'] = request.json.get('done', task[0]['done'])
  return jsonify({'task': task[0]})


@app.route('/datamanager/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
  task = [task for task in tasks if task['id'] == task_id]
  if len(task) == 0:
      abort(404)
  tasks.remove(task[0])
  return jsonify({'result': True})



#----------------------------------------------------------------------------
#   Route /ticker
#----------------------------------------------------------------------------

@app.route('/ticker', methods=['GET'])
def get_ticker():
  """ Get BTC/USD ticker info.

  Args:


  Returns:
    Json-formatted data.

  """
  return jsonify({'ticker': fetch_ticker()})




#----------------------------------------------------------------------------
# MAIN
#----------------------------------------------------------------------------

def start():
  """ Start DataManager API Server
  Starts in a separate subprocess.

  Args:

  Returns:
    Subprocess ID.
  """

  child = subprocess.Popen([sys.executable, './DataManager.py'])
  return child

if __name__ == '__main__':
  print("Starting API Server.")
  app.run(debug=True)
else:
  print("Imported Orbbit.")

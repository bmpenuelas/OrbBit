clc
addpath ../../../../matlab-json
json.startup

api = 'http://127.0.0.1:5000/datamanager/get/';

figure(1)
while 1
  response = webread(api);
  y = [y response.ticker.last]
  plot(y, '-ob')
  x = x+1;
  pause (3)
end


import dataset


db = dataset.connect('mysql://0rb1t4ant3s:p1cKl3r1CKy8a12l@localhost/MySQLorbbit')


table = db['user']

# Insert a new record.
table.insert(dict(name='John Doe', age=46, country='China'))

# dataset will create "missing" columns any time you insert a dict with an unknown key
table.insert(dict(name='Jane Doe', age=37, country='France', gender='female'))
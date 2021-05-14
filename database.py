from walrus import *


def open_db():
    return Database(host='localhost', port=6379, db=0)


# TODO: add interaction with redis
#

if __name__ == '__main__':
    db = open_db()
    db['walrus'] = 'tusk'
    print(db['walrus'])



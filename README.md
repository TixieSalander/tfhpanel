Tux-FreeHost Panel
==================

There is no *complete* documentation yet. However,
you can [follow](https://twitter.com/tuxfreehost) the project on twitter,
read [the blog](http://tux-fh.net/posts.html), post in
[the forum](http://forum.tux-fh.net), or come chat with us on #TuxFH @ Freenode.

To install the panel
--------------------
Manually :
```bash
PATH="~/.local/bin/:$PATH" # If it's not already done yet
python3 setup.py install

# Create a SQLite DB and fill it with default data
python3 tfh.py -c development.ini initdb

# Start the web application
pserve development.ini
```
<<<<<<< HEAD
Moreover, you can use the installation/management [scripts](https://gist.github.com/Edelwin/7857978).
=======
Or with a little script by Edelwin : https://gist.github.com/Edelwin/7857978
>>>>>>> upstream/master

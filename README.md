Tux-FreeHost Panel
=======

There is no *complete* documentation yet. However, you can [follow](https://twitter.com/tuxfeehost) the project on twitter, read [the blog](http://tux-fh.net/posts.html) and write in [the forum](http://forum.tux-fh.net).

To install the panel
--------------------
```
su -c "python3 setup.py install"
python3 setup.py develop --user
python3 tfh.py -c development.ini initdb
PATH="~/.local/bin/:$PATH" # If it's not done yet
pserve development.ini
```


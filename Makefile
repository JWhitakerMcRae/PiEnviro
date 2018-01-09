all:
	git remote add resin whitaker@git.resin.io:info_gooee/pienviro.git

install:
	git push -f resin HEAD:master

clean:
	git remote rm resin
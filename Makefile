all: clean
	git init resin_pkg
	cp -rp Dockerfile start.sh scripts resin_pkg
	cd resin_pkg && git add . && git commit -m "Commit for new Resin build."
	cd resin_pkg && git remote add resin g_j_whitaker_mcrae@git.resin.io:g_j_whitaker_mcrae/pienviro.git

install:
	cd resin_pkg && git push -f resin master

clean:
	rm -rf resin_pkg
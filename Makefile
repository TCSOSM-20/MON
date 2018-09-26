all: clean package

clean:
	rm -rf dist deb_dist osm_mon-*.tar.gz osm_mon.egg-info .eggs

package:
	python3 setup.py --command-packages=stdeb.command sdist_dsc
	cp debian/python3-osm-mon.postinst deb_dist/osm-mon*/debian
	cd deb_dist/osm-mon*/  && dpkg-buildpackage -rfakeroot -uc -us
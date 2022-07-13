try:
	from setuptools import setup, find_packages
except ImportError:
	from ez_setup import use_setuptools
	use_setuptools()
	from setuptools import setup, find_packages

setup(
	name='endotools',
	version="",
	install_requires=["Pylons>=0.9.6.1"],
	packages=find_packages(exclude=['ez_setup']),
	include_package_data=True,
	test_suite='nose.collector',
	package_data={'endotools': ['i18n/*/LC_MESSAGES/*.mo']},
	message_extractors = {'endotools': [
			('**.py', 'python', None),
			('templates/**.mako', 'mako', None),
			('public/webapp/**.js', 'javascript', None),
			('public/webapp/**.html', 'html', None)
	]},
	entry_points="""
	[babel.extractors]
	html = endotools.lib.babel_extract_html:extract_html

	[paste.app_factory]
	main = endotools.config.middleware:make_app

	[paste.app_install]
	main = pylons.util:PylonsInstaller
	"""
)
try:
    # 1.0
    from paver.easy import path as paver_path
    from paver.easy import sh as paver_sh
    from paver.easy import *
    import paver.misctasks
    from paver import setuputils
    setuputils.install_distutils_tasks()
    PAVER_VER = '1.0'
except ImportError:
    # 0.8
    from paver.defaults import *
    from paver.runtime import path as paver_path
    from paver.runtime import sh as paver_sh
    PAVER_VER = '0.8'

import sys, os
import glob
import paver.doctools
from setuptools import find_packages, command

sys.path.insert(0, str(paver_path.getcwd()))

from fedora.release import *

options(
    setup = Bunch(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        license=LICENSE,
        keywords='Fedora Python Modules',
        url=URL,
        download_url=DOWNLOAD_URL,
        packages=find_packages(),
        include_package_data=True,
        # non-setuptools package.  When everything we care about uses
        # python-2.5 distutils we can add these:
        #   for bodhi (koji yum)
        install_requires=['simplejson'],
        # And these to extra_require:
        #   for widgets: (bugzilla feedparser)
        extras_require = {'tg' : ['TurboGears >= 1.0.4', 'SQLAlchemy',
            'decorator']},
        entry_points = {
            'turbogears.identity.provider' : (
                'jsonfas = fedora.tg.identity.jsonfasprovider1:JsonFasIdentityProvider [tg]',
                'jsonfas2 = fedora.tg.identity.jsonfasprovider2:JsonFasIdentityProvider [tg]'),
            'turbogears.visit.manager' : (
                'jsonfas = fedora.tg.visit.jsonfasvisit1:JsonFasVisitManager [tg]',
                'jsonfas2 = fedora.tg.visit.jsonfasvisit2:JsonFasVisitManager [tg]'),
            },
        message_extractors = {
            'fedora': [('**.py', 'python', None),
                ('tg/templates/genshi/**.html', 'genshi', None),],
            },
        classifiers = [
            'Development Status :: 4 - Beta',
            'Framework :: TurboGears',
            'Framework :: Django',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU General Public License (GPL)',
            'Programming Language :: Python :: 2.4',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Software Development :: Libraries :: Python Modules',
            ],
        ),
    sphinx=Bunch(
        docroot='.',
        builddir='build-doc',
        sourcedir='doc'
        ),
    pylint=Bunch(
        module=['fedora']
        ),
    publish=Bunch(
        doc_location='fedorahosted.org:/srv/web/releases/p/y/python-fedora/doc/',
        tarball_location='fedorahosted.org:/srv/web/releases/p/y/python-fedora/'
        ),
    i18n=Bunch(
        builddir='locale',
        installdir='/usr/share/locale',
        domain='python-fedora',
        ),
    )

@task
@needs(['html'])
def publish_doc():
    options.order('publish', add_rest=True)
    command = 'rsync -av build-doc/html/ %s' % (options.doc_location,)
    dry(command, paver_sh, [command])

@task
@needs(['sdist'])
def publish_tarball():
    options.order('publish', add_rest=True)
    tarname = '%s-%s.tar.gz' % (options.name, options.version)
    command = 'scp dist/%s %s' % (tarname, options.tarball_location)
    dry(command, paver_sh, [command])

@task
@needs(['publish_doc', 'publish_tarball'])
def publish():
    pass

try:
    import babel.messages.frontend
    has_babel = True
except ImportError:
    has_babel = False

if has_babel:
    @task
    def make_catalogs():
        '''Compile all message catalogs for release'''
        options.order('i18n', add_rest=True)
        for po_file in glob.glob('po/*.po'):
            locale, ext = os.path.splitext(os.path.basename(po_file))
            build_dir = paver_path(os.path.join(options.builddir, locale,
                'LC_MESSAGES'))

            try:
                build_dir.makedirs(mode=0755)
            except OSError, e:
                # paver < 1.0 raises if directory exists
                if e.errno == 17:
                    pass
                else:
                    raise
            if 'compile_catalog' in options.keys():
                defaults = options.compile_catalog
            else:
                defaults = Bunch(domain=options.domain,
                        directory=options.builddir)
                options.compile_catalog = defaults

            defaults.update({'input-file': po_file, 'locale': locale})
            ### FIXME: compile_catalog cannot handle --dry-run on its own
            dry('paver compile_catalog -D %(domain)s -d %(directory)s'
                    ' -i %(input-file)s --locale %(locale)s' % defaults,
                    call_task, 'babel.messages.frontend.compile_catalog')

def _install_catalogs(args):
    '''Install message catalogs in their proper location on the filesystem.

    Note: To use this with non-default commandline arguments, you must use 
    '''
    # Rebuild message catalogs
    if 'skip_build' not in args:
        call_task('make_catalogs')

    options.order('i18n', add_rest=True)
    # Setup the install_dir
    if 'install_catalogs' in args:
        cat_dir = args['install_catalogs']
    elif 'install_data' in args:
        cat_dir = os.path.join(args['install_data'], 'locale')
    else:
        cat_dir = options.installdir

    if 'root' in args:
        if cat_dir.startswith('/'):
            cat_dir = cat_dir[1:]
        cat_dir = paver_path(os.path.join(args['root'], cat_dir))

    for catalog in paver_path(options.builddir).walkfiles('*.mo'):
        locale_dir = catalog.dirname()
        path = paver_path('.')
        for index, nextpath in enumerate(locale_dir.splitall()):
            path = path.joinpath(nextpath)
            if paver_path(options.builddir).samefile(path):
                install_locale = cat_dir.joinpath(os.path.join(
                        *locale_dir.splitall()[index + 1:]))
                try:
                    install_locale.makedirs(mode=0755)
                except OSError, e:
                    # paver < 1.0 raises if directory exists
                    if e.errno == 17:
                        pass
                    else:
                        raise
                install_locale = install_locale.joinpath(catalog.basename())
                if install_locale.exists():
                    install_locale.remove()
                catalog.copy(install_locale)
                install_locale.chmod(0644)

@task
@cmdopts([('root=', None, 'Base root directory to install into'),
    ('install-catalogs=', None, 'directory that locale catalogs go in'),
    ('skip-build', None, 'Skip directly to installing'),
    ])
def install_catalogs():
    _install_catalogs(options.install_catalogs)
    pass

@task
@needs(['make_catalogs', 'setuptools.command.sdist'])
def sdist():
    pass

if PAVER_VER != '0.8':
    # Paver 0.8 will have to explicitly install the message catalogs
    @task
    @needs(['setuptools.command.install'])
    def install():
        '''Override the setuptools install.'''
        _install_catalogs(options.install)

#
# Generic Tasks
#

try:
    from pylint import lint
    has_pylint = True
except ImportError:
    has_pylint = False

if has_pylint:
    @task
    def pylint():
        '''Check the module you're building with pylint.'''
        options.order('pylint', add_rest=True)
        pylintopts = options.module
        dry('pylint %s' % (" ".join(pylintopts)), lint.Run, pylintopts)


